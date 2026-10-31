import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest


@pytest.mark.e2e
def test_owner_exit_stops_dependencies():
    if os.getenv('TEST_WINDOWS_SERVICE_LIFECYCLE') != '1':
        pytest.skip('Explicit opt-in required: this test stops local dependencies')
    root = Path(__file__).resolve().parents[3]
    start = time.time()
    process = subprocess.Popen(
        [sys.executable, '-u', str(root / 'scripts/windows/service_window.py')],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(120):
            logs = [p for p in (root / '.runtime/logs').glob('service-window-*.log')
                    if p.stat().st_mtime >= start]
            ready = [p for p in logs if 'SERVICES READY' in p.read_text(errors='replace')]
            if ready:
                break
            time.sleep(0.5)
        assert ready, 'Supervisor did not become ready'
        owner = int(ready[0].stem.rsplit('-', 1)[1])
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(1, False, owner)
        assert handle
        try:
            assert kernel.TerminateProcess(handle, 0)
        finally:
            kernel.CloseHandle(handle)
        for _ in range(120):
            ports = []
            for port in (15432, 16379, 19000, 11883):
                with socket.socket() as client:
                    client.settimeout(0.2)
                    if client.connect_ex(('127.0.0.1', port)) == 0:
                        ports.append(port)
            if not ports:
                break
            time.sleep(0.5)
        assert not ports, f'Dependencies still listening: {ports}'
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.terminate()
