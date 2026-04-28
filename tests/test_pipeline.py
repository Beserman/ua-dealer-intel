from pathlib import Path

from ua_dealer_intel.pipeline import run_pipeline


def test_pipeline_handles_company_without_url(tmp_path: Path) -> None:
    seeds = tmp_path / "seed_urls.csv"
    companies = tmp_path / "seed_companies.csv"

    seeds.write_text("source_url,company_hint,city,region,source_type\n", encoding="utf-8")
    companies.write_text(
        "company_name,city,region,notes\nDealer Bez Webu,Uzhhorod,Zakarpatska,\n",
        encoding="utf-8",
    )

    result = run_pipeline(seeds_path=seeds, companies_path=companies, output_dir=tmp_path / "outputs")
    assert result["targets_count"] == 1
    assert result["manual_queue_count"] == 1
    assert (tmp_path / "outputs" / "ua_dealer_targets.xlsx").exists()
    assert (tmp_path / "outputs" / "ua_dealer_targets.csv").exists()

