from setuptools import setup

package_name = 'pico_teleop_drivers'

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
    description='Arm driver abstraction layer',
    license='MIT',
    entry_points={
        'console_scripts': [],
    },
)
