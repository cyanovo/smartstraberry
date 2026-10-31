"""Non-actuating smoke checks; failures are recorded rather than hidden."""
import json
import hashlib
import io
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
results = []

def check(name, function):
    try:
        detail = function()
        results.append({'name': name, 'status': 'PASS', 'detail': str(detail)})
    except Exception as exc:
        results.append({'name': name, 'status': 'FAIL', 'detail': str(exc)})
    print(results[-1], flush=True)

def port_open(port):
    with socket.create_connection(('127.0.0.1', port), timeout=3):
        return port

def request(path, data=None, token=None, binary=False):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    req = urllib.request.Request(os.environ.get('STRAWBERRY_TEST_API', 'http://127.0.0.1:5050') + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read() if binary else json.load(response)

def api():
    deadline = time.monotonic() + 240
    while True:
        try:
            health = request('/api/system/health')
            assert health.get('status') == 'ok', health
            return health
        except Exception:
            if time.monotonic() >= deadline:
                raise
            time.sleep(3)

def login():
    info = json.loads((ROOT / 'backup/restored.json').read_text(encoding='utf-8'))
    data = urllib.parse.urlencode({'username': os.environ.get('STRAWBERRY_TEST_UID', info['uid']), 'password': os.environ.get('STRAWBERRY_TEST_PASSWORD', info['password'])}).encode()
    token = request('/api/auth/token', data=data)['access_token']
    offset = checked = 0
    while True:
        albums = request(f'/api/albums?limit=100&offset={offset}', token=token)
        assert isinstance(albums['items'], list)
        for album in albums['items']:
            if not album['photo_count']:
                continue
            photos = []
            while True:
                page = request(f"/api/albums/{album['id']}/photos?limit=100&offset={len(photos)}", token=token)
                photos.extend(page['items'])
                if len(photos) >= page['total']:
                    break
                if not page['items']:
                    raise RuntimeError('Album pagination stalled')
            data = request(f"/api/albums/{album['id']}/archive", token=token, binary=True)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                assert archive.testzip() is None
                actual = sorted(hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist())
                assert actual == sorted(photo['sha256'] for photo in photos), 'Album ZIP differs from stored originals'
                assert len(set(archive.namelist())) == len(photos)
            checked += len(photos)
        offset += len(albums['items'])
        if offset >= albums['total']:
            break
        if not albums['items']:
            raise RuntimeError('Album list pagination stalled')
    suggestions = request('/api/disease-care', token=token)
    assert isinstance(suggestions, list)
    return f'Authenticated albums, ZIP original hashes ({checked} photos), disease-care read passed; no device commands'

def execute(relative, args, cwd=None):
    result = subprocess.run([str(ROOT / relative), *args], cwd=cwd or ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    if result.returncode:
        raise RuntimeError((result.stderr + result.stdout)[-4000:])
    return result.stdout[-1500:]

if __name__ == '__main__':
    for port in (15432, 16379, 16333, 17687, 19000, 11883, 1883):
        check('service:' + str(port), lambda p=port: port_open(p))
    check('api health', api)
    check('login and albums', login)
    check('cleaning imports', lambda: execute('strawberry_project/.venv/Scripts/python.exe', ['-c', 'import cv2,numpy; print(cv2.__version__)']))
    check('YOLO26 load', lambda: execute('strawberry_vision/.venv/Scripts/python.exe', ['-c', "from ultralytics import YOLO; m=YOLO('weights/yolo26n.pt'); assert m.task=='detect'; print(len(m.names))"], ROOT / 'strawberry_vision'))
    check('dataset split', lambda: execute('strawberry_vision/.venv/Scripts/python.exe', ['tests/verify_maturity_split.py'], ROOT / 'strawberry_vision'))
    report = {'release': json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8')).get('release'), 'scope': 'basic smoke only, not full acceptance', 'checks': results, 'manual_required': ['browser routes and screenshots', 'folder upload with nested files', 'shared upload/download', 'maturity and disease real inference', 'short YOLO training and validation', 'camera permission', 'AI provider availability', 'hardware disconnected confirmation'],
              'excluded_by_design': ['existing knowledge bases', 'Ollama and its models', 'physical actuator commands']}
    (ROOT / 'DEPLOY_TEST_REPORT.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    raise SystemExit(1 if any(x['status'] == 'FAIL' for x in results) else 0)
