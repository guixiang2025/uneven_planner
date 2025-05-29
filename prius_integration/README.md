# Prius Integration for Uneven Planner

这个目录包含了将1:10比例的Prius模型集成到Uneven Planner中所需的ROS包。

## 包含的包

### prius_scaled_description

包含1:10比例Prius模型的URDF描述文件、网格文件和启动文件。

特点：
- 缩放比例：原始Prius模型的1:10
- 适配了物理参数以匹配小型车辆动力学
- 包含Gazebo插件用于模拟车辆行为

### prius_scaled_controller

提供了控制1:10比例Prius模型的控制器，用于在不平坦地形上进行导航。

特点：
- 接收轨迹或速度命令，转换为Prius控制命令
- 支持在不平坦地形上的路径规划和导航
- 与Uneven Planner集成
- 适配缩小比例的动力学模型参数

## 使用方法

可以通过以下启动文件启动完整的系统：

```bash
# 带图形界面启动（本地使用）
roslaunch prius_scaled_controller prius_scaled_hill.launch

# 无图形界面启动（适用于远程服务器）
roslaunch prius_scaled_controller prius_scaled_hill_headless.launch
```

## 测试

可以使用`test_navigation.py`脚本测试导航功能：

```bash
rosrun prius_scaled_controller test_navigation.py
```

详细的文档请参阅各个包内的README.md文件。 