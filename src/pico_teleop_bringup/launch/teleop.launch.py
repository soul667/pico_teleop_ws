import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('pico_teleop_bringup')

    arm_config_arg = DeclareLaunchArgument(
        'arm_config', default_value='franka_single',
        description='Arm configuration name')

    ik_solver_arg = DeclareLaunchArgument(
        'ik_solver', default_value='trac_ik',
        description='IK solver: curobo | moveit | trac_ik')

    workspace_scale_arg = DeclareLaunchArgument(
        'workspace_scale', default_value='1.0',
        description='VR to robot workspace scaling factor')

    retarget_node = Node(
        package='pico_teleop_core',
        executable='retarget_node',
        name='retarget_node',
        parameters=[{
            'workspace_scale': LaunchConfiguration('workspace_scale'),
            'arm_config': LaunchConfiguration('arm_config'),
        }],
        output='screen',
    )

    ik_node = Node(
        package='pico_teleop_core',
        executable='ik_node',
        name='ik_node',
        parameters=[{
            'solver': LaunchConfiguration('ik_solver'),
            'arm_config': LaunchConfiguration('arm_config'),
        }],
        output='screen',
    )

    arm_dispatcher = Node(
        package='pico_teleop_core',
        executable='arm_dispatcher',
        name='arm_dispatcher',
        parameters=[{
            'arm_config': LaunchConfiguration('arm_config'),
        }],
        output='screen',
    )

    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        parameters=[{
            'port': 9090,
            'use_compression': True,
        }],
        output='screen',
    )

    server_bridge = Node(
        package='pico_teleop_core',
        executable='server_bridge',
        name='server_bridge',
        output='screen',
    )

    return LaunchDescription([
        arm_config_arg,
        ik_solver_arg,
        workspace_scale_arg,
        retarget_node,
        ik_node,
        arm_dispatcher,
        rosbridge,
        server_bridge,
    ])
