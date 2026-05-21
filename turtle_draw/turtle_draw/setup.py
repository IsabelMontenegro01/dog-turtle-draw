from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'turtle_draw'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         [os.path.join('resource', package_name)]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob(os.path.join('launch', '*.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aluno',
    maintainer_email='aluno@inteli.edu.br',
    description='Pipeline de visão computacional + controle turtlesim',
    license='MIT',
    entry_points={
        'console_scripts': [
            'turtle_draw_node = turtle_draw.turtle_draw_node:main',
        ],
    },
)