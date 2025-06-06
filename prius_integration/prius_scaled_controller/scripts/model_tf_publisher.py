#!/usr/bin/env python

import rospy
import tf2_ros
from gazebo_msgs.msg import ModelStates
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped

class ModelTFPublisher:
    def __init__(self):
        rospy.init_node('model_tf_publisher')
        
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()
        self.odom_publisher = rospy.Publisher('/prius/base_pose_ground_truth', Odometry, queue_size=10)
        
        self.model_sub = rospy.Subscriber('/gazebo/model_states', ModelStates, self.model_states_callback)
        
        rospy.loginfo("Model TF Publisher started")
        
    def model_states_callback(self, msg):
        try:
            # Find prius_scaled model
            model_idx = msg.name.index('prius_scaled')
            
            # Get pose and twist
            pose = msg.pose[model_idx]
            twist = msg.twist[model_idx]
            
            # Create and publish TF transform (odom -> base_link)
            transform = TransformStamped()
            transform.header.stamp = rospy.Time.now()
            transform.header.frame_id = "odom"
            transform.child_frame_id = "base_link"
            transform.transform.translation.x = pose.position.x
            transform.transform.translation.y = pose.position.y
            transform.transform.translation.z = pose.position.z
            transform.transform.rotation = pose.orientation
            
            self.tf_broadcaster.sendTransform(transform)
            
            # Create and publish Odometry message
            odom = Odometry()
            odom.header.stamp = transform.header.stamp
            odom.header.frame_id = "odom"
            odom.child_frame_id = "base_link"
            odom.pose.pose = pose
            odom.twist.twist = twist
            
            self.odom_publisher.publish(odom)
            
        except ValueError:
            # prius_scaled model not found in the list
            pass
        except Exception as e:
            rospy.logwarn("Error in model_states_callback: {}".format(e))

if __name__ == '__main__':
    try:
        publisher = ModelTFPublisher()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass 