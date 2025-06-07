#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64, Int32, Header
import math

class PriusTrajectoryController:
    def __init__(self):
        rospy.init_node('prius_trajectory_controller', anonymous=True)
        
        # 订阅cmd_vel话题
        self.cmd_vel_sub = rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback)
        
        # 根据搜索结果，Prius需要特定的控制话题
        # 发布简化的控制消息 - 使用Float64替代复杂的prius_msgs
        self.throttle_pub = rospy.Publisher('/prius/throttle_cmd', Float64, queue_size=1)
        self.brake_pub = rospy.Publisher('/prius/brake_cmd', Float64, queue_size=1)
        self.steer_pub = rospy.Publisher('/prius/steer_cmd', Float64, queue_size=1)
        self.gear_pub = rospy.Publisher('/prius/gear_cmd', Int32, queue_size=1)
        
        rospy.loginfo("Prius trajectory controller started (using simplified control)")
        
    def cmd_vel_callback(self, cmd_vel):
        # 从cmd_vel提取速度和转向
        linear_vel = cmd_vel.linear.x  # 线性速度 m/s
        angular_vel = cmd_vel.angular.z  # 角速度 rad/s
        
        # 创建控制消息
        throttle_msg = Float64()
        brake_msg = Float64()
        steer_msg = Float64()
        gear_msg = Int32()
        
        if linear_vel > 0:
            # 前进
            throttle_msg.data = min(abs(linear_vel) * 500.0, 1000.0)  # 缩放到Prius范围
            brake_msg.data = 0.0
            gear_msg.data = 2  # FORWARD
        elif linear_vel < 0:
            # 后退
            throttle_msg.data = min(abs(linear_vel) * 500.0, 1000.0)
            brake_msg.data = 0.0
            gear_msg.data = 3  # REVERSE
        else:
            # 停止
            throttle_msg.data = 0.0
            brake_msg.data = 100.0
            gear_msg.data = 0  # NEUTRAL
        
        # 转向控制 (限制在合理范围内)
        steer_msg.data = max(-0.6, min(angular_vel * 2.0, 0.6))
        
        # 发布控制消息
        self.throttle_pub.publish(throttle_msg)
        self.brake_pub.publish(brake_msg)
        self.steer_pub.publish(steer_msg)
        self.gear_pub.publish(gear_msg)
        
        if abs(linear_vel) > 0.01 or abs(angular_vel) > 0.01:
            rospy.loginfo("Control: throttle=%.0f, brake=%.0f, steer=%.2f, gear=%d",
                         throttle_msg.data, brake_msg.data, steer_msg.data, gear_msg.data)

if __name__ == '__main__':
    try:
        controller = PriusTrajectoryController()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass 