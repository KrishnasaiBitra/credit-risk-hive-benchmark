"""Smoke-check benchmark code paths separately from the reported five-run experiment."""
from pathlib import Path
from datetime import datetime, timezone
import json
import argparse
import subprocess
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--resume',type=Path,help='Continue a saved smoke-check run without rerunning completed checks')
args=parser.parse_args()
project=Path(__file__).resolve().parents[1]
folder=args.resume.resolve() if args.resume else project/'results/reproducibility'/('harness_checks_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
if not args.resume:
    folder.mkdir(parents=True,exist_ok=False)
status=json.loads((folder/'checks.json').read_text()) if args.resume else dict(status='running',scope='New benchmark harness smoke checks; original published measurements are retained.',checks=[])
status['status']='running'
status.pop('error',None)
manifest=folder/'checks.json'
def save():
    manifest.write_text(json.dumps(status,indent=2))
save()
def run(name,args):
    if any(check['name']==name and check['exit_code']==0 for check in status['checks']):
        print('Already passed: '+name,flush=True)
        return
    print('\nCHECK: '+name,flush=True)
    command=[sys.executable,*map(str,args)]
    with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=project,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in process.stdout:
            print(line,end='',flush=True); log.write(line); log.flush()
        code=process.wait()
    status['checks'].append(dict(name=name,command=command,exit_code=code)); save()
    if code:
        raise RuntimeError(name+' failed; see log.')
try:
    run('exports',[project/'src/benchmark_pipelines.py','--repeats','1'])
    run('resources',[project/'src/benchmark_pipelines.py','--monitor','--repeats','1','--skip-initial'])
    candidates=[p for p in (project/'results/reproducibility').glob('resources*/*')
                if p.is_dir() and (p/'configuration.json').exists()
                and json.loads((p/'configuration.json').read_text()).get('status')=='completed']
    resources=sorted(candidates,key=lambda p:p.name)[-1]
    run('summarize_resources',[project/'src/summarize_resources.py',resources])
    run('preparation',[project/'src/benchmark_preparation.py'])
    run('environment',[project/'src/capture_environment.py'])
    run('frozen_outputs',[project/'src/verify_project.py'])
    status['status']='passed'
except Exception as exc:
    status.update(status='failed',error=str(exc))
    raise
finally:
    save()
    print('\nVerification evidence:',folder,flush=True)
