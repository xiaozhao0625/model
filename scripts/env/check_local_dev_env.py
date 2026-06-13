from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path


REQUIRED_CONFIGS = [
    "configs/topology/single_node_dev.example.json",
    "configs/topology/four_node_prod.example.json",
    "configs/machines/local_dev.example.json",
    "configs/machines/four_machine_roles.example.json",
    "configs/model_gateway/model_manifest.example.json",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    missing_configs = [
        config
        for config in REQUIRED_CONFIGS
        if not (repo_root / config).exists()
    ]
    summary = {
        "valid": not missing_configs,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "repo_root": str(repo_root),
        "configs_present": not missing_configs,
        "missing_configs": missing_configs,
        "gpu": {
            "required": False,
            "nvidia_smi_available": shutil.which("nvidia-smi") is not None,
            "note": "GPU information is optional in P6 and never fails this check.",
        },
        "services_started": False,
        "dependencies_installed": False,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
