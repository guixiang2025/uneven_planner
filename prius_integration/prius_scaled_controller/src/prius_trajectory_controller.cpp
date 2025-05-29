#include "prius_trajectory_controller.h"
#include <cmath>

namespace prius_scaled_controller
{

    PriusTrajectoryController::PriusTrajectoryController(ros::NodeHandle &nh)
        : nh_(nh),
          tf_listener_(tf_buffer_),
          received_odom_(false),
          received_cmd_vel_(false)
    {
        // Initialize control message
        control_msg_.header.frame_id = "base_link";
        control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
    }

    PriusTrajectoryController::~PriusTrajectoryController()
    {
        // Ensure we stop the vehicle before shutting down
        if (prius_control_pub_.getNumSubscribers() > 0)
        {
            // Create a safe stop command
            prius_msgs::Control stop_cmd;
            stop_cmd.header.stamp = ros::Time::now();
            stop_cmd.throttle = 0.0;
            stop_cmd.brake = 0.5; // moderate braking
            stop_cmd.steer = 0.0;
            stop_cmd.shift_gears = prius_msgs::Control::NEUTRAL;

            // Publish the stop command
            prius_control_pub_.publish(stop_cmd);

            // Allow time for command to be processed
            ros::Duration(0.1).sleep();
        }
    }

    bool PriusTrajectoryController::initialize()
    {
        ROS_INFO("Initializing PriusTrajectoryController...");

        // Load parameters
        nh_.param<double>("max_steering_angle", max_steering_angle_, 0.7);
        nh_.param<double>("max_velocity", max_velocity_, 0.5); // Reduced max velocity for scaled model
        nh_.param<double>("throttle_gain", throttle_gain_, 0.5);
        nh_.param<double>("brake_gain", brake_gain_, 0.5);

        // Load additional parameters
        double min_velocity;
        nh_.param<double>("min_velocity", min_velocity, 0.01);                    // min velocity to consider non-zero (reduced)
        nh_.param<double>("speed_error_tolerance", speed_error_tolerance_, 0.01); // m/s (reduced)
        nh_.param<double>("steering_deadband", steering_deadband_, 0.01);         // rad
        nh_.param<double>("throttle_deadband", throttle_deadband_, 0.05);         // 0-1 scale
        nh_.param<double>("brake_deadband", brake_deadband_, 0.05);               // 0-1 scale

        // Initialize publishers
        prius_control_pub_ = nh_.advertise<prius_msgs::Control>("/prius_controls", 10);

        // Initialize subscribers
        cmd_vel_sub_ = nh_.subscribe("/racebot/cmd_vel", 10, &PriusTrajectoryController::cmdVelCallback, this);
        odom_sub_ = nh_.subscribe("/prius/base_pose_ground_truth", 10, &PriusTrajectoryController::odomCallback, this);

        ROS_INFO("PriusTrajectoryController initialized successfully");
        return true;
    }

    void PriusTrajectoryController::update()
    {
        if (!received_odom_ || !received_cmd_vel_)
        {
            ROS_WARN_THROTTLE(1.0, "Waiting for odometry and cmd_vel data...");
            return;
        }

        // Convert Twist command to Prius control command
        convertCmdVelToPriusControl();

        // Publish control command
        publishControl();
    }

    void PriusTrajectoryController::cmdVelCallback(const geometry_msgs::Twist::ConstPtr &msg)
    {
        current_cmd_vel_ = *msg;
        received_cmd_vel_ = true;
        ROS_DEBUG_THROTTLE(1.0, "Received cmd_vel: linear.x=%f, angular.z=%f",
                           msg->linear.x, msg->angular.z);
    }

    void PriusTrajectoryController::odomCallback(const nav_msgs::Odometry::ConstPtr &msg)
    {
        current_odom_ = *msg;
        received_odom_ = true;
        ROS_DEBUG_THROTTLE(1.0, "Received odom: position=(%f,%f,%f)",
                           msg->pose.pose.position.x,
                           msg->pose.pose.position.y,
                           msg->pose.pose.position.z);
    }

    void PriusTrajectoryController::convertCmdVelToPriusControl()
    {
        // Set timestamp
        control_msg_.header.stamp = ros::Time::now();

        // Get current vehicle velocity
        double current_velocity = getCurrentLinearVelocity();

        // Desired velocity from command
        double desired_velocity = current_cmd_vel_.linear.x;

        // Calculate desired steering angle from angular velocity
        // For small angles, we can use the kinematic bicycle model:
        // omega = v/L * tan(delta) where L is wheelbase
        double steering_angle = 0.0;
        double wheelbase = 0.286; // scaled wheelbase in meters

        if (std::abs(current_velocity) > 0.1)
        { // Only calculate steering angle when moving
            // Solve for steering angle: delta = arctan(omega*L/v)
            steering_angle = std::atan2(current_cmd_vel_.angular.z * wheelbase, std::abs(current_velocity));
        }
        else if (std::abs(desired_velocity) > 0.1)
        { // Stationary but wants to move
            // Use desired velocity for determining steering direction
            steering_angle = std::atan2(current_cmd_vel_.angular.z * wheelbase, std::abs(desired_velocity));
        }

        // Apply deadband (minimum threshold) to steering
        if (std::abs(steering_angle) < steering_deadband_)
            steering_angle = 0.0;

        // Scale steering angle to range [-1, 1] for the Prius controller
        // Normalize by maximum steering angle
        double normalized_steering = steering_angle / max_steering_angle_;

        // Clamp to valid range
        normalized_steering = std::max(-1.0, std::min(1.0, normalized_steering));

        // Set steering (the controller expects a value between -1.0 and 1.0)
        control_msg_.steer = normalized_steering;

        // Calculate velocity error
        double velocity_error = desired_velocity - current_velocity;
        double velocity_error_abs = std::abs(velocity_error);
        double throttle_value = 0.0;
        double brake_value = 0.0;

        // Speed control logic
        // Start with all control values at zero
        control_msg_.throttle = 0.0;
        control_msg_.brake = 0.0;

        if (std::abs(desired_velocity) < 0.01)
        {
            // Stopping - apply brakes proportional to current speed
            if (std::abs(current_velocity) > 0.01)
            {
                control_msg_.brake = std::max(brake_deadband_, brake_value);
                control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
            }
            else
            {
                // If already stopped, just maintain brakes
                control_msg_.brake = 0.3; // Light brake to maintain position
                control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
            }
        }
        else if (desired_velocity > 0.0)
        {
            // Forward motion
            if (current_velocity < -0.1)
            {
                // We're moving backward but want to go forward - first stop
                control_msg_.brake = std::min(1.0, brake_gain_ * std::abs(current_velocity) + 0.2);
                control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
            }
            else
            {
                // Set forward gear
                control_msg_.shift_gears = prius_msgs::Control::FORWARD;

                // Decide whether to accelerate or brake
                if (velocity_error_abs > speed_error_tolerance_)
                {
                    if (velocity_error > 0)
                    {
                        // Need more speed - apply throttle proportional to error
                        throttle_value = std::min(1.0, throttle_gain_ * velocity_error);
                        brake_value = 0.0;
                    }
                    else
                    {
                        // Going too fast - apply brakes
                        throttle_value = 0.0;
                        brake_value = std::min(1.0, brake_gain_ * velocity_error_abs);
                    }
                }

                // Apply deadband to throttle
                if (throttle_value > 0 && throttle_value < throttle_deadband_)
                    throttle_value = throttle_deadband_;

                control_msg_.throttle = throttle_value;
                control_msg_.brake = brake_value;
            }
        }
        else
        {
            // Backward motion
            if (current_velocity > 0.1)
            {
                // We're moving forward but want to go backward - first stop
                control_msg_.brake = std::max(0.0, std::min(1.0, brake_gain_ * velocity_error_abs));
                control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
            }
            else
            {
                // Set reverse gear
                control_msg_.shift_gears = prius_msgs::Control::REVERSE;

                if (current_velocity < -0.1 && velocity_error > 0)
                {
                    // We're going too fast in reverse - apply brakes
                    control_msg_.brake = std::min(1.0, brake_gain_ * std::abs(current_velocity) + 0.2);
                    control_msg_.throttle = 0.0;
                }
                else
                {
                    // Need more reverse speed - adjust throttle
                    if (velocity_error_abs > speed_error_tolerance_)
                    {
                        if (velocity_error < 0)
                        {
                            // Need more reverse speed
                            throttle_value = std::min(1.0, throttle_gain_ * (-velocity_error));
                            brake_value = 0.0;
                        }
                        else
                        {
                            // Going too fast in reverse - apply brakes
                            throttle_value = 0.0;
                            brake_value = std::min(1.0, brake_gain_ * velocity_error_abs);
                        }
                    }

                    // Apply deadband to throttle
                    if (throttle_value > 0 && throttle_value < throttle_deadband_)
                        throttle_value = throttle_deadband_;

                    control_msg_.throttle = throttle_value;
                    control_msg_.brake = brake_value;
                }
            }
        }

        ROS_DEBUG_THROTTLE(1.0, "Control: steer=%f, throttle=%f, brake=%f, gear=%d",
                           control_msg_.steer, control_msg_.throttle, control_msg_.brake, control_msg_.shift_gears);
    }

    double PriusTrajectoryController::getCurrentLinearVelocity()
    {
        // Calculate the current linear velocity from odometry
        return std::sqrt(
            std::pow(current_odom_.twist.twist.linear.x, 2) +
            std::pow(current_odom_.twist.twist.linear.y, 2));
    }

    void PriusTrajectoryController::publishControl()
    {
        prius_control_pub_.publish(control_msg_);
    }

} // namespace prius_scaled_controller