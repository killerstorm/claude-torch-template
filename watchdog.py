#!/usr/bin/env python3
"""
Simple watchdog to prevent experiments from running forever.
Monitors iterations and can force completion if needed.
"""

import json
import sys
import time
from pathlib import Path

def check_experiment(exp_dir: Path, max_hours: float = 24):
    """Check if experiment should be stopped"""
    status_file = exp_dir / "status.json"
    
    if not status_file.exists():
        return False, "No status file"
    
    with open(status_file) as f:
        status = json.load(f)
    
    # Check runtime
    start_time = status.get("timestamp", time.time())
    hours_elapsed = (time.time() - start_time) / 3600
    
    if hours_elapsed > max_hours:
        return True, f"Running for {hours_elapsed:.1f} hours"
    
    # Check iterations
    iteration = status.get("iteration", 0)
    if iteration > 20:
        return True, f"Exceeded 20 iterations"
    
    # Check if stuck (no progress in 2 hours)
    last_update = status.get("timestamp", time.time())
    hours_since_update = (time.time() - last_update) / 3600
    if hours_since_update > 2:
        return True, f"No progress for {hours_since_update:.1f} hours"
    
    return False, f"Iteration {iteration}, {hours_elapsed:.1f} hours"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python watchdog.py experiment_dir")
        sys.exit(1)
    
    exp_dir = Path(sys.argv[1])
    should_stop, reason = check_experiment(exp_dir)
    
    print(f"Status: {reason}")
    if should_stop:
        print("Creating REPORT.md to stop experiment...")
        report = exp_dir / "REPORT.md"
        report.write_text(f"""# Experiment Report (Watchdog Termination)

## Summary
- **Status**: Stopped by watchdog
- **Reason**: {reason}

## Recommendation
Check logs to understand why the experiment didn't complete naturally.
""")
        print("Experiment will stop on next iteration")