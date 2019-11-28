from setuptools import setup

setup(
    name='lineus',
    version='0.1.16',
    packages=['lineus'],
    url='https://www.line-us.com',
    license='MIT',
    author='Robert Poll',
    author_email='rob@line-us.com',
    description='The Python module for Line-us',
    install_requires=[
        'zeroconf>=0.21.3',
        'netifaces>=0.10.9',
        'ipaddress>=1.0.22',
    ]
)
