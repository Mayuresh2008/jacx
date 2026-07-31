"""Automatic Cleanup for Jacx QA storage.

Manages the lifecycle of temporary data:
- jacx_qa/temp/ → archive after batch analysis
- jacx_qa/archive/ → delete after 7 days
- jacx_qa/reports/failed_commands.jsonl → prune entries older than 30 days
- jacx_qa/reports/ → keep only latest 20 batch reports
- jacx_qa/temp/ → enforce max storage size (500MB default)

Provides cleanup reports and storage statistics.
"""

import os
import json
import time
import glob
from typing import Dict, Any, List
from datetime import datetime, timedelta


QA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DIR = os.path.join(QA_ROOT, "temp")
ARCHIVE_DIR = os.path.join(QA_ROOT, "archive")
REPORTS_DIR = os.path.join(QA_ROOT, "reports")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "jacx_brain", "config", "brain_config.json")


def _load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _file_age_days(filepath: str) -> float:
    if not os.path.exists(filepath):
        return 0
    mtime = os.path.getmtime(filepath)
    return (time.time() - mtime) / 86400


def _dir_size_mb(path: str) -> float:
    if not os.path.exists(path):
        return 0.0
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return round(total / (1024 * 1024), 2)


class QACleanup:
    """Manages automatic cleanup of QA storage."""

    def __init__(self):
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        config = _load_config()
        limits = config.get("storage_limits", {})
        self.archive_days = limits.get("archive_days", 7)
        self.failure_log_days = limits.get("failure_log_days", 30)
        self.keep_latest_reports = limits.get("keep_latest_reports", 20)
        self.max_temp_mb = limits.get("max_temp_storage_mb", 500)

    def run_full_cleanup(self) -> Dict[str, Any]:
        """Run all cleanup operations and return summary report."""
        report = {
            "timestamp": _now_iso(),
            "temp_archived": 0,
            "temp_deleted": 0,
            "archive_deleted": 0,
            "failure_lines_pruned": 0,
            "reports_pruned": 0,
            "temp_size_mb_before": _dir_size_mb(TEMP_DIR),
            "archive_size_mb_before": _dir_size_mb(ARCHIVE_DIR),
        }

        self._archive_temp_files(report)
        self._delete_expired_archive(report)
        self._prune_failure_log(report)
        self._prune_old_reports(report)
        self._enforce_temp_size_limit(report)

        report["temp_size_mb_after"] = _dir_size_mb(TEMP_DIR)
        report["archive_size_mb_after"] = _dir_size_mb(ARCHIVE_DIR)

        self._save_cleanup_report(report)
        return report

    def _archive_temp_files(self, report: Dict[str, Any]):
        """Move temp batch files to archive."""
        if not os.path.exists(TEMP_DIR):
            return
        for fname in os.listdir(TEMP_DIR):
            fpath = os.path.join(TEMP_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            dest = os.path.join(ARCHIVE_DIR, fname)
            try:
                os.replace(fpath, dest)
                report["temp_archived"] += 1
            except Exception:
                pass

    def _delete_expired_archive(self, report: Dict[str, Any]):
        """Delete archive files older than archive_days."""
        if not os.path.exists(ARCHIVE_DIR):
            return
        for fname in os.listdir(ARCHIVE_DIR):
            fpath = os.path.join(ARCHIVE_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            age = _file_age_days(fpath)
            if age > self.archive_days:
                try:
                    os.remove(fpath)
                    report["archive_deleted"] += 1
                except Exception:
                    pass

    def _prune_failure_log(self, report: Dict[str, Any]):
        """Remove failure entries older than failure_log_days from failed_commands.jsonl."""
        failed_path = os.path.join(REPORTS_DIR, "failed_commands.jsonl")
        if not os.path.exists(failed_path):
            return

        cutoff = datetime.now() - timedelta(days=self.failure_log_days)
        kept_lines = []
        pruned = 0

        try:
            with open(failed_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if ts:
                            entry_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                            if entry_time < cutoff:
                                pruned += 1
                                continue
                        kept_lines.append(line)
                    except (json.JSONDecodeError, ValueError):
                        kept_lines.append(line)

            if pruned > 0:
                with open(failed_path, "w", encoding="utf-8") as f:
                    for line in kept_lines:
                        f.write(line + "\n")

            report["failure_lines_pruned"] = pruned
        except Exception:
            pass

    def _prune_old_reports(self, report: Dict[str, Any]):
        """Keep only the latest N batch reports by file modification time."""
        report_files = glob.glob(os.path.join(REPORTS_DIR, "batch_*.json"))
        if len(report_files) <= self.keep_latest_reports:
            return

        report_files.sort(key=lambda f: os.path.getmtime(f))
        to_delete = report_files[: len(report_files) - self.keep_latest_reports]
        for fpath in to_delete:
            try:
                os.remove(fpath)
                report["reports_pruned"] += 1
            except Exception:
                pass

    def _enforce_temp_size_limit(self, report: Dict[str, Any]):
        """Delete oldest temp files if size exceeds limit."""
        current_mb = _dir_size_mb(TEMP_DIR)
        if current_mb <= self.max_temp_mb:
            return

        files = []
        if os.path.exists(TEMP_DIR):
            for fname in os.listdir(TEMP_DIR):
                fpath = os.path.join(TEMP_DIR, fname)
                if os.path.isfile(fpath):
                    files.append((fpath, os.path.getmtime(fpath)))

        files.sort(key=lambda x: x[1])
        for fpath, _ in files:
            if current_mb <= self.max_temp_mb * 0.8:
                break
            size = os.path.getsize(fpath) / (1024 * 1024)
            try:
                os.remove(fpath)
                current_mb -= size
                report["temp_deleted"] += 1
            except Exception:
                pass

    def _save_cleanup_report(self, report: Dict[str, Any]):
        """Save the cleanup report."""
        report_path = os.path.join(REPORTS_DIR, "latest_cleanup_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    def get_cleanup_report(self) -> Dict[str, Any]:
        """Load the most recent cleanup report."""
        report_path = os.path.join(REPORTS_DIR, "latest_cleanup_report.json")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"message": "No cleanup has been run yet."}

    def get_storage_stats(self) -> Dict[str, Any]:
        """Return current storage statistics."""
        temp_files = len(os.listdir(TEMP_DIR)) if os.path.exists(TEMP_DIR) else 0
        archive_files = len(os.listdir(ARCHIVE_DIR)) if os.path.exists(ARCHIVE_DIR) else 0

        failed_lines = 0
        failed_path = os.path.join(REPORTS_DIR, "failed_commands.jsonl")
        if os.path.exists(failed_path):
            try:
                with open(failed_path, "r", encoding="utf-8") as f:
                    failed_lines = sum(1 for line in f if line.strip())
            except Exception:
                pass

        report_files = glob.glob(os.path.join(REPORTS_DIR, "batch_*.json"))

        return {
            "temp_files": temp_files,
            "temp_size_mb": _dir_size_mb(TEMP_DIR),
            "archive_files": archive_files,
            "archive_size_mb": _dir_size_mb(ARCHIVE_DIR),
            "failure_log_lines": failed_lines,
            "batch_reports_count": len(report_files),
            "limits": {
                "max_temp_mb": self.max_temp_mb,
                "archive_days": self.archive_days,
                "failure_log_days": self.failure_log_days,
                "keep_latest_reports": self.keep_latest_reports,
            },
        }
