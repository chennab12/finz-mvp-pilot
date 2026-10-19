"""Regenerate the synthetic test files in data/ (dates are relative to the day you run it).

    python scripts/make_sample_files.py              # dates relative to today
    python scripts/make_sample_files.py 2026-10-19   # or to a fixed day
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finlife.data import sample, storage  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    data = sample.comprehensive_data(today)
    (DATA / "tables").mkdir(parents=True, exist_ok=True)
    (DATA / "finlife-full-sample-backup.json").write_text(storage.to_backup_json(data), encoding="utf-8")
    (DATA / "sample_bank_export.csv").write_bytes(sample.bank_export_csv(today))
    (DATA / "sample_transactions.csv").write_bytes(storage.table_to_csv("transactions", data))
    for key in storage.SCHEMAS:
        (DATA / "tables" / f"{key}.csv").write_bytes(storage.table_to_csv(key, data))
    print(f"Wrote sample files for {today} to {DATA}")


if __name__ == "__main__":
    main()
