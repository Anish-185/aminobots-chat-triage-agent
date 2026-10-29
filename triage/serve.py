"""`uv run python -m triage.serve`: the website and API on localhost, one process (SPEC §11)."""

import uvicorn

from triage.config import load_server

if __name__ == "__main__":
    cfg = load_server()
    print(f"Triage Desk (simulation only): http://{cfg.host}:{cfg.port}/")
    uvicorn.run("api.main:app", host=cfg.host, port=cfg.port)
