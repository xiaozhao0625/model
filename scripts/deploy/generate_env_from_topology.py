from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    topology = Path("configs/deploy/four_machine_topology.example.json")
    data = json.loads(topology.read_text(encoding="utf-8"))
    print(json.dumps({"machines": list(data), "generated_files": [], "dry_run": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
