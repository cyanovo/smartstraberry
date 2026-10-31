"""Validate restored data on an isolated PostgreSQL port, never the source database."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STRAWBERRY_DELIVERY_DIR', ROOT / 'delivery/Strawberry-Student-Windows-2026-10-26')).resolve()
TEST = ROOT / 'delivery-validation-2026-10-26'
TEST.mkdir(exist_ok=True)
PG = OUT / 'Newsmart-Strawberry/.runtime/pgsql/bin'
DATA = TEST / 'postgres'
password = secrets.token_hex(20)
pw = TEST / 'pg-password.txt'
pw.write_text(password, encoding='ascii')
env = {**os.environ, 'PGPASSWORD': password, 'PGHOST': '127.0.0.1', 'PGPORT': '25432', 'PGUSER': 'postgres'}

def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, env=env, **kwargs)

started = False
try:
    run([PG / 'initdb.exe', '-D', DATA, '-U', 'postgres', '-A', 'scram-sha-256', '--encoding=UTF8', '--locale=C', f'--pwfile={pw}'], stdout=subprocess.DEVNULL)
    run([PG / 'pg_ctl.exe', '-D', DATA, '-l', TEST / 'postgres.log', '-o', '-h 127.0.0.1 -p 25432', '-w', 'start'])
    started = True
    run([PG / 'createdb.exe', 'student_validation'])
    local = OUT / 'Newsmart-Strawberry/.runtime/local.env'
    local.write_text(f'POSTGRES_URL=postgresql+asyncpg://postgres:{password}@127.0.0.1:25432/student_validation\n', encoding='ascii')
    run([OUT / 'Newsmart-Strawberry/backend/.venv/Scripts/python.exe', OUT / 'deploy.py', 'restore'])
    import psycopg
    with psycopg.connect(f'postgresql://postgres:{password}@127.0.0.1:25432/student_validation') as conn:
        expected = json.loads((OUT / 'backup/source-counts.json').read_text())
        for table, count in expected.items():
            actual = conn.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            assert actual == count, (table, actual, count)
        assert conn.execute('SELECT count(*) FROM knowledge_bases').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM knowledge_graph_entities').fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM field_work_records WHERE kind IN ('control','disease_care') AND status IN ('pending','sending')").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM cluster_albums WHERE device_id <> ''").fetchone()[0] == 0
    print('PASS: transactional restore, account reset, business counts, empty knowledge and graph tables', flush=True)
finally:
    if started:
        run([PG / 'pg_ctl.exe', '-D', DATA, '-m', 'fast', '-w', 'stop'])
