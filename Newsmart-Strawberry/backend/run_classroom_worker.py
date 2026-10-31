"""PyCharm 直接运行：启动当前学生专属的 ARQ worker。"""

import subprocess
import sys
from pathlib import Path


if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "arq", "server.worker_main.WorkerSettings"],
            cwd=Path(__file__).resolve().parent,
        )
    )
