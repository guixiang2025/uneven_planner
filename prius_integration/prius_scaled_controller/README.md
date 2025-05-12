# Prius Scaled Controller

这个包提供了针对1:10比例的Prius模型的控制器，用于在不平坦地形上进行导航。

## 功能

- 接收轨迹或速度命令，转换为Prius控制命令
- 支持在不平坦地形上的路径规划和导航
- 与现有的轨迹规划器集成
- 适配缩小比例的动力学模型参数

## 组件

- `prius_trajectory_controller`: 将速度命令转换为Prius控制命令的核心控制器
- `prius_scaled_controller_node`: 运行控制器的ROS节点
- 启动文件：
  - `prius_scaled_hill.launch`: 启动带图形界面的完整系统
  - `prius_scaled_hill_headless.launch`: 无图形界面版本，适合远程服务器
- 测试工具:
  - `test_navigation.py`: 用于测试导航功能的脚本

## 依赖

- ROS Noetic
- Gazebo 11
- prius_msgs
- plan_manager
- uneven_map
- prius_scaled_description

## 使用方法

### 启动系统

带图形界面（本地使用）:
```
roslaunch prius_scaled_controller prius_scaled_hill.launch
```

无图形界面（远程服务器使用）:
```
roslaunch prius_scaled_controller prius_scaled_hill_headless.launch
```

### 测试导航

```
rosrun prius_scaled_controller test_navigation.py
```

### 手动发送命令

发送目标点:
```
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped '{header: {stamp: now, frame_id: "map"}, pose: {position: {x: 6.0, y: -2.0, z: 0.0}, orientation: {w: 1.0}}}' -1
```

直接发送速度命令:
```
rostopic pub /racebot/cmd_vel geometry_msgs/Twist '{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' -r 10
```

## 参数调整

控制器参数可以在启动文件中调整:
- `max_velocity`: 最大速度 (m/s)
- `max_steering_angle`: 最大转向角 (rad)
- `throttle_gain`: 油门增益
- `brake_gain`: 制动增益

## 故障排除

- 如果在远程服务器上启动失败，确保使用无图形界面版本的启动文件
- 如果车辆不移动，检查是否正在接收速度命令或轨迹消息
- 如果控制不稳定，尝试调整控制器参数，特别是油门和制动增益 