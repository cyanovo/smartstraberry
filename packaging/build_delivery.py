"""Build a relocation-aware Windows classroom snapshot without modifying source data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STRAWBERRY_DELIVERY_DIR', ROOT / 'delivery' / 'Strawberry-Student-Windows-2026-10-26')).resolve()
PLATFORM = ROOT / 'Newsmart-Strawberry'
SKIP = {'.git', '.idea', '.vscode', '__pycache__', '.pytest_cache', '.ruff_cache', '.venv', 'node_modules', '.DS_Store', 'test_student_packaging.py'}
LINKS = []

def copy_tree(src, dst, skip=()):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in SKIP or item.name in skip or item.name.endswith(('.pyc', '.log')):
            continue
        target = dst / item.name
        if item.is_junction() or item.is_symlink():
            resolved = item.resolve()
            relative = resolved.relative_to(ROOT)
            LINKS.append([str(target.relative_to(OUT)), str(relative)])
        elif item.is_dir():
            copy_tree(item, target, skip)
        else:
            shutil.copy2(item, target)

def main():
    if OUT.exists():
        raise SystemExit(f'Delivery already exists, choose a new output: {OUT}')
    OUT.mkdir(parents=True)
    for name in ('backend', 'web', 'scripts', 'skills', 'docs'):
        print('Copy platform', name, flush=True)
        copy_tree(PLATFORM / name, OUT / 'Newsmart-Strawberry' / name,
                  ('saves', '.env', '.env.local', '.env.production', 'classroom.env', 'dist'))
    for name in ('AGENTS.md', 'ARCHITECTURE.md', 'LICENSE', 'start-services.cmd', 'start-worker.cmd', 'check-services.cmd', 'setup-mqtt-lan.cmd'):
        shutil.copy2(PLATFORM / name, OUT / 'Newsmart-Strawberry' / name)
    for name in ('albums', 'field-work', 'skills', 'agents'):
        copy_tree(PLATFORM / 'backend/saves' / name, OUT / 'Newsmart-Strawberry/backend/saves' / name)
    for name in ('strawberry_project', 'strawberry_vision'):
        print('Copy project', name, flush=True)
        copy_tree(ROOT / name, OUT / name)
    for name in ('pgsql', 'redis', 'qdrant', 'seaweedfs', 'java'):
        print('Copy service', name, flush=True)
        copy_tree(PLATFORM / '.runtime' / name, OUT / 'Newsmart-Strawberry/.runtime' / name,
                  ('data', 'storage', 'snapshots', 'logs', 'dump.rdb', 'appendonlydir'))
    copy_tree(PLATFORM / '.runtime/neo4j/lib', OUT / 'Newsmart-Strawberry/.runtime/neo4j/lib')
    runtimes = OUT / 'runtimes'
    copy_tree(Path(r'C:\Users\cyan\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none'), runtimes / 'python312', ('site-packages',))
    copy_tree(Path(r'D:\app\Python310'), runtimes / 'python310', ('site-packages', 'Scripts', 'Doc', 'Tools'))
    (runtimes / 'node').mkdir(parents=True)
    shutil.copy2(r'D:\app\nodejs\node.exe', runtimes / 'node/node.exe')
    copy_tree(Path(r'D:\app\nodejs\node_modules\pnpm'), runtimes / 'node/pnpm')
    copy_tree(Path(r'D:\app\Python310\Lib\site-packages\pip\_vendor\distlib'), OUT / 'distlib')
    environments = {
        'backend': 'Newsmart-Strawberry/backend',
        'mqtt': 'Newsmart-Strawberry/scripts/windows',
        'cleaning': 'strawberry_project',
        'training': 'strawberry_vision',
    }
    for name, project in environments.items():
        print('Snapshot environment', name, flush=True)
        copy_tree(ROOT / project / '.venv/Lib/site-packages', OUT / 'offline' / name,
                  ('__editable__.yuxi-0.7.0b2.pth', '__editable___yuxi_0_7_0b2_finder.py'))
    print('Snapshot frontend dependencies', flush=True)
    # Node links must be reconstructed; copying their absolute junctions is not portable.
    SKIP.remove('node_modules')
    copy_tree(PLATFORM / 'web/node_modules', OUT / 'Newsmart-Strawberry/web/node_modules', ('.vite', '.cache'))
    (OUT / 'node-links.json').write_text(json.dumps(LINKS, indent=2), encoding='utf-8')
    (OUT / 'snapshot.json').write_text(json.dumps({'source_root': str(ROOT), 'environments': environments,
        'release': 'student-2026.10.26',
        'python': {'backend': '3.12.14', 'mqtt': '3.12.14', 'training': '3.12.14', 'cleaning': '3.10.11'},
        'excluded': ['knowledge content', 'vectors', 'graphs', 'Ollama', 'chat history', 'pending tasks']}, indent=2), encoding='utf-8')
    from dotenv import dotenv_values
    import psycopg
    settings = dotenv_values(PLATFORM / '.runtime/local.env')
    dsn = settings['POSTGRES_URL'].replace('postgresql+asyncpg', 'postgresql')
    keep = {'departments', 'users', 'agents', 'skills', 'model_providers', 'detect_records',
            'sensor_samples', 'cluster_albums', 'album_photos', 'field_work_records'}
    with psycopg.connect(dsn, connect_timeout=10) as conn:
        tables = conn.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')").fetchall()
        counts = {f'{schema}.{table}': conn.execute(f'SELECT count(*) FROM "{schema}"."{table}"').fetchone()[0]
                  for schema, table in tables if schema == 'traceability' or table in keep}
    backup = OUT / 'backup'
    backup.mkdir()
    args = [str(PLATFORM / '.runtime/pgsql/bin/pg_dump.exe'), '--format=custom', '--no-owner', '--no-acl', '--file', str(backup / 'business.dump')]
    for schema, table in tables:
        if schema != 'traceability' and table not in keep:
            args.append(f'--exclude-table-data={schema}.{table}')
    from urllib.parse import urlparse, unquote
    parsed = urlparse(dsn)
    env = os.environ.copy()
    env.update(PGHOST=parsed.hostname, PGPORT=str(parsed.port), PGUSER=unquote(parsed.username),
               PGPASSWORD=unquote(parsed.password), PGDATABASE=parsed.path.lstrip('/'))
    print('Export logical business database', flush=True)
    subprocess.run(args, env=env, check=True)
    (backup / 'source-counts.json').write_text(json.dumps(counts, indent=2), encoding='utf-8')
    # Deployment must restore before launching the background worker.
    service = OUT / 'Newsmart-Strawberry/scripts/windows/services.ps1'
    text = service.read_text(encoding='utf-8-sig')
    text = text.replace("    Start-Owned 'worker' $python @((Join-Path $root 'backend/run_local.py'), '--worker') (Join-Path $root 'backend')",
                        "    if ($env:STRAWBERRY_SKIP_WORKER -ne '1') { Start-Owned 'worker' $python @((Join-Path $root 'backend/run_local.py'), '--worker') (Join-Path $root 'backend') }")
    if 'STRAWBERRY_SKIP_WORKER' not in text:
        raise RuntimeError('Worker restore gate missing; review changed services.ps1 before packaging')
    service.write_text(text, encoding='utf-8-sig')
    repository = OUT / 'Newsmart-Strawberry/backend/package/yuxi/repositories/detect_repository.py'
    repository.write_text(repository.read_text(encoding='utf-8').replace('ROUND(AVG(maturity_ratio), 2)', 'ROUND(AVG(maturity_ratio)::numeric, 2)'), encoding='utf-8')
    for item in (ROOT / 'packaging/templates').iterdir():
        if item.is_file():
            shutil.copy2(item, OUT / item.name)
    copy_tree(ROOT / '学生版本同步', OUT / '学生版本同步')
    print('Create SHA256 inventory', flush=True)
    manifest = {}
    paths = [p for p in OUT.rglob('*') if p.is_file()]
    def fingerprint(p):
        with p.open('rb') as stream:
            return p.relative_to(OUT).as_posix(), hashlib.file_digest(stream, 'sha256').hexdigest()
    with ThreadPoolExecutor(max_workers=16) as pool:
        for index, (name, sha) in enumerate(pool.map(fingerprint, paths)):
            manifest[name] = sha
            if index % 10000 == 0:
                print('Hashed files:', index, flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('BUILD_READY', str(OUT), len(manifest), flush=True)

if __name__ == '__main__':
    main()
