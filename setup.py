#!/usr/bin/env python
import setuptools

from pyzoomapi import __version__

setuptools.setup(
    name='pyzoomapi',
    version=__version__,
    packages=['pyzoomapi',],
    license='MIT',
    long_description=open('README.md').read(),
    url='https://api.zoommedia.ai/',
    author='Zoom Media',
    author_email='support@zoommedia.ai',
    install_requires=[
        "requests >= 2.18.4"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

