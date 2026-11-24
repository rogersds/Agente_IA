from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soc-agent")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("triage")
    sub.add_parser("correlate")
    sub.add_parser("propose-query")
    sub.add_parser("propose-containment")
    args, rest = parser.parse_known_args(argv)
    if args.cmd == "triage":
        from .triage import main as m
    elif args.cmd == "correlate":
        from .correlate import main as m
    elif args.cmd == "propose-query":
        from .propose_query import main as m
    else:
        from .propose_containment import main as m
    return m(rest)


if __name__ == "__main__":
    raise SystemExit(main())
