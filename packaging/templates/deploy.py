"""Offline environment reconstruction and guarded business-data restoration."""
import argparse
import hashlib
import json
import os
import secrets
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PLATFORM = ROOT / 'Newsmart-Strawberry'
META = json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8'))

def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)

def prepare():
    for name, relative in META['environments'].items():
        project = ROOT / relative
        venv = project / '.venv'
        runtime = ROOT / 'runtimes' / ('python310' if name == 'cleaning' else 'python312') / 'python.exe'
        marker = venv / '.student-ready'
        if marker.exists() and marker.read_text(encoding='utf-8') == str(ROOT):
            print('Environment already prepared:', name, flush=True)
            continue
        print('Prepare environment:', name, flush=True)
        run([runtime, '-m', 'venv', '--without-pip', venv])
        site = venv / 'Lib/site-packages'
        shutil.copytree(ROOT / 'offline' / name, site, dirs_exist_ok=True)
        if name == 'backend':
            (site / 'student-yuxi.pth').write_text(str(project / 'package') + '\n', encoding='utf-8')
        # Regenerate console launchers against this new interpreter, not teacher paths.
        run([venv / 'Scripts/python.exe', ROOT / 'entrypoints.py'])
        marker.write_text(str(ROOT), encoding='utf-8')
    pending = []
    for link, target in json.loads((ROOT / 'node-links.json').read_text(encoding='utf-8')):
        dst, src = ROOT / link, ROOT / target
        if not src.exists():
            raise RuntimeError(f'Missing dependency junction target: {src}')
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            pending.append([str(dst), str(src)])
    (ROOT / 'pending-links.json').write_text(json.dumps(pending), encoding='utf-8')
    run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ROOT / 'restore-links.ps1'])
    old = META['source_root']
    for p in (PLATFORM / 'web/node_modules').rglob('*'):
        if p.is_file() and p.parent.name == '.bin':
            text = p.read_text(encoding='utf-8', errors='replace')
            if str(ROOT) not in text and ROOT.as_posix() not in text:
                text = text.replace(old, str(ROOT)).replace(old.replace('\\', '/'), ROOT.as_posix())
            p.write_text(text, encoding='utf-8')
    node = ROOT / 'runtimes/node'
    (node / 'pnpm.cmd').write_text('@echo off\r\n"%~dp0node.exe" "%~dp0pnpm\\bin\\pnpm.cjs" %*\r\n', encoding='ascii')
    print('Environment reconstruction finished.', flush=True)

def restore():
    from dotenv import dotenv_values
    import psycopg
    from argon2 import PasswordHasher
    from urllib.parse import urlparse, unquote
    marker = ROOT / 'backup/restored.json'
    if marker.exists():
        print('Business data was restored before; refusing to overwrite student changes.')
        return
    settings = dotenv_values(PLATFORM / '.runtime/local.env')
    dsn = settings['POSTGRES_URL'].replace('postgresql+asyncpg', 'postgresql')
    with psycopg.connect(dsn) as conn:
        count = conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')").fetchone()[0]
        if count:
            raise RuntimeError('Database is not empty. Do not overwrite it. Agent must inspect/backup first.')
    parsed = urlparse(dsn)
    env = {**os.environ, 'PGHOST': parsed.hostname, 'PGPORT': str(parsed.port),
           'PGUSER': unquote(parsed.username), 'PGPASSWORD': unquote(parsed.password), 'PGDATABASE': parsed.path.lstrip('/')}
    run([PLATFORM / '.runtime/pgsql/bin/pg_restore.exe', '--no-owner', '--no-acl', '--exit-on-error',
         '--single-transaction', '--dbname', env['PGDATABASE'], ROOT / 'backup/business.dump'], env=env)
    # Source dump stays unchanged; only the freshly restored student database is edited.
    with psycopg.connect(dsn) as conn:
        columns = conn.execute("SELECT table_schema,table_name,column_name,data_type FROM information_schema.columns WHERE table_schema IN ('public','traceability') AND data_type IN ('text','character varying','json','jsonb')").fetchall()
        from psycopg import sql
        old = META['source_root']
        for schema, table, col, kind in columns:
            if kind in ('json', 'jsonb'):
                query = sql.SQL('SELECT ctid::text, {} FROM {}.{}').format(sql.Identifier(col), sql.Identifier(schema), sql.Identifier(table))
                for rowid, value in conn.execute(query).fetchall():
                    if value is None:
                        continue
                    def rebase(v):
                        if isinstance(v, str):
                            return v.replace(old, str(ROOT)).replace(old.replace('\\', '/'), ROOT.as_posix())
                        if isinstance(v, list):
                            return [rebase(x) for x in v]
                        if isinstance(v, dict):
                            return {k: ([] if k in ('knowledge_base_ids', 'knowledge_ids', 'knowledges') else rebase(x)) for k, x in v.items()}
                        return v
                    new = rebase(value)
                    if new != value:
                        conn.execute(sql.SQL('UPDATE {}.{} SET {}=%s::{} WHERE ctid=%s::tid').format(sql.Identifier(schema), sql.Identifier(table), sql.Identifier(col), sql.SQL(kind)), (json.dumps(new), rowid))
            else:
                conn.execute(sql.SQL('UPDATE {}.{} SET {}=replace(replace({},%s,%s),%s,%s)').format(
                    sql.Identifier(schema), sql.Identifier(table), sql.Identifier(col), sql.Identifier(col)),
                    (old, str(ROOT), old.replace('\\', '/'), ROOT.as_posix()))
        account = conn.execute("SELECT id,uid FROM users WHERE role='superadmin' AND is_deleted=0 ORDER BY id LIMIT 1").fetchone()
        if not account:
            raise RuntimeError('No active superadmin in snapshot; inspect users before starting API.')
        password = 'Strawberry-' + secrets.token_urlsafe(12)
        conn.execute('UPDATE users SET password_hash=%s,login_failed_count=0,login_locked_until=NULL WHERE id=%s', (PasswordHasher().hash(password), account[0]))
        conn.execute("UPDATE field_work_records SET status='paused' WHERE kind='capture'")
        conn.execute("UPDATE cluster_albums SET device_id='' WHERE device_id IS NOT NULL")
        conn.execute("UPDATE field_work_records SET status='expired' WHERE kind IN ('control','disease_care') AND status IN ('pending','sending')")
    info = {'uid': account[1], 'password': password, 'root': str(ROOT)}
    marker.write_text(json.dumps(info, indent=2), encoding='utf-8')
    (ROOT / 'LOGIN.txt').write_text(f'Login UID: {account[1]}\nPassword: {password}\nChange this password after first login.\n', encoding='utf-8')
    print('Business data restored. See LOGIN.txt.', flush=True)

def verify():
    failures = []
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    for relative, expected in manifest.items():
        p = ROOT / relative
        if not p.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError(f'Unsafe manifest path: {relative}')
        if not p.is_file():
            failures.append(relative + ': missing')
        else:
            with p.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    failures.append(relative + ': mismatch')
    (ROOT / 'integrity-report.json').write_text(json.dumps(failures, indent=2), encoding='utf-8')
    if failures:
        raise RuntimeError(f'{len(failures)} files failed integrity check; see integrity-report.json')
    print('All packaged files passed SHA256 verification.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'restore', 'verify'])
    args = parser.parse_args()
    {'prepare': prepare, 'restore': restore, 'verify': verify}[args.action]()
