"""PyCharm entry point for the native Windows API and optional worker."""

import asyncio
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == '__main__':
    if '--worker' not in sys.argv:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', 5050)) == 0:
                raise SystemExit('Port 5050 is in use. Stop the existing API instance before starting this one.')
    print('[startup] Loading local configuration...', flush=True)
    if os.getenv('LOCAL_STARTUP_DEBUG') == '1':
        import faulthandler

        faulthandler.dump_traceback_later(60, repeat=True)
    os.chdir(ROOT)
    os.environ['LOCAL_WINDOWS_MODE'] = 'true'
    sys.path.insert(0, str(ROOT / 'package'))
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import yuxi  # noqa: F401

    print('[startup] Local configuration loaded.', flush=True)

    if '--worker' in sys.argv:
        from arq.worker import run_worker
        from server.worker_main import WorkerSettings

        asyncio.set_event_loop(asyncio.SelectorEventLoop())
        run_worker(WorkerSettings, handle_signals=False)
    else:
        import uvicorn

        print('[startup] Loading FastAPI and model dependencies; first startup may take several minutes.', flush=True)
        server = uvicorn.Server(uvicorn.Config('server.main:app', host='127.0.0.1', port=5050))
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(server.serve())
