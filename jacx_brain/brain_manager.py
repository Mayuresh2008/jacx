"""Brain Manager for Jacx knowledge persistence.

Manages the 4-tier knowledge system:
  Tier 1: Raw batch data (jacx_qa/temp/) - ephemeral, deleted after analysis
  Tier 2: Failure logs (jacx_qa/reports/failed_commands.jsonl) - 30-day retention
  Tier 3: Distilled rules (jacx_brain/rules/) - permanent generalized knowledge
  Tier 4: Statistics (jacx_brain/stats/) - permanent aggregate metrics

Provides duplicate detection, rule merging, confidence adjustment,
and storage lifecycle management.
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta


BRAIN_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES_DIR = os.path.join(BRAIN_ROOT, "rules")
STATS_DIR = os.path.join(BRAIN_ROOT, "stats")
CONFIG_PATH = os.path.join(BRAIN_ROOT, "config", "brain_config.json")


def _load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _days_ago_iso(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def _file_age_days(filepath: str) -> float:
    if not os.path.exists(filepath):
        return 0
    mtime = os.path.getmtime(filepath)
    age_seconds = time.time() - mtime
    return age_seconds / 86400


def _rule_id(rule: Dict[str, Any]) -> str:
    """Generate a deterministic ID for a rule based on its core content."""
    key_parts = [
        rule.get("bug_type", ""),
        rule.get("category", ""),
        rule.get("root_cause", ""),
    ]
    raw = "|".join(key_parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class BrainManager:
    """Manages Jacx's permanent knowledge base."""

    def __init__(self):
        os.makedirs(RULES_DIR, exist_ok=True)
        os.makedirs(STATS_DIR, exist_ok=True)
        self.config = _load_config()
        self.limits = self.config.get("storage_limits", {})
        self.distill_cfg = self.config.get("distillation", {})

    # ── Rule CRUD ──────────────────────────────────────────────────────

    def load_all_rules(self) -> List[Dict[str, Any]]:
        """Load all distilled rules from jacx_brain/rules/."""
        rules = []
        if not os.path.exists(RULES_DIR):
            return rules
        for fname in sorted(os.listdir(RULES_DIR)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(RULES_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        rules.extend(data)
                    else:
                        rules.append(data)
            except Exception:
                pass
        return rules

    def save_rule(self, rule: Dict[str, Any]) -> str:
        """Save a single rule. Returns the rule file path."""
        rule_id = rule.get("rule_id") or _rule_id(rule)
        rule["rule_id"] = rule_id
        if "created_at" not in rule:
            rule["created_at"] = _now_iso()
        rule["updated_at"] = _now_iso()

        bug_type = rule.get("bug_type", "general")
        filename = f"{bug_type}_{rule_id}.json"
        fpath = os.path.join(RULES_DIR, filename)

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(rule, f, indent=2)

        return fpath

    def save_rules_batch(self, rules: List[Dict[str, Any]]) -> int:
        """Save multiple rules. Returns count saved."""
        count = 0
        for rule in rules:
            try:
                self.save_rule(rule)
                count += 1
            except Exception:
                pass
        return count

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by its ID."""
        for fname in os.listdir(RULES_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(RULES_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("rule_id") == rule_id:
                    os.remove(fpath)
                    return True
            except Exception:
                pass
        return False

    # ── Duplicate Detection ────────────────────────────────────────────

    def find_similar_rules(self, new_rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find existing rules similar to a new rule."""
        existing = self.load_all_rules()
        if not existing:
            return []

        threshold = self.distill_cfg.get("merge_similarity_threshold", 0.75)
        similar = []

        new_key = new_rule.get("bug_type", "") + "|" + new_rule.get("category", "")
        new_cause = new_rule.get("root_cause", "").lower()

        for rule in existing:
            existing_key = rule.get("bug_type", "") + "|" + rule.get("category", "")
            if existing_key != new_key:
                continue

            existing_cause = rule.get("root_cause", "").lower()
            similarity = self._text_similarity(new_cause, existing_cause)
            if similarity >= threshold:
                similar.append(rule)

        return similar

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple token-overlap similarity for short strings."""
        if not a or not b:
            return 0.0
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union) if union else 0.0

    def merge_or_create_rule(self, new_rule: Dict[str, Any]) -> Tuple[bool, str]:
        """Merge with existing rule or create new one. Returns (was_merged, rule_id)."""
        similar = self.find_similar_rules(new_rule)
        if not similar:
            rule_id = self.save_rule(new_rule)
            return False, new_rule.get("rule_id", _rule_id(new_rule))

        best = max(similar, key=lambda r: r.get("confidence", 0.5))
        best["confidence"] = min(1.0, best.get("confidence", 0.5) + 0.05)
        best["occurrences"] = best.get("occurrences", 1) + 1
        best["updated_at"] = _now_iso()
        if new_rule.get("example_failures"):
            existing_examples = best.get("example_failures", [])
            merged = existing_examples + new_rule["example_failures"]
            best["example_failures"] = merged[-10:]
        self.save_rule(best)
        return True, best.get("rule_id", _rule_id(best))

    # ── Statistics ─────────────────────────────────────────────────────

    def load_stats(self) -> Dict[str, Any]:
        stats_path = os.path.join(STATS_DIR, "brain_stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "total_rules": 0,
            "total_batches_analyzed": 0,
            "total_failures_distilled": 0,
            "total_duplicates_merged": 0,
            "last_optimized_at": "",
            "last_distilled_at": "",
            "bug_type_rule_counts": {},
            "confidence_distribution": {"low": 0, "medium": 0, "high": 0},
        }

    def save_stats(self, stats: Dict[str, Any]):
        stats_path = os.path.join(STATS_DIR, "brain_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

    def update_stats(self, **kwargs):
        stats = self.load_stats()
        stats.update(kwargs)
        self.save_stats(stats)

    def increment_stat(self, key: str, amount: int = 1):
        stats = self.load_stats()
        stats[key] = stats.get(key, 0) + amount
        self.save_stats(stats)

    # ── Brain Optimization ─────────────────────────────────────────────

    def optimize(self) -> Dict[str, Any]:
        """Run full brain optimization: merge duplicates, remove obsolete, adjust confidence."""
        rules = self.load_all_rules()
        initial_count = len(rules)
        merged_count = 0
        removed_count = 0
        confidence_adjusted = 0

        groups: Dict[str, List[Dict[str, Any]]] = {}
        for rule in rules:
            key = rule.get("bug_type", "") + "|" + rule.get("category", "")
            groups.setdefault(key, []).append(rule)

        kept_rules = []
        for key, group in groups.items():
            if len(group) == 1:
                kept_rules.append(group[0])
                continue

            group.sort(key=lambda r: r.get("confidence", 0.5), reverse=True)
            best = group[0]
            for duplicate in group[1:]:
                merged_count += 1
                dup_count = duplicate.get("occurrences", 1)
                best["occurrences"] = best.get("occurrences", 1) + dup_count
                dup_examples = duplicate.get("example_failures", [])
                if dup_examples:
                    best_examples = best.get("example_failures", [])
                    best["example_failures"] = (best_examples + dup_examples)[-10:]
            kept_rules.append(best)

        final_rules = []
        for rule in kept_rules:
            occurrences = rule.get("occurrences", 1)
            if occurrences <= 1 and rule.get("confidence", 0.5) < 0.3:
                removed_count += 1
                continue

            if occurrences >= 5:
                old_conf = rule.get("confidence", 0.5)
                rule["confidence"] = min(1.0, old_conf + 0.1)
                if rule["confidence"] != old_conf:
                    confidence_adjusted += 1

            final_rules.append(rule)

        for rule in kept_rules:
            if rule not in final_rules:
                self.delete_rule(rule.get("rule_id", ""))

        for rule in final_rules:
            self.save_rule(rule)

        stats = self.load_stats()
        stats["total_rules"] = len(final_rules)
        stats["total_duplicates_merged"] = stats.get("total_duplicates_merged", 0) + merged_count
        stats["last_optimized_at"] = _now_iso()
        bug_counts = {}
        for r in final_rules:
            bt = r.get("bug_type", "unknown")
            bug_counts[bt] = bug_counts.get(bt, 0) + 1
        stats["bug_type_rule_counts"] = bug_counts
        low = sum(1 for r in final_rules if r.get("confidence", 0.5) < 0.4)
        med = sum(1 for r in final_rules if 0.4 <= r.get("confidence", 0.5) < 0.7)
        high = sum(1 for r in final_rules if r.get("confidence", 0.5) >= 0.7)
        stats["confidence_distribution"] = {"low": low, "medium": med, "high": high}
        self.save_stats(stats)

        return {
            "initial_rules": initial_count,
            "final_rules": len(final_rules),
            "merged_duplicates": merged_count,
            "removed_obsolete": removed_count,
            "confidence_adjusted": confidence_adjusted,
        }

    # ── Size / Stats Queries ───────────────────────────────────────────

    def get_brain_size(self) -> Dict[str, Any]:
        """Return size metrics for the brain."""
        rules = self.load_all_rules()
        stats = self.load_stats()

        rules_bytes = 0
        if os.path.exists(RULES_DIR):
            for f in os.listdir(RULES_DIR):
                fp = os.path.join(RULES_DIR, f)
                if os.path.isfile(fp):
                    rules_bytes += os.path.getsize(fp)

        return {
            "total_rules": len(rules),
            "rules_size_bytes": rules_bytes,
            "rules_size_kb": round(rules_bytes / 1024, 2),
            "total_batches_analyzed": stats.get("total_batches_analyzed", 0),
            "total_failures_distilled": stats.get("total_failures_distilled", 0),
            "total_duplicates_merged": stats.get("total_duplicates_merged", 0),
            "last_optimized_at": stats.get("last_optimized_at", "never"),
            "last_distilled_at": stats.get("last_distilled_at", "never"),
            "bug_type_rule_counts": stats.get("bug_type_rule_counts", {}),
            "confidence_distribution": stats.get("confidence_distribution", {}),
        }

    def get_rule_statistics(self) -> Dict[str, Any]:
        """Detailed statistics about all rules."""
        rules = self.load_all_rules()
        if not rules:
            return {"total": 0, "rules": []}

        rule_summaries = []
        for r in rules:
            rule_summaries.append({
                "rule_id": r.get("rule_id", ""),
                "bug_type": r.get("bug_type", ""),
                "category": r.get("category", ""),
                "root_cause": r.get("root_cause", "")[:100],
                "confidence": r.get("confidence", 0.5),
                "occurrences": r.get("occurrences", 1),
                "created_at": r.get("created_at", ""),
                "updated_at": r.get("updated_at", ""),
            })

        return {
            "total": len(rules),
            "rules": rule_summaries,
        }
