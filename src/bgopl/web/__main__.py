from __future__ import annotations

import argparse

import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="bgopl.web", description=__doc__)
    parser.add_argument("data_dir", help="folder with standard-layout .xlsx files")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--suppress", help="file with lifters to hide (removal requests)")
    args = parser.parse_args()
    uvicorn.run(create_app(args.data_dir, args.suppress), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
