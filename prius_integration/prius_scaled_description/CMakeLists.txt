cmake_minimum_required(VERSION 3.0.2)
project(prius_scaled_description)

find_package(catkin REQUIRED COMPONENTS
  urdf
  xacro
)

catkin_package()

install(DIRECTORY urdf meshes
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
) 