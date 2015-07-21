# -*- coding: utf-8 -*-

from setuptools import setup

requires = [
        'autopep8',
        'flake8',
        'ipython',
        'nose',
        'mako',
        'awscli>=1.7.31',
        'boto>=2.38',
        'psycopg2',
        'numpy',
        'sqlalchemy',
        'shapely',
        'pyproj',
    ]

setup(name='3d-forge',
      version='0.0',
      description='QMesh reader/writer',
      url='',
      author='',
      author_email='',
      license='MIT',
      packages=['forge'],
      zip_safe=False,
      install_requires=requires,
      )
