"""PyCharm 直接运行：启动学生本机 FastAPI。"""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    uvicorn.run(
        "server.main:app",
        host="127.0.0.1",
        port=int(os.getenv("API_PORT", "5050")),
        reload=True,
        reload_dirs=["server", "package"],
    )
