#ifndef PRIUS_TRAJECTORY_CONTROLLER_H
#define PRIUS_TRAJECTORY_CONTROLLER_H

#include <ros/ros.h>
#include <geometry_msgs/Twist.h>
#include <nav_msgs/Odometry.h>
#include <prius_msgs/Control.h>
#include <tf2/utils.h>
#include <tf2_ros/transform_listener.h>
#include <tf2/LinearMath/Quaternion.h>

namespace prius_controller
{

    /**
     * @brief Controller class for Prius trajectory tracking
     *
     * This class acts as an adapter between uneven_planner and Prius model.
     * It subscribes to trajectory data and vehicle odometry, and publishes
     * control commands to the Prius model.
     */
    class PriusTrajectoryController
    {
    public:
        /**
         * @brief Constructor
         * @param nh ROS node handle
         */
        PriusTrajectoryController(ros::NodeHandle &nh);

        /**
         * @brief Destructor
         */
        ~PriusTrajectoryController();

        /**
         * @brief Initialize the controller
         * @return true if initialization successful
         */
        bool initialize();

        /**
         * @brief Main update function, called in the control loop
         */
        void update();

    private:
        // ROS node handle
        ros::NodeHandle nh_;

        // Publishers
        ros::Publisher prius_control_pub_;

        // Subscribers
        ros::Subscriber cmd_vel_sub_;
        ros::Subscriber odom_sub_;

        // TF related
        tf2_ros::Buffer tf_buffer_;
        tf2_ros::TransformListener tf_listener_;

        // Current vehicle state
        nav_msgs::Odometry current_odom_;
        geometry_msgs::Twist current_cmd_vel_;

        // Command conversion parameters
        double max_steering_angle_;
        double max_velocity_;
        double throttle_gain_;
        double brake_gain_;
        double speed_error_tolerance_;
        double steering_deadband_;
        double throttle_deadband_;
        double brake_deadband_;

        // Command message
        prius_msgs::Control control_msg_;

        // Callback functions
        void cmdVelCallback(const geometry_msgs::Twist::ConstPtr &msg);
        void odomCallback(const nav_msgs::Odometry::ConstPtr &msg);

        // Helper functions
        void convertCmdVelToPriusControl();
        void publishControl();

        /**
         * @brief Calculates the current linear velocity in vehicle's forward direction
         * @return Current forward velocity in m/s (positive forward, negative backward)
         */
        double getCurrentLinearVelocity();

        // Flag to check if we received necessary data
        bool received_odom_;
        bool received_cmd_vel_;
    };

} // namespace prius_controller

#endif // PRIUS_TRAJECTORY_CONTROLLER_H