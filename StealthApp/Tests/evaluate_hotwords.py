"""Opt-in local ASR comparison. Uses synthetic speech, no credentials or cloud calls.
Run with --executable <worker> --zipformer <model dir> --paraformer <model dir>
--output <directory> [--realtime]. Timings exclude cold model loading; first/final
latency includes PCM delivery, VAD, native inference and IPC, not UI rendering.
"""
import argparse
import base64
import json
from pathlib import Path
import statistics
import subprocess
import time
import wave
from reproduce_trigger_asr import Worker


def feed(worker, pcm, realtime=False, halfway=None):
    times, segments = [], []
    first, final, updated = None, None, False
    started = time.perf_counter()
    for offset in range(0, len(pcm), 3200):
        delivery = (offset + min(3200, len(pcm) - offset)) / 32000
        if realtime:
            time.sleep(max(0, started + delivery - time.perf_counter()))
        if halfway and offset >= len(pcm) // 2 and not updated:
            halfway(); updated = True
        before = time.perf_counter()
        value = worker.call(op='audio', pcm=base64.b64encode(pcm[offset:offset + 3200]).decode())
        elapsed = time.perf_counter() - before
        times.append(elapsed * 1000)
        latency = (time.perf_counter() - started) * 1000 if realtime else delivery * 1000 + elapsed * 1000
        if value.get('partial') and first is None:
            first = latency
        if value.get('segments'):
            final = latency
        segments.extend(value.get('segments', []))
    segments.extend(worker.call(op='flush').get('segments', []))
    return dict(text=''.join(s['text'] for s in segments), mean_inference_ipc_ms=statistics.mean(times),
                p95_inference_ipc_ms=sorted(times)[int(len(times) * .95)], max_inference_ipc_ms=max(times),
                first_partial_ms=first, final_ms=final, rtf=sum(times) / (len(pcm) / 32))


def main():
    p = argparse.ArgumentParser()
    for flag in ['executable', 'zipformer', 'paraformer', 'output']:
        p.add_argument('--' + flag, required=True)
    p.add_argument('--realtime', action='store_true')
    args = p.parse_args()
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    cases = ['我们使用 React 和 TypeScript 开发前端。', '这个项目用了 Vue 和 Next.js。',
             '我们用 PyTorch 训练模型，再通过 Kubernetes 部署。', '请介绍一下 LiveCopilot 的架构。',
             '今天下午三点开会，讨论项目进度。']
    # Same spoken forms as the app's punctuation-to-space normalization.
    terms = ['VUE', 'REACT', 'TYPESCRIPT', 'NEXT JS', 'PYTORCH', 'KUBERNETES', 'LIVECOPILOT']
    audio, results = [], []
    for i, sentence in enumerate(cases):
        path = root / f'{i}.wav'
        if not path.exists():
            subprocess.run(['say', '-v', 'Tingting', '-r', '180', '-o', str(path),
                            '--file-format=WAVE', '--data-format=LEI16@16000', sentence], check=True)
        with wave.open(str(path)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
            pcm = bytes(16000) + w.readframes(w.getnframes()) + bytes(32000)
        audio.append(pcm)
        for mode, enabled in [('paraformer', False), ('zipformer', False), ('zipformer', True)]:
            worker = Worker([args.executable, mode, getattr(args, mode)])
            try:
                if mode == 'zipformer': worker.call(op='terms', terms=terms if enabled else [])
                row = dict(input=sentence, mode=mode, enabled=enabled, **feed(worker, pcm, args.realtime))
            finally: worker.close()
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
            (root / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    # Change terms during an utterance. Its result must stay identical to the off
    # run, while the next utterance must match the on run, without worker restart.
    worker = Worker([args.executable, 'zipformer', args.zipformer])
    try:
        first = feed(worker, audio[0], halfway=lambda: worker.call(op='terms', terms=terms))
        second = feed(worker, audio[0])
        assert first['text'] == results[1]['text'], (first, results[1])
        assert second['text'] == results[2]['text'], (second, results[2])
        worker.call(op='terms', terms=[])
        third = feed(worker, audio[0])
        assert third['text'] == results[1]['text']
        assert results[1]['text'] != results[2]['text'], 'This fixture must prove an actual decoding effect'
    finally: worker.close()
    (root / 'boundary.json').write_text(json.dumps(dict(mid_utterance=first['text'], next_utterance=second['text'], disabled_again=third['text'], passed=True), ensure_ascii=False, indent=2))
    print('PASS: native hotwords change decoding; edits wait for segment boundaries; disabling restores baseline.', flush=True)


if __name__ == '__main__':
    main()
