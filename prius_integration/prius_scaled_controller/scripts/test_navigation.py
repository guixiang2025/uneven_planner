#!/usr/bin/env python3

import rospy
import sys
import math
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
import tf.transformations

class TestNavigation:
    def __init__(self):
        rospy.init_node('prius_navigation_tester', anonymous=True)
        
        # 创建发布器和订阅器
        self.goal_pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=1)
        self.odom_sub = rospy.Subscriber('/prius/base_pose_ground_truth', Odometry, self.odom_callback)
        
        # 目标点列表 [x, y, orientation_z]
        self.goals = [
            [5.0, -3.0, 0.0],
            [6.0, -2.0, 1.57],
            [4.0, 0.0, 3.14],
            [4.3, -4.3, 1.57]  # 回到起点
        ]
        
        self.current_goal_index = 0
        self.current_pose = None
        self.goal_reached = False
        self.goal_distance_threshold = 0.5  # 距离目标多近算到达
        
        rospy.loginfo("Navigation tester initialized with %d waypoints", len(self.goals))
        
    def odom_callback(self, msg):
        self.current_pose = msg
        
        # 检查是否到达当前目标
        if self.current_goal_index < len(self.goals) and not self.goal_reached:
            goal = self.goals[self.current_goal_index]
            pose = msg.pose.pose
            
            dx = goal[0] - pose.position.x
            dy = goal[1] - pose.position.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < self.goal_distance_threshold:
                rospy.loginfo("Goal %d reached! Distance: %.2f", 
                             self.current_goal_index, distance)
                self.goal_reached = True
                rospy.sleep(2.0)  # 等待2秒
                self.send_next_goal()
    
    def send_next_goal(self):
        if self.current_goal_index < len(self.goals):
            goal = self.goals[self.current_goal_index]
            self.send_goal(goal[0], goal[1], goal[2])
            rospy.loginfo("Sent goal %d: (%.2f, %.2f, %.2f)", 
                         self.current_goal_index, goal[0], goal[1], goal[2])
            self.current_goal_index += 1
            self.goal_reached = False
        else:
            rospy.loginfo("All goals have been completed!")
            
    def send_goal(self, x, y, yaw):
        goal = PoseStamped()
        goal.header.stamp = rospy.Time.now()
        goal.header.frame_id = "map"
        
        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.position.z = 0.0
        
        # 从偏航角计算四元数
        q = tf.transformations.quaternion_from_euler(0, 0, yaw)
        goal.pose.orientation.x = q[0]
        goal.pose.orientation.y = q[1]
        goal.pose.orientation.z = q[2]
        goal.pose.orientation.w = q[3]
        
        self.goal_pub.publish(goal)
        
    def start(self):
        rospy.sleep(3.0)  # 等待系统启动
        self.send_next_goal()
        rospy.spin()

if __name__ == '__main__':
    try:
        tester = TestNavigation()
        tester.start()
    except rospy.ROSInterruptException:
        pass 