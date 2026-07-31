"""QA Loop runner for Jacx automated testing.

Controls batch lifecycle, resource cleanup, report persistence, stop file checks,
and human approval checkpoints between test batches.
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from jacx_qa.generators.command_generator import CommandGenerator
from jacx_qa.runner.qa_runner import QARunner


def load_config() -> Dict[str, Any]:
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "qa_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[QALoop Warning] Failed to load config from {cfg_path}: {e}")
    return {
        "batch_size": 100,
        "max_batches": 1,
        "loop_enabled": False,
        "require_confirmation_between_batches": True,
        "auto_continue": False,
        "delay_seconds": 1,
        "stop_file": "jacx_qa/STOP_QA",
        "cleanup_after_each_command": True,
        "cleanup_after_each_batch": True,
        "close_browser_after_batch": True,
        "terminate_hanging_processes": True,
        "request_timeout_seconds": 30,
        "save_report_before_cleanup": True,
        "write_reports": True,
        "generate_fix_prompt": True,
        "safe_mode": True,
    }


def update_qa_state(state: str, batch_id: str = "", waiting_approval: bool = False, batch_summary: Dict[str, Any] = None):
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    state_path = os.path.join(reports_dir, "qa_state.json")

    current_data = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            pass

    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    total_batches = current_data.get("total_batches_run", 0)
    total_tested = current_data.get("total_commands_tested", 0)
    total_passed = current_data.get("total_commands_passed", 0)
    total_failed = current_data.get("total_commands_failed", 0)
    history = current_data.get("batches_history", [])

    if batch_summary and state in ("batch_completed_waiting_for_approval", "idle"):
        existing_ids = [h.get("batch_id") for h in history if isinstance(h, dict)]
        if not batch_id or batch_id not in existing_ids:
            total_batches += 1
            b_tested = batch_summary.get("total_tested", 0)
            b_passed = batch_summary.get("passed_count", 0)
            b_failed = batch_summary.get("failed_count", 0)
            b_pass_rate = batch_summary.get("pass_rate_percent", 0.0)

            total_tested += b_tested
            total_passed += b_passed
            total_failed += b_failed

            history.append({
                "batch_id": batch_id,
                "timestamp": now_str,
                "tested": b_tested,
                "passed": b_passed,
                "failed": b_failed,
                "pass_rate_percent": b_pass_rate,
            })
            history = history[-20:]

    overall_pass_rate = round((total_passed / total_tested * 100), 1) if total_tested > 0 else 0.0

    state_obj = {
        "qa_state": state,
        "last_batch_id": batch_id or current_data.get("last_batch_id", ""),
        "last_report_path": "jacx_qa/reports/latest_report.json",
        "last_fix_prompt_path": "jacx_qa/reports/opencode_fix_prompt.md",
        "waiting_for_user_approval": waiting_approval,
        "last_started_at": current_data.get("last_started_at", now_str) if state != "running" else now_str,
        "last_completed_at": now_str if state in ("batch_completed_waiting_for_approval", "stopped") else current_data.get("last_completed_at", ""),
        "total_batches_run": total_batches,
        "total_commands_tested": total_tested,
        "total_commands_passed": total_passed,
        "total_commands_failed": total_failed,
        "overall_pass_rate_percent": overall_pass_rate,
        "batches_history": history,
    }

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state_obj, f, indent=2)


def check_stop_file(config: Dict[str, Any]) -> bool:
    stop_file = config.get("stop_file", "jacx_qa/STOP_QA")
    return os.path.exists(stop_file)


def run_qa_loop(config: Dict[str, Any], interactive: bool = True):
    """Main loop controller for Jacx Auto-QA batch execution."""
    stop_file = config.get("stop_file", "jacx_qa/STOP_QA")
    if os.path.exists(stop_file):
        print(f"[QALoop] Stop file exists at '{stop_file}'. Remove it before running QA loop.")
        return

    batch_size = config.get("batch_size", 100)
    max_batches = config.get("max_batches", 1)
    loop_enabled = config.get("loop_enabled", False)
    require_approval = config.get("require_confirmation_between_batches", True)
    auto_continue = config.get("auto_continue", False)

    generator = CommandGenerator()
    runner = QARunner(config)

    batches_run = 0
    brain_optimize_interval = config.get("brain_optimize_interval_batches", 25)

    while True:
        if check_stop_file(config):
            print("\n[QALoop] STOP_QA file detected. Stopping QA loop safely.")
            update_qa_state("stopped", waiting_approval=False)
            break

        batches_run += 1
        batch_id = f"batch_{int(time.time())}"
        print(f"\n==================================================")
        print(f" STARTING QA BATCH {batches_run} (ID: {batch_id})")
        print(f"==================================================")
        update_qa_state("running", batch_id=batch_id, waiting_approval=False)

        # 1. Generate varied test commands
        commands = generator.generate_batch(batch_size)

        # 2. Run batch and capture results
        batch_output = runner.run_batch(commands, batch_id=batch_id)
        analysis = batch_output["analysis"]

        # 3. Display Learn → Distill → Forget results
        distill = batch_output.get("distill", {})
        cleanup = batch_output.get("cleanup", {})
        if distill:
            print(f"\n[Learn > Distill > Forget]")
            print(f"  Rules distilled: {distill.get('distilled', 0)}")
            print(f"  Rules merged: {distill.get('merged', 0)}")
            print(f"  Failures skipped: {distill.get('skipped', 0)}")
        if cleanup:
            print(f"  Cleanup: {cleanup.get('temp_archived', 0)} archived, "
                  f"{cleanup.get('archive_deleted', 0)} expired, "
                  f"{cleanup.get('failure_lines_pruned', 0)} failure lines pruned, "
                  f"{cleanup.get('reports_pruned', 0)} reports pruned")

        # 4. Brain optimization every N batches
        if batches_run % brain_optimize_interval == 0:
            print(f"\n[Brain Optimization] Running optimization after {batches_run} batches...")
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "jacx_brain"))
                from brain_manager import BrainManager
                brain = BrainManager()
                opt_result = brain.optimize()
                print(f"  Rules before: {opt_result['initial_rules']}, after: {opt_result['final_rules']}")
                print(f"  Duplicates merged: {opt_result['merged_duplicates']}")
                print(f"  Obsolete removed: {opt_result['removed_obsolete']}")
                print(f"  Confidence adjusted: {opt_result['confidence_adjusted']}")
            except Exception as e:
                print(f"  [Warning] Brain optimization failed: {e}")

        # 5. Check for migration regression and auto-rollback if needed
        try:
            sys.path.insert(0, PROJECT_ROOT)
            from openjarvis.step1.pipeline_integration import check_qa_regression_and_rollback
            report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "latest_report.json")
            if os.path.exists(report_path):
                rollback_triggered = check_qa_regression_and_rollback(report_path, threshold=100.0)
                if rollback_triggered:
                    print("\n[MIGRATION] Auto-rollback triggered due to QA regression!")
        except Exception as e:
            print(f"\n[MIGRATION] Warning: Could not check migration regression: {e}")

        # 6. Update state to completed & waiting for approval
        update_qa_state("batch_completed_waiting_for_approval", batch_id=batch_id, waiting_approval=True, batch_summary=analysis)

        # 7. Display human approval checkpoint summary
        print(f"\n[BATCH PROGRESS] BATCH {batches_run} OF {max_batches} DONE! ({analysis['passed_count']}/{analysis['total_tested']} passed - {analysis['pass_rate_percent']}%)")
        print(f"QA batch completed.")
        print(f"Commands tested: {analysis['total_tested']}")
        print(f"Passed: {analysis['passed_count']}")
        print(f"Failed: {analysis['failed_count']}")
        print(f"Pass rate: {analysis['pass_rate_percent']}%")
        print(f"Top bug category: {analysis['top_bug_category']}")
        print(f"Report saved to: jacx_qa/reports/latest_report.json")
        print(f"Fix prompt saved to: jacx_qa/reports/opencode_fix_prompt.md")
        print(f"Resources cleaned: yes.")

        # Check exit conditions
        if not loop_enabled and batches_run >= max_batches:
            print("\n[QALoop] Max batches limit reached. Loop finished cleanly.")
            update_qa_state("idle", batch_id=batch_id, waiting_approval=False, batch_summary=analysis)
            break

        # 7. Check human approval before starting next batch
        if require_approval and not auto_continue:
            print("\nDo you want to run the next batch?")
            if interactive:
                try:
                    user_input = input("(yes/no): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    user_input = "no"

                valid_affirmatives = ["yes", "continue", "run next batch", "continue qa loop", "yes run next batch"]
                if user_input in valid_affirmatives:
                    print("[QALoop] Explicit approval received. Proceeding to next batch...")
                    continue
                else:
                    print("[QALoop] User declined or requested stop. Halting QA loop.")
                    update_qa_state("stopped", batch_id=batch_id, waiting_approval=False)
                    break
            else:
                print("[QALoop] Non-interactive mode: Waiting for explicit user approval command before starting next batch.")
                break
        elif auto_continue:
            print("[QALoop] Auto-continue enabled in config. Starting next batch in 3 seconds...")
            time.sleep(3)
        else:
            break


def main():
    parser = argparse.ArgumentParser(description="Jacx Auto-QA Loop Runner")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of commands per batch (default 100)")
    parser.add_argument("--max-batches", type=int, default=1, help="Max batches to run (default 1)")
    parser.add_argument("--loop", action="store_true", help="Enable loop mode (requires approval between batches by default)")
    parser.add_argument("--auto-continue", action="store_true", help="Auto-continue between batches without prompt")
    parser.add_argument("--stop", action="store_true", help="Create STOP_QA file to stop active loop")
    parser.add_argument("--resume", action="store_true", help="Remove STOP_QA file")
    parser.add_argument("--status", action="store_true", help="Print current QA loop state")
    args = parser.parse_args()

    config = load_config()
    stop_file = config.get("stop_file", "jacx_qa/STOP_QA")

    if args.stop:
        with open(stop_file, "w", encoding="utf-8") as f:
            f.write("STOP")
        print(f"[QALoop] Created stop file '{stop_file}'. QA loop will halt.")
        update_qa_state("stopped", waiting_approval=False)
        return

    if args.resume:
        if os.path.exists(stop_file):
            os.remove(stop_file)
            print(f"[QALoop] Removed stop file '{stop_file}'. QA loop ready.")
        update_qa_state("idle", waiting_approval=False)
        return

    if args.status:
        state_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "qa_state.json")
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("No qa_state.json found.")
        return

    config["batch_size"] = args.batch_size
    config["max_batches"] = args.max_batches if not args.loop else 9999
    config["loop_enabled"] = args.loop
    if args.auto_continue:
        config["auto_continue"] = True
        config["require_confirmation_between_batches"] = False

    run_qa_loop(config, interactive=True)


if __name__ == "__main__":
    main()
