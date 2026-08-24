"""Entry point for the ``glossanon-serve`` console script.

Thin wrapper around uvicorn so users can launch the REST API without
remembering the import path. Requires the ``api`` extra.
"""

from __future__ import annotations

import argparse
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="glossanon-serve", description="Run the glossanon REST API."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "uvicorn is required to serve the API. Install with: "
            'pip install "glossanon[api]"'
        ) from exc

    uvicorn.run(
        "glossanon.api.app:app", host=args.host, port=args.port, reload=args.reload
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
