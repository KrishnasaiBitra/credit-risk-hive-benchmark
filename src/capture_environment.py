"""Capture current software/service/storage observations in a new results folder."""
from pathlib import Path
from datetime import datetime, timezone
from importlib.metadata import version
import json
import platform
import subprocess

project=Path(__file__).resolve().parents[1]
folder=project/'results/reproducibility'/('environment_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
folder.mkdir(parents=True,exist_ok=False)
details=dict(python=platform.python_version(),platform=platform.platform(),
             packages={name:version(name) for name in ['pandas','numpy','impyla','scikit-learn','lightgbm','fairlearn','matplotlib']})
(folder/'python_versions.json').write_text(json.dumps(details,indent=2))
commands={
    'docker_version.txt':['docker','--version'],
    'compose_version.txt':['docker','compose','version'],
    'services.txt':['docker','compose','ps'],
    'images.txt':['docker','compose','images'],
    'idle_resource_snapshot.txt':['docker','stats','--no-stream','--format','table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'],
    'hdfs_storage_bytes.txt':['docker','compose','exec','-T','namenode','hdfs','dfs','-du','-s','/credit-risk/raw/cohort','/warehouse/external/raw_credit_orc','/warehouse/external/model_features_prepared_orc'],
}
for filename,command in commands.items():
    result=subprocess.check_output(command,cwd=project/'infrastructure',text=True,timeout=60)
    (folder/filename).write_text(result,encoding='utf-8')
print('Environment captured:',folder)
