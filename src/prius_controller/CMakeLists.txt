cmake_minimum_required(VERSION 3.0.2)
project(prius_controller)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  geometry_msgs
  nav_msgs
  tf2
  tf2_ros
  std_msgs
  prius_msgs
)

catkin_package(
  INCLUDE_DIRS include
  LIBRARIES ${PROJECT_NAME}
  CATKIN_DEPENDS roscpp geometry_msgs nav_msgs tf2 tf2_ros std_msgs prius_msgs
)

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
)

# Create the adapter node executable
add_executable(${PROJECT_NAME}_node 
  src/prius_controller_node.cpp
  src/prius_trajectory_controller.cpp
)

target_link_libraries(${PROJECT_NAME}_node
  ${catkin_LIBRARIES}
)

# Install the headers
install(DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
  FILES_MATCHING PATTERN "*.h"
)

# Install the executable
install(TARGETS ${PROJECT_NAME}_node
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
) 