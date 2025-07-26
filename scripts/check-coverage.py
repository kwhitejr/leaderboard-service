#!/usr/bin/env python3
"""
Dynamic coverage threshold checker for CI/CD pipeline.

This script implements a ratcheting coverage system where the minimum
threshold automatically increases when coverage improves, preventing
regression while encouraging continuous improvement.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_coverage():
    """Run pytest with coverage and return coverage percentage."""
    try:
        # Run tests with coverage
        result = subprocess.run([
            'python3', '-m', 'pytest', 
            '--cov=src', 
            '--cov-report=term-missing',
            '--tb=short',
            '-q'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ Tests failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return None
            
        # Parse coverage from output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'TOTAL' in line and '%' in line:
                # Extract percentage from line like "TOTAL     160      5  96.88%"
                parts = line.split()
                for part in parts:
                    if part.endswith('%'):
                        return float(part.rstrip('%'))
        
        print("❌ Could not parse coverage percentage from output")
        print("Coverage output:", result.stdout)
        return None
        
    except subprocess.TimeoutExpired:
        print("❌ Coverage tests timed out")
        return None
    except Exception as e:
        print(f"❌ Error running coverage: {e}")
        return None


def load_baseline():
    """Load the current coverage baseline from file."""
    baseline_file = Path('.github/coverage-baseline.json')
    
    if not baseline_file.exists():
        print("⚠️  No baseline file found, creating with default values")
        return {
            "baseline_coverage": 85.0,  # Conservative default
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "commit_hash": "initial",
            "branch": "main",
            "total_lines": 0,
            "covered_lines": 0,
            "test_count": 0,
            "per_file_coverage": {},
            "notes": "Initial baseline - will be updated automatically"
        }
    
    try:
        with open(baseline_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading baseline: {e}")
        sys.exit(1)


def save_baseline(baseline_data):
    """Save updated baseline to file."""
    baseline_file = Path('.github/coverage-baseline.json')
    
    try:
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        print(f"✅ Updated baseline to {baseline_data['baseline_coverage']:.2f}%")
    except Exception as e:
        print(f"❌ Error saving baseline: {e}")
        sys.exit(1)


def get_git_info():
    """Get current git commit hash and branch."""
    try:
        commit_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                   capture_output=True, text=True).stdout.strip()
        branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                               capture_output=True, text=True).stdout.strip()
        return commit_hash[:7], branch
    except:
        return "unknown", "unknown"


def main():
    """Main coverage checking logic."""
    print("🔍 Dynamic Coverage Threshold Checker")
    print("=" * 50)
    
    # Load current baseline
    baseline = load_baseline()
    baseline_coverage = baseline['baseline_coverage']
    print(f"📊 Current baseline: {baseline_coverage:.2f}%")
    
    # Run coverage tests
    print("🧪 Running tests with coverage...")
    current_coverage = run_coverage()
    
    if current_coverage is None:
        print("❌ Failed to measure coverage")
        sys.exit(1)
    
    print(f"📈 Current coverage: {current_coverage:.2f}%")
    
    # Compare coverage
    coverage_diff = current_coverage - baseline_coverage
    
    if coverage_diff < -0.01:  # Allow tiny float precision differences
        print(f"❌ Coverage regression detected!")
        print(f"   Baseline: {baseline_coverage:.2f}%")
        print(f"   Current:  {current_coverage:.2f}%")
        print(f"   Drop:     {abs(coverage_diff):.2f} percentage points")
        print("\n💡 To fix this:")
        print("   1. Add tests to cover the missing lines")
        print("   2. Review why existing coverage was lost")
        print("   3. Ensure all tests are running properly")
        sys.exit(1)
    
    elif coverage_diff > 0.01:  # Coverage improved
        print(f"🎉 Coverage improved by {coverage_diff:.2f} percentage points!")
        
        # Update baseline if we're on main branch or if explicitly requested
        branch_name = os.environ.get('GITHUB_REF_NAME', get_git_info()[1])
        is_main_branch = branch_name in ['main', 'master']
        force_update = os.environ.get('UPDATE_COVERAGE_BASELINE', '').lower() == 'true'
        
        if is_main_branch or force_update:
            commit_hash, current_branch = get_git_info()
            
            # Update baseline
            baseline.update({
                "baseline_coverage": round(current_coverage, 2),
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "commit_hash": commit_hash,
                "branch": current_branch,
                "notes": f"Coverage improved from {baseline_coverage:.2f}% to {current_coverage:.2f}%"
            })
            
            save_baseline(baseline)
            print(f"✅ Baseline updated! New minimum: {current_coverage:.2f}%")
        else:
            print(f"ℹ️  Coverage improved but baseline not updated (not on main branch)")
            print(f"   Current branch: {branch_name}")
            print(f"   Baseline will be updated when merged to main")
    
    else:
        print(f"✅ Coverage maintained at {current_coverage:.2f}%")
    
    print("\n🎯 Coverage check passed!")
    

if __name__ == "__main__":
    main()