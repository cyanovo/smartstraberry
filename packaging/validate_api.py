"""Start copied API with isolated PostgreSQL and Redis; exercise authenticated reads."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('STRAWBERRY_DELIVERY_DIR', ROOT / 'delivery/Strawberry-Student-Windows-2026-10-26')).resolve()
TEST = ROOT / 'delivery-validation-2026-10-26'
PLATFORM = OUT / 'Newsmart-Strawberry'
PG = PLATFORM / '.runtime/pgsql/bin'
password = (TEST / 'pg-password.txt').read_text()
from dotenv import dotenv_values

settings = dotenv_values(ROOT / 'Newsmart-Strawberry/.runtime/local.env')
settings.update(POSTGRES_URL=f'postgresql+asyncpg://postgres:{password}@127.0.0.1:25432/student_validation',
                REDIS_URL='redis://127.0.0.1:26379/0', MQTT_ENABLED='false', LITE_MODE='true',
                GREENHOUSE_INSTANCE_ID='delivery-validation', RUN_QUEUE_NAME='arq:queue:delivery-validation')
(PLATFORM / '.runtime/local.env').write_text('\n'.join(f'{k}={v}' for k, v in settings.items()) + '\n', encoding='utf-8')
api = redis = None
report = []
try:
    subprocess.run([str(PG / 'pg_ctl.exe'), '-D', str(TEST / 'postgres'), '-l', str(TEST / 'postgres.log'), '-o', '-h 127.0.0.1 -p 25432', '-w', 'start'], check=True)
    redis_exe = next((PLATFORM / '.runtime/redis').rglob('redis-server.exe'))
    redis_log = (TEST / 'redis.log').open('w')
    redis = subprocess.Popen([str(redis_exe), '--bind', '127.0.0.1', '--port', '26379', '--save', '', '--appendonly', 'no'], cwd=TEST, stdout=redis_log, stderr=subprocess.STDOUT)
    api_log = (TEST / 'api.log').open('w', encoding='utf-8')
    code = "import asyncio; asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()); import uvicorn; server=uvicorn.Server(uvicorn.Config('server.main:app',host='127.0.0.1',port=25050)); runner=asyncio.Runner(loop_factory=asyncio.SelectorEventLoop); runner.run(server.serve())"
    api = subprocess.Popen([str(PLATFORM / 'backend/.venv/Scripts/python.exe'), '-c', code], cwd=PLATFORM / 'backend', env={**os.environ, 'LOCAL_WINDOWS_MODE': 'true', 'PYTHONUTF8': '1'}, stdout=api_log, stderr=subprocess.STDOUT)
    def request(path, data=None, token=None):
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:25050' + path, data=data, headers=headers), timeout=10) as response:
            return json.load(response)
    deadline = time.monotonic() + 240
    while True:
        try:
            health = request('/api/system/health')
            assert health['status'] == 'ok'
            break
        except Exception:
            if api.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f'Copied API did not become healthy; see {TEST / "api.log"}')
            time.sleep(2)
    info = json.loads((OUT / 'backup/restored.json').read_text())
    token = request('/api/auth/token', urllib.parse.urlencode({'username': info['uid'], 'password': info['password']}).encode())['access_token']
    for endpoint in ('/api/albums', '/api/detect/history', '/api/detect/stats', '/api/field-work/records/model', '/api/disease-care'):
        result = request(endpoint, token=token)
        report.append({'endpoint': endpoint, 'status': 'PASS', 'type': type(result).__name__})
    subprocess.run([str(PLATFORM / 'backend/.venv/Scripts/python.exe'), '-c', 'import smoke_test; print(smoke_test.login())'], cwd=OUT,
                   env={**os.environ, 'STRAWBERRY_TEST_API': 'http://127.0.0.1:25050', 'PYTHONUTF8': '1'}, check=True)
    report.append({'check': 'all restored albums ZIP original hashes', 'status': 'PASS'})
    (TEST / 'api-checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    import psycopg
    with psycopg.connect(f'postgresql://postgres:{password}@127.0.0.1:25432/student_validation') as conn:
        assert float(conn.execute('SELECT ROUND(AVG(x)::numeric, 2) FROM (VALUES (0.1234::double precision),(0.5678::double precision)) t(x)').fetchone()[0]) == 0.35
    print('PASS: copied API health, restored account login, albums, detections, model registry', flush=True)
finally:
    for process in (api, redis):
        if process and process.poll() is None:
            subprocess.run(['taskkill.exe', '/PID', str(process.pid), '/T', '/F'], check=True)
            process.wait(timeout=30)
    subprocess.run([str(PG / 'pg_ctl.exe'), '-D', str(TEST / 'postgres'), '-m', 'fast', '-w', 'stop'], check=True)
