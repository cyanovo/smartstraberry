import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
platform = ROOT / 'Newsmart-Strawberry'
sys.path.insert(0, str(platform / 'backend/package'))
from dotenv import dotenv_values
import psycopg
from minio import Minio

settings = dotenv_values(platform / '.runtime/local.env')
dsn = settings['POSTGRES_URL'].replace('postgresql+asyncpg', 'postgresql')
try:
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        tables = conn.execute("SELECT schemaname,tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')").fetchall()
        print('TABLES', json.dumps(tables))
        print('RECORDS', conn.execute('SELECT kind, count(*) FROM field_work_records GROUP BY kind').fetchall())
        print('USERS', conn.execute('SELECT username, role FROM users').fetchall())
except Exception as exc:
    print('DB_ERROR', type(exc).__name__, str(exc)[:200])
try:
    client = Minio('127.0.0.1:19000', access_key=settings['MINIO_ACCESS_KEY'], secret_key=settings['MINIO_SECRET_KEY'], secure=False)
    for bucket in client.list_buckets():
        objects = list(client.list_objects(bucket.name, recursive=True))
        print('BUCKET', bucket.name, len(objects), sum(o.size for o in objects))
except Exception as exc:
    print('S3_ERROR', type(exc).__name__, str(exc)[:200])
for rel in ['Newsmart-Strawberry/backend/.venv', 'strawberry_project/.venv', 'strawberry_vision/.venv', 'Newsmart-Strawberry/web/node_modules', 'Newsmart-Strawberry/.runtime', 'strawberry_vision/dataset_maturity', 'strawberry_vision/datasets', 'strawberry_vision/runs', 'strawberry_project/images']:
    total = sum(p.stat().st_size for p in (ROOT / rel).rglob('*') if p.is_file())
    print('SIZE_GB', rel, round(total / 1024**3, 3), flush=True)
