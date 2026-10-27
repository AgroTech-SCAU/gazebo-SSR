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

r"""
Bring up only the sweet-pepper greenhouse scene in Gazebo Classic 11.

This launch does not spawn a robot. Any ROS 2 chassis can use the world:

    PKG=$(ros2 pkg prefix pepper_greenhouse)/share/pepper_greenhouse
    WORLD=$PKG/worlds/pepper_greenhouse.world
    ros2 launch <chassis_pkg> <chassis_launch.py> world:=$WORLD

or be spawned into the running scene with gazebo_ros/spawn_entity.py.

Usage:
    ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py
    ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py gui:=false
    ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py profile:=visual gui:=true
    ros2 launch pepper_greenhouse pepper_greenhouse_world.launch.py pause:=true
"""
from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

_PROFILES = {
    'layout': 'pepper_greenhouse.world',
    'visual': 'pepper_greenhouse_visual.world',
}

# Gazebo 11 default resource root on Ubuntu (must contain media/).
_GAZEBO_RESOURCE_ROOT = '/usr/share/gazebo-11'


def _fix_gazebo_resource_path() -> None:
    """
    Append Gazebo's default resource root to GAZEBO_RESOURCE_PATH.

    gazebo_ros overwrites GAZEBO_RESOURCE_PATH with ROS package export
    directories, which have no media/ subdirectory. Gazebo then appends
    /media to each entry, fails to find its shaders and materials, and gzclient
    crashes while initialising the OGRE camera. The same workaround is used by
    steer_wheel_chassis/gazebo.launch.py.
    """
    if not os.path.isdir(os.path.join(_GAZEBO_RESOURCE_ROOT, 'media')):
        return
    current = os.environ.get('GAZEBO_RESOURCE_PATH', '')
    if _GAZEBO_RESOURCE_ROOT in current.split(os.pathsep):
        return
    os.environ['GAZEBO_RESOURCE_PATH'] = os.pathsep.join(
        p for p in (current, _GAZEBO_RESOURCE_ROOT) if p)


def _launch_setup(context, *args, **kwargs):
    profile = LaunchConfiguration('profile').perform(context)
    if profile not in _PROFILES:
        raise ValueError(
            f"profile must be one of {sorted(_PROFILES)}, got '{profile}'")

    world = os.path.join(
        get_package_share_directory('pepper_greenhouse'),
        'worlds', _PROFILES[profile],
    )
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('gazebo_ros'),
            'launch', 'gazebo.launch.py')),
        launch_arguments={
            'world': world,
            'gui': LaunchConfiguration('gui'),
            'verbose': LaunchConfiguration('verbose'),
            'pause': LaunchConfiguration('pause'),
            'server_required': 'false',
        }.items(),
    )
    return [gazebo]


def generate_launch_description() -> LaunchDescription:
    """Build the launch description."""
    _fix_gazebo_resource_path()
    return LaunchDescription([
        DeclareLaunchArgument(
            'profile', default_value='layout',
            description='layout (sparse, fast) or visual (dense plants)'),
        DeclareLaunchArgument(
            'gui', default_value='true',
            description='start the Gazebo client'),
        DeclareLaunchArgument(
            'verbose', default_value='false',
            description='verbose gzserver output'),
        DeclareLaunchArgument(
            'pause', default_value='false',
            description='start the simulation paused'),
        OpaqueFunction(function=_launch_setup),
    ])
