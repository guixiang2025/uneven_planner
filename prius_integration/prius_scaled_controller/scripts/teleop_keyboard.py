#!/usr/bin/env python

# Copyright (c) 2011, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Willow Garage, Inc. nor the names of its
#      contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import rospy
from geometry_msgs.msg import Twist
import sys, select, os
import tty, termios

# 速度增减量
SPEED_DELTA = 0.05
TURN_DELTA = 0.1

# 最大速度和最大转向角
MAX_SPEED = 1.0
MAX_TURN = 0.7

msg = """
控制Prius车辆:
---------------------------
方向键:
   q    w    e
   a    s    d
   z    x    c

w/x : 增加/减少线性速度
a/d : 增加/减少转向角度
s : 停止
空格键 : 紧急停止

CTRL-C 退出
"""

# 按键映射
moveBindings = {
    'w': (1, 0),    # 向前
    'e': (1, -1),   # 向前右转
    'a': (0, 1),    # 原地左转
    'd': (0, -1),   # 原地右转
    'q': (1, 1),    # 向前左转
    'x': (-1, 0),   # 向后
    'c': (-1, -1),  # 向后右转
    'z': (-1, 1),   # 向后左转
    's': (0, 0),    # 停止
}

speedBindings = {
    'w': (1, 0),    # 增加线性速度
    'x': (-1, 0),   # 减少线性速度
    'a': (0, 1),    # 增加角速度
    'd': (0, -1),   # 减少角速度
}

class KeyboardTeleop:
    def __init__(self):
        # 发布者初始化
        self.velocity_publisher = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.x = 0.0
        self.th = 0.0
        self.status = 0
        self.target_speed = 0.0
        self.target_turn = 0.0
        self.control_speed = 0.0
        self.control_turn = 0.0
        self.print_instructions()

    def print_instructions(self):
        print(msg)
        print('当前速度: %s, 当前转向角: %s ' % (self.control_speed, self.control_turn))

    def getKey(self):
        tty.setraw(sys.stdin.fileno())
        select.select([sys.stdin], [], [], 0)
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def run(self):
        self.settings = termios.tcgetattr(sys.stdin)

        try:
            while not rospy.is_shutdown():
                key = self.getKey()

                # CTRL-C退出
                if key == '\x03':
                    break

                # 方向控制
                if key in moveBindings.keys():
                    self.x = moveBindings[key][0]
                    self.th = moveBindings[key][1]
                # 速度控制
                elif key in speedBindings.keys():
                    if speedBindings[key][0] != 0:
                        self.target_speed += speedBindings[key][0] * SPEED_DELTA
                        self.target_speed = max(-MAX_SPEED, min(self.target_speed, MAX_SPEED))
                    if speedBindings[key][1] != 0:
                        self.target_turn += speedBindings[key][1] * TURN_DELTA
                        self.target_turn = max(-MAX_TURN, min(self.target_turn, MAX_TURN))
                    print('当前目标速度: %s, 当前目标转向角: %s ' % (self.target_speed, self.target_turn))
                # 空格键紧急停止
                elif key == ' ':
                    self.x = 0
                    self.th = 0
                    self.control_speed = 0
                    self.control_turn = 0
                    self.target_speed = 0
                    self.target_turn = 0
                else:
                    if key == '\x1b':  # 方向键前缀
                        key = self.getKey()  # 读取'['
                        key = self.getKey()  # 读取实际方向键
                        if key == 'A':  # Up
                            self.x = 1
                            self.th = 0
                        elif key == 'B':  # Down
                            self.x = -1
                            self.th = 0
                        elif key == 'C':  # Right
                            self.x = 0
                            self.th = -1
                        elif key == 'D':  # Left
                            self.x = 0
                            self.th = 1
                    else:
                        self.x = 0
                        self.th = 0
                        # 如果控制不更新，停止车辆
                        if (key == '\x1b'):
                            pass

                # 平滑控制速度
                if self.target_speed > self.control_speed:
                    self.control_speed = min(self.target_speed, self.control_speed + SPEED_DELTA)
                elif self.target_speed < self.control_speed:
                    self.control_speed = max(self.target_speed, self.control_speed - SPEED_DELTA)

                # 平滑控制转向
                if self.target_turn > self.control_turn:
                    self.control_turn = min(self.target_turn, self.control_turn + TURN_DELTA)
                elif self.target_turn < self.control_turn:
                    self.control_turn = max(self.target_turn, self.control_turn - TURN_DELTA)

                # 创建速度消息
                twist = Twist()
                linear_x = self.control_speed * self.x
                angular_z = self.control_turn * self.th

                # 更新消息
                twist.linear.x = linear_x
                twist.linear.y = 0.0
                twist.linear.z = 0.0
                twist.angular.x = 0.0
                twist.angular.y = 0.0
                twist.angular.z = angular_z

                # 发布消息
                self.velocity_publisher.publish(twist)

        except Exception as e:
            print(e)

        finally:
            # 停止车辆
            twist = Twist()
            twist.linear.x = 0.0
            twist.linear.y = 0.0
            twist.linear.z = 0.0
            twist.angular.x = 0.0
            twist.angular.y = 0.0
            twist.angular.z = 0.0
            self.velocity_publisher.publish(twist)
            
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)

if __name__ == "__main__":
    rospy.init_node('prius_keyboard_teleop')
    teleop = KeyboardTeleop()
    teleop.run() 