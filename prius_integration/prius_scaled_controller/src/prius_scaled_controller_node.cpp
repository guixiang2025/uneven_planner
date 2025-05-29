#include "prius_trajectory_controller.h"
#include <ros/ros.h>

int main(int argc, char **argv)
{
    ros::init(argc, argv, "prius_scaled_controller_node");
    ros::NodeHandle nh("~");
    ros::Rate loop_rate(50); // 50 Hz control loop

    prius_scaled_controller::PriusTrajectoryController controller(nh);

    if (!controller.initialize())
    {
        ROS_ERROR("Failed to initialize Prius scaled controller");
        return -1;
    }

    ROS_INFO("Prius scaled controller node started");

    while (ros::ok())
    {
        controller.update();
        ros::spinOnce();
        loop_rate.sleep();
    }

    return 0;
}