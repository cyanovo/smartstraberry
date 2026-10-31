from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def test_native_cloud_model_requires_key(monkeypatch):
    from yuxi.services import agent_run_service as service

    monkeypatch.setenv('LOCAL_WINDOWS_MODE', 'true')
    info = SimpleNamespace(model_type='chat', base_url='https://example.com/v1', api_key='')
    monkeypatch.setattr(service.model_cache, 'get_model_info', lambda _: info)
    with pytest.raises(HTTPException) as error:
        service._validate_native_model('provider:model')
    assert error.value.status_code == 422
    info.api_key = 'test-only'
    service._validate_native_model('provider:model')
    info.api_key = ''
    info.base_url = 'http://127.0.0.1:1234/v1'
    service._validate_native_model('provider:model')


def test_native_missing_model_is_actionable(monkeypatch):
    from yuxi.services import agent_run_service as service

    monkeypatch.setenv('LOCAL_WINDOWS_MODE', 'true')
    monkeypatch.setattr(service.model_cache, 'get_model_info', lambda _: None)
    with pytest.raises(HTTPException) as error:
        service._validate_native_model(None)
    assert error.value.status_code == 422
