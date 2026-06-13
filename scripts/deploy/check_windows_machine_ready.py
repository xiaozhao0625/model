from __future__ import annotations

import json
import shutil
import socket
import sys
from pathlib import Path


def main() -> None:
    result = {
        "python_version": sys.version.split()[0],
        "git": "available" if shutil.which("git") else "unavailable",
        "nvidia_smi": "available" if shutil.which("nvidia-smi") else "unavailable",
        "project_path_exists": Path.cwd().exists(),
        "venv_exists": Path(".venv").exists(),
        "port_8000_available": _port_available(8000),
        "downloads_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


if __name__ == "__main__":
    main()
