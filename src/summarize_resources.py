"""Summarize complete seven-container snapshots ending within each export window."""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import json
import re
import statistics

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    units={'B':1/1024**2,'kB':1000/1024**2,'KB':1000/1024**2,'KiB':1/1024,
           'MB':1e6/1024**2,'MiB':1,'GB':1e9/1024**2,'GiB':1024}
    def mib(text):
        match=re.fullmatch(r'([\d.]+)\s*([A-Za-z]+)',text.split('/')[0].strip())
        if not match:
            raise ValueError('Unknown memory value: '+text)
        return float(match[1])*units[match[2]]
    rows=[]
    for path in sorted(args.folder.glob('*.json')):
        report=json.loads(path.read_text())
        if 'samples' not in report or report.get('phase','measured')!='measured':
            continue
        snapshots=defaultdict(list)
        for sample in report['samples']:
            if sample['ended_before_export_finished']:
                snapshots[(sample['sample_start_seconds'],sample['sample_end_seconds'])].append(sample)
        complete=[batch for batch in snapshots.values() if len(batch)==7 and len({s['container'] for s in batch})==7]
        cpu=[sum(float(s['cpu_percent'].rstrip('%')) for s in batch) for batch in complete]
        memory=[sum(mib(s['memory_usage_and_limit']) for s in batch) for batch in complete]
        rows.append(dict(pipeline=report['pipeline'],round=report['round'],complete_snapshots_during_export=len(complete),
                         median_sampled_total_cpu_percent=statistics.median(cpu) if cpu else None,
                         maximum_sampled_total_memory_mib=max(memory) if memory else None))
    if not rows:
        raise RuntimeError('No monitored export files found.')
    destination=args.folder/'resource_summary.csv'
    if destination.exists():
        raise FileExistsError('Summary already exists: '+str(destination))
    with destination.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(rows,indent=2))
    print('Saved:',destination)

if __name__=='__main__':
    main()
