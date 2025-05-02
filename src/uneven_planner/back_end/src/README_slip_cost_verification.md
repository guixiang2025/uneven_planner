# 滑动成本验证工具

本目录包含用于验证ALM轨迹优化中滑动成本计算的工具。

## 文件说明

- `alm_traj_opt.cpp` - ALM轨迹优化类，包含调试日志
- `verify_slip_cost.py` - Python验证脚本
- `test_log.txt` - 示例日志文件

## 使用方法

### 1. 启用调试日志

在运行轨迹规划器之前，设置ROS日志级别为DEBUG：

```bash
# 设置日志格式
export ROSCONSOLE_FORMAT='[${severity}] [${time}] [${node}]: ${message}'

# 方法1：运行时设置日志级别
rosservice call /your_node_name/set_logger_level "{logger: 'ros.uneven_planner', level: 'DEBUG'}"

# 方法2：启动时设置环境变量
export ROSCONSOLE_MIN_SEVERITY=DEBUG
```

### 2. 收集日志

运行轨迹规划器并将日志保存到文件：

```bash
# 将日志输出重定向到文件
your_planning_command 2>&1 | tee slip_cost_debug.log

# 或者运行rosnode并记录日志
rosrun back_end back_end_node 2>&1 | tee slip_cost_debug.log
```

### 3. 分析日志

使用Python脚本分析收集的日志：

```bash
# 基本用法
python3 verify_slip_cost.py slip_cost_debug.log 1.5

# 详细输出模式
python3 verify_slip_cost.py slip_cost_debug.log 1.5 --verbose

# 查看帮助
python3 verify_slip_cost.py --help
```

### 参数说明

- `log_file_path`: ROS日志文件的路径
- `Ps_value`: 滑动成本权重参数
- `--verbose, -v`: 启用详细输出模式

### 4. 测试脚本

使用提供的示例日志文件测试脚本：

```bash
python3 verify_slip_cost.py test_log.txt 1.0
```

## 输出说明

脚本会为每个找到的调试日志行输出：

- **输入值**: 从日志中提取的原始数据
  - `v_norm`: 速度范数
  - `inv_cos_vphix`: 地形调整因子
  - `phi_x_rad`, `phi_y_rad`: 坡度角（弧度）

- **计算值**: 脚本独立计算的结果
  - `Expected slope`: 计算的坡度
  - `Terrain-adjusted velocity`: 地形调整后的速度
  - `Slip factor`: 滑动因子
  - `Expected slip cost step`: 预期的滑动成本

- **对比验证**: 如果日志中包含C++计算结果，会进行比较

## 滑动成本计算公式

```
slope = sqrt(phi_x_rad² + phi_y_rad²)
v_terrain_adjusted = v_norm × inv_cos_vphix
slip_factor = slope × v_terrain_adjusted
slip_cost_step = Ps × (slip_factor)² × dt_step
```

## 注意事项

1. 确保ROS节点启用了DEBUG日志级别
2. 日志中应包含包含 "Slip cost debug" 的行
3. 脚本支持多种输入格式（角度值或正弦值）
4. 缺失的 `inv_cos_vphix` 值将默认为1.0
5. 缺失的 `dt_step` 值将默认为1.0

## 故障排除

如果脚本没有找到调试行：

1. 检查ROS日志级别是否设置为DEBUG
2. 确认轨迹优化正在运行
3. 验证日志文件包含ALMTrajOpt的输出
4. 检查日志文件路径是否正确 