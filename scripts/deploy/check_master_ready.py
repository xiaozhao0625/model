from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> None:
    result = {
        "database_url_configured": bool(os.environ.get("DATABASE_URL", "sqlite:///runs/master/master.db")),
        "redis_url_configured": bool(os.environ.get("REDIS_URL", "memory://")),
        "master_api_health": "not_checked",
        "web_console_dist_exists": Path("apps/web-console/dist").exists(),
        "model_gateway_health": "not_checked",
        "real_services_started": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
