#!/usr/bin/env python3
"""
Mutation Testing Baseline Tracking

This script tracks mutation testing scores over time, similar to the coverage
baseline system but for mutation test quality metrics.
"""

import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path


def get_git_info():
    """Get current git commit information."""
    try:
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], 
            text=True
        ).strip()
        
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
            text=True
        ).strip()
        
        return commit_hash, branch
    except subprocess.CalledProcessError:
        return "unknown", "unknown"


def run_mutation_tests():
    """Run mutation tests and parse the results."""
    print("🦠 Running mutation tests...")
    
    try:
        # Run mutmut
        result = subprocess.run(['python3', '-m', 'mutmut', 'run'], 
                               capture_output=True, text=True, timeout=3600)
        
        if result.returncode != 0:
            print(f"❌ Mutation tests failed: {result.stderr}")
            return None
            
        # Get results
        results_process = subprocess.run(['python3', '-m', 'mutmut', 'results'], 
                                       capture_output=True, text=True)
        
        if results_process.returncode != 0:
            print(f"❌ Failed to get mutation results: {results_process.stderr}")
            return None
            
        results_output = results_process.stdout
        print("📊 Mutation test results:")
        print(results_output)
        
        # Parse mutation score from output
        mutation_data = parse_mutation_results(results_output)
        return mutation_data
        
    except subprocess.TimeoutExpired:
        print("❌ Mutation tests timed out after 1 hour")
        return None
    except Exception as e:
        print(f"❌ Error running mutation tests: {e}")
        return None


def parse_mutation_results(results_output):
    """Parse mutation test results to extract metrics."""
    # Look for patterns like "🎉 X  ⏰ Y  🤔 Z  🙁 W  🔇 V"
    emoji_pattern = r'🎉 (\d+).*?🙁 (\d+)'
    match = re.search(emoji_pattern, results_output)
    
    if match:
        killed = int(match.group(1))
        survived = int(match.group(2))
        total = killed + survived
        
        if total > 0:
            mutation_score = (killed / total) * 100
        else:
            mutation_score = 0.0
            
        return {
            'mutation_score': round(mutation_score, 2),
            'killed_mutants': killed,
            'surviving_mutants': survived,
            'total_mutants': total,
            'raw_output': results_output
        }
    
    # Fallback: try to parse from different format
    # Look for "X/Y" pattern
    fraction_pattern = r'(\d+)/(\d+)'
    killed_pattern = r'🎉 (\d+)'
    
    fraction_match = re.search(fraction_pattern, results_output)
    killed_match = re.search(killed_pattern, results_output)
    
    if fraction_match and killed_match:
        total = int(fraction_match.group(2))
        killed = int(killed_match.group(1))
        survived = total - killed
        
        if total > 0:
            mutation_score = (killed / total) * 100
        else:
            mutation_score = 0.0
            
        return {
            'mutation_score': round(mutation_score, 2),
            'killed_mutants': killed,
            'surviving_mutants': survived,
            'total_mutants': total,
            'raw_output': results_output
        }
    
    # If we can't parse, return minimal data
    print("⚠️ Could not parse mutation score from output")
    return {
        'mutation_score': 0.0,
        'killed_mutants': 0,
        'surviving_mutants': 0,
        'total_mutants': 0,
        'raw_output': results_output
    }


def load_baseline():
    """Load the current mutation testing baseline."""
    baseline_file = Path('.github/mutation-baseline.json')
    
    if not baseline_file.exists():
        return {
            'baseline_mutation_score': 0.0,
            'last_updated': None,
            'commit_hash': None,
            'branch': None,
            'total_mutants': 0,
            'killed_mutants': 0,
            'notes': 'Initial baseline'
        }
    
    try:
        with open(baseline_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading baseline: {e}")
        return {
            'baseline_mutation_score': 0.0,
            'last_updated': None,
            'commit_hash': None,
            'branch': None,
            'total_mutants': 0,
            'killed_mutants': 0,
            'notes': 'Error loading previous baseline'
        }


def save_baseline(mutation_data):
    """Save the new mutation testing baseline."""
    commit_hash, branch = get_git_info()
    
    baseline_data = {
        'baseline_mutation_score': mutation_data['mutation_score'],
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'commit_hash': commit_hash,
        'branch': branch,
        'total_mutants': mutation_data['total_mutants'],
        'killed_mutants': mutation_data['killed_mutants'],
        'surviving_mutants': mutation_data['surviving_mutants'],
        'notes': f'Baseline updated after mutation testing run'
    }
    
    baseline_file = Path('.github/mutation-baseline.json')
    baseline_file.parent.mkdir(exist_ok=True)
    
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"✅ Baseline saved: {mutation_data['mutation_score']:.2f}%")


def main():
    """Main mutation baseline tracking function."""
    print("🧬 Mutation Testing Baseline Tracker")
    print("=" * 50)
    
    # Load current baseline
    baseline = load_baseline()
    current_baseline = baseline.get('baseline_mutation_score', 0.0)
    
    print(f"📊 Current baseline: {current_baseline:.2f}%")
    
    # Run mutation tests
    mutation_data = run_mutation_tests()
    if mutation_data is None:
        print("❌ Failed to run mutation tests")
        sys.exit(1)
    
    current_score = mutation_data['mutation_score']
    print(f"📈 Current mutation score: {current_score:.2f}%")
    
    # Compare with baseline
    score_diff = current_score - current_baseline
    
    if score_diff >= 0.5:
        print(f"🎉 Mutation score improved by {score_diff:.2f}%")
        save_baseline(mutation_data)
        print("✅ New baseline established")
    elif score_diff <= -5.0:
        print(f"⚠️ Significant mutation score drop: {score_diff:.2f}%")
        print("Consider investigating why mutation tests are less effective")
        # Don't update baseline on significant drops
    else:
        print(f"📊 Mutation score change: {score_diff:+.2f}% (within acceptable range)")
    
    # Summary
    print("\n📋 Summary:")
    print(f"   Killed mutants: {mutation_data['killed_mutants']}")
    print(f"   Surviving mutants: {mutation_data['surviving_mutants']}")
    print(f"   Total mutants: {mutation_data['total_mutants']}")
    print(f"   Mutation score: {current_score:.2f}%")
    
    if score_diff <= -5.0:
        print("\n⚠️ Consider reviewing and improving test quality")
        sys.exit(1)  # Exit with error for significant drops
    
    print("\n✅ Mutation testing baseline check completed")


if __name__ == "__main__":
    main()