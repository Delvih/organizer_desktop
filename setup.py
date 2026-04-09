"""
setup.py - Package configuration for FileOrganizer.
Run:  pip install -e .   or   python setup.py install
"""

from setuptools import setup, find_packages

setup(
    name="fileorganizer",
    version="1.0.0",
    description="Automated cross-platform file organizer with real-time monitoring",
    author="FileOrganizer Contributors",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "watchdog>=4.0.0",
    ],
    extras_require={
        "tray": [
            "pystray>=0.19.4",
            "Pillow>=10.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "fileorganizer=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
)
