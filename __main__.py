#!/usr/bin/env python3
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("ENV", "development") == "development"
    uvicorn.run(
        "adapters.inbound.rest.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
