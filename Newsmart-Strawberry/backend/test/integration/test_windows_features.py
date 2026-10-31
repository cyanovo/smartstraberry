import os
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.integration
def test_native_management_and_workspace(monkeypatch, tmp_path):
    if os.getenv('TEST_WINDOWS_LOCAL') != '1':
        pytest.skip('Requires local Windows dependencies')
    from dotenv import dotenv_values
    from fastapi.testclient import TestClient

    for key, value in dotenv_values(Path(__file__).resolve().parents[3] / '.runtime/local.env').items():
        monkeypatch.setenv(key, value)
    from server.main import app
    from server.utils.auth_middleware import get_admin_user, get_required_user
    from yuxi.agents.backends.sandbox import paths

    monkeypatch.setattr(paths.conf, 'save_dir', str(tmp_path))
    user = SimpleNamespace(uid='test_native_features', role='superadmin', department_id=None)
    app.dependency_overrides[get_admin_user] = lambda: user
    app.dependency_overrides[get_required_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get('/api/knowledge/databases')
            assert response.status_code == 200, response.text
            response = client.get('/api/graph/list')
            assert response.status_code == 200, response.text
            assert response.json()['success'] is True
            response = client.get('/api/workspace/tree')
            assert response.status_code == 200, response.text
            assert isinstance(response.json()['entries'], list)
            response = client.post('/api/workspace/upload', data={'parent_path': '/'},
                                   files={'files': ('native.txt', b'local workspace', 'text/plain')})
            assert response.status_code == 200, response.text
            response = client.get('/api/workspace/download', params={'path': '/native.txt'})
            assert response.status_code == 200, response.text
            assert response.content == b'local workspace'
            response = client.delete('/api/workspace/file', params={'path': '/native.txt'})
            assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.clear()
