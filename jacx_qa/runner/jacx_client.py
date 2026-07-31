"""Jacx Client for sending commands to Jacx assistant.

Supports HTTP endpoint execution with timeout protection and fallback to direct
Python pipeline invocation when the backend server is running in-process.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

# Ensure openjarvis source path is in sys.path
PROJECT_ROOT = r"C:\jarvis\veyra-openjarvis-base"
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Environment flags for full Step 1-5 support
os.environ["ENABLE_SUPABASE"] = "true"
os.environ["ENABLE_STEP_1_BASIC_COMMANDS"] = "true"
os.environ["ENABLE_LOCAL_APP_OPENING"] = "true"
os.environ["ENABLE_STEP_2_BROWSER_SEARCH"] = "true"
os.environ["ENABLE_LOCAL_WEBSITE_OPENING"] = "true"
os.environ["ENABLE_LOCAL_BROWSER_SEARCH"] = "true"
os.environ["OMNIROUTE_ENABLED"] = "false"
os.environ["OMNIROUTE_BASE_URL"] = os.environ.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")
os.environ["OMNIROUTE_TIMEOUT_SECONDS"] = "1"


class JacxClient:
    """Client interface for executing test commands against Jacx."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_url = self.config.get("jacx_base_url", "http://localhost:5173")
        self.backend_url = self.config.get("backend_command_url", "http://localhost:8000/veyra/command")
        self.timeout = 2

        # Pre-import direct Python modules for fallback/in-process execution
        self._python_pipeline_available = False
        try:
            from openjarvis.step1.intent_router import classify_intent
            from openjarvis.step1.command_pipeline import run_pipeline
            from openjarvis.step1.cloud_brain.safety import should_use_cloud_brain
            self.classify_intent = classify_intent
            self.run_pipeline = run_pipeline
            self.should_use_cloud_brain = should_use_cloud_brain
            self._python_pipeline_available = True
        except ImportError as e:
            print(f"[JacxClient Warning] Could not import openjarvis direct pipeline: {e}")

    def send_command(self, command_text: str) -> Dict[str, Any]:
        """Send a command string to Jacx backend and return captured telemetry."""
        start_time = time.time()
        result = {
            "input": command_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_response": "",
            "text_response_returned": False,
            "route": "",
            "intent": {},
            "tool": "",
            "tool_executed": False,
            "cloud_used": False,
            "memory_used": False,
            "query_used": "",
            "query_used_by_browser_tool": "",
            "browser_used": "",
            "safety_blocked": False,
            "error": "",
            "debug_output": {},
            "elapsed_seconds": 0.0,
        }

        # Prefer Python direct execution (fast, no network)
        if self._python_pipeline_available:
            self._send_python_direct(command_text, result)
        else:
            self._send_http(command_text, result)

        result["elapsed_seconds"] = round(time.time() - start_time, 3)
        return result

    def _send_http(self, command_text: str, result: Dict[str, Any]) -> bool:
        """Attempt to send command over HTTP to the backend URL."""
        urls_to_try = [
            self.backend_url,
            "http://localhost:8000/v1/step1/commands/execute",
            "http://localhost:8000/api/command",
        ]

        payload = json.dumps({"text": command_text, "command": command_text, "input_source": "qa_runner"}).encode("utf-8")

        for url in urls_to_try:
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        self._parse_response_payload(data, result)
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
                continue
        return False

    def _send_python_direct(self, command_text: str, result: Dict[str, Any]):
        """Execute command using in-process openjarvis modules."""
        try:
            intent_obj = self.classify_intent(command_text)
            result["route"] = getattr(intent_obj, "route", "")
            result["tool"] = getattr(intent_obj, "tool_needed", "") or ""
            result["intent"] = {
                "action": getattr(intent_obj, "action", ""),
                "target": getattr(intent_obj, "target", ""),
                "confidence": getattr(intent_obj, "confidence", 0.0),
                "browser_source": getattr(intent_obj, "browser_source", ""),
                "query": getattr(intent_obj, "query", ""),
            }

            should_cloud, cloud_reason = self.should_use_cloud_brain(
                command_text, intent_obj.action, intent_obj.target, intent_obj.confidence
            )
            result["cloud_used"] = bool(should_cloud)

            # Check if intent was safety blocked directly
            if result["route"] == "safety_block":
                result["safety_blocked"] = True
                result["actual_response"] = "Security block: Operation prohibited for safety."
                result["text_response_returned"] = True
                return

            # Execute pipeline
            pipeline_resp = self.run_pipeline(command_text, input_source="qa_runner")
            msg = getattr(pipeline_resp, "message", "") or ""
            result["actual_response"] = msg
            result["text_response_returned"] = bool(msg.strip())
            result["tool_executed"] = bool(getattr(pipeline_resp, "ok", False))

            if hasattr(pipeline_resp, "query") and pipeline_resp.query:
                result["query_used"] = pipeline_resp.query
            if hasattr(pipeline_resp, "browser") and pipeline_resp.browser:
                result["browser_used"] = pipeline_resp.browser
            if "memory" in result["route"]:
                result["memory_used"] = True

            # Capture query_used_by_browser_tool from response data if available
            if hasattr(pipeline_resp, "data") and isinstance(pipeline_resp.data, dict):
                if "query_used_by_browser_tool" in pipeline_resp.data:
                    result["query_used_by_browser_tool"] = pipeline_resp.data["query_used_by_browser_tool"]

        except Exception as e:
            result["error"] = str(e)
            result["actual_response"] = f"Pipeline execution error: {str(e)}"

    def _parse_response_payload(self, data: Dict[str, Any], result: Dict[str, Any]):
        """Extract standardized result fields from HTTP response JSON."""
        result["actual_response"] = data.get("message") or data.get("response") or data.get("text") or ""
        result["text_response_returned"] = bool(result["actual_response"].strip())
        result["route"] = data.get("route") or data.get("intent_route") or ""
        result["tool"] = data.get("tool") or data.get("tool_needed") or ""
        result["tool_executed"] = data.get("ok", True)
        result["cloud_used"] = data.get("cloud_used", False)
        result["memory_used"] = data.get("memory_used", False)
        result["query_used"] = data.get("query_used", "")
        result["browser_used"] = data.get("browser_used", "")
        result["safety_blocked"] = data.get("safety_blocked", False) or result["route"] == "safety_block"
        result["error"] = data.get("error", "")
        result["debug_output"] = data.get("debug", {})


if __name__ == "__main__":
    client = JacxClient()
    res = client.send_command("open calculator")
    print("Test JacxClient output:", res)
