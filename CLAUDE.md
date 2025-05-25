# Instructions for Claude in Automated ML Experiments

You are running in automated mode, called by `runner.py` to iteratively improve ML experiments.

## Your Core Tasks

1. **Fix Errors First** - If training fails, diagnose and fix the issue
2. **Improve Incrementally** - Make one focused change per iteration
3. **Track Progress** - Monitor metrics and convergence
4. **Generate Report** - Create REPORT.md when goals are achieved

## Where to Put Your Code

- Use `train.py` for consistency
- runner.py looks for: `temp_check.py`, `train.py` (in that order)
- Keep all training logic in this single file initially
- Only create additional files if absolutely necessary
- use `temp_check.py` if you need to debug something outside of main code

## CRITICAL: Always Use fp32 unless explicitly requested otherwise

```python
model = model.float()  # Ensure fp32

# Only use fp16/bf16 if specifically requested in IDEA.md
```

## Iteration Strategy

### First Iteration
- Read IDEA.md and PLAN.md
- Check logs/iter_1_stderr.txt for errors
- **Create `train.py`** if it doesn't exist
- Focus on getting something running, even if simple

### Early Iterations (2-4)
- Fix any remaining errors
- Establish baseline performance
- Add basic logging and metrics
- Tune learning rate first (most important)

### Middle Iterations (5-7)
- Optimize architecture if needed
- Add regularization if overfitting
- Improve data handling
- Consider computational efficiency

### Late Iterations (8+)
- Fine-tune remaining hyperparameters
- Polish implementation
- Create comprehensive REPORT.md if successful

## train.py starting point

```python
#!/usr/bin/env python3
import torch
import torch.nn as nn
import numpy as np

# ALWAYS use fp32 to prevent NaN issues
torch.set_default_dtype(torch.float32)

```

## Logs

1. **logs/iter_N_stderr.txt** - Python errors or warnings?
2. **logs/iter_N_stdout.txt** - Training progress and metrics

## When to Create REPORT.md

Create the report when:
- Training runs successfully for multiple epochs
- Loss converges or shows clear trend
- There is an error which is impossible to fix (e.g. no package installation is allowed)
- No critical errors in recent iterations
- OR max iterations reached (summarize what was learned)

## Report Structure

```markdown
# Experiment Report

## Summary
- **Status**: Success/Partial/Failed
- **Key Finding**: [One sentence summary]
- **Best Performance**: [Metrics]

## Approach
[What was implemented]

## Results
[Metrics, graphs if available, key observations]

## Challenges
[What didn't work and why]

## Recommendations
[Next steps for improvement]
```

## Important Reminders

- **Log everything** - Print statements are free
- **Start simple** - Complexity can come later
- **Save checkpoints** - Protect against crashes
- **Do not use tqdm** - We are sending output to files, not interactive console. Just use `print` statements.

## Quick Diagnostic Checklist

If training fails, check in order:

1. Import errors → Install missing packages
2. File not found → Check paths
3. CUDA errors → Reduce batch size
4. NaN loss → Ensure fp32, reduce learning rate, clip gradients
5. No progress → Check data loading
