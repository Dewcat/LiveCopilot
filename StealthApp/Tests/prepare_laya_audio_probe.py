#!/usr/bin/env python3
"""Generate synthetic speech and replay a real local ASR worker, without a mic/API.

This is an extra integration probe, not an independent population benchmark.
Store audio in local-data; metadata may be saved in validation evidence.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import wave
from reproduce_trigger_asr import Worker

CASES = [
    ('第一项工作你展开说说', True),
    ('他让我把第一项工作展开说说', False),
    ('这题先不问了，等我想好再说', False),
    ('换一道题，请解释系统出错后怎么恢复', True),
    ('能不能说明这个系统在', False),
    ('能不能说明这个系统在断线后怎样恢复', True),
    ('请你介绍当资源不足时怎样', True),
    ('请你介绍当资源不足时怎样安排任务', True),
    ('她当时问我为什么要把顺序调换', False),
    ('我也想知道为什么要把顺序调换', True),
    ('先别讲理由，今天就到这里', False),
    ('先别讲背景，只说结果', True),
    ('He asked me to describe the first project.', False),
    ('Could you describe the first project?', True),
    ('How would you keep the system running when the', True),
    ('How would you keep the system running when the connection fails?', True),
]


def main():
    p = argparse.ArgumentParser()
    for name in ['executable', 'model', 'audio', 'output']:
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.audio.exists():
        raise SystemExit('Refusing to overwrite an existing probe')
    args.audio.mkdir(parents=True)
    rows = []
    for i, (text, respond) in enumerate(CASES):
        path = args.audio / f'{i}.wav'
        voice = 'Tingting' if i < 12 else 'Samantha'
        subprocess.run(['/usr/bin/say', '-v', voice, '-r', '180', '-o', str(path),
                        '--file-format=WAVE', '--data-format=LEI16@16000', text], check=True)
        with wave.open(str(path)) as f:
            assert (f.getframerate(), f.getnchannels(), f.getsampwidth()) == (16000, 1, 2)
            pcm = bytes(16000) + f.readframes(f.getnframes()) + bytes(64000)
        worker = Worker([str(args.executable), 'zipformer', str(args.model)])
        segments, previews = [], []
        try:
            worker.call(op='terms', terms=[])
            for start in range(0, len(pcm), 3200):
                value = worker.call(op='audio', pcm=base64.b64encode(pcm[start:start+3200]).decode())
                segments.extend(value.get('segments', []))
                partial = value.get('partial', '')
                if partial and (not previews or previews[-1] != partial):
                    previews.append(partial)
            segments.extend(worker.call(op='flush').get('segments', []))
        finally:
            worker.close()
        row = dict(id=f'audio-{i}', spoken=text, respond=respond, text=''.join(s['text'] for s in segments),
                   segments=segments, partials=previews, voice=voice,
                   context=dict(currentSpeaker='Room', recentTurns=[]))
        rows.append(row)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k: row[k] for k in ['id', 'spoken', 'text', 'respond']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
