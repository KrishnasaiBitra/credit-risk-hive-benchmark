"""Recreate the Linux x86_64 fallback from the pinned sklearn wheel's OpenMP library.

Development-only: requires patchelf==0.17.2.4 on PATH. Does not alter model files.
"""
from importlib.metadata import distribution
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
package = distribution('scikit-learn')
libraries = list(Path(package.locate_file('scikit_learn.libs')).glob('libgomp*.so*'))
if len(libraries) != 1:
    raise RuntimeError('Expected one GNU OpenMP runtime in the pinned Linux x86_64 wheel.')
original = libraries[0]
target = root / 'native/libgomp.so.1'
target.parent.mkdir(exist_ok=True)
shutil.copyfile(original, target)
subprocess.run(['patchelf', '--set-soname', 'libgomp.so.1', str(target)], check=True)
notice = root / 'third_party/scikit-learn-COPYING.txt'
notice.parent.mkdir(exist_ok=True)
shutil.copyfile(package.locate_file(f'scikit_learn-{package.version}.dist-info/licenses/COPYING'), notice)
(target.parent / 'provenance.json').write_text(json.dumps({
    'source': 'GNU OpenMP library distributed in the official scikit-learn Linux x86_64 wheel',
    'scikit_learn_version': package.version,
    'original_library_name': original.name,
    'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
    'bundled_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'change': 'ELF SONAME changed with patchelf to libgomp.so.1; model binaries are unchanged.',
    'license_notice': 'third_party/scikit-learn-COPYING.txt',
    'upstream_source': 'https://gcc.gnu.org/git/?p=gcc.git;a=tree;f=libgomp',
}, indent=2) + '\n', encoding='utf-8')
print('Prepared compatible OpenMP fallback:', target.name, target.stat().st_size, 'bytes')
