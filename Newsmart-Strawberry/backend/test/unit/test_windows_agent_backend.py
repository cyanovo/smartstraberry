from types import SimpleNamespace

import pytest


def test_native_files_are_scoped_and_do_not_expose_shell(monkeypatch, tmp_path):
    from deepagents.backends.protocol import SandboxBackendProtocol
    from yuxi.agents.backends.composite import _BackendScope
    from yuxi.agents.backends.sandbox import paths
    from yuxi.utils.paths import VIRTUAL_PATH_OUTPUTS, VIRTUAL_PATH_WORKSPACE

    monkeypatch.setenv('LOCAL_WINDOWS_MODE', 'true')
    monkeypatch.setattr(paths, 'conf', SimpleNamespace(save_dir=str(tmp_path)))
    scope = _BackendScope('thread1', 'user1', [], 'thread1', 'thread1')
    backend = scope.create_backend()
    workspace = backend.routes[VIRTUAL_PATH_WORKSPACE + '/']
    assert not isinstance(workspace, SandboxBackendProtocol)
    result = backend.write(VIRTUAL_PATH_WORKSPACE + '/hello.txt', 'native file')
    assert not result.error
    assert (paths.sandbox_workspace_dir('thread1', 'user1') / 'hello.txt').read_text() == 'native file'
    assert not backend.read(VIRTUAL_PATH_WORKSPACE + '/hello.txt').error
    with pytest.raises(ValueError):
        workspace._resolve_path('/../../secret.env')
    with pytest.raises(ValueError):
        workspace._resolve_path('C:\\Windows\\system.ini')
    other = _BackendScope('thread2', 'user2', [], 'thread2', 'thread2').create_backend()
    assert other.read(VIRTUAL_PATH_WORKSPACE + '/hello.txt').error
    assert not backend.write(VIRTUAL_PATH_OUTPUTS + '/result.txt', 'result').error


@pytest.mark.asyncio
async def test_native_uploads_remain_readonly(monkeypatch, tmp_path):
    from yuxi.agents.backends.composite import _BackendScope
    from yuxi.agents.backends.sandbox import paths
    from yuxi.utils.paths import VIRTUAL_PATH_UPLOADS

    monkeypatch.setenv('LOCAL_WINDOWS_MODE', 'true')
    monkeypatch.setattr(paths, 'conf', SimpleNamespace(save_dir=str(tmp_path)))
    backend = _BackendScope('thread1', 'user1', [], 'thread1', 'thread1').create_backend()
    source = paths.sandbox_uploads_dir('thread1') / 'source.txt'
    source.write_text('original')
    path = VIRTUAL_PATH_UPLOADS + '/source.txt'
    assert not (await backend.aread(path)).error
    assert (await backend.awrite(path, 'changed')).error
    assert (await backend.aedit(path, 'original', 'changed')).error
    assert (await backend.aupload_files([(path, b'changed')]))[0].error == 'permission_denied'
    assert source.read_text() == 'original'
