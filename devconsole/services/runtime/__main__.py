"""Read-only shadow report CLI (roadmap phase 0B.9).

Usage::

    python3 -m devconsole.services.runtime               # only running services
    python3 -m devconsole.services.runtime --all         # every configured service
    python3 -m devconsole.services.runtime --json        # machine-readable

This performs **observation only**.  It never starts, stops, restarts or signals
anything; it reads ``/proc`` and prints what a safe resolver would conclude.

The command is *not* gated on ``SISPER_PROCESS_MODE``: running it is an explicit,
deliberate request for the comparison, and it changes no behaviour either way.
"""

from __future__ import annotations

import argparse
import json
import sys

from devconsole.services.runtime.shadow import (
    ProcessMode,
    ShadowComparator,
    build_report,
    current_mode,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m devconsole.services.runtime",
        description="Read-only process-identity shadow report (phase 0B).",
    )
    parser.add_argument("--all", action="store_true",
                        help="include services with no running process")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of a table")
    parser.add_argument("--service", action="append", default=None,
                        help="restrict to a service name (repeatable)")
    args = parser.parse_args(argv)

    comparator = ShadowComparator()
    report = build_report(
        services=args.service,
        comparator=comparator,
        only_running=not args.all,
    )

    if args.json:
        payload = report.to_dict()
        payload["SISPER_PROCESS_MODE"] = current_mode().value
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"SISPER_PROCESS_MODE = {current_mode().value} "
          f"(shadow computation is {'active' if current_mode() is ProcessMode.SHADOW else 'inactive for live operations'})")
    print()
    if not report.comparisons:
        print("No running services matched. Use --all to list every configured service.")
        return 0

    header = f"{'SERVICE':<34} {'PORT':>6} {'LEGACY':>8} {'SAFE PID':>9} {'CONF':>7} {'OWNED':>6} {'MATCH':>6}  REASON"
    print(header)
    print("-" * len(header))
    for cmp in report.comparisons:
        legacy_pids = cmp.legacy.get("pids") or []
        print(f"{cmp.service:<34} {str(cmp.legacy.get('port') or '-'):>6} "
              f"{len(legacy_pids):>8} "
              f"{str(cmp.shadow.get('pid') or '-'):>9} "
              f"{cmp.shadow.get('confidence', 'NONE'):>7} "
              f"{str(cmp.shadow.get('owned', False)):>6} "
              f"{str(cmp.match):>6}  {cmp.reason or '-'}")
    print()
    print(f"totals: services={len(report.comparisons)} "
          f"matches={report.matches} mismatches={report.mismatches}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
