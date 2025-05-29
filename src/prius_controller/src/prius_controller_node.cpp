#include <ros/ros.h>
#include "prius_controller/prius_trajectory_controller.h"

int main(int argc, char **argv)
{
    ros::init(argc, argv, "prius_controller_node");

    ros::NodeHandle nh("~");

    // Create the controller instance
    prius_controller::PriusTrajectoryController controller(nh);

    // Initialize the controller
    if (!controller.initialize())
    {
        ROS_ERROR("Failed to initialize PriusTrajectoryController");
        return -1;
    }

    // Set control loop rate (50 Hz matches Prius model update rate)
    ros::Rate loop_rate(50);

    ROS_INFO("Prius controller node is running...");

    // Main control loop
    while (ros::ok())
    {
        ros::spinOnce();     // Process callbacks
        controller.update(); // Update controller
        loop_rate.sleep();   // Maintain loop rate
    }

    return 0;
}