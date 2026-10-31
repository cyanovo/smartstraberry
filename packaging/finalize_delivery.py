import hashlib
import json
import os
import sys
from pathlib import Path
import zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STRAWBERRY_DELIVERY_DIR', ROOT / 'delivery/Strawberry-Student-Windows-2026-10-26')).resolve()
archive = OUT.with_suffix('.zip')
if archive.exists():
    raise SystemExit(f'Refusing to overwrite an existing archive: {archive}')

EXCLUDE = {'.venv', '__pycache__', '.prepared', 'pending-links.json', 'LOGIN.txt', 'local.env', 'restored.json', 'logs', '.vite', '.cache', '.pytest_cache', '.ruff_cache', 'integrity-report.json', 'DEPLOY_TEST_REPORT.json', 'student-version.json'}

def files(folder):
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.name in EXCLUDE or entry.is_junction() or entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                yield from files(Path(entry.path))
            elif entry.is_file(follow_symlinks=False):
                yield Path(entry.path)

manifest = {}
paths = [p for p in files(OUT) if p.name != 'manifest.json']
# Validation rewrites launchers; publish source-root paths for prepare to relocate.
source_root = json.loads((OUT / 'snapshot.json').read_text(encoding='utf-8'))['source_root']
for p in paths:
    if p.parent.name == '.bin':
        text = p.read_text(encoding='utf-8')
        text = text.replace(str(OUT), source_root).replace(OUT.as_posix(), source_root.replace('\\', '/'))
        p.write_text(text, encoding='utf-8')
print('Inventory files:', len(paths), flush=True)
def hash_file(p):
    with p.open('rb') as stream:
        return p.relative_to(OUT).as_posix(), hashlib.file_digest(stream, 'sha256').hexdigest()
if '--reuse-manifest' in sys.argv:
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
else:
    with ThreadPoolExecutor(max_workers=16) as pool:
      for i, (relative, digest) in enumerate(pool.map(hash_file, paths)):
        manifest[relative] = digest
        if i % 10000 == 0:
            print('Hashed files:', i, flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Files:', len(manifest), 'Creating ZIP64...', flush=True)
paths.append(OUT / 'manifest.json')
def load(p):
    if p.stat().st_size > 32 * 1024 * 1024:
        return p, None
    return p, p.read_bytes()
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as output, ThreadPoolExecutor(max_workers=16) as pool:
    for start in range(0, len(paths), 256):
        for p, data in pool.map(load, paths[start:start+256]):
            name = p.relative_to(OUT.parent).as_posix()
            if data is None:
                output.write(p, name)
            else:
                output.writestr(name, data)
        if start % 10240 == 0:
            print('Archived entries:', start, flush=True)
print('Verifying every archive CRC...', flush=True)
with zipfile.ZipFile(archive) as check:
    bad = check.testzip()
    if bad:
        raise RuntimeError('Archive CRC failed: ' + bad)
with archive.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
archive.with_suffix('.zip.sha256').write_text(digest + '  ' + archive.name + '\n', encoding='ascii')
print('ARCHIVE_READY', archive, archive.stat().st_size, digest, flush=True)
