#!/usr/bin/env python3
"""
Automated ML Experiment Runner - Simplified and Robust Version

Orchestrates experiments by alternating between:
1. Running Python training scripts
2. Using Claude Code CLI to analyze and improve
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class ExperimentRunner:
    def __init__(self, experiment_dir: str, max_iterations: int = 10, allow_uv: bool = False, allow_pip: bool = False):
        self.experiment_dir = Path(experiment_dir).resolve()
        self.max_iterations = max_iterations
        self.allow_uv = allow_uv
        self.allow_pip = allow_pip
        self.iteration = 0
        
        # Key files
        self.idea_file = self.experiment_dir / "IDEA.md"
        self.plan_file = self.experiment_dir / "PLAN.md"
        self.report_file = self.experiment_dir / "REPORT.md"
        self.status_file = self.experiment_dir / "status.json"
        
        # Logs directory
        self.logs_dir = self.experiment_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        self._validate_setup()
        self.session_id = self.get_session_id()
    
    def _validate_setup(self):
        """Ensure required files exist"""
        if not self.idea_file.exists():
            print(f"ERROR: IDEA.md not found in {self.experiment_dir}")
            print("Please create IDEA.md with your experiment description")
            sys.exit(1)
    
    def log(self, message: str):
        """Simple logging with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
        # Also save to file
        log_file = self.logs_dir / "runner.log"
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def save_status(self):
        """Save current status"""        
        # Update status while preserving session_id
        status = {
            "iteration": self.iteration,
            "timestamp": time.time(),
            "complete": self.report_file.exists(),
            "session_id": self.session_id
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def run_claude(self, prompt: str, retry_count: int = 0) -> bool:
        """Run Claude Code CLI command with retry logic"""
        # Build command with JSON output
        allowed_tools = "Edit,Write,WebFetch,Bash(ls:*)"
        if self.allow_uv:
            allowed_tools += ",Bash(uv:*)"
        if self.allow_pip:
            allowed_tools += ",Bash(pip:*)"
        
        cmd = [
            "claude", 
            "--output-format", "json",
            "--allowedTools", allowed_tools
        ]
        
        # Add resume flag if we have a session ID
        if self.session_id:
            cmd.extend(["--resume", self.session_id])
            self.log(f"Resuming session: {self.session_id}")

        cmd.extend(["-p", prompt])
        
        self.log(f"Iteration {self.iteration}: Running Claude analysis...")

        # print(cmd)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.experiment_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Parse JSON output
                try:
                    output_data = json.loads(result.stdout)
                    
                    # Extract session ID from first call
                    if "session_id" in output_data:
                        self.session_id = output_data["session_id"]
                        self.save_status()
                        self.log(f"Session ID saved: {self.session_id}")
                    
                    # Log formatted output
                    self._log_claude_output(output_data)
                    
                    self.log(f"Claude analysis completed, cost: ${output_data['cost_usd']} USD, total: {output_data['total_cost']}, turns: {output_data['num_turns']}")
                    return True
                    
                except json.JSONDecodeError as e:
                    self.log(f"Failed to parse Claude JSON output: {e}")
                    # Save raw output for debugging
                    debug_file = self.logs_dir / f"claude_raw_output_{self.iteration}.txt"
                    debug_file.write_text(result.stdout)
                    return False
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                self.log(f"Claude error: {error_msg}...")
                
                # Retry logic for transient failures
                if retry_count < 2 and "rate limit" in error_msg.lower():
                    self.log(f"Retrying in 30 seconds...")
                    time.sleep(30)
                    return self.run_claude(prompt, retry_count + 1)
                
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Claude command timed out")
            # Save prompt for manual inspection
            timeout_file = self.logs_dir / f"timeout_prompt_{self.iteration}.txt"
            timeout_file.write_text(prompt)
            return False
        except Exception as e:
            self.log(f"Claude error: {str(e)}")
            return False
    
    def get_session_id(self) -> Optional[str]:
        """Get stored session ID from status.json"""
        if self.status_file.exists():
            try:
                with open(self.status_file) as f:
                    status = json.load(f)
                    return status.get("session_id")
            except:
                pass
        return None
    
    def save_session_id(self, session_id: str):
        """Save session ID to status.json"""
        status = {}
        if self.status_file.exists():
            try:
                with open(self.status_file) as f:
                    status = json.load(f)
            except:
                pass
        
        status["session_id"] = session_id
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def _log_claude_output(self, output_data: dict):
        """Log formatted output from Claude JSON response"""
        # Log the main response text if available
        if "result" in output_data:
            content = output_data["result"]
            self.log(f"Claude response:\n{content}")
        
        # Save full JSON for debugging
        json_file = self.logs_dir / f"claude_response_{self.iteration}.json"
        with open(json_file, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    def run_training(self) -> Tuple[bool, str]:
        """Run the main training script"""
        # Find training script
        train_scripts = ["temp_check.py", "train.py"]
        script_path = None
        
        for script in train_scripts:
            if (self.experiment_dir / script).exists():
                script_path = script
                break
        
        if not script_path:
            return False, "No training script found"
        
        self.log(f"Running {script_path}...")
        
        # Prepare output files
        stdout_file = self.logs_dir / f"iter_{self.iteration}_stdout.txt"
        stderr_file = self.logs_dir / f"iter_{self.iteration}_stderr.txt"
        
        try:
            with open(stdout_file, 'w') as out, open(stderr_file, 'w') as err:
                result = subprocess.run(
                    [sys.executable, script_path],
                    cwd=self.experiment_dir,
                    stdout=out,
                    stderr=err,
                    timeout=7200  # 2 hour timeout
                )
            
            if result.returncode == 0:
                self.log(f"Training completed successfully")
                return True, "Success"
            else:
                self.log(f"Training failed with code {result.returncode}")
                return False, f"Exit code {result.returncode}"
                
        except subprocess.TimeoutExpired:
            self.log("Training timed out after 2 hours")
            return False, "Timeout"
        except Exception as e:
            self.log(f"Training error: {str(e)}")
            return False, str(e)
    
    def create_initial_plan(self):
        """Create initial experiment plan"""
        if self.plan_file.exists():
            self.log("PLAN.md already exists, skipping creation")
            return True
        
        # Check available resources
        self._check_resources()
        
        prompt = f"""Read IDEA.md and create a detailed PLAN.md that includes:
1. Clear objectives and success metrics
2. Simple initial implementation approach
3. Key hyperparameters to start with
4. Expected challenges and solutions

Focus on getting a minimal working version first.

System Information:
- {self.gpu_info if hasattr(self, 'gpu_info') else 'GPU status unknown'}"""
        
        if self.allow_uv:
            prompt += "\n- You can install Python libraries using `uv pip install package_name`"
        if self.allow_pip:
            prompt += "\n- You can install Python libraries using `pip install package_name`"
        
        return self.run_claude(prompt)
    
    def _check_resources(self):
        """Check available system resources"""
        self.gpu_info = None
        try:
            import torch
            if torch.cuda.is_available():
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
                gpu_name = torch.cuda.get_device_name(0)
                self.gpu_info = f"GPU: {gpu_name} ({gpu_mem:.1f}GB)"
                self.log(f"GPU available: {gpu_name} ({gpu_mem:.1f}GB)")
            else:
                self.gpu_info = "No GPU available - using CPU"
                self.log("No GPU available - will use CPU")
        except ImportError:
            self.gpu_info = "PyTorch not installed"
            self.log("PyTorch not installed - install dependencies first")
            sys.exit(1)
        except Exception as e:
            self.gpu_info = f"Resource check failed: {e}"
            self.log(f"Resource check failed: {e}")
            sys.exit(1)
    
    def run_iteration(self):
        """Run one experiment iteration"""
        self.iteration += 1
        self.log(f"\n{'='*60}")
        self.log(f"Starting iteration {self.iteration}")
        
        # Check if complete
        if self.report_file.exists():
            self.log("Experiment complete - REPORT.md exists")
            return False
        
        # Step 1: Run training if script exists
        success, error = self.run_training()
        
        # Step 2: Analyze with Claude
        if self.iteration == 1:
            # Check resources if not already done
            if not hasattr(self, 'gpu_info'):
                self._check_resources()
            
            prompt = f"""This is iteration {self.iteration} of the ML experiment.

First examine these files:
- PLAN.md (the experiment plan)
- logs/iter_{self.iteration}_stderr.txt (check for errors)
- logs/iter_{self.iteration}_stdout.txt (training output)

Based on the results:
1. If there are errors, fix them in the training script
2. If training worked, analyze performance and suggest improvements
3. Make small, focused changes to improve results

Create or update the training script as needed."""
            
            if self.allow_uv:
                prompt += "\n\nNote: You can install Python libraries using `uv pip install package_name`"
            if self.allow_pip:
                prompt += "\n\nNote: You can install Python libraries using `pip install package_name`"
        else:
                
            prompt = f"""This is iteration {self.iteration}. The previous training {'succeeded' if success else f'failed: {error}'}.

Examine the latest logs and results, then:
1. Fix any errors if present
2. Improve hyperparameters or architecture if needed
3. If the experiment has achieved its goals, create REPORT.md
"""
            
            if self.allow_uv:
                prompt += "\n\nNote: You can install Python libraries using `uv pip install package_name`"
            if self.allow_pip:
                prompt += "\n\nNote: You can install Python libraries using `pip install package_name`"
        
        claude_success = self.run_claude(prompt)
        
        if not claude_success:
            self.log("Claude analysis failed - will retry next iteration")
        
        self.save_status()
        return True  # Continue iterating
    
    def run(self):
        """Run the complete experiment"""
        self.log(f"Starting automated experiment in {self.experiment_dir}")
        
        # Load previous iteration if resuming
        if self.status_file.exists():
            with open(self.status_file) as f:
                status = json.load(f)
                self.iteration = status.get("iteration", 0)
                if status.get("complete", False):
                    self.log("Experiment already complete")
                    return
        
        # Create initial plan
        if not self.plan_file.exists():
            self.log("Creating initial experiment plan...")
            if not self.create_initial_plan():
                self.log("Failed to create plan - exiting")
                return
            time.sleep(2)  # Brief pause
        
        # Main experiment loop
        try:
            while self.iteration < self.max_iterations:
                if not self.run_iteration():
                    break
                time.sleep(3)  # Brief pause between iterations
                
        except KeyboardInterrupt:
            self.log("\nExperiment interrupted by user")
        except Exception as e:
            self.log(f"\nExperiment error: {e}")
        
        # Final summary
        self.log(f"\nExperiment finished after {self.iteration} iterations")
        if self.report_file.exists():
            self.log("✓ REPORT.md generated successfully")
        else:
            self.log("✗ No final report generated")
        
        self.save_status()


def main():
    parser = argparse.ArgumentParser(
        description="Run automated ML experiments with Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python runner.py .                    # Run in current directory
  python runner.py my_experiment/       # Run in specific directory
  python runner.py . --max-iterations 5 # Limit iterations
        """
    )
    
    parser.add_argument(
        "experiment_dir",
        help="Directory containing IDEA.md and experiment files"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum iterations (default: 10)"
    )
    parser.add_argument(
        "--allow-uv",
        action="store_true",
        help="Allow Claude to use uv for package installation"
    )
    parser.add_argument(
        "--allow-pip",
        action="store_true",
        help="Allow Claude to use pip for package installation"
    )
    
    args = parser.parse_args()
    
    # Verify Claude is available
    try:
        subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: Claude Code CLI not found")
        print("Please install: https://github.com/anthropics/claude-code")
        sys.exit(1)
    
    # Run experiment
    runner = ExperimentRunner(
        experiment_dir=args.experiment_dir,
        max_iterations=args.max_iterations,
        allow_uv=args.allow_uv,
        allow_pip=args.allow_pip
    )
    runner.run()


if __name__ == "__main__":
    main()