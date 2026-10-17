#!/usr/bin/env python3
"""Run one local training command with durable process and exit metadata.

This supervisor is launched in its own session, so a tool observation ending
cannot kill the experiment. It never retries, selects a model, or installs it.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args()
    spec=json.loads(a.spec.read_text());status=Path(spec['status']);log=Path(spec['log'])
    if status.exists() or log.exists():raise SystemExit('Refusing to replace job evidence')
    state=dict(status='starting',supervisor_pid=os.getpid(),started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=spec['command'],cwd=spec['cwd'],log=str(log))
    def write():
        temporary=status.with_suffix('.tmp');temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(status)
    write()
    with log.open('w') as output:
        child=subprocess.Popen(spec['command'],cwd=spec['cwd'],stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        state.update(status='running',pid=child.pid);write()
        # Keep an explicitly running local compute job from idle sleep; this
        # assertion ends automatically with the training process.
        wake=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(child.pid)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        code=child.wait()
        state.update(status='completed' if code==0 else 'failed',exit_code=code,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat());write()
        try:wake.wait(timeout=3)
        except subprocess.TimeoutExpired:wake.terminate()

if __name__=='__main__':main()
