"""Export vystupov."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ua_dealer_intel.constants import EXCLUDED_REASON_COLUMN, SCORING_RULES, TARGET_COLUMNS


MANUAL_COLUMNS = [
    "company_name",
    "city",
    "region",
    "missing_fields",
    "research_queries",
    "priority_level",
]


def export_outputs(
    targets: list[dict[str, object]],
    excluded: list[dict[str, object]],
    sources: list[dict[str, object]],
    run_logs: list[dict[str, object]],
    manual_queue: list[dict[str, object]],
    output_dir: str | Path,
) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = out_dir / "ua_dealer_targets.xlsx"
    csv_path = out_dir / "ua_dealer_targets.csv"
    log_path = out_dir / "run_log.txt"

    targets_df = pd.DataFrame(targets, columns=TARGET_COLUMNS)
    excluded_df = pd.DataFrame(excluded, columns=TARGET_COLUMNS + [EXCLUDED_REASON_COLUMN])
    sources_df = pd.DataFrame(sources)
    rules_df = pd.DataFrame(SCORING_RULES)
    logs_df = pd.DataFrame(run_logs)
    manual_df = pd.DataFrame(manual_queue, columns=MANUAL_COLUMNS)

    targets_df.to_csv(csv_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        targets_df.to_excel(writer, sheet_name="targets", index=False)
        excluded_df.to_excel(writer, sheet_name="excluded", index=False)
        sources_df.to_excel(writer, sheet_name="sources", index=False)
        rules_df.to_excel(writer, sheet_name="scoring_rules", index=False)
        logs_df.to_excel(writer, sheet_name="run_log", index=False)
        manual_df.to_excel(writer, sheet_name="manual_enrichment_queue", index=False)

    with log_path.open("w", encoding="utf-8") as handle:
        for item in run_logs:
            handle.write(f'[{item.get("uroven", "info")}] {item.get("sprava", "")}\n')

    return {"xlsx": xlsx_path, "csv": csv_path, "log": log_path}

