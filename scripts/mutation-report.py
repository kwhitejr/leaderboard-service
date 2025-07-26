#!/usr/bin/env python3
"""
Enhanced Local Mutation Testing Report Generator

This script provides detailed analysis and reporting for local mutation testing
results with better visualization and actionable insights.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class MutationAnalyzer:
    """Analyzes mutation test results and generates enhanced reports."""
    
    def __init__(self):
        self.results_data = {}
        self.cache_path = Path('.mutmut-cache')
        self.html_path = Path('html')
        
    def check_prerequisites(self) -> bool:
        """Check if mutation test results are available."""
        if not self.cache_path.exists():
            print("❌ No mutation test cache found")
            print("   Run mutation tests first: ./scripts/mutate-local.sh")
            return False
            
        return True
    
    def get_mutation_results(self) -> Dict:
        """Get mutation test results from mutmut."""
        try:
            result = subprocess.run(['python3', '-m', 'mutmut', 'results'], 
                                  capture_output=True, text=True, check=True)
            return self.parse_results(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting mutation results: {e}")
            return {}
    
    def parse_results(self, output: str) -> Dict:
        """Parse mutmut results output into structured data."""
        data = {
            'killed': 0,
            'survived': 0,
            'timeout': 0,
            'suspicious': 0,
            'skipped': 0,
            'total': 0,
            'score': 0.0,
            'raw_output': output
        }
        
        # Parse emoji counts
        patterns = {
            'killed': r'🎉 (\d+)',
            'timeout': r'⏰ (\d+)',
            'suspicious': r'🤔 (\d+)',
            'survived': r'🙁 (\d+)',
            'skipped': r'🔇 (\d+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                data[key] = int(match.group(1))
        
        # Calculate totals
        data['total'] = data['killed'] + data['survived'] + data['timeout'] + data['suspicious']
        if data['total'] > 0:
            data['score'] = (data['killed'] / data['total']) * 100
        
        return data
    
    def get_file_breakdown(self) -> Dict[str, Dict]:
        """Get per-file mutation breakdown if available."""
        file_stats = {}
        
        # Try to extract file information from HTML report
        html_index = self.html_path / 'index.html'
        if html_index.exists():
            try:
                with open(html_index, 'r') as f:
                    content = f.read()
                    
                # Look for file entries in HTML (basic parsing)
                file_pattern = r'href="([^"]*\.py\.html)".*?(\d+)/(\d+)'
                matches = re.findall(file_pattern, content)
                
                for match in matches:
                    filename = match[0].replace('_', '/').replace('.html', '')
                    killed = int(match[1])
                    total = int(match[2])
                    survived = total - killed
                    score = (killed / total * 100) if total > 0 else 0
                    
                    file_stats[filename] = {
                        'killed': killed,
                        'survived': survived,
                        'total': total,
                        'score': score
                    }
            except Exception as e:
                print(f"⚠️ Could not parse file breakdown: {e}")
        
        return file_stats
    
    def get_surviving_mutants(self) -> List[Dict]:
        """Get details about surviving mutants."""
        surviving = []
        
        try:
            # Get list of all mutants
            result = subprocess.run(['python3', '-m', 'mutmut', 'results'], 
                                  capture_output=True, text=True, check=True)
            
            # Look for surviving mutant IDs
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Survived' in line and '(' in line:
                    # Extract mutant IDs from lines like "Survived (1-3, 7, 10-12)"
                    id_match = re.search(r'\(([^)]+)\)', line)
                    if id_match:
                        id_ranges = id_match.group(1).split(', ')
                        for id_range in id_ranges:
                            if '-' in id_range:
                                start, end = map(int, id_range.split('-'))
                                for mutant_id in range(start, end + 1):
                                    surviving.append({'id': mutant_id})
                            else:
                                surviving.append({'id': int(id_range)})
        except Exception as e:
            print(f"⚠️ Could not get surviving mutant details: {e}")
        
        return surviving
    
    def generate_summary_report(self) -> str:
        """Generate a text summary report."""
        results = self.get_mutation_results()
        if not results:
            return "❌ No mutation test results available"
        
        file_breakdown = self.get_file_breakdown()
        surviving = self.get_surviving_mutants()
        
        report = []
        report.append("🦠 MUTATION TESTING REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Overall summary
        report.append("📊 OVERALL RESULTS")
        report.append("-" * 20)
        report.append(f"Mutation Score: {results['score']:.1f}%")
        report.append(f"Total Mutants: {results['total']}")
        report.append(f"  🎉 Killed: {results['killed']}")
        report.append(f"  🙁 Survived: {results['survived']}")
        report.append(f"  ⏰ Timeout: {results['timeout']}")
        report.append(f"  🤔 Suspicious: {results['suspicious']}")
        report.append(f"  🔇 Skipped: {results['skipped']}")
        report.append("")
        
        # Quality assessment
        score = results['score']
        if score >= 90:
            report.append("✅ EXCELLENT: Your tests are very robust!")
        elif score >= 80:
            report.append("💚 VERY GOOD: High quality test suite")
        elif score >= 70:
            report.append("💛 GOOD: Solid test coverage with room for improvement")
        elif score >= 60:
            report.append("🟡 FAIR: Tests could be strengthened")
        else:
            report.append("🔴 NEEDS WORK: Consider improving test quality")
        report.append("")
        
        # Per-file breakdown
        if file_breakdown:
            report.append("📁 PER-FILE BREAKDOWN")
            report.append("-" * 22)
            for filename, stats in sorted(file_breakdown.items(), 
                                        key=lambda x: x[1]['score'], reverse=True):
                report.append(f"{filename}")
                report.append(f"  Score: {stats['score']:.1f}% ({stats['killed']}/{stats['total']})")
            report.append("")
        
        # Surviving mutants guidance
        if results['survived'] > 0:
            report.append("🔧 IMPROVEMENT SUGGESTIONS")
            report.append("-" * 25)
            report.append(f"You have {results['survived']} surviving mutants to investigate:")
            report.append("1. Run: make mutate-browse")
            report.append("2. Or open: html/index.html")
            report.append("3. Focus on red/surviving mutants")
            report.append("4. Add tests to catch these mutations")
            report.append("")
        
        # Next steps
        report.append("🚀 NEXT STEPS")
        report.append("-" * 12)
        report.append("• View detailed report: open html/index.html")
        report.append("• Interactive analysis: make mutate-browse")
        report.append("• Target specific files: ./scripts/mutate-local.sh --target <file>")
        report.append("• Quick iteration: ./scripts/mutate-local.sh --quick")
        
        return "\n".join(report)
    
    def save_report(self, report: str, filename: str = "mutation-report.txt"):
        """Save report to file."""
        try:
            with open(filename, 'w') as f:
                f.write(report)
            print(f"📄 Report saved: {filename}")
        except Exception as e:
            print(f"⚠️ Could not save report: {e}")
    
    def generate_json_summary(self) -> str:
        """Generate JSON summary for programmatic use."""
        results = self.get_mutation_results()
        file_breakdown = self.get_file_breakdown()
        
        summary = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'overall': results,
            'files': file_breakdown,
            'recommendations': []
        }
        
        # Add recommendations based on score
        score = results['score']
        if score < 70:
            summary['recommendations'].append("Consider adding more comprehensive tests")
        if results['survived'] > 0:
            summary['recommendations'].append("Investigate surviving mutants for test gaps")
        if score >= 90:
            summary['recommendations'].append("Excellent test quality - maintain this standard")
        
        return json.dumps(summary, indent=2)


def main():
    """Main function for mutation report generation."""
    analyzer = MutationAnalyzer()
    
    if not analyzer.check_prerequisites():
        sys.exit(1)
    
    print("📊 Generating enhanced mutation testing report...")
    
    # Generate text report
    text_report = analyzer.generate_summary_report()
    print(text_report)
    
    # Offer to save reports
    save_text = input("\n💾 Save detailed text report? (y/N): ").lower().strip()
    if save_text == 'y':
        analyzer.save_report(text_report)
    
    save_json = input("💾 Save JSON summary? (y/N): ").lower().strip()
    if save_json == 'y':
        json_report = analyzer.generate_json_summary()
        try:
            with open('mutation-summary.json', 'w') as f:
                f.write(json_report)
            print("📄 JSON summary saved: mutation-summary.json")
        except Exception as e:
            print(f"⚠️ Could not save JSON: {e}")
    
    print("\n✅ Report generation completed!")


if __name__ == "__main__":
    main()