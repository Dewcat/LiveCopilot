#!/usr/bin/env python3
"""Replay a predeclared held-out subset through local TTS and native Zipformer.

No Laya scoring, microphone, user recordings or network requests occur here.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import wave

from reproduce_trigger_asr import Worker


def main():
    p=argparse.ArgumentParser()
    for name in ['fixtures','executable','model','audio','output']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--selection',choices=['legacy-ordinals','two-per-language','all'],default='legacy-ordinals')
    a=p.parse_args()
    if a.output.exists() or a.audio.exists(): raise SystemExit('Refusing to replace probe evidence')
    cases=json.loads(a.fixtures.read_text())
    # Select by stable ordinal before any semantic scores, two per category.
    if a.selection == 'all':
        selected=cases
        assert len(selected)==len({c['id'] for c in selected}) and selected
    elif a.selection == 'legacy-ordinals':
        selected=[c for c in cases if int(c['id'].rsplit('-',1)[1]) in [0,17]]
        assert len(selected)==16 and len({c['category'] for c in selected})==8
    else:
        selected=[]
        for category in dict.fromkeys(c['category'] for c in cases):
            for chinese in [True,False]:
                group=[c for c in cases if c['category']==category
                       and any('\u4e00'<=x<='\u9fff' for x in c['text'])==chinese]
                assert len(group)>=2,category
                selected.extend(group[:2])
        assert len(selected)==32
    a.audio.mkdir(parents=True)
    rows=[]
    for c in selected:
        path=a.audio/(c['id']+'.wav')
        voice='Tingting' if any('\u4e00'<=x<='\u9fff' for x in c['text']) else 'Samantha'
        subprocess.run(['/usr/bin/say','-v',voice,'-r','180','-o',str(path),
                        '--file-format=WAVE','--data-format=LEI16@16000',c['text']],check=True)
        with wave.open(str(path)) as f:
            assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
            pcm=bytes(16000)+f.readframes(f.getnframes())+bytes(64000)
        worker=Worker([str(a.executable),'zipformer',str(a.model)])
        segments=[];partials=[]
        try:
            worker.call(op='terms',terms=[])
            for start in range(0,len(pcm),3200):
                value=worker.call(op='audio',pcm=base64.b64encode(pcm[start:start+3200]).decode())
                segments.extend(value.get('segments',[]))
                partial=value.get('partial','')
                if partial and (not partials or partials[-1]!=partial): partials.append(partial)
            segments.extend(worker.call(op='flush').get('segments',[]))
        finally: worker.close()
        rows.append(dict(id=c['id'],spoken=c['text'],respond=c['respond'],text=''.join(s['text'] for s in segments),
                         segments=segments,partials=partials,context=c['context'],voice=voice,
                         audio_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         fixture_sha256=hashlib.sha256(a.fixtures.read_bytes()).hexdigest()))
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        print(c['id'],rows[-1]['text'],flush=True)


if __name__=='__main__':main()
