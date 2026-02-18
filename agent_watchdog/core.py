from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math
import time


@dataclass
class WatchdogConfig:
    """
    Minimal configuration for the watchdog.

    freshness_window: how many recent messages are considered "fresh"
    min_freshness_ratio: threshold below which we flag likely drift/loop
    """
    freshness_window: int = 12
    min_freshness_ratio: float = 0.28


@dataclass
class WatchdogResult:
    ok: bool
    freshness_ratio: float
    reason: str
    details: Dict[str, Any]


class AgentWatchdog:
    """
    A lightweight "governor" for agent conversations / traces.
    It computes a simple Freshness Ratio over the last N turns and flags
    likely loop/drift regimes.

    This is intentionally dependency-free: you can wire in embeddings later.
    """

    def __init__(self, config: Optional[WatchdogConfig] = None):
        self.config = config or WatchdogConfig()

    @staticmethod
    def _normalize_text(s: str) -> str:
        s = (s or "").strip().lower()
        # cheap normalization to reduce trivial differences
        for ch in ["\n", "\t", "\r"]:
            s = s.replace(ch, " ")
        while "  " in s:
            s = s.replace("  ", " ")
        return s

    @staticmethod
    def _jaccard(a: str, b: str) -> float:
        """
        Very cheap similarity proxy: token Jaccard.
        1.0 => identical sets, 0.0 => disjoint.
        """
        ta = set(a.split())
        tb = set(b.split())
        if not ta and not tb:
            return 1.0
        if not ta or not tb:
            return 0.0
        inter = len(ta.intersection(tb))
        union = len(ta.union(tb))
        return inter / union if union else 0.0

    def freshness_ratio(self, messages: List[str]) -> float:
        """
        Freshness Ratio heuristic:
        - Take last N messages.
        - Measure how "novel" each message is relative to the previous ones.
        - If new messages are very similar to earlier ones, freshness drops.

        Returns in [0,1].
        """
        if not messages:
            return 1.0

        window = max(2, int(self.config.freshness_window))
        msgs = [self._normalize_text(m) for m in messages][-window:]

        # For each message i, compute max similarity to any earlier message < i.
        # Freshness contribution = 1 - max_sim.
        contribs: List[float] = []
        for i in range(len(msgs)):
            if i == 0:
                contribs.append(1.0)
                continue
            sims = [self._jaccard(msgs[i], msgs[j]) for j in range(i)]
            max_sim = max(sims) if sims else 0.0
            contribs.append(max(0.0, 1.0 - max_sim))

        # Average, clamp
        fr = sum(contribs) / len(contribs)
        return max(0.0, min(1.0, fr))

    def evaluate(self, messages: List[str]) -> WatchdogResult:
        fr = self.freshness_ratio(messages)
        ok = fr >= float(self.config.min_freshness_ratio)

        if ok:
            reason = "freshness_ok"
        else:
            reason = "freshness_low"

        details = {
            "freshness_window": self.config.freshness_window,
            "min_freshness_ratio": self.config.min_freshness_ratio,
            "n_messages": len(messages),
        }

        return WatchdogResult(ok=ok, freshness_ratio=fr, reason=reason, details=details)

    def calibrate_threshold(self, labeled_runs: List[Dict[str, Any]]) -> float:
        """
        Optional helper: given labeled runs, estimate a reasonable threshold.
        Each item: {"messages": [...], "label": "good"|"bad"}.

        Returns a suggested min_freshness_ratio.
        """
        good = []
        bad = []
        for item in labeled_runs:
            msgs = item.get("messages", [])
            label = item.get("label", "")
            fr = self.freshness_ratio(msgs)
            if label == "good":
                good.append(fr)
            elif label == "bad":
                bad.append(fr)

        # If we don't have both, just return current.
        if not good or not bad:
            return self.config.min_freshness_ratio

        # Simple separation: midpoint between bad median and good median.
        good_sorted = sorted(good)
        bad_sorted = sorted(bad)
        good_med = good_sorted[len(good_sorted) // 2]
        bad_med = bad_sorted[len(bad_sorted) // 2]

        suggested = (good_med + bad_med) / 2.0
        # keep it sane
        suggested = max(0.05, min(0.95, suggested))
        return suggested