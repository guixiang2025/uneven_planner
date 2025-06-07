#!/bin/bash

echo "=== Prius控制系统启动脚本 ==="
echo "正在启动Prius控制系统..."

# 确保在正确的工作目录
cd /home/grey/catkin_ws

# 设置正确的环境变量
echo "设置隔离构建环境..."
source install_isolated/setup.bash

# 检查基础系统是否运行
if ! rostopic list > /dev/null 2>&1; then
    echo "错误: ROS master未运行！"
    echo "请先启动基础系统："
    echo "  roslaunch prius_scaled_controller prius_scaled_hill.launch"
    exit 1
fi

echo "✓ ROS master正在运行"

# 检查Gazebo是否运行
if ! rostopic list | grep -q "/gazebo"; then
    echo "警告: Gazebo似乎未运行，请确保已启动基础系统"
fi

# 启动Prius轨迹控制器
echo "启动Prius轨迹控制器..."
rosrun prius_scaled_controller prius_trajectory_controller.py &
PRIUS_CONTROLLER_PID=$!
echo $PRIUS_CONTROLLER_PID > /tmp/prius_controller.pid
sleep 2

# 检查Prius控制器是否成功启动
if ps -p $PRIUS_CONTROLLER_PID > /dev/null; then
    echo "✓ Prius轨迹控制器已启动 (PID: $PRIUS_CONTROLLER_PID)"
else
    echo "✗ Prius轨迹控制器启动失败"
    exit 1
fi

# 启动MPC控制器
echo "启动MPC控制器..."
rosrun mpc_controller mpc_controller_node __name:=mpc_node \
    _odom:=/prius/base_pose_ground_truth \
    _traj:=/prius/trajectory \
    _cmd:=/cmd_vel &
MPC_CONTROLLER_PID=$!
echo $MPC_CONTROLLER_PID > /tmp/mpc_controller.pid
sleep 2

# 检查MPC控制器是否成功启动
if ps -p $MPC_CONTROLLER_PID > /dev/null; then
    echo "✓ MPC控制器已启动 (PID: $MPC_CONTROLLER_PID)"
else
    echo "✗ MPC控制器启动失败，可能缺少依赖包"
    echo "继续使用Prius控制器进行直接控制..."
fi

echo ""
echo "=== 系统启动完成 ==="
echo "当前运行的控制节点："
rosnode list | grep -E "(mpc|prius|controller)" || echo "  无控制节点运行"

echo ""
echo "可用的控制话题："
rostopic list | grep -E "(cmd_vel|prius.*cmd)" || echo "  无控制话题"

echo ""
echo "使用方法："
echo "1. 键盘控制:"
echo "   python3 src/uneven_planner/prius_integration/prius_scaled_controller/scripts/teleop_keyboard.py"
echo ""
echo "2. 在RViz中使用 '2D Nav Goal' 工具设置目标点"
echo ""
echo "3. 发送速度命令:"
echo "   rostopic pub /cmd_vel geometry_msgs/Twist '{linear: {x: 0.5}, angular: {z: 0.0}}' -1"
echo ""
echo "4. 停止控制器:"
echo "   ./src/uneven_planner/prius_integration/prius_scaled_controller/stop_prius_control.sh"
echo ""
echo "注意: 确保在新终端中先运行 'source ~/catkin_ws/install_isolated/setup.bash'"

# 等待用户中断
trap 'echo "脚本已退出，控制器继续运行。如需停止所有控制器，请运行: killall -9 python3 mpc_controller_node"' EXIT

# 持续监控（可选）
while true; do
    sleep 10
    # 检查进程是否还在运行
    if ! ps -p $PRIUS_CONTROLLER_PID > /dev/null; then
        echo "警告: Prius控制器进程已停止"
        break
    fi
    if ! ps -p $MPC_CONTROLLER_PID > /dev/null; then
        echo "警告: MPC控制器进程已停止"
        break
    fi
done 