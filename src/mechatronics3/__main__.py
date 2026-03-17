"""CLI entry point for mechatronics3."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mechatronics3",
        description="Arduino-based mobile robot controller",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("server", help="Start the FastAPI web server")
    subparsers.add_parser("ml", help="Run autonomous ML-based strategy")
    subparsers.add_parser("vision", help="Run camera-tracking strategy")
    subparsers.add_parser("manual", help="Run manual control GUI")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "server":
        from mechatronics3.server.app import start

        start()
    elif args.command == "ml":
        from mechatronics3.strategies.ml_strategy import run

        run()
    elif args.command == "vision":
        from mechatronics3.strategies.vision_strategy import run

        run()
    elif args.command == "manual":
        from mechatronics3.strategies.manual_strategy import run

        run()


if __name__ == "__main__":
    main()
