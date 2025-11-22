#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script для Windows HDD Collector
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="windows-hdd-collector",
    version="1.0.0",
    author="Flask TMC App",
    description="Скрипт для сбора информации о жестких дисках на Windows и отправки на сервер",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/windows-hdd-collector",
    py_modules=["hdd_collector"],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "hdd-collector=hdd_collector:main",
        ],
    },
)

