"""
Betaflight Tuning Analyzer – Entry point.

Usage:
    python run.py            # Start on port 8000
    python run.py --port 5000
    PORT=5000 python run.py  # via env var (used by Render.com)
"""
import argparse
import os
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Betaflight Tuning Analyzer")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port (default: 8000 or $PORT)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    # Render.com (and other cloud platforms) inject PORT env variable
    port = args.port or int(os.environ.get("PORT", 8000))
    # On cloud, bind to all interfaces so it's reachable
    host = args.host if args.host != "127.0.0.1" else os.environ.get("HOST", "127.0.0.1")

    print(f"\n{'='*50}")
    print(f"  Betaflight Tuning Analyzer")
    print(f"  http://{host}:{port}")
    print(f"{'='*50}\n")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
