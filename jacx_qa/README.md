# Jacx Auto-QA System

Automated Quality Assurance & Intent-Based Testing System for Jacx Assistant.

## Overview
The Jacx Auto-QA system repeatedly tests Jacx with varied, intent-based natural language commands, records detailed pass/fail results, groups failure patterns by root cause, generates a ready-to-paste OpenCode system-level fix prompt, cleans up all QA-owned resources, and requests explicit user permission before starting subsequent test batches.

## Features
- **Varied Intent Command Generator**: Dynamically generates test commands across 21 intent categories with varied phrasing (short, casual, long, memory-referenced, typo-tolerant, vague, unsafe).
- **Rule-Based Pass/Fail Evaluator**: Evaluates behavior using general contract rules (`must` and `must_not`), not hardcoded exact match strings.
- **Resource Cleanup & Ownership**: Tracks QA-spawned resources (browser tabs, subprocesses, async requests, temp files) and cleans them after each command and batch without touching user or server processes.
- **Root-Cause Pattern Analysis**: Groups failed tests by system module (query extractor, route selection, memory, response pipeline, cloud fallback, safety).
- **OpenCode Fix Prompt Generator**: Produces `opencode_fix_prompt.md` focusing on general architectural fixes rather than hardcoding failed command strings.
- **Human Approval Checkpoint**: Halts execution after each 100-command batch and prompts the user for explicit confirmation before continuing.
- **Stop File Control**: Supports immediate batch halting via `jacx_qa/STOP_QA`.

## Directory Structure
```
jacx_qa/
  README.md
  config/
    qa_config.json
    test_categories.json
    expected_behavior_rules.json
  generators/
    command_generator.py
  runner/
    jacx_client.py
    qa_runner.py
  analyzers/
    result_analyzer.py
    pattern_analyzer.py
    prompt_generator.py
  reports/
    latest_report.json
    latest_report.md
    failed_commands.jsonl
    pass_fail_summary.json
    opencode_fix_prompt.md
    qa_state.json
  loops/
    qa_loop.py
  tests/
    test_command_generator.py
    test_result_analyzer.py
```

## How to Run

### Run a Single Batch (100 commands)
```bash
python jacx_qa/loops/qa_loop.py --batch-size 100 --max-batches 1
```

### Run Loop Mode with Approval Between Batches
```bash
python jacx_qa/loops/qa_loop.py --batch-size 100 --loop
```

### Stop QA Loop
Create the stop file:
```bash
touch jacx_qa/STOP_QA
```
or run:
```bash
python jacx_qa/loops/qa_loop.py --stop
```

### Run Unit Tests
```bash
python -m unittest discover -s jacx_qa/tests
```
