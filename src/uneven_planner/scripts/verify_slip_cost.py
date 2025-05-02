#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证打滑成本计算脚本 (verify_slip_cost.py)
该脚本用于分析包含"SlipCostDebug:"日志的ROS日志文件，验证打滑成本计算的正确性。
"""

import re
import argparse
import sys
from typing import Dict, List, Tuple


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="验证打滑成本计算的日志分析脚本")
    parser.add_argument("log_file", help="ROS日志文件路径")
    parser.add_argument("--ps", type=float, default=None, 
                        help="期望的打滑成本权重Ps值 (如果不提供，则使用日志中记录的值)")
    parser.add_argument("--threshold", type=float, default=1e-6,
                        help="误差阈值，超过此值的计算将被标记为异常 (默认: 1e-6)")
    parser.add_argument("--top", type=int, default=5,
                        help="显示误差最大的前N条记录 (默认: 5)")
    return parser.parse_args()


def extract_values(line: str) -> Dict[str, float]:
    """
    从日志行中提取相关数值
    参数:
        line: 包含"SlipCostDebug:"的日志行
    返回:
        包含提取出的参数值的字典，如果提取失败则返回None
    """
    try:
        # 使用正则表达式匹配参数
        pattern = r'SlipCostDebug: j=(\d+), t=([0-9.-]+), v=([0-9.-]+), slope=([0-9.-]+), ' \
                  r'phi_x=([0-9.-]+), phi_y=([0-9.-]+), Ps=([0-9.-]+), dt=([0-9.-]+), ' \
                  r'slip_cost_step=([0-9.-]+), current_total_cost=([0-9.-]+)'
        
        match = re.search(pattern, line)
        if not match:
            return None
        
        # 提取匹配的参数值并转换为浮点数
        values = {
            'j': int(match.group(1)),
            't': float(match.group(2)),
            'v': float(match.group(3)),
            'slope': float(match.group(4)),
            'phi_x': float(match.group(5)),
            'phi_y': float(match.group(6)),
            'Ps': float(match.group(7)),
            'dt': float(match.group(8)),
            'slip_cost_step': float(match.group(9)),
            'total_cost': float(match.group(10))
        }
        return values
    
    except Exception as e:
        print(f"警告: 解析行时出错: {e}")
        print(f"问题行: {line.strip()}")
        return None


def calculate_expected_slip_cost(values: Dict[str, float], ps_override: float = None) -> float:
    """
    根据提取的参数计算预期的打滑成本
    参数:
        values: 包含参数值的字典
        ps_override: 可选的外部Ps值，如果提供则使用此值代替日志中记录的Ps
    返回:
        计算出的预期打滑成本值
    """
    ps = ps_override if ps_override is not None else values['Ps']
    v = values['v']
    slope = values['slope']
    dt = values['dt']
    
    # 使用公式: slip_cost = Ps * (slope * v)^2 * dt
    expected_slip_cost = ps * pow(slope * v, 2) * dt
    return expected_slip_cost


def analyze_log_file(log_path: str, ps_override: float = None, 
                    error_threshold: float = 1e-6) -> Tuple[int, List[Tuple[Dict[str, float], float, float]]]:
    """
    分析日志文件中的打滑成本计算
    参数:
        log_path: 日志文件路径
        ps_override: 外部提供的Ps值
        error_threshold: 误差阈值
    返回:
        分析结果: (总记录数, 误差列表)
    """
    # 记录各种统计信息
    total_lines = 0
    errors = []  # 格式: (日志值字典, 预期值, 误差)
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if "SlipCostDebug:" in line:
                    total_lines += 1
                    
                    # 提取参数值
                    values = extract_values(line)
                    if not values:
                        continue
                    
                    # 计算预期值和误差
                    expected = calculate_expected_slip_cost(values, ps_override)
                    actual = values['slip_cost_step']
                    error = abs(expected - actual)
                    
                    # 如果误差超过阈值，记录下来
                    if error > error_threshold:
                        errors.append((values, expected, error))
    
    except Exception as e:
        print(f"错误: 读取日志文件时发生错误: {e}")
        sys.exit(1)
    
    # 按误差大小排序
    errors.sort(key=lambda x: x[2], reverse=True)
    
    return total_lines, errors


def generate_report(total_lines: int, errors: List[Tuple[Dict[str, float], float, float]], 
                   threshold: float, top_n: int = 5):
    """
    生成分析报告
    参数:
        total_lines: 总分析行数
        errors: 误差记录列表
        threshold: 误差阈值
        top_n: 显示误差最大的前N条记录
    """
    print("\n===== 打滑成本验证报告 =====")
    print(f"总共分析的日志行数: {total_lines}")
    
    if not errors:
        print("所有计算均在误差阈值内，计算正确！")
        return
    
    max_error = errors[0][2] if errors else 0
    print(f"最大误差: {max_error:.8e}")
    print(f"误差超过阈值 ({threshold:.8e}) 的行数: {len(errors)}")
    
    if errors and top_n > 0:
        print(f"\n误差最大的 {min(top_n, len(errors))} 条记录:")
        print("-" * 100)
        print(f"{'索引':>5} {'时间':>8} {'速度':>8} {'坡度':>8} {'Ps值':>8} {'dt':>8} {'记录值':>15} {'预期值':>15} {'误差':>15}")
        print("-" * 100)
        
        for i, (values, expected, error) in enumerate(errors[:top_n]):
            print(f"{values['j']:5d} {values['t']:8.3f} {values['v']:8.3f} {values['slope']:8.3f} "
                  f"{values['Ps']:8.3f} {values['dt']:8.3f} {values['slip_cost_step']:15.8e} "
                  f"{expected:15.8e} {error:15.8e}")


def main():
    """主函数"""
    args = parse_args()
    
    print(f"分析日志文件: {args.log_file}")
    if args.ps is not None:
        print(f"使用外部提供的Ps值: {args.ps}")
    print(f"误差阈值: {args.threshold}")
    
    # 分析日志文件
    total_lines, errors = analyze_log_file(args.log_file, args.ps, args.threshold)
    
    # 生成报告
    generate_report(total_lines, errors, args.threshold, args.top)


if __name__ == "__main__":
    main()