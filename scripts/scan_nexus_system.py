#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "agent_storage"
MIRROR = STORAGE / "mirrored_data"
LIFECYCLE = STORAGE / "lifecycle_logs"
DB_PATH = STORAGE / "system_state.db"


def ensure_structure() -> None:
    for directory in [STORAGE, MIRROR, LIFECYCLE]:
        directory.mkdir(parents=True, exist_ok=True)


def collect_repository_snapshot() -> dict:
    file_map = []
    for pattern in ("**/*.inc", "**/*.pwn", "**/*.pawn", "**/*.yml", "**/*.yaml", "**/*.md", "**/*.py"):
        for path in sorted(ROOT.glob(pattern)):
            if ".git" in path.parts:
                continue
            file_map.append({
                "path": str(path.relative_to(ROOT)),
                "size": path.stat().st_size,
            })

    inventory = {
        "repository": str(ROOT),
        "scan_time": "generated_by_nexus_scan",
        "files": file_map,
    }
    snapshot_path = MIRROR / "repository_snapshot.json"
    snapshot_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory


def write_lifecycle_report(inventory: dict) -> None:
    report = {
        "status": "ok",
        "observed_files": len(inventory["files"]),
        "summary": "Repository mirrored and lifecycle state captured.",
    }
    log_path = LIFECYCLE / "lifecycle_report.json"
    log_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def update_sqlite(inventory: dict) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository TEXT NOT NULL,
            file_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            summary TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO scans (repository, file_count, status, summary) VALUES (?, ?, ?, ?)",
        (
            str(ROOT),
            len(inventory["files"]),
            "ok",
            "Repository mirrored and lifecycle state captured.",
        ),
    )
    conn.commit()
    conn.close()


def validate_repository() -> list[str]:
    warnings: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".inc", ".pwn", ".pawn"}:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "#include" in content and "#pragma" in content:
                warnings.append(f"{path.relative_to(ROOT)} contains include and pragma directives; validate tag consistency.")
    return warnings


def main() -> int:
    ensure_structure()
    inventory = collect_repository_snapshot()
    write_lifecycle_report(inventory)
    update_sqlite(inventory)
    warnings = validate_repository()
    if warnings:
        print("[NEXUS SCAN] Warnings:")
        for warning in warnings:
            print(f" - {warning}")
    print(f"[NEXUS SCAN] repository={ROOT}")
    print(f"[NEXUS SCAN] discovered_files={len(inventory['files'])}")
    print("[NEXUS SCAN] mirror and lifecycle state stored successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
