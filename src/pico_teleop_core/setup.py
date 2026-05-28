from setuptools import setup

package_name = 'pico_teleop_core'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='axgu',
    maintainer_email='axgu@todo.com',
    description='Core teleoperation pipeline nodes',
    license='MIT',
    entry_points={
        'console_scripts': [
            'retarget_node = pico_teleop_core.retarget_node:main',
            'ik_node = pico_teleop_core.ik_node:main',
            'arm_dispatcher = pico_teleop_core.arm_dispatcher:main',
            'server_bridge = pico_teleop_core.server_bridge:main',
        ],
    },
)
