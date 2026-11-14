"""Repeat the full-export benchmark; optional sampled Docker resource monitoring."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import json
import random
import re
import statistics
import subprocess
import threading
import time

from impala.dbapi import connect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--database', default='credit_risk')
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--monitor', action='store_true')
    parser.add_argument('--skip-initial', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9_]*', args.database) or args.repeats < 1:
        parser.error('Use a safe lowercase database name and at least one repeat.')
    project = args.project.resolve()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    output = project / 'results/reproducibility' / ('resources' if args.monitor else 'exports') / stamp
    output.mkdir(parents=True, exist_ok=False)
    tables = {'CSV': 'model_features', 'Raw_ORC': 'model_features_orc', 'Prepared_ORC': 'model_features_prepared_orc'}
    container_ids = []
    if args.monitor:
        container_ids = subprocess.check_output(['docker','compose','ps','-q'], cwd=project/'infrastructure', text=True, timeout=30).strip().splitlines()
        if len(container_ids) != 7:
            raise RuntimeError(f'Expected seven project containers; found {len(container_ids)}.')
    configuration = {
        'database': args.database, 'tables': tables, 'expected_rows': 306462,
        'measured_runs_per_pipeline': args.repeats, 'initial_runs_per_pipeline': int(not args.skip_initial),
        'batch_size': 10000, 'seed': 42, 'fresh_cursor_per_export': True,
        'query_results_cache_enabled': False, 'monitoring': args.monitor,
        'timing_scope': 'Execute through CSV write and close; no forced filesystem sync.',
        'cache_note': 'OS/JVM caches are not cleared; initial runs are not cold-cache measurements.',
        'resource_note': 'Sampled Docker totals for seven services, excluding Python. Not true peaks or CPU-seconds.',
        'status': 'running',
    }
    config_file = output/'configuration.json'
    def save_config():
        config_file.write_text(json.dumps(configuration, indent=2), encoding='utf-8')
    save_config()
    runs = []
    connection = None
    try:
        connection = connect(host='localhost', port=10000, user='hive', database=args.database, auth_mechanism='PLAIN', timeout=600)
        cursor = connection.cursor()
        try:
            cursor.execute('SET hive.query.results.cache.enabled=false')
        finally:
            cursor.close()
        orders = []
        if not args.skip_initial:
            orders.append(('initial', 0, ['Raw_ORC','CSV','Prepared_ORC']))
        rng = random.Random(42)
        for number in range(1, args.repeats+1):
            order = list(tables)
            rng.shuffle(order)
            orders.append(('measured', number, order))
        for phase, number, order in orders:
            for position, name in enumerate(order, 1):
                print(f'{phase} round {number}: {name}...', flush=True)
                samples, errors = [], []
                stop = threading.Event()
                origin = time.perf_counter()
                def monitor():
                    while not stop.is_set():
                        try:
                            started = time.perf_counter()-origin
                            raw = subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}',*container_ids], text=True, timeout=30)
                            finished = time.perf_counter()-origin
                            for line in raw.splitlines():
                                item = json.loads(line)
                                samples.append(dict(sample_start_seconds=started, sample_end_seconds=finished,
                                                    container=item['Name'], cpu_percent=item['CPUPerc'],
                                                    memory_usage_and_limit=item['MemUsage']))
                        except Exception as exc:
                            errors.append(str(exc))
                            break
                        stop.wait(.5)
                worker = threading.Thread(target=monitor, daemon=True) if args.monitor else None
                if worker:
                    worker.start()
                temporary = output / f'{phase}_{number}_{name}.partial.csv'
                cursor = connection.cursor()
                try:
                    start = time.perf_counter()
                    cursor.execute(f'SELECT * FROM {args.database}.{tables[name]}')
                    execute_seconds = time.perf_counter()-start
                    rows = 0
                    with temporary.open('w', newline='', encoding='utf-8') as handle:
                        writer = csv.writer(handle)
                        writer.writerow([item[0].rsplit('.',1)[-1] for item in cursor.description])
                        while True:
                            batch = cursor.fetchmany(10000)
                            if not batch:
                                break
                            writer.writerows(batch)
                            rows += len(batch)
                    elapsed = time.perf_counter()-start
                    export_finished = time.perf_counter()-origin
                finally:
                    stop.set()
                    if worker:
                        worker.join(timeout=35)
                        if worker.is_alive():
                            errors.append('Monitor did not finish.')
                    cursor.close()
                for sample in samples:
                    sample['ended_before_export_finished'] = sample['sample_end_seconds'] <= export_finished
                record = dict(phase=phase, round=number, position=position, pipeline=name,
                              row_count=rows, execute_seconds=execute_seconds, total_export_seconds=elapsed,
                              export_bytes=temporary.stat().st_size, valid=(rows==306462 and not errors))
                runs.append(record)
                with (output/'runs.csv').open('w',newline='',encoding='utf-8') as handle:
                    writer=csv.DictWriter(handle,fieldnames=list(record)); writer.writeheader(); writer.writerows(runs)
                if args.monitor:
                    (output/f'{phase}_{number}_{name}.json').write_text(json.dumps(dict(
                        **record, samples=samples, monitor_errors=errors), indent=2),encoding='utf-8')
                if not record['valid']:
                    raise RuntimeError(f'Invalid export: {record}; monitor errors={errors}. Partial CSV retained.')
                temporary.unlink()
                print(f'  {rows:,} records | {elapsed:.2f}s | {len(samples)} container sample records',flush=True)
        summary=[]
        for name in tables:
            times=[row['total_export_seconds'] for row in runs if row['pipeline']==name and row['phase']=='measured']
            summary.append(dict(pipeline=name,runs=len(times),median_seconds=statistics.median(times),minimum_seconds=min(times),maximum_seconds=max(times)))
        with (output/'summary.csv').open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
        configuration['status']='completed'
        print(json.dumps(summary,indent=2),flush=True)
    except Exception as exc:
        configuration.update(status='failed',error=str(exc))
        raise
    finally:
        if connection is not None:
            connection.close()
        save_config()
        print(f'Results: {output}',flush=True)


if __name__=='__main__':
    main()
