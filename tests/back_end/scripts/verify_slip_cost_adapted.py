#!/usr/bin/env python3
"""
Adapted Slip Cost Verification Script for ALMTrajOpt Debug Logs

This script analyzes ROS log files containing ALMTrajOpt slip cost calculation
and independently calculates expected slip costs to verify C++ implementation.

Usage:
    python3 verify_slip_cost_adapted.py <log_file_path> <Ps_value>

Example:
    python3 verify_slip_cost_adapted.py hill_flat_Ps1_detailed.log 1.0
"""

import sys
import re
import math
import argparse
from typing import Dict, List, Optional, Tuple


def parse_arguments() -> Tuple[str, float]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify slip cost calculations from ALMTrajOpt debug logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("log_file", help="Path to the ROS log file")
    parser.add_argument("Ps", type=float, help="Slip cost weight parameter")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    return args.log_file, args.Ps, args.verbose


def extract_debug_data(line: str) -> Optional[Dict[str, float]]:
    """
    Extract numerical values from an ALMTrajOpt slip cost calculation log line.
    
    Expected format:
    [ALMTrajOpt] Slip cost calculation at segment X, sample Y | time: T | velocity: V | 
    v_norm: VN | sin_phix: SPX | sin_phiy: SPY | slip_slope_squared: SSS | 
    step: S | temp_param_Ps: P | slip_cost_delta: SCD
    
    Args:
        line: Log line containing ALMTrajOpt slip cost information
        
    Returns:
        Dictionary with extracted values or None if parsing fails
    """
    # Look for lines containing our debug identifier
    if "[ALMTrajOpt] Slip cost calculation" not in line:
        return None
    
    data = {}
    
    try:
        # Extract segment and sample indices
        segment_match = re.search(r'segment (\d+)', line)
        sample_match = re.search(r'sample (\d+)', line)
        if segment_match and sample_match:
            data['segment'] = int(segment_match.group(1))
            data['sample'] = int(sample_match.group(1))
        
        # Extract time
        time_match = re.search(r'time: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if time_match:
            data['time'] = float(time_match.group(1))
        
        # Extract velocity
        vel_match = re.search(r'velocity: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if vel_match:
            data['velocity'] = float(vel_match.group(1))
        
        # Extract v_norm
        vnorm_match = re.search(r'v_norm: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if vnorm_match:
            data['v_norm'] = float(vnorm_match.group(1))
        
        # Extract sin_phix
        sin_phix_match = re.search(r'sin_phix: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if sin_phix_match:
            data['sin_phix'] = float(sin_phix_match.group(1))
        
        # Extract sin_phiy
        sin_phiy_match = re.search(r'sin_phiy: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if sin_phiy_match:
            data['sin_phiy'] = float(sin_phiy_match.group(1))
        
        # Extract slip_slope_squared
        slip_slope_match = re.search(r'slip_slope_squared: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if slip_slope_match:
            data['slip_slope_squared'] = float(slip_slope_match.group(1))
        
        # Extract step
        step_match = re.search(r'step: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if step_match:
            data['step'] = float(step_match.group(1))
        
        # Extract temp_param_Ps
        ps_match = re.search(r'temp_param_Ps: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if ps_match:
            data['temp_param_Ps'] = float(ps_match.group(1))
        
        # Extract slip_cost_delta
        slip_cost_match = re.search(r'slip_cost_delta: ([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
        if slip_cost_match:
            data['slip_cost_delta'] = float(slip_cost_match.group(1))
        
        return data if data else None
        
    except (ValueError, AttributeError) as e:
        print(f"Warning: Failed to parse line: {line.strip()}")
        print(f"Error: {e}")
        return None


def calculate_expected_slip_cost(data: Dict[str, float], Ps_cmdline: float) -> Dict[str, float]:
    """
    Calculate expected slip cost based on extracted data.
    
    Based on C++ logic: slip_cost_delta = slip_slope_squared * v_norm^2 * step * temp_param_Ps
    
    Args:
        data: Dictionary with extracted log values
        Ps_cmdline: Slip cost weight from command line
        
    Returns:
        Dictionary with calculation results
    """
    results = {}
    
    # Get values from log data
    v_norm = data.get('v_norm', 0.0)
    slip_slope_squared = data.get('slip_slope_squared', 0.0)
    step = data.get('step', 0.0)
    temp_param_Ps = data.get('temp_param_Ps', Ps_cmdline)
    
    # Calculate expected slip cost delta using C++ formula
    expected_slip_cost_delta = slip_slope_squared * (v_norm ** 2) * step * temp_param_Ps
    
    # Store results
    results['expected_slip_cost_delta'] = expected_slip_cost_delta
    results['slip_slope_squared'] = slip_slope_squared
    results['v_norm'] = v_norm
    results['step'] = step
    results['temp_param_Ps'] = temp_param_Ps
    
    # Also verify slip_slope_squared calculation if sin values are available
    if 'sin_phix' in data and 'sin_phiy' in data:
        sin_phix = data['sin_phix']
        sin_phiy = data['sin_phiy']
        expected_slip_slope_squared = sin_phix**2 + sin_phiy**2
        results['expected_slip_slope_squared'] = expected_slip_slope_squared
        results['sin_phix'] = sin_phix
        results['sin_phiy'] = sin_phiy
    
    return results


def analyze_log_file(log_file_path: str, Ps_value: float, verbose: bool = False) -> None:
    """
    Analyze the log file and verify slip cost calculations.
    
    Args:
        log_file_path: Path to the ROS log file
        Ps_value: Slip cost weight parameter
        verbose: Enable detailed output
    """
    try:
        with open(log_file_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: Log file '{log_file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading log file: {e}")
        sys.exit(1)
    
    # Handle multi-line log entries by joining them
    lines = content.replace('\\\n', ' ').split('\n')
    
    print(f"Analyzing log file: {log_file_path}")
    print(f"Using slip cost weight Ps = {Ps_value}")
    print("=" * 80)
    
    debug_lines_found = 0
    successful_calculations = 0
    perfect_matches = 0
    mismatches = []
    
    for line_num, line in enumerate(lines, 1):
        data = extract_debug_data(line)
        if data is None:
            continue
        
        debug_lines_found += 1
        
        try:
            # Calculate expected slip cost
            results = calculate_expected_slip_cost(data, Ps_value)
            successful_calculations += 1
            
            # Compare with C++ calculation
            cpp_cost = data.get('slip_cost_delta', 0.0)
            expected_cost = results['expected_slip_cost_delta']
            diff = abs(cpp_cost - expected_cost)
            
            if diff < 1e-8:  # Very high precision match
                perfect_matches += 1
            elif diff > 1e-5:  # Significant difference
                mismatches.append({
                    'line': line_num,
                    'segment': data.get('segment', '?'),
                    'sample': data.get('sample', '?'),
                    'cpp_cost': cpp_cost,
                    'expected_cost': expected_cost,
                    'diff': diff
                })
            
            # Print results for first few entries or if verbose
            if debug_lines_found <= 5 or verbose:
                print(f"\nLine {line_num}: Segment {data.get('segment', '?')}, "
                      f"Sample {data.get('sample', '?')}")
                
                time_val = data.get('time', None)
                if time_val is not None:
                    print(f"  Time: {time_val:.6f}")
                
                print(f"  Input values:")
                print(f"    v_norm: {results['v_norm']:.6f}")
                print(f"    slip_slope_squared: {results['slip_slope_squared']:.6f}")
                print(f"    step: {results['step']:.6f}")
                print(f"    temp_param_Ps: {results['temp_param_Ps']:.6f}")
                
                if 'sin_phix' in results:
                    print(f"    sin_phix: {results['sin_phix']:.6f}")
                    print(f"    sin_phiy: {results['sin_phiy']:.6f}")
                    if 'expected_slip_slope_squared' in results:
                        exp_sss = results['expected_slip_slope_squared']
                        act_sss = results['slip_slope_squared']
                        sss_diff = abs(exp_sss - act_sss)
                        print(f"    Expected slip_slope_squared: {exp_sss:.6f}")
                        if sss_diff < 1e-8:
                            print(f"    ✓ slip_slope_squared calculation correct")
                        else:
                            print(f"    ⚠ slip_slope_squared difference: {sss_diff:.2e}")
                
                print(f"  Calculated values:")
                print(f"    Expected slip_cost_delta: {expected_cost:.8f}")
                print(f"    C++ slip_cost_delta: {cpp_cost:.8f}")
                
                if diff < 1e-8:
                    print(f"    ✓ Perfect match: C++ and Python calculations agree")
                elif diff < 1e-5:
                    print(f"    ✓ Good match: Difference = {diff:.2e}")
                else:
                    print(f"    ✗ Mismatch: Difference = {diff:.2e}")
        
        except Exception as e:
            print(f"Error processing line {line_num}: {e}")
            if verbose:
                print(f"  Line content: {line.strip()}")
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Total debug lines found: {debug_lines_found}")
    print(f"  Successful calculations: {successful_calculations}")
    print(f"  Perfect matches (diff < 1e-8): {perfect_matches}")
    print(f"  Significant mismatches (diff > 1e-5): {len(mismatches)}")
    
    if successful_calculations > 0:
        accuracy = (perfect_matches / successful_calculations) * 100
        print(f"  Accuracy: {accuracy:.2f}%")
    
    if mismatches:
        print(f"\nSignificant mismatches detected:")
        for m in mismatches[:5]:  # Show first 5 mismatches
            print(f"  Line {m['line']} (Seg {m['segment']}, Sample {m['sample']}): "
                  f"Expected {m['expected_cost']:.8f}, Got {m['cpp_cost']:.8f}, "
                  f"Diff {m['diff']:.2e}")
        if len(mismatches) > 5:
            print(f"  ... and {len(mismatches) - 5} more")
    
    if debug_lines_found == 0:
        print("  No debug lines found. Make sure:")
        print("  1. ROS log level is set to DEBUG")
        print("  2. The trajectory optimization is running")
        print("  3. The log file contains ALMTrajOpt debug output")
    
    # Overall verification result
    print(f"\n" + "=" * 80)
    if debug_lines_found > 0 and len(mismatches) == 0:
        print("✅ VERIFICATION PASSED: All slip cost calculations are correct!")
    elif debug_lines_found > 0 and len(mismatches) < successful_calculations * 0.01:
        print("✅ VERIFICATION MOSTLY PASSED: >99% of calculations are correct!")
    elif debug_lines_found > 0:
        print("⚠️  VERIFICATION ISSUES: Some calculations may be incorrect!")
    else:
        print("❌ VERIFICATION FAILED: No valid debug data found!")


def main():
    """Main function."""
    try:
        log_file_path, Ps_value, verbose = parse_arguments()
        analyze_log_file(log_file_path, Ps_value, verbose)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 