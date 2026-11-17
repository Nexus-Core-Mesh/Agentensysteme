#!/usr/bin/env python3
"""Master monitoring agent for a modular GTA:SA Reallife gamemode project.

Features:
- Watches expected project directories and source files.
- Validates path existence and include references.
- Detects suspicious or broken file states.
- Logs issues to a local JSON report and console.
- Supports one-time scan or continuous watch mode.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List


DEFAULT_EXPECTED_DIRS = [
    "core",
    "db",
    "state",
    "admin",
    "auth",
    "camera",
    "government",
    "economy",
    "jobs",
    "housing",
    "inventory",
    "vehicles",
    "factions",
    "business",
    "law",
    "emergency",
    "social",
    "web",
    "control-panel",
    "c++",
    "scripts",
    "agent_storage",
]

DEFAULT_FILE_PATTERNS = ["**/*.pwn", "**/*.inc", "**/*.pawn", "**/*.sql", "**/*.py", "**/*.js", "**/*.html", "**/*.md", "**/*.json"]


class MasterMonitorAgent:
    def __init__(self, root: Path, watch: bool = False, interval: int = 5) -> None:
        self.root = root.resolve()
        self.watch = watch
        self.interval = max(1, interval)
        self.db_path = self.root / "agent_storage" / "system_state.db"
        self.log_dir = self.root / "agent_storage" / "lifecycle_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.report_path = self.log_dir / "master_monitor_report.json"
        self.status_path = self.log_dir / "master_monitor_status.json"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def ensure_structure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "agent_storage").mkdir(parents=True, exist_ok=True)
        (self.root / "agent_storage" / "mirrored_data").mkdir(parents=True, exist_ok=True)
        (self.root / "agent_storage" / "lifecycle_logs").mkdir(parents=True, exist_ok=True)

        for directory in DEFAULT_EXPECTED_DIRS:
            target = self.root / directory
            if target.exists():
                self.passed.append(f"Directory exists: {directory}")
            else:
                self.warnings.append(f"Missing expected directory: {directory}")

    def collect_files(self, patterns: Iterable[str]) -> List[Path]:
        files = []
        for pattern in patterns:
            for path in self.root.glob(pattern):
                if path.is_file() and ".git" not in path.parts:
                    files.append(path)
        seen = set()
        unique = []
        for path in sorted(files, key=lambda p: str(p.relative_to(self.root))):
            key = str(path.resolve())
            if key not in seen:
                unique.append(path)
                seen.add(key)
        return unique

    def detect_missing_includes(self, files: List[Path]) -> List[str]:
        issues: List[str] = []
        include_pattern = re.compile(r'#include\s+["<]([^">]+)[">]')
        known = {p.name: p for p in files}

        for file in files:
            if file.suffix.lower() not in {".inc", ".pwn", ".pawn"}:
                continue
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in include_pattern.findall(content):
                if match in {"", "."}:
                    continue
                if match in known:
                    continue
                candidate = file.parent / match
                if not candidate.exists():
                    issues.append(f"Missing include reference: {file.relative_to(self.root)} -> {match}")
        return issues

    def validate_path_integrity(self, files: List[Path]) -> List[str]:
        issues: List[str] = []
        for file in files:
            relative = file.relative_to(self.root)
            if ".." in relative.as_posix():
                issues.append(f"Suspicious path traversal: {relative}")
            if not file.exists():
                issues.append(f"File disappears during scan: {relative}")
        return issues

    def check_for_runtime_red_flags(self, files: List[Path]) -> List[str]:
        findings: List[str] = []
        keywords = [
            r"TODO",
            r"FIXME",
            r"DEBUG",
            r"print\s*\(",
            r"assert\s*\(",
        ]

        for file in files:
            if file.suffix.lower() in {".pwn", ".inc", ".pawn", ".py", ".js", ".sql"}:
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for key in keywords:
                    if re.search(key, content, flags=re.IGNORECASE):
                        findings.append(f"Potential debug marker in {file.relative_to(self.root)}: {key}")
        return findings

    def write_database_state(self, stats: Dict[str, int]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                warnings INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO monitor_runs (timestamp, total_files, warnings, errors, status) VALUES (?, ?, ?, ?, ?)",
            (
                time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                stats["total_files"],
                stats["warnings"],
                stats["errors"],
                stats["status"],
            ),
        )
        conn.commit()
        conn.close()

    def run_scan(self) -> Dict[str, object]:
        self.passed = []
        self.warnings = []
        self.ensure_structure()

        files = self.collect_files(DEFAULT_FILE_PATTERNS)
        issues = []
        issues.extend(self.detect_missing_includes(files))
        issues.extend(self.validate_path_integrity(files))
        issues.extend(self.check_for_runtime_red_flags(files))

        self.errors = issues
        summary = {
            "root": str(self.root),
            "total_files": len(files),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "status": "ok" if not self.errors else "warning",
            "passed_checks": self.passed,
            "warnings_detail": self.warnings,
            "errors_detail": self.errors,
            "files": [str(p.relative_to(self.root)) for p in files],
        }

        self.report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        self.status_path.write_text(json.dumps({"status": summary["status"], "timestamp": time.time()}, indent=2), encoding="utf-8")
        self.write_database_state({"total_files": len(files), "warnings": len(self.warnings), "errors": len(self.errors), "status": summary["status"]})
        return summary

    def monitor(self) -> None:
        while True:
            self.ensure_structure()
            summary = self.run_scan()
            print("[MASTER MONITOR] scan complete")
            print(json.dumps({
                "status": summary["status"],
                "files": summary["total_files"],
                "warnings": summary["warnings"],
                "errors": summary["errors"],
            }, indent=2))
            if not self.watch:
                break
            time.sleep(self.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nexus master monitoring agent for modular SA:MP gamemode projects.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to monitor")
    parser.add_argument("--watch", action="store_true", help="Run continuously in watch mode")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds for watch mode")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agent = MasterMonitorAgent(root=args.root, watch=args.watch, interval=args.interval)
    try:
        agent.ensure_structure()
        agent.run_scan()
        if args.watch:
            agent.monitor()
    except KeyboardInterrupt:
        print("\n[MASTER MONITOR] interrupted by user.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
