#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 添加prius_integration目录到ROS_PACKAGE_PATH
export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:$SCRIPT_DIR/prius_integration

# 提示信息
echo "Prius integration packages added to ROS_PACKAGE_PATH"
echo "ROS_PACKAGE_PATH = $ROS_PACKAGE_PATH" 