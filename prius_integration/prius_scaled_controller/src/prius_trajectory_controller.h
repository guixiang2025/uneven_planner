#ifndef PRIUS_SCALED_TRAJECTORY_CONTROLLER_H
#define PRIUS_SCALED_TRAJECTORY_CONTROLLER_H

#include <ros/ros.h>
#include <tf2_ros/transform_listener.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>
#include <geometry_msgs/Twist.h>
#include <geometry_msgs/TransformStamped.h>
#include <nav_msgs/Odometry.h>
#include <prius_msgs/Control.h>

namespace prius_scaled_controller
{

    class PriusTrajectoryController
    {
    public:
        PriusTrajectoryController(ros::NodeHandle &nh);
        ~PriusTrajectoryController();

        bool initialize();
        void update();

    private:
        ros::NodeHandle nh_;
        tf2_ros::Buffer tf_buffer_;
        tf2_ros::TransformListener tf_listener_;

        ros::Publisher prius_control_pub_;
        ros::Subscriber cmd_vel_sub_;
        ros::Subscriber odom_sub_;

        geometry_msgs::Twist current_cmd_vel_;
        nav_msgs::Odometry current_odom_;
        prius_msgs::Control control_msg_;

        bool received_odom_;
        bool received_cmd_vel_;

        double max_steering_angle_;
        double max_velocity_;
        double throttle_gain_;
        double brake_gain_;
        double steering_deadband_;
        double throttle_deadband_;
        double brake_deadband_;
        double speed_error_tolerance_;

        void cmdVelCallback(const geometry_msgs::Twist::ConstPtr &msg);
        void odomCallback(const nav_msgs::Odometry::ConstPtr &msg);
        void convertCmdVelToPriusControl();
        void publishControl();
        double getCurrentLinearVelocity();
    };

} // namespace prius_scaled_controller

#endif // PRIUS_SCALED_TRAJECTORY_CONTROLLER_H