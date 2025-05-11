#include "prius_controller/prius_trajectory_controller.h"
#include <cmath>

namespace prius_controller
{

    PriusTrajectoryController::PriusTrajectoryController(ros::NodeHandle &nh)
        : nh_(nh),
          tf_listener_(tf_buffer_),
          received_odom_(false),
          received_cmd_vel_(false)
    {
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
        nh_.param<double>("max_velocity", max_velocity_, 5.0);
        nh_.param<double>("throttle_gain", throttle_gain_, 0.5);
        nh_.param<double>("brake_gain", brake_gain_, 0.5);

        // Load additional parameters
        double min_velocity;
        nh_.param<double>("min_velocity", min_velocity, 0.1);                    // min velocity to consider non-zero
        nh_.param<double>("speed_error_tolerance", speed_error_tolerance_, 0.1); // m/s
        nh_.param<double>("steering_deadband", steering_deadband_, 0.01);        // rad
        nh_.param<double>("throttle_deadband", throttle_deadband_, 0.05);        // 0-1 scale
        nh_.param<double>("brake_deadband", brake_deadband_, 0.05);              // 0-1 scale

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
        // Update header timestamp
        control_msg_.header.stamp = ros::Time::now();

        // Get current velocity from odometry
        double current_velocity = getCurrentLinearVelocity();

        // Get desired velocity and steering from command
        double desired_velocity = current_cmd_vel_.linear.x;
        double desired_angular_velocity = current_cmd_vel_.angular.z;

        // Convert angular velocity to steering angle based on current velocity
        double steering_angle;
        if (std::abs(current_velocity) > 0.1)
        {
            // Using bicycle model: steering_angle = atan(wheelbase * angular_velocity / linear_velocity)
            // Assuming Prius wheelbase of ~2.7 meters
            steering_angle = std::atan2(2.7 * desired_angular_velocity, std::abs(current_velocity));
        }
        else
        {
            // When stationary or near-stationary, use a direct mapping
            steering_angle = desired_angular_velocity * 0.5; // Scale factor for more intuitive control
        }

        // Apply steering deadband and normalize to [-1, 1]
        if (std::abs(steering_angle) < steering_deadband_)
        {
            steering_angle = 0.0;
        }

        // Normalize to [-1, 1] range, where 1 is max left turn
        double normalized_steering = steering_angle / max_steering_angle_;
        control_msg_.steer = std::max(-1.0, std::min(1.0, normalized_steering));

        // Velocity control with smoother acceleration and deceleration
        double velocity_error = desired_velocity - current_velocity;
        double velocity_error_abs = std::abs(velocity_error);

        // Determine direction
        bool moving_forward = (desired_velocity > 0.01);
        bool moving_backward = (desired_velocity < -0.01);
        bool current_forward = (current_velocity > 0.01);
        bool current_backward = (current_velocity < -0.01);

        // Handle different scenarios
        if (std::abs(desired_velocity) < 0.01)
        {
            // Stop command - apply brakes and set neutral
            control_msg_.shift_gears = prius_msgs::Control::NEUTRAL;
            control_msg_.throttle = 0.0;

            // Apply brakes proportionally to current speed
            double brake_value = std::min(0.5, std::abs(current_velocity) / 2.0 + 0.1);
            control_msg_.brake = std::max(brake_deadband_, brake_value);
        }
        else if (moving_forward)
        {
            // Forward driving
            control_msg_.shift_gears = prius_msgs::Control::FORWARD;

            // If currently moving backward but want to go forward, apply brakes first
            if (current_backward)
            {
                control_msg_.throttle = 0.0;
                control_msg_.brake = std::min(1.0, brake_gain_ * std::abs(current_velocity) + 0.2);
            }
            // Normal forward acceleration
            else
            {
                // Adaptive throttle based on velocity error
                double throttle_value = 0.0;
                if (velocity_error_abs > speed_error_tolerance_)
                {
                    // Scale throttle by error magnitude
                    throttle_value = std::min(1.0, throttle_gain_ * velocity_error);

                    // Apply additional gain for starting from stop
                    if (std::abs(current_velocity) < 0.1 && velocity_error > 0)
                    {
                        throttle_value += 0.1; // Extra boost from standstill
                    }
                }

                // Apply deadband
                if (throttle_value > 0 && throttle_value < throttle_deadband_)
                {
                    throttle_value = throttle_deadband_;
                }

                // Set throttle and brake
                if (velocity_error > 0)
                {
                    // Need to accelerate
                    control_msg_.throttle = std::max(0.0, std::min(1.0, throttle_value));
                    control_msg_.brake = 0.0;
                }
                else
                {
                    // Need to decelerate
                    control_msg_.throttle = 0.0;
                    control_msg_.brake = std::max(0.0, std::min(1.0, brake_gain_ * velocity_error_abs));
                }
            }
        }
        else if (moving_backward)
        {
            // Reverse driving
            control_msg_.shift_gears = prius_msgs::Control::REVERSE;

            // If currently moving forward but want to go backward, apply brakes first
            if (current_forward)
            {
                control_msg_.throttle = 0.0;
                control_msg_.brake = std::min(1.0, brake_gain_ * std::abs(current_velocity) + 0.2);
            }
            // Normal backward acceleration
            else
            {
                // Reverse has opposite sign for error
                velocity_error = -velocity_error;

                // Adaptive throttle similar to forward case
                double throttle_value = 0.0;
                if (velocity_error_abs > speed_error_tolerance_)
                {
                    throttle_value = std::min(1.0, throttle_gain_ * velocity_error);

                    // Extra boost from standstill
                    if (std::abs(current_velocity) < 0.1 && velocity_error > 0)
                    {
                        throttle_value += 0.1;
                    }
                }

                // Apply deadband
                if (throttle_value > 0 && throttle_value < throttle_deadband_)
                {
                    throttle_value = throttle_deadband_;
                }

                // Set throttle and brake
                if (velocity_error > 0)
                {
                    // Need to accelerate backward
                    control_msg_.throttle = std::max(0.0, std::min(1.0, throttle_value));
                    control_msg_.brake = 0.0;
                }
                else
                {
                    // Need to decelerate
                    control_msg_.throttle = 0.0;
                    control_msg_.brake = std::max(0.0, std::min(1.0, brake_gain_ * velocity_error_abs));
                }
            }
        }

        ROS_DEBUG_THROTTLE(1.0, "Converted to Prius control: throttle=%f, brake=%f, steer=%f, gear=%d, current_vel=%f, desired_vel=%f",
                           control_msg_.throttle, control_msg_.brake, control_msg_.steer, control_msg_.shift_gears,
                           current_velocity, desired_velocity);
    }

    void PriusTrajectoryController::publishControl()
    {
        prius_control_pub_.publish(control_msg_);
    }

    double PriusTrajectoryController::getCurrentLinearVelocity()
    {
        // Extract linear velocity from odometry
        double vx = current_odom_.twist.twist.linear.x;
        double vy = current_odom_.twist.twist.linear.y;

        // Get yaw angle from quaternion
        tf2::Quaternion q;
        tf2::fromMsg(current_odom_.pose.pose.orientation, q);
        double yaw = tf2::getYaw(q);

        // Calculate velocity in the vehicle's forward direction
        double cos_yaw = std::cos(yaw);
        double sin_yaw = std::sin(yaw);

        // Project velocity onto vehicle's forward direction
        double forward_velocity = vx * cos_yaw + vy * sin_yaw;

        return forward_velocity;
    }

} // namespace prius_controller