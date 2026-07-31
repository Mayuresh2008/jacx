"""QA Runner for executing command batches and managing resource lifecycles.

Tracks QA-owned browser contexts, pages, subprocesses, pending requests, temporary files,
and timers. Executes per-command and per-batch resource cleanup.
"""

import os
import gc
import sys
import json
import time
import subprocess
from typing import Dict, Any, List, Optional

from jacx_qa.runner.jacx_client import JacxClient
from jacx_qa.analyzers.result_analyzer import ResultAnalyzer
from jacx_qa.analyzers.pattern_analyzer import PatternAnalyzer
from jacx_qa.analyzers.prompt_generator import PromptGenerator
from jacx_qa.cleanup import QACleanup


class QAOwnedResources:
    """Tracks resources instantiated specifically by the QA test runner."""

    def __init__(self):
        self.browser_contexts: List[Any] = []
        self.browser_pages: List[Any] = []
        self.subprocesses: List[subprocess.Popen] = []
        self.pending_requests: List[Any] = []
        self.temporary_files: List[str] = []
        self.timers: List[Any] = []

    def clear(self):
        self.browser_contexts.clear()
        self.browser_pages.clear()
        self.subprocesses.clear()
        self.pending_requests.clear()
        self.temporary_files.clear()
        self.timers.clear()


class QARunner:
    """Batch executor with per-command and per-batch cleanup protections."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = JacxClient(config)
        self.analyzer = ResultAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        self.prompt_generator = PromptGenerator()
        self.resources = QAOwnedResources()
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def run_single_command(self, cmd_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single command with per-command cleanup protection."""
        text = cmd_obj.get("input", "")
        raw_result = self.client.send_command(text)
        eval_result = self.analyzer.evaluate(cmd_obj, raw_result)

        # Per-command cleanup
        if self.config.get("cleanup_after_each_command", True):
            self._cleanup_per_command()

        return eval_result

    def run_batch(self, commands: List[Dict[str, Any]], batch_id: str = "") -> Dict[str, Any]:
        """Run a batch of test commands, evaluate results, and save reports."""
        if not batch_id:
            batch_id = f"batch_{int(time.time())}"

        batch_results = []
        start_time = time.time()

        for idx, cmd in enumerate(commands, 1):
            # Check stop file before executing each command
            stop_file = self.config.get("stop_file", "jacx_qa/STOP_QA")
            if os.path.exists(stop_file):
                print(f"\n[QARunner] STOP_QA file detected at command {idx}/{len(commands)}. Halting batch.")
                break

            cmd["batch_id"] = batch_id
            eval_res = self.run_single_command(cmd)
            batch_results.append(eval_res)

            delay = self.config.get("delay_seconds", 0)
            if delay > 0 and idx < len(commands):
                time.sleep(delay)

        elapsed = round(time.time() - start_time, 2)
        analysis = self.pattern_analyzer.analyze(batch_results)
        analysis["batch_id"] = batch_id
        analysis["elapsed_seconds"] = elapsed

        fix_prompt = self.prompt_generator.generate_fix_prompt(analysis)

        # Save report outputs
        if self.config.get("write_reports", True):
            self.save_reports(batch_id, batch_results, analysis, fix_prompt)

        # Candidate mistakes integration with jacx_brain if present
        self._record_candidate_mistakes(batch_results)

        # Learn → Distill: Extract permanent rules from failures
        distill_result = self._distill_rules(batch_results, batch_id)

        # Archive batch data to temp for cleanup lifecycle
        self._archive_batch_data(batch_id, batch_results, analysis)

        # Per-batch cleanup of QA-owned resources
        if self.config.get("cleanup_after_each_batch", True):
            self.cleanup_batch()

        # Forget: Run automatic cleanup of old data
        cleanup = QACleanup()
        cleanup_report = cleanup.run_full_cleanup()

        return {
            "batch_id": batch_id,
            "results": batch_results,
            "analysis": analysis,
            "fix_prompt": fix_prompt,
            "distill": distill_result,
            "cleanup": cleanup_report,
        }

    def _cleanup_per_command(self):
        """Clean temporary resources created during single command execution."""
        # Close QA-owned browser pages if exceeding max allowed limit
        max_pages = self.config.get("max_open_browser_pages", 3)
        while len(self.resources.browser_pages) > max_pages:
            page = self.resources.browser_pages.pop(0)
            try:
                if hasattr(page, "close"):
                    page.close()
            except Exception:
                pass

        # Clear pending request references
        self.resources.pending_requests.clear()

    def cleanup_batch(self):
        """Clean all QA-owned resources instantiated across the batch."""
        # 1. Close QA-owned browser pages
        for page in list(self.resources.browser_pages):
            try:
                if hasattr(page, "close"):
                    page.close()
            except Exception:
                pass
        self.resources.browser_pages.clear()

        # 2. Close QA-owned browser contexts
        for ctx in list(self.resources.browser_contexts):
            try:
                if hasattr(ctx, "close"):
                    ctx.close()
            except Exception:
                pass
        self.resources.browser_contexts.clear()

        # 3. Terminate QA-owned subprocesses
        for proc in list(self.resources.subprocesses):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.resources.subprocesses.clear()

        # 4. Clean temporary QA files
        for tmp_file in list(self.resources.temporary_files):
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
        self.resources.temporary_files.clear()

        # 5. Trigger garbage collection
        gc.collect()

    def save_reports(self, batch_id: str, results: List[Dict[str, Any]], analysis: Dict[str, Any], fix_prompt: str):
        """Write report files: latest_report.json, latest_report.md, failed_commands.jsonl, etc."""
        # 1. latest_report.json
        json_path = os.path.join(self.reports_dir, "latest_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"summary": analysis, "results": results}, f, indent=2)

        # 2. latest_report.md
        md_path = os.path.join(self.reports_dir, "latest_report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Jacx QA Batch Report ({batch_id})\n\n")
            f.write(f"- **Batch ID**: {batch_id}\n")
            f.write(f"- **Total Tested**: {analysis['total_tested']}\n")
            f.write(f"- **Passed**: {analysis['passed_count']}\n")
            f.write(f"- **Failed**: {analysis['failed_count']}\n")
            f.write(f"- **Pass Rate**: {analysis['pass_rate_percent']}%\n")
            f.write(f"- **Top Bug Category**: {analysis['top_bug_category']}\n\n")
            f.write("## Bug Type Breakdown\n")
            for bug, count in analysis.get("bug_type_counts", {}).items():
                f.write(f"- `{bug}`: {count}\n")
            f.write("\n## System Diagnoses\n")
            for diag in analysis.get("system_diagnoses", []):
                f.write(f"### {diag['component']}\n- {diag['root_cause']}\n- **Remediation**: {diag['remediation']}\n\n")

        # 3. failed_commands.jsonl
        failed_path = os.path.join(self.reports_dir, "failed_commands.jsonl")
        with open(failed_path, "w", encoding="utf-8") as f:
            for r in results:
                if not r.get("passed", False):
                    f.write(json.dumps(r) + "\n")

        # 4. pass_fail_summary.json
        summary_path = os.path.join(self.reports_dir, "pass_fail_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)

        # 5. opencode_fix_prompt.md
        prompt_path = os.path.join(self.reports_dir, "opencode_fix_prompt.md")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(fix_prompt)

    def _record_candidate_mistakes(self, results: List[Dict[str, Any]]):
        """Record candidate mistakes for jacx_brain dataset if available."""
        brain_dir = r"C:\jarvis\jacx_brain\examples"
        if not os.path.exists(brain_dir):
            try:
                os.makedirs(brain_dir, exist_ok=True)
            except Exception:
                return

        candidate_file = os.path.join(brain_dir, "candidate_mistakes.jsonl")
        try:
            with open(candidate_file, "a", encoding="utf-8") as f:
                for r in results:
                    if not r.get("passed", False):
                        entry = {
                            "failed_command": r.get("input", ""),
                            "bad_behavior": r.get("actual_response", "") or r.get("fail_reasons", ["No response"])[0],
                            "expected_behavior_rule": r.get("category", ""),
                            "bug_type": r.get("bug_type", ""),
                            "needs_review": True,
                        }
                        f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[QARunner Warning] Could not write candidate mistakes: {e}")

    def _distill_rules(self, results: List[Dict[str, Any]], batch_id: str) -> Dict[str, Any]:
        """Learn → Distill: Extract permanent generalized rules from batch failures."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "jacx_brain"))
            from distiller import RuleDistiller
            distiller = RuleDistiller()
            return distiller.distill_from_batch(results, batch_id)
        except Exception as e:
            print(f"[QARunner Warning] Distillation failed: {e}")
            return {"distilled": 0, "merged": 0, "skipped": 0, "rules": [], "error": str(e)}

    def _archive_batch_data(self, batch_id: str, results: List[Dict[str, Any]], analysis: Dict[str, Any]):
        """Archive batch data to temp directory for cleanup lifecycle."""
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        archive_path = os.path.join(temp_dir, f"{batch_id}.json")
        try:
            with open(archive_path, "w", encoding="utf-8") as f:
                json.dump({
                    "batch_id": batch_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": analysis,
                    "result_count": len(results),
                }, f, indent=2)
        except Exception as e:
            print(f"[QARunner Warning] Could not archive batch data: {e}")


if __name__ == "__main__":
    cfg = {"batch_size": 2, "cleanup_after_each_batch": True}
    runner = QARunner(cfg)
    test_cmds = [
        {"test_id": "TC-001", "category": "memory_save", "input": "remember browser is brave"},
        {"test_id": "TC-002", "category": "preferred_browser_search", "input": "use saved browser to search rust"},
    ]
    res = runner.run_batch(test_cmds, "test_batch_001")
    print("Test QARunner execution complete. Pass rate:", res["analysis"]["pass_rate_percent"], "%")
