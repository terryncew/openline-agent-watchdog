# Agent Watchdog (v0.2.0)
**Stop burning compute on zombie loops.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE) [![Status: Active](https://img.shields.io/badge/Status-Active-green)]()

Autonomous agents have a predictable failure mode: **The Zombie Loop**. They encounter a hard problem, lose coherence, and start repeating low-entropy actions (`ls`, `read_file`, `thinking...`) until your API budget hits zero.

**Agent Watchdog** is a lightweight **budget governor** that detects this drift *before* the money is gone.

---

## What it does (in one sentence)
It monitors the agent's action history and kills the run if "Freshness" (unique actions / total actions) drops below a calibrated threshold.

---

## The Metric: Freshness
We measure **Freshness** in two ways:

1.  **Global Freshness:** "Did we stagnate overall?"
2.  **Rolling-Window Freshness:** "Are we looping *right now*?" (Crucial for long-running agents).

### The Status Signals
Watchdog returns a status object during every audit:

* 🟢 **GREEN**: Healthy exploration / progress.
* 🟡 **AMBER**: Drift risk. (Warn the user or tighten the budget).
* 🔴 **RED**: Likely zombie loop. (Stop, reset, or change strategy).

> **Important:** This is a budget control signal, not a truth oracle. Some productive work is repetitive (e.g., edit→test loops). The goal is to cut *waste*, not punish iteration.

---

## Quick Start

```python
from agent_watchdog import AgentWatchdog

# Initialize with rolling window (default size=15)
dog = AgentWatchdog(kill_threshold=0.25, window_size=15)

for step in agent.run():
    # Log the tool name, command, or action string
    dog.log_action(step['tool_name'])
    
    # Audit recent history
    status = dog.audit(use_window=True)
    
    if status.status == "AMBER":
        print(f"⚠️ Warning: Drift detected (Freshness: {status.freshness:.2f})")
        
    if status.status == "RED":
        print(f"💀 KILLING RUN. Stalled at freshness: {status.freshness:.2f}")
        agent.stop()
        break
```

---

## Auto-Calibration (New in v0.2.0)

There is no universal magic threshold. Different agents (SWE-agent vs. AutoGen) and different schemas (Moatless vs. Devin) have different "dialects."

**Agent Watchdog v0.2.0** includes an auto-calibrator. Feed it your labeled logs (Success/Fail) to find your specific "Kill Line."

```python
from agent_watchdog import AgentWatchdog

# 1. Load your labeled trajectory data
data = [
    {'actions': ['ls', 'ls', 'ls', 'ls'], 'success': False},
    {'actions': ['read', 'edit', 'test', 'edit', 'test'], 'success': True},
    # ... more runs ...
]

# 2. Calculate the optimal threshold
optimal_threshold = AgentWatchdog.calibrate(data)

print(f"Your agent's calibrated kill threshold is: {optimal_threshold}")
# Use this value in your production initialization:
# dog = AgentWatchdog(kill_threshold=optimal_threshold)
```

---

## Action Dialects (Schema Notes)

Watchdog normalizes inputs to handle messy logs. By default, `log_action()`:
1.  Converts to string.
2.  Lowercases.
3.  Trims whitespace.
4.  Takes the first token only (e.g., `"ls -la"` -> `"ls"`).

 This ensures that arguments (like filenames) don't falsely inflate freshness scores.

---

## Recommended Posture
* **Treat AMBER as "Slow Down":** If you hit Amber, maybe force a summarization step or refresh the context window.
* **Treat RED as "Stop":** If you hit Red, the probability of recovery is statistically near zero (based on SWE-bench audits). Kill the run to save cash.

---

## License
Apache 2.0

---
**Built by [OpenLine](https://github.com/terryncew/openline-core)**
