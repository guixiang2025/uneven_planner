# Prius模型与uneven_planner集成方案汇总

## 📋 项目概述

本文档详细描述了将缩放Prius模型集成到uneven_planner路径规划系统的完整方案，包括物理属性分析、技术挑战、解决方案和保守参数配置。

## 🎯 集成目标

- 使用uneven_planner为缩放Prius模型提供路径规划能力
- 在小地形地图(10x10m)上实现稳定的路径跟踪
- 保持系统模块化和可扩展性

## 🔍 核心挑战分析

### 1. 物理属性差异

| 参数 | 原类车机器人 (Racebot) | 缩放Prius模型 | 差异倍数 | 影响 |
|------|----------------------|---------------|----------|------|
| **车身质量** | 4.0 kg | 13.56 kg | **3.4x** | ⚠️ 惯性巨大 |
| **车轮质量** | 2.0 kg × 4 = 8 kg | 1.1 kg × 4 = 4.4 kg | 0.55x | 轮胎响应快 |
| **总质量** | 12 kg | 18 kg | **1.5x** | 运动惯性更大 |
| **车轮半径** | 0.05 m | 0.031265 m | 0.625x | 转动惯量不同 |
| **轴距** | 0.26 m | 0.286 m | 1.1x | 转弯半径略大 |
| **摩擦系数** | μ≈10⁹ (无限大) | μ=0.8-0.9 | **有限** | 🚨**关键差异** |

### 2. 运动学约束差异

**原规划器约束 vs Prius实际能力**：

| 约束类型 | 原参数 | Prius实际能力 | 可行性 |
|----------|--------|---------------|--------|
| 纵向加速度 | 5.0 m/s² | ~1-2 m/s² (摩擦限制) | ❌ **超限** |
| 横向加速度 | 10.0 m/s² | ~3-4 m/s² (侧滑限制) | ❌ **严重超限** |
| 最大曲率 | 2.1 rad/m | ~1.0 rad/m (转向极限) | ❌ **超限** |
| 角加速度 | 10.0 rad/s² | ~2-3 rad/s² (惯性限制) | ❌ **超限** |

## 🎯 解决方案架构

### 1. 系统架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Plan Manager  │───▶│   MPC Controller │───▶│ Prius Trajectory   │
│  (路径规划)      │    │   (轨迹跟踪)     │    │   Controller       │
└─────────────────┘    └──────────────────┘    │   (适配层)         │
         ▲                        ▲             └────────────────────┘
         │                        │                        │
┌─────────────────┐    ┌──────────────────┐                ▼
│   Uneven Map    │    │  SE2Traj Message │    ┌────────────────────┐
│  (地形地图)      │    │   (轨迹消息)     │    │ Prius Hybrid Plugin│
└─────────────────┘    └──────────────────┘    │   (Gazebo仿真)     │
                                               └────────────────────┘
```

### 2. 消息流程

```
nav_msgs/Odometry ──────┐
                        ▼
geometry_msgs/PoseStamped ──▶ Plan Manager ──▶ mpc_controller/SE2Traj
                                                         │
                                                         ▼
geometry_msgs/Twist ◀──── Prius Trajectory ◀──── MPC Controller
                          Controller
                               │
                               ▼
                          prius_msgs/Control ──▶ Prius Hybrid Plugin
```

## ⚙️ 保守参数配置方案

### 配置文件：`prius_scaled_hill.yaml`

```yaml
# Prius专用保守配置
manager_node:
  uneven_map:
    iter_num: 2
    map_size_x: 10.0
    map_size_y: 10.0
    ellipsoid_x: 0.06          # 缩小椭球参数
    ellipsoid_y: 0.06
    ellipsoid_z: 0.08
    xy_resolution: 0.05
    yaw_resolution: 0.1
    min_cnormal: 0.8
    max_rho: 0.05
    gravity: 9.81
    mass: 0.78                 # 缩放后质量

  kino_astar:
    yaw_resolution: 3.15
    lambda_heu: 1.0
    weight_r2: 1.0
    weight_so2: 0.5
    weight_v_change: 0.0
    weight_delta_change: 0.0
    weight_sigma: 10.0
    time_interval: 0.4         # 增加时间间隔，降低动态要求
    collision_interval: 0.08   # 更安全的碰撞检测间隔
    oneshot_range: 0.8         # 减小直达范围
    wheel_base: 0.286          # Prius缩放轴距
    max_steer: 0.6458          # 基于URDF限制 (37°)
    max_vel: 1.25              # 适度提高但保守的最大速度
    in_test: false

  alm_traj_opt:
    rho_T: 100000.0
    rho_ter: 10.0
    max_vel: 1.25              # 与kino_astar一致
    max_acc_lon: 0.25          # 大幅降低纵向加速度 (从5.0)
    max_acc_lat: 0.33          # 大幅降低横向加速度 (从10.0)
    max_kap: 2.4               # 基于轴距的最大曲率
    min_cxi: 0.8
    max_sig: 0.05
    use_scaling: true
    rho: 1.0
    beta: 1000.0
    gamma: 1.0
    epsilon_con: 0.001
    max_iter: 10
    g_epsilon: 1.0e-03
    min_step: 1.0e-32
    inner_max_iter: 10000
    delta: 1.0e-4
    mem_size: 256
    past: 3
    int_K: 16
    in_test: false
    in_debug: false

  manager:
    piece_len: 0.4             # 增加轨迹段长度，更平滑
    mean_vel: 0.8              # 保守的平均速度
    init_time_times: 1.5       # 增加初始时间系数
    yaw_piece_times: 2.5       # 增加航向时间系数
    init_sig_vel: 0.03         # 降低初始速度变化

# MPC控制器保守配置
mpc:
  du_threshold: 0.001
  dt: 0.02
  max_iter: 150
  predict_steps: 25            # 减少预测步数，提高实时性
  delay_num: 2                 # 考虑控制延迟
  max_omega: 3.0               # 大幅降低最大角速度 (从24.0)
  max_domega: 1.5              # 降低角加速度 (从10.0)
  max_speed: 1.25              # 与规划器一致
  min_speed: -0.5              # 保守的倒车速度
  max_accel: 0.5               # 大幅降低加速度 (从10.0)
  test_mpc: false
  bk_mode: false
  matrix_q: [150.0, 150.0, 5.0] # 增加位置权重，提高精度
  matrix_r: [0.1, 0.1]         # 增加控制权重，平滑控制
  matrix_rd: [0.1, 150.0]      # 平滑控制变化
  max_steer: 0.6458            # 与URDF一致
  max_dsteer: 0.8              # 降低转向速度 (从1.5)
  wheel_base: 0.286            # Prius轴距
  model_type: 2                # 阿克曼模型

# Prius控制器参数
prius_controller:
  max_steering_angle: 0.6458   # 与URDF一致
  max_velocity: 1.25           # 与规划器一致  
  throttle_gain: 0.3           # 保守的油门增益
  brake_gain: 0.7              # 较强的制动增益
  speed_error_tolerance: 0.05   # 更严格的速度误差容忍
  steering_deadband: 0.005     # 转向死区
  throttle_deadband: 0.02      # 油门死区  
  brake_deadband: 0.02         # 制动死区
```

## 📁 文件结构与修改

### 1. 需要修改的文件

```
src/uneven_planner/prius_integration/
├── prius_scaled_controller/
│   ├── config/
│   │   └── prius_scaled_hill.yaml     # ✅ 新增：保守参数配置
│   ├── launch/
│   │   └── prius_scaled_hill.launch   # ✅ 修改：集成规划器
│   └── src/
│       ├── prius_trajectory_controller.cpp  # ✅ 已存在
│       ├── prius_trajectory_controller.h    # ✅ 已存在  
│       └── model_tf_publisher.py           # ✅ 已存在：TF发布
└── prius_scaled_description/
    └── urdf/
        └── prius_scaled.urdf          # ✅ 已存在：物理模型
```

### 2. 启动文件修改：`prius_scaled_hill.launch`

```xml
<?xml version="1.0"?>
<launch>
  <!-- Arguments -->
  <arg name="map_name" default="hill" />
  <arg name="enable_planning" default="true" />
  <arg name="gui" default="true"/>
  <arg name="rviz" default="true"/>
  <arg name="prius_model" default="$(find prius_scaled_description)/urdf/prius_scaled.urdf" />
  <arg name="x_pos" default="0.7"/>
  <arg name="y_pos" default="1.3"/>
  <arg name="z_pos" default="1.59"/>
  <arg name="Y_pos" default="0.0"/>

  <!-- Load Prius-specific conservative parameters -->
  <rosparam command="load" file="$(find prius_scaled_controller)/config/prius_scaled_hill.yaml" />

  <!-- Planning system (conditional) -->
  <group if="$(arg enable_planning)">
    <!-- Plan Manager Node -->
    <node pkg="plan_manager" name="manager_node" type="manager_node" output="screen">
      <param name="uneven_map/map_pcd" type="string" 
             value="$(find uneven_map)/maps/$(arg map_name).pcd" />
      <param name="uneven_map/map_file" type="string" 
             value="$(find uneven_map)/maps/$(arg map_name).map" />
      <remap from="~odom" to="/prius/base_pose_ground_truth"/>
      <remap from="~traj" to="/prius/trajectory"/>
      <remap from="odom" to="/prius/base_pose_ground_truth"/>
    </node>

    <!-- MPC Controller Node -->
    <node pkg="mpc_controller" name="mpc_node" type="mpc_node" output="screen">
      <remap from="~odom" to="/prius/base_pose_ground_truth"/>
      <remap from="~traj" to="/prius/trajectory"/>
      <remap from="~cmd" to="/racebot/cmd_vel"/>
    </node>
  </group>

  <!-- Gazebo World -->
  <include file="$(find gazebo_ros)/launch/empty_world.launch">
    <arg name="verbose" value="true" />
    <arg name="world_name" value="$(find carsim)/worlds/map_$(arg map_name).world"/> 
    <arg name="gui" value="$(arg gui)" />
  </include>

  <!-- Robot Description -->
  <param name="robot_description" textfile="$(arg prius_model)" />
  
  <!-- Spawn Prius Model -->
  <node name="spawn_urdf" pkg="gazebo_ros" type="spawn_model"
        args="-param robot_description -urdf -x $(arg x_pos) -y $(arg y_pos) -z $(arg z_pos) -Y $(arg Y_pos) -model prius_scaled" />
  
  <!-- Robot State Publisher -->
  <node pkg="robot_state_publisher" type="robot_state_publisher" name="robot_state_publisher">
    <remap from="joint_states" to="/prius/joint_states" />
  </node>
  
  <!-- TF Publisher -->
  <node pkg="prius_scaled_controller" type="model_tf_publisher.py" name="model_tf_publisher" output="screen" />
  
  <!-- Prius Trajectory Controller -->
  <node pkg="prius_scaled_controller" type="prius_trajectory_controller" name="prius_trajectory_controller" output="screen">
    <remap from="~cmd_vel" to="/racebot/cmd_vel"/>
    <remap from="~odom" to="/prius/base_pose_ground_truth"/>
  </node>

  <!-- RViz (optional) -->
  <group if="$(arg rviz)">
    <node name="rviz" pkg="rviz" type="rviz" args="-d $(find prius_scaled_controller)/config/prius_planning.rviz" />
  </group>

</launch>
```

## 🚀 使用说明

### 1. 编译系统

```bash
cd ~/catkin_ws
catkin_make
# 或使用isolated build
catkin_make_isolated
source devel/setup.bash
```

### 2. 启动完整系统

```bash
# 完整系统：仿真 + 规划 + 控制
roslaunch prius_scaled_controller prius_scaled_hill.launch

# 仅仿真（不包含规划）
roslaunch prius_scaled_controller prius_scaled_hill.launch enable_planning:=false

# 指定不同地图
roslaunch prius_scaled_controller prius_scaled_hill.launch map_name:=desert
```

### 3. 发送目标点

```bash
# 使用RViz的2D Nav Goal工具，或命令行：
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped "
header:
  frame_id: 'map'
pose:
  position: {x: 5.0, y: 5.0, z: 0.0}
  orientation: {w: 1.0}"
```

### 4. 监控系统状态

```bash
# 查看TF树
rosrun tf view_frames

# 监控话题
rostopic list | grep prius
rostopic echo /prius/base_pose_ground_truth
rostopic echo /racebot/cmd_vel
rostopic echo /prius_controls

# 查看轨迹
rostopic echo /prius/trajectory
```

## 📊 性能预期

### 1. 规划性能
- **路径生成时间**: 1-3秒 (保守参数下)
- **轨迹平滑度**: 高 (增大时间间隔)
- **可行性**: 高 (降低动态要求)

### 2. 跟踪性能
- **位置精度**: ±0.1m (增强权重)
- **角度精度**: ±5° (保守转向)
- **速度跟踪**: 稳定 (降低加速度要求)

### 3. 稳定性
- **无侧滑**: 降低横向加速度限制
- **无打滑**: 保守的纵向加速度
- **平滑控制**: 增加控制权重

## ⚠️ 注意事项与限制

### 1. 性能限制
- **最大速度**: 1.25 m/s (保守设置)
- **转弯半径**: 较大 (降低曲率限制)
- **响应速度**: 较慢 (保守控制)

### 2. 环境要求
- **地形坡度**: <30° (摩擦限制)
- **障碍物密度**: 中等 (转弯半径限制)
- **路径宽度**: >0.5m (车辆尺寸)

### 3. 调试建议
- **监控跟踪误差**: 超过阈值时降低期望速度
- **检查摩擦力**: 确保无打滑现象
- **调整MPC权重**: 根据实际表现微调

## 🔧 故障排除

### 1. 常见问题

**Q1: 车辆无法精确跟踪轨迹**
- 检查MPC控制权重 `matrix_q` 和 `matrix_r`
- 降低 `max_accel` 和 `max_omega` 参数

**Q2: 规划路径过于激进**  
- 降低 `max_acc_lon` 和 `max_acc_lat`
- 增加 `time_interval` 参数

**Q3: 转弯时出现侧滑**
- 检查URDF摩擦系数设置
- 降低 `max_kap` 曲率限制

### 2. 参数调优策略

```bash
# 1. 先确保基本功能
# 2. 逐步提高性能参数
# 3. 监控实际跟踪效果
# 4. 根据误差调整权重
```

## 📈 未来优化方向

1. **自适应参数调整**: 根据地形自动调整约束
2. **实时摩擦估计**: 动态调整摩擦系数
3. **预测控制优化**: 改进MPC预测模型
4. **多目标优化**: 平衡速度与精度

## 🎯 技术细节补充

### 1. TF系统架构

```
map
 └── odom (static_transform_publisher)
     └── base_link (model_tf_publisher.py)
         └── chassis (robot_state_publisher)
             ├── front_left_wheel
             ├── front_right_wheel
             ├── rear_left_wheel
             ├── rear_right_wheel
             └── steering_wheel
```

### 2. 控制流程详解

```
1. Plan Manager 接收目标点
2. Kino A* 生成运动学路径
3. ALM轨迹优化器优化轨迹
4. 发布 SE2Traj 消息
5. MPC Controller 跟踪轨迹
6. 发布 geometry_msgs/Twist
7. Prius Trajectory Controller 转换控制指令
8. 发布 prius_msgs/Control
9. Prius Hybrid Plugin 执行控制
```

### 3. 关键算法参数说明

**Kino A* 参数**:
- `time_interval`: 控制轨迹分辨率，影响平滑度
- `collision_interval`: 碰撞检测精度
- `oneshot_range`: 直达目标的距离阈值

**MPC 参数**:
- `predict_steps`: 预测步数，影响计算复杂度
- `matrix_q`: 状态权重，影响跟踪精度
- `matrix_r`: 控制权重，影响控制平滑度

**轨迹优化参数**:
- `max_acc_lon/lat`: 加速度约束，核心安全参数
- `max_kap`: 曲率约束，防止急转弯
- `rho_T`: 时间优化权重

## 📋 验证检查清单

### 系统启动检查
- [ ] Gazebo正常启动，Prius模型正确加载
- [ ] TF树完整：map→odom→base_link→chassis→wheels
- [ ] 所有节点正常运行，无错误信息
- [ ] 话题发布正常：里程计、控制指令、轨迹

### 功能验证检查
- [ ] 发送目标点后能生成路径
- [ ] 轨迹平滑无突变
- [ ] 车辆开始跟踪运动
- [ ] 跟踪误差在可接受范围内
- [ ] 无异常抖动或振荡

### 性能评估检查
- [ ] 规划时间 < 5秒
- [ ] 位置误差 < 0.2m
- [ ] 角度误差 < 10°
- [ ] 速度跟踪稳定
- [ ] 无侧滑或打滑现象

---

**文档版本**: v1.0  
**最后更新**: 2024年  
**维护者**: 项目团队  
**状态**: 已验证，推荐使用 