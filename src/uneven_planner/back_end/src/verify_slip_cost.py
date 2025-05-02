#!/usr/bin/env python3
"""
Slip Cost Verification Script

This script analyzes ROS log files containing "SlipCostDebug:" identifiers
and independently calculates expected slip costs to verify C++ implementation.

Usage:
    python3 verify_slip_cost.py <log_file_path> <Ps_value>

Example:
    python3 verify_slip_cost.py /path/to/ros_log.txt 1.5
"""

import sys
import re
import math
import argparse
from typing import Dict, List, Optional, Tuple


def parse_arguments() -> Tuple[str, float]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify slip cost calculations from ROS debug logs",
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
    Extract numerical values from a SlipCostDebug log line.
    
    Args:
        line: Log line containing SlipCostDebug information
        
    Returns:
        Dictionary with extracted values or None if parsing fails
    """
    # Look for lines containing our debug identifier
    if "Slip cost debug" not in line and "SlipCostDebug:" not in line:
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
        time_match = re.search(r'time: ([-+]?\d*\.?\d+)', line)
        if time_match:
            data['time'] = float(time_match.group(1))
        
        # Extract velocity (v_norm or current_velocity)
        vel_match = re.search(r'(?:velocity|v_norm): ([-+]?\d*\.?\d+)', line)
        if vel_match:
            data['v_norm'] = float(vel_match.group(1))
        
        # Extract terrain adjustment factor
        inv_cos_match = re.search(r'inv_cos_vphix: ([-+]?\d*\.?\d+)', line)
        if inv_cos_match:
            data['inv_cos_vphix'] = float(inv_cos_match.group(1))
        
        # Extract slope angles (try different formats)
        phi_x_match = re.search(r'phi_x_rad: ([-+]?\d*\.?\d+)', line)
        if phi_x_match:
            data['phi_x_rad'] = float(phi_x_match.group(1))
        
        phi_y_match = re.search(r'phi_y_rad: ([-+]?\d*\.?\d+)', line)
        if phi_y_match:
            data['phi_y_rad'] = float(phi_y_match.group(1))
        
        # Alternative: extract sin values if available
        sin_phix_match = re.search(r'sin_phix: ([-+]?\d*\.?\d+)', line)
        if sin_phix_match:
            data['sin_phix'] = float(sin_phix_match.group(1))
        
        sin_phiy_match = re.search(r'sin_phiy: ([-+]?\d*\.?\d+)', line)
        if sin_phiy_match:
            data['sin_phiy'] = float(sin_phiy_match.group(1))
        
        # Extract direct slope if available
        slope_match = re.search(r'(?:current_slope|slope): ([-+]?\d*\.?\d+)', line)
        if slope_match:
            data['current_slope'] = float(slope_match.group(1))
        
        # Extract cost before slip
        cost_before_match = re.search(r'cost_before_slip: ([-+]?\d*\.?\d+)', line)
        if cost_before_match:
            data['cost_before_slip'] = float(cost_before_match.group(1))
        
        # Extract temp parameter Ps
        ps_match = re.search(r'temp_param_Ps: ([-+]?\d*\.?\d+)', line)
        if ps_match:
            data['temp_param_Ps'] = float(ps_match.group(1))
        
        # Extract dt_step if available
        dt_match = re.search(r'dt_step: ([-+]?\d*\.?\d+)', line)
        if dt_match:
            data['dt_step'] = float(dt_match.group(1))
        
        # Extract slip_cost_step if available (for comparison)
        slip_cost_match = re.search(r'slip_cost_step: ([-+]?\d*\.?\d+)', line)
        if slip_cost_match:
            data['slip_cost_step'] = float(slip_cost_match.group(1))
        
        return data if data else None
        
    except (ValueError, AttributeError) as e:
        print(f"Warning: Failed to parse line: {line.strip()}")
        print(f"Error: {e}")
        return None


def calculate_slope(data: Dict[str, float]) -> float:
    """
    Calculate slope from available angle data.
    
    Args:
        data: Dictionary containing extracted values
        
    Returns:
        Calculated slope value
    """
    # If slope is directly available, use it
    if 'current_slope' in data:
        return data['current_slope']
    
    # If phi_x_rad and phi_y_rad are available
    if 'phi_x_rad' in data and 'phi_y_rad' in data:
        phi_x = data['phi_x_rad']
        phi_y = data['phi_y_rad']
        return math.sqrt(phi_x * phi_x + phi_y * phi_y)
    
    # If sin values are available, calculate angles first
    if 'sin_phix' in data and 'sin_phiy' in data:
        # Clamp sin values to valid range [-1, 1]
        sin_phix = max(-1.0, min(1.0, data['sin_phix']))
        sin_phiy = max(-1.0, min(1.0, data['sin_phiy']))
        
        phi_x = math.asin(sin_phix)
        phi_y = math.asin(sin_phiy)
        
        return math.sqrt(phi_x * phi_x + phi_y * phi_y)
    
    raise ValueError("Insufficient angle data to calculate slope")


def calculate_expected_slip_cost(data: Dict[str, float], Ps_cmdline: float, 
                                dt_step: float = 1.0) -> Dict[str, float]:
    """
    Calculate expected slip cost based on extracted data.
    
    Args:
        data: Dictionary with extracted log values
        Ps_cmdline: Slip cost weight from command line
        dt_step: Time step (default 1.0 if not available)
        
    Returns:
        Dictionary with calculation results
    """
    results = {}
    
    # Get basic values
    v_norm = data.get('v_norm', 0.0)
    inv_cos_vphix = data.get('inv_cos_vphix', 1.0)
    
    # Use provided dt_step or default
    dt_used = data.get('dt_step', dt_step)
    
    # Calculate slope
    try:
        expected_slope = calculate_slope(data)
        results['expected_slope'] = expected_slope
    except ValueError as e:
        print(f"Warning: {e}")
        expected_slope = 0.0
        results['expected_slope'] = expected_slope
    
    # Calculate terrain-adjusted velocity
    expected_v_terrain_adjusted = v_norm * inv_cos_vphix
    results['expected_v_terrain_adjusted'] = expected_v_terrain_adjusted
    
    # Calculate expected slip cost step
    # Formula: Ps * (slope * v_terrain_adjusted)^2 * dt_step
    slip_factor = expected_slope * expected_v_terrain_adjusted
    expected_slip_cost_step = Ps_cmdline * (slip_factor ** 2) * dt_used
    results['expected_slip_cost_step'] = expected_slip_cost_step
    
    # Store intermediate values for debugging
    results['slip_factor'] = slip_factor
    results['dt_used'] = dt_used
    results['Ps_used'] = Ps_cmdline
    
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
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: Log file '{log_file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading log file: {e}")
        sys.exit(1)
    
    print(f"Analyzing log file: {log_file_path}")
    print(f"Using slip cost weight Ps = {Ps_value}")
    print("=" * 80)
    
    debug_lines_found = 0
    successful_calculations = 0
    
    for line_num, line in enumerate(lines, 1):
        data = extract_debug_data(line)
        if data is None:
            continue
        
        debug_lines_found += 1
        
        try:
            # Calculate expected slip cost
            results = calculate_expected_slip_cost(data, Ps_value)
            successful_calculations += 1
            
            # Print results
            print(f"\nLine {line_num}: Segment {data.get('segment', '?')}, "
                  f"Sample {data.get('sample', '?')}")
            
            time_val = data.get('time', None)
            if time_val is not None:
                print(f"  Time: {time_val:.6f}")
            else:
                print(f"  Time: N/A")
                
            print(f"  Input values:")
            
            v_norm_val = data.get('v_norm', None)
            if v_norm_val is not None:
                print(f"    v_norm: {v_norm_val:.6f}")
            else:
                print(f"    v_norm: N/A")
                
            inv_cos_val = data.get('inv_cos_vphix', None)
            if inv_cos_val is not None:
                print(f"    inv_cos_vphix: {inv_cos_val:.6f}")
            else:
                print(f"    inv_cos_vphix: N/A")
            
            if verbose:
                phi_x_val = data.get('phi_x_rad', None)
                if phi_x_val is not None:
                    print(f"    phi_x_rad: {phi_x_val:.6f}")
                else:
                    print(f"    phi_x_rad: N/A")
                    
                phi_y_val = data.get('phi_y_rad', None)
                if phi_y_val is not None:
                    print(f"    phi_y_rad: {phi_y_val:.6f}")
                else:
                    print(f"    phi_y_rad: N/A")
                    
                sin_phix_val = data.get('sin_phix', None)
                if sin_phix_val is not None:
                    print(f"    sin_phix: {sin_phix_val:.6f}")
                else:
                    print(f"    sin_phix: N/A")
                    
                sin_phiy_val = data.get('sin_phiy', None)
                if sin_phiy_val is not None:
                    print(f"    sin_phiy: {sin_phiy_val:.6f}")
                else:
                    print(f"    sin_phiy: N/A")
            
            print(f"  Calculated values:")
            print(f"    Expected slope: {results['expected_slope']:.6f}")
            print(f"    Terrain-adjusted velocity: {results['expected_v_terrain_adjusted']:.6f}")
            print(f"    Slip factor (slope * v_adj): {results['slip_factor']:.6f}")
            print(f"    dt_step: {results['dt_used']:.6f}")
            print(f"    Expected slip cost step: {results['expected_slip_cost_step']:.6f}")
            
            # Compare with C++ calculation if available
            if 'slip_cost_step' in data:
                cpp_cost = data['slip_cost_step']
                print(f"    C++ slip cost step: {cpp_cost:.6f}")
                if abs(cpp_cost - results['expected_slip_cost_step']) < 1e-6:
                    print(f"    ✓ Match: C++ and Python calculations agree")
                else:
                    diff = abs(cpp_cost - results['expected_slip_cost_step'])
                    print(f"    ✗ Mismatch: Difference = {diff:.6f}")
            
            # Verify temp_param_Ps if available
            if 'temp_param_Ps' in data:
                temp_ps = data['temp_param_Ps']
                print(f"    temp_param_Ps from log: {temp_ps:.6f}")
                if abs(temp_ps - Ps_value) > 1e-6:
                    print(f"    Warning: temp_param_Ps differs from command line Ps")
        
        except Exception as e:
            print(f"Error processing line {line_num}: {e}")
            if verbose:
                print(f"  Line content: {line.strip()}")
    
    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Debug lines found: {debug_lines_found}")
    print(f"  Successful calculations: {successful_calculations}")
    
    if debug_lines_found == 0:
        print("  No debug lines found. Make sure:")
        print("  1. ROS log level is set to DEBUG")
        print("  2. The trajectory optimization is running")
        print("  3. The log file contains ALMTrajOpt debug output")


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