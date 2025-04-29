#!/bin/bash
CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]:-${(%):-%x}}" )" >/dev/null 2>&1 && pwd )"
#source ${CURRENT_DIR}/devel/setup.bash
# 计算工作空间根目录 (向上两级)
CATKIN_WS_DIR="$( cd "${CURRENT_DIR}/../../" && pwd )"
# Source 正确的 setup.bash
source ${CATKIN_WS_DIR}/devel/setup.bash

roslaunch plan_manager run_hill.launch & sleep 1;
wait;
