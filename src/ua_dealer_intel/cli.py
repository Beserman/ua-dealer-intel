"""CLI rozhranie projektu."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ua_dealer_intel.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ua_dealer_intel",
        description="Zber, extrakcia a hodnotenie ukrajinskych automobilovych dealerov.",
    )
    parser.add_argument(
        "--seeds",
        help="Cesta k CSV suboru s URL seedmi.",
    )
    parser.add_argument(
        "--companies",
        help="Volitelna cesta k CSV suboru s firmami bez URL.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Adresar pre vystupne subory.",
    )
    parser.add_argument(
        "--google-sheet-id",
        help="Volitelne ID Google Sheetu pre nahratie vysledkov.",
    )
    parser.add_argument(
        "--google-credentials",
        help="Cesta k service account JSON suboru pre Google Sheets.",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Zapne autonomne objavovanie kandidatov z verejnych zdrojov.",
    )
    parser.add_argument(
        "--discover-limit",
        type=int,
        default=25,
        help="Maximum autonomne objavenych kandidatov za jeden beh.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.seeds and not args.companies and not args.discover:
        parser.error("Treba zadat --seeds alebo --companies, pripadne zapnut --discover.")

    result = run_pipeline(
        seeds_path=Path(args.seeds) if args.seeds else None,
        companies_path=Path(args.companies) if args.companies else None,
        output_dir=Path(args.output_dir),
        google_sheet_id=args.google_sheet_id,
        google_credentials=Path(args.google_credentials) if args.google_credentials else None,
        discover=args.discover,
        discovery_limit=args.discover_limit,
    )
    print(json.dumps(_serialize_result(result), ensure_ascii=False, indent=2))


def _serialize_result(result: dict[str, object]) -> dict[str, object]:
    serialized = dict(result)
    outputs = serialized.get("outputs", {})
    if isinstance(outputs, dict):
        serialized["outputs"] = {key: str(value) for key, value in outputs.items()}
    return serialized


if __name__ == "__main__":
    main()
