#!/bin/bash

echo "=== 停止Prius控制系统 ==="

# 函数：安全地杀死进程
kill_process() {
    local pid=$1
    local name=$2
    
    if [ -n "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        echo "停止 $name (PID: $pid)..."
        kill $pid
        sleep 2
        if ps -p $pid > /dev/null 2>&1; then
            echo "强制停止 $name..."
            kill -9 $pid
        fi
        echo "✓ $name 已停止"
    else
        echo "✓ $name 未运行或已停止"
    fi
}

# 从PID文件读取进程ID
if [ -f "/tmp/prius_controller.pid" ]; then
    PRIUS_PID=$(cat /tmp/prius_controller.pid)
    kill_process "$PRIUS_PID" "Prius控制器"
    rm -f /tmp/prius_controller.pid
fi

if [ -f "/tmp/mpc_controller.pid" ]; then
    MPC_PID=$(cat /tmp/mpc_controller.pid)
    kill_process "$MPC_PID" "MPC控制器"
    rm -f /tmp/mpc_controller.pid
fi

# 查找并停止所有相关进程
echo "查找其他相关进程..."

# 停止所有prius_trajectory_controller进程
PRIUS_PIDS=$(pgrep -f "prius_trajectory_controller")
for pid in $PRIUS_PIDS; do
    kill_process "$pid" "Prius轨迹控制器"
done

# 停止所有mpc_controller_node进程
MPC_PIDS=$(pgrep -f "mpc_controller_node")
for pid in $MPC_PIDS; do
    kill_process "$pid" "MPC控制器节点"
done

# 停止teleop_keyboard进程（如果在运行）
TELEOP_PIDS=$(pgrep -f "teleop_keyboard")
for pid in $TELEOP_PIDS; do
    kill_process "$pid" "键盘控制"
done

echo ""
echo "检查剩余的控制进程..."
REMAINING=$(rosnode list 2>/dev/null | grep -E "(mpc|prius|controller)" | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✓ 所有Prius控制进程已停止"
else
    echo "警告: 仍有 $REMAINING 个相关节点在运行"
    echo "剩余节点:"
    rosnode list 2>/dev/null | grep -E "(mpc|prius|controller)"
    echo ""
    echo "如需强制停止所有相关进程，运行:"
    echo "  killall -9 python3"
    echo "  killall -9 mpc_controller_node"
fi

echo ""
echo "=== Prius控制系统停止完成 ===" 