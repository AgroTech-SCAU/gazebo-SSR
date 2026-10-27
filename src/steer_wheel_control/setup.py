import os
from glob import glob

from setuptools import setup

package_name = 'steer_wheel_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='funfun',
    maintainer_email='funfun@example.com',
    description='4WIS chassis control: cmd_vel (vx, vy, wz) to steering and wheel commands',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'steer_wheel_kinematics = steer_wheel_control.steer_wheel_kinematics:main',
        ],
    },
)
