from setuptools import setup, find_packages

setup(
  name='balance-bridge',
  version="0.1",
  install_requires=[
    'Flask',
    'Flask-API',
    'nose',
    'mock',
    'redis',
  ],
  packages=find_packages(),
  entry_points={
    'console_scripts': ['balance-bridge=balance_bridge:main',]
  },
)
