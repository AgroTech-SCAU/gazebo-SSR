import os
from glob import glob

from setuptools import setup

package_name = 'steer_wheel_odometry'

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
    description='4WIS wheel odometry from steering angles and wheel velocities',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odometry = steer_wheel_odometry.steer_wheel_odometry:main',
        ],
    },
)
