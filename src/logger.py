"""
Logger — tracks all fill operations in JSON + markdown.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from src.config import DATA_DIR


LOG_JSON = DATA_DIR / "run_log.json"
LOG_MD = DATA_DIR / "run_log.md"


def _load_log() -> list[dict]:
    if LOG_JSON.exists():
        return json.loads(LOG_JSON.read_text())
    return []


def _save_log(entries: list[dict]):
    LOG_JSON.write_text(json.dumps(entries, indent=2, default=str))

    # Also update markdown
    lines = [
        "# Salesforce PDF Filler — Run Log\n",
        "| Timestamp | Record ID | SF Object | Template | Output | Status |",
        "|-----------|-----------|-----------|----------|--------|--------|",
    ]
    for entry in reversed(entries[-50:]):  # Last 50 entries
        lines.append(
            f"| {entry['timestamp']} | {entry.get('record_id', '-')} | {entry.get('sf_object', '-')} "
            f"| {entry.get('template', '-')} | {entry.get('output', '-')} | {entry.get('status', '-')} |"
        )
    LOG_MD.write_text("\n".join(lines) + "\n")


def log_run(
    record_id: str,
    sf_object: str,
    template: str,
    output: str,
    status: str = "success",
    error: str | None = None,
    fields_filled: int = 0,
    coverage_pct: float = 0.0,
):
    entries = _load_log()
    entries.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record_id": record_id,
        "sf_object": sf_object,
        "template": template,
        "output": output,
        "status": status,
        "error": error,
        "fields_filled": fields_filled,
        "coverage_pct": coverage_pct,
    })
    _save_log(entries)


def get_stats() -> dict:
    entries = _load_log()
    total = len(entries)
    success = sum(1 for e in entries if e["status"] == "success")
    failed = total - success
    return {
        "total_runs": total,
        "successful": success,
        "failed": failed,
        "success_rate": round(success / max(total, 1) * 100, 1),
        "last_run": entries[-1]["timestamp"] if entries else None,
    }
