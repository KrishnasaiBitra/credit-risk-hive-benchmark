"""Measure preparation jobs in uniquely named managed scratch tables."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import time
from impala.dbapi import connect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    project=args.project.resolve()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    output=project/'results/reproducibility'/('preparation_'+stamp)
    output.mkdir(parents=True,exist_ok=False)
    connection=connect(host='localhost',port=10000,user='hive',database='credit_risk',auth_mechanism='PLAIN',timeout=600)
    reports=[]
    def execute(sql,fetch=False):
        cursor=connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall() if fetch else None
        finally:
            cursor.close()
    try:
        execute('SET hive.query.results.cache.enabled=false')
        for label,source in [('raw_orc','raw_credit'),('prepared_orc','model_features_orc')]:
            table='repro_prep_'+label+'_'+stamp
            schema=execute('DESCRIBE credit_risk.'+source,True)
            columns=[]
            for row in schema:
                name=str(row[0] or '').strip()
                if not name or name.startswith('#'):
                    break
                columns.append((name,str(row[1]).strip()))
            definition=', '.join(f'`{name}` {dtype}' for name,dtype in columns)
            selection=', '.join(f'`{name}`' for name,_ in columns)
            ddl=f"CREATE TABLE credit_risk.{table} ({definition}) STORED AS ORC TBLPROPERTIES ('orc.compress'='ZLIB','transactional'='false')"
            insert=f'INSERT OVERWRITE TABLE credit_risk.{table} SELECT {selection} FROM credit_risk.{source}'
            (output/(label+'.sql')).write_text(ddl+';\n'+insert+';\n')
            execute(ddl)
            try:
                print('Timing '+label,flush=True)
                start=time.perf_counter(); execute(insert); seconds=time.perf_counter()-start
                count=int(execute(f'SELECT COUNT(*) FROM credit_risk.{table}',True)[0][0])
                reports.append(dict(stage=label,source=source,seconds=seconds,rows=count,valid=count==306462))
                (output/'measurements.json').write_text(json.dumps(dict(
                    runs=reports,scope='Insert only; excludes table creation, source extraction and model training.',
                    note='Separate jobs on existing sources; not a directly timed full-chain cold-start experiment.'),indent=2))
                if count!=306462:
                    raise RuntimeError('Preparation row count failed.')
                print(f'{label}: {seconds:.2f}s; {count:,} rows',flush=True)
            finally:
                execute(f'DROP TABLE credit_risk.{table}')
    finally:
        connection.close()
    print('Saved:',output,flush=True)


if __name__=='__main__':
    main()
