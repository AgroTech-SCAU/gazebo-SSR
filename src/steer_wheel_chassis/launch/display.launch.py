#!/usr/bin/env python3
# Copyright 2026 funfun
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Display the robot model in RViz2 (no Gazebo).

用法:
    ros2 launch steer_wheel_chassis display.launch.py
    ros2 launch steer_wheel_chassis display.launch.py joint_state_gui:=false
    ros2 launch steer_wheel_chassis display.launch.py use_mesh_collision:=true
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory('steer_wheel_chassis')
    xacro_file = os.path.join(pkg_share, 'urdf', 'steer_wheel_chassis.urdf.xacro')
    rviz_config = os.path.join(pkg_share, 'rviz', 'steer_wheel_chassis.rviz')
    controllers_file = os.path.join(pkg_share, 'config', 'steer_wheel_controllers.yaml')

    use_mesh_collision = LaunchConfiguration('use_mesh_collision')
    use_mid360 = LaunchConfiguration('use_mid360')

    robot_description = ParameterValue(
        Command([
            'xacro ', xacro_file,
            ' use_mesh_collision:=', use_mesh_collision,
            ' use_mid360:=', use_mid360,
            ' controllers_file:=', controllers_file,
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_mesh_collision', default_value='false',
            description='用原始 STL 网格作为碰撞体（精确但很慢）'),
        DeclareLaunchArgument(
            'use_mid360', default_value='true',
            description='在车头安装 Livox MID-360（false 则不生成传感器）'),
        DeclareLaunchArgument(
            'joint_state_gui', default_value='true',
            description='启动 joint_state_publisher_gui，可用滑块手动拖动 8 个关节'),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='启动 RViz2'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}],
        ),

        # 带滑块的手动关节控制
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            condition=IfCondition(LaunchConfiguration('joint_state_gui')),
        ),

        # joint_state_gui:=false 时用无界面的 joint_state_publisher，
        # 否则 /joint_states 没人发布，TF 里 8 个关节不会更新
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            condition=UnlessCondition(LaunchConfiguration('joint_state_gui')),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
    ])
