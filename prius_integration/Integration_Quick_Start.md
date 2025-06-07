# Prius集成快速启动指南

## 🚀 快速启动

### 1. 编译系统
```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### 2. 启动完整系统
```bash
# 完整系统（仿真 + 规划 + 控制）
roslaunch prius_scaled_controller prius_scaled_hill.launch

# 仅仿真模式
roslaunch prius_scaled_controller prius_scaled_hill.launch enable_planning:=false
```

### 3. 发送目标点
使用RViz的"2D Nav Goal"工具，或者命令行：
```bash
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped "
header:
  frame_id: 'map'
pose:
  position: {x: 5.0, y: 5.0, z: 0.0}
  orientation: {w: 1.0}"
```

### 4. 监控状态
```bash
# 查看所有Prius相关话题
rostopic list | grep prius

# 监控车辆位置
rostopic echo /prius/base_pose_ground_truth

# 监控控制指令
rostopic echo /racebot/cmd_vel
```

## ⚙️ 关键参数调整

### 位置：`prius_scaled_controller/config/prius_scaled_hill.yaml`

**如果跟踪不稳定，降低这些参数**：
- `max_acc_lon: 0.25` → `0.15`
- `max_acc_lat: 0.33` → `0.25`
- `max_omega: 3.0` → `2.0`

**如果响应太慢，提高这些参数**：
- `matrix_q: [150.0, 150.0, 5.0]` → `[200.0, 200.0, 8.0]`
- `throttle_gain: 0.3` → `0.4`

## 🔧 故障排除

### 问题1：车辆不动
- 检查TF链：`rosrun tf view_frames`
- 确认话题：`rostopic echo /prius_controls`

### 问题2：跟踪不准
- 降低速度：修改`max_vel`参数
- 增加控制权重：修改`matrix_q`

### 问题3：规划失败
- 检查地图加载：`rostopic echo /manager_node/occupancy_grid`
- 确认目标点在地图范围内

## 📁 文件说明

- **详细文档**: `Prius_Integration_Summary.md`
- **参数配置**: `prius_scaled_controller/config/prius_scaled_hill.yaml`
- **启动文件**: `prius_scaled_controller/launch/prius_scaled_hill.launch`
- **控制器代码**: `prius_scaled_controller/src/prius_trajectory_controller.*`

## 🎯 性能指标

使用保守配置预期性能：
- **最大速度**: 1.25 m/s
- **位置精度**: ±0.1m  
- **规划时间**: 1-3秒
- **稳定性**: 无侧滑/打滑 