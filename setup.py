from setuptools import setup, find_packages

setup(
  name='balance-bridge',
  version="0.1",
  install_requires=[
    'aiohttp',
    'redis',
    'pyfcm',
    'boto3',
  ],
  packages=find_packages(),
  entry_points={
    'console_scripts': ['balance-bridge=balance_bridge:main',]
  },
)
