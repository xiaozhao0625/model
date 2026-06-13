from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ConfigCheckError(ValueError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigCheckError(f"config not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigCheckError(f"invalid JSON in config: {path}") from error


def require_mapping(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise ConfigCheckError(f"missing or invalid {key}")
    return value


def require_workers(config: dict[str, Any]) -> list[dict[str, Any]]:
    workers = config.get("workers")
    if not isinstance(workers, list) or not workers:
        raise ConfigCheckError("workers must be a non-empty list")
    seen_worker_ids: set[str] = set()
    for worker in workers:
        if not isinstance(worker, dict):
            raise ConfigCheckError("worker entry must be an object")
        worker_id = worker.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id:
            raise ConfigCheckError("worker_id is required")
        if worker_id in seen_worker_ids:
            raise ConfigCheckError(f"duplicate worker_id: {worker_id}")
        seen_worker_ids.add(worker_id)
        capabilities = worker.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise ConfigCheckError(f"worker {worker_id} capabilities must be non-empty")
    return workers


def validate_topology(config: dict[str, Any]) -> dict[str, Any]:
    topology_name = config.get("topology_name")
    if not isinstance(topology_name, str) or not topology_name:
        raise ConfigCheckError("topology_name is required")
    require_mapping(config, "master")
    require_mapping(config, "model_gateway")
    workers = require_workers(config)
    worker_types = {str(worker.get("worker_type")) for worker in workers}
    machine_ids: list[str] = []

    if topology_name == "single_node_dev":
        required_types = {"pc_game", "android"}
        if not required_types <= worker_types:
            raise ConfigCheckError("single_node_dev requires pc_game and android workers")
        if not ({"pc_app", "pc_app_web", "web"} & worker_types):
            raise ConfigCheckError("single_node_dev requires pc_app or web worker")

    if topology_name == "four_node_prod":
        machines = config.get("machines")
        if not isinstance(machines, list) or not machines:
            raise ConfigCheckError("four_node_prod requires machines")
        machine_ids = [str(machine.get("machine_id")) for machine in machines]
        if not {"M0", "W1", "W2", "W3"} <= set(machine_ids):
            raise ConfigCheckError("four_node_prod requires M0, W1, W2, and W3")

    return {
        "valid": True,
        "topology_name": topology_name,
        "mode": config.get("mode"),
        "worker_count": len(workers),
        "worker_ids": [worker["worker_id"] for worker in workers],
        "worker_types": sorted(worker_types),
        "machine_ids": machine_ids,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a topology JSON file.")
    parser.add_argument("--config", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = validate_topology(load_json(Path(args.config)))
    except ConfigCheckError as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
