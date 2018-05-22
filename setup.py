from setuptools import setup, find_packages

setup(
  name='walletconnect-bridge',
  version="0.1",
  install_requires=[
    'aiohttp',
    'aioredis',
    'uvloop',
    'boto3',
  ],
  packages=find_packages(),
  entry_points={
    'console_scripts': ['walletconnect-bridge=walletconnect_bridge:main',]
  },
)
