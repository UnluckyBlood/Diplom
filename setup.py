"""
Setup script для Arduino Monitoring System
"""

from setuptools import setup, find_packages
import os

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="arduino-monitoring-system",
    version="2.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Система мониторинга Arduino с AI рекомендациями",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/arduino-monitoring",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Home Automation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.14",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "arduino-monitor=run:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.html", "*.css", "*.js", "*.pkl"],
    },
)