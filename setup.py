from setuptools import setup

# python setup.py sdist
# twine upload dist/*

setup(
    name='lineus',
    version='1.0.1',
    packages=['lineus'],
    url='https://github.com/Line-us/LineUsPythonModule',
    license='MIT',
    author='Robert Poll',
    author_email='rob@line-us.com',
    description='The Python module for Line-us',
    install_requires=[
        'zeroconf>=0.21.3',
        'netifaces>=0.10.9',
        'ipaddress>=1.0.22',
    ],
    keywords='Line-us lineus drawing robot',

)
