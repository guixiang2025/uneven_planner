# Prius Scaled Controller

这个包提供了针对1:10比例的Prius模型的控制器，用于在不平坦地形上进行导航。

## 功能

- 接收轨迹或速度命令，转换为Prius控制命令
- 支持在不平坦地形上的路径规划和导航
- 与现有的轨迹规划器集成
- 适配缩小比例的动力学模型参数

## 组件

- `prius_trajectory_controller.py`: 将cmd_vel命令转换为Prius控制命令的核心控制器
- `mpc_controller_node`: MPC控制器，将轨迹转换为速度命令
- `model_tf_publisher.py`: TF变换发布器
- 启动文件：
  - `prius_scaled_hill.launch`: 启动带图形界面的完整系统
  - `prius_scaled_hill_headless.launch`: 无图形界面版本，适合远程服务器
- 测试工具:
  - `test_navigation.py`: 用于测试导航功能的脚本
  - `teleop_keyboard.py`: 键盘手动控制脚本

## 依赖

- ROS Noetic
- Gazebo 11
- prius_msgs (可选，如果不可用会使用简化控制)
- plan_manager
- uneven_map
- prius_scaled_description
- mpc_controller

## 重要：构建说明

⚠️ **由于工作空间包含非catkin包，必须使用隔离构建模式：**

```bash
cd ~/catkin_ws
catkin_make_isolated --install -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

构建完成后，使用隔离环境：
```bash
source ~/catkin_ws/install_isolated/setup.bash
```

## 完整使用流程

### 1. 构建系统
```bash
cd ~/catkin_ws
catkin_make_isolated --install -DCMAKE_POLICY_VERSION_MINIMUM=3.5
source install_isolated/setup.bash
```

### 2. 启动基础系统

**方法一：带图形界面（本地使用）**
```bash
roslaunch prius_scaled_controller prius_scaled_hill.launch
```

**方法二：无图形界面（远程服务器/低资源）**
```bash
roslaunch prius_scaled_controller prius_scaled_hill_headless.launch
```

### 3. 启动控制系统

**方法1：使用一键启动脚本（推荐）**
```bash
# 在新终端中
cd ~/catkin_ws
source install_isolated/setup.bash
./src/uneven_planner/prius_integration/prius_scaled_controller/start_prius_control.sh
```

**方法2：手动启动**
```bash
# 在新终端中，确保正确source环境
source ~/catkin_ws/install_isolated/setup.bash

# 启动Prius轨迹控制器
rosrun prius_scaled_controller prius_trajectory_controller.py &

# 启动MPC控制器
rosrun mpc_controller mpc_controller_node __name:=mpc_node _odom:=/prius/base_pose_ground_truth _traj:=/prius/trajectory _cmd:=/cmd_vel &
```

### 4. 使用控制

**选项A：键盘手动控制**
```bash
python3 src/uneven_planner/prius_integration/prius_scaled_controller/scripts/teleop_keyboard.py
```
- `w` : 前进
- `x` : 后退
- `a` : 左转
- `d` : 右转
- `s` : 停止
- `q/e` : 增减最大速度
- `z/c` : 增减最大转向角

**选项B：在RViz中设置目标点**
1. 在RViz中点击 "2D Nav Goal" 工具
2. 在地图上拖拽设置目标位置和方向
3. 系统将自动规划路径并控制Prius移动

**选项C：通过话题发送目标**
```bash
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped '{
  header: {frame_id: "world"}, 
  pose: {
    position: {x: 5.0, y: 0.0, z: 0.0}, 
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  }
}'
```

### 5. 停止系统

**停止控制器：**
```bash
./src/uneven_planner/prius_integration/prius_scaled_controller/stop_prius_control.sh
```

**完全停止系统：**
```bash
# 按 Ctrl+C 终止 roslaunch
# 或者使用 rosnode kill
rosnode kill -a
```

## 控制流程说明

```
1. 目标设置 → 路径规划算法 (Kino A*, ALM SE2/SE3)
2. 生成轨迹 → /prius/trajectory
3. MPC控制器 → 将轨迹转换为 /cmd_vel
4. Prius控制器 → 转换为Prius特定控制信号
5. Gazebo中的Prius模型执行动作
```

## 重要话题

**输入：**
- `/move_base_simple/goal` - 目标点
- `/cmd_vel` - 速度命令（用于手动控制）

**输出：**
- `/prius/throttle_cmd` - 油门控制 (0-1000)
- `/prius/brake_cmd` - 刹车控制 (0-100)  
- `/prius/steer_cmd` - 转向控制 (-0.6 to 0.6)
- `/prius/gear_cmd` - 档位控制

**状态监控：**
- `/prius/base_pose_ground_truth` - Prius真实位置
- `/prius/trajectory` - 当前轨迹
- `/terrain_map_pcl` - 地形点云

## 参数说明

由于物理缩放的影响，使用了保守的运动参数：
- 最大线速度：0.5 m/s (原来2.5 m/s的1/5)
- 最大角速度：0.2 rad/s (原来1.0 rad/s的1/5)
- 加速度限制：相应缩减至原来的1/5-1/10

## 故障排除

**1. 构建失败**
```bash
# 清理并重新构建
rm -rf build_isolated/ devel_isolated/ install_isolated/
catkin_make_isolated --install -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

**2. Prius不移动**
- 检查控制器是否运行：`rosnode list | grep controller`
- 检查轨迹是否生成：`rostopic echo /prius/trajectory -n 1`
- 检查控制命令：`rostopic echo /cmd_vel -n 1`

**3. 环境变量问题**
```bash
# 确保正确source环境
source ~/catkin_ws/install_isolated/setup.bash
echo $ROS_PACKAGE_PATH  # 应该包含install_isolated路径
```

**4. RViz显示问题**
- 检查Fixed Frame设置为 "world"
- 确保相关话题订阅正确
- 重新加载RViz配置文件

## 开发人员说明

- 控制器使用简化的Float64消息替代prius_msgs::Control
- 支持退化到标准cmd_vel接口
- 所有时间戳问题已修复
- TF树完整：world→map→odom→base_link→chassis