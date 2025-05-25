# Automated ML Experiment Template

Run ML experiments automatically with Claude Code analyzing and improving results iteratively.

## Quick Start

1. **You need an environment with working Python, PyTorch, Claude Code and, optionally, CUDA** Perhaps, also venv. Also, read the WARNING below.

2. **Create experiment directory with your idea:**
```bash
mkdir my_experiment
cd my_experiment
echo "# My Experiment Idea\nTrain a model to..." > IDEA.md
```

3. **Copy and run the automation script:**
```bash
cp /path/to/template/runner.py .
cp /path/to/template/CLAUDE.md .
python runner.py .
```

That's it! Claude will create a plan, write code, run training, and iterate.

Check `logs/` directory to monitor progress.

## How It Works

```
IDEA.md → Claude creates PLAN.md → Claude writes train.py → Run training →
Claude analyzes results → Claude improves code → Repeat → Final REPORT.md
```

## WARNING

You need to be aware of the fact this will automatically run AI-generated code when you run runner.py.
This template does NOT include any kind of sandboxing, the responsibility for sandboxing and outcomes is 
entirely on the person running the script. The script is provided for educational purposes only.


## Files

- `IDEA.md` - Your experiment description (required)
- `runner.py` - Automation script
- `CLAUDE.md` - Instructions for Claude
- `PLAN.md` - Created by Claude
- `train.py` - Created/modified by Claude (main training script)
- `logs/` - Training outputs (stdout, stderr for each iteration)
- `status.json` - Current experiment status and iteration counter
- `REPORT.md` - Final results
- `watchdog.py` - Optional safety script to prevent runaway experiments

## Options

```bash
python runner.py . --max-iterations 5  # Limit iterations
python runner.py . --allow-pip          # Allow pip for package management
python runner.py . --allow-uv           # Allow `uv pip` for package management
```

### --allow-pip

When enabled, allows Claude to use `pip` for Python package installation:
- Adds `pip install` capability to Claude's allowed tools
- Useful for experiments that need additional libraries
- Standard Python package manager

Example:
```bash
python runner.py . --allow-pip  # Claude can now use: pip install torch numpy etc.
```

### --allow-uv

When enabled, allows Claude to use `uv` for fast Python package installation:
- Adds `uv pip install` capability to Claude's allowed tools
- Useful for experiments that need additional libraries
- Much faster than regular pip for dependency resolution

Example:
```bash
python runner.py . --allow-uv  # Claude can now use: uv pip install torch numpy etc.
```

## Watchdog (Optional, half-baked)

To prevent experiments from running forever:
```bash
# In a separate terminal, check experiment status
python watchdog.py my_experiment/

# Run periodically (e.g., via cron) to auto-stop long-running experiments
python watchdog.py my_experiment/
```

The watchdog will create a REPORT.md to stop the experiment if:
- Running longer than 24 hours
- More than 20 iterations
- No progress for 2+ hours

Note: currently watchdog cannot actually kill a process. It's more like a concept of a watchdog.

## Tips for Success

1. **Start with a clear, focused idea** in IDEA.md
2. **Specify constraints** (GPU memory, time limits)
3. **Watch the first iteration** to ensure it's on track
4. **Check logs/** if something goes wrong
5. **Always use fp32** unless you specifically need fp16/bf16 (prevents NaN issues)

## Example IDEA.md

```markdown
# Transformer Memory Injection

Test if injecting memory tokens into transformer attention improves performance.

**Constraints:**
- Use small model (max 50M parameters)
- Train on simple task first
- Should run on 8GB GPU
- Use fp32 precision (more stable)

**Success Criteria:**
- Model trains without errors
- Shows improvement over baseline
```

## Status Tracking

The experiment creates `status.json` with:
```json
{
  "iteration": 3,
  "timestamp": 1234567890,
  "complete": false
}
```

Check this file to see current progress without interrupting the experiment.

## Troubleshooting

**"IDEA.md not found"** - Create this file first
**"Claude Code CLI not found"** - Install from https://github.com/anthropics/claude-code
**Training keeps failing** - Add constraints to IDEA.md (smaller model, less memory)
**NaN losses** - Ensure fp32 is used, reduce learning rate
**No progress** - Check logs/runner.log and status.json

## Advanced Usage

To resume after interruption:
```bash
python runner.py .  # Automatically resumes from last iteration
```

To use existing code:
```bash
# Place your train.py in the directory before running
# Claude will modify it rather than creating from scratch
```

To monitor without interrupting:
```bash
# Check status
cat status.json

# Watch logs
tail -f logs/runner.log
```

## TODO

1. Tensorboard support (also maybe wandb?)
2. Save PIDs to status.json