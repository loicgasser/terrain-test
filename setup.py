# -*- coding: utf-8 -*-

from setuptools import setup

requires = [
        'autopep8==1.2.4',
        'flake8==3.0.4',
        'ipython==4.0.0',
        'nose',
        'mako',
        'awscli>=1.7.31',
        'boto>=2.38',
        'psycopg2',
        'sqlalchemy',
        'geoalchemy2==0.4.2',
        'requests',
        'pyproj',
        'gatilegrid>=0.1.9',
        'poolmanager>=0.0.6',
        'quantized-mesh-tile>=0.6'
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
