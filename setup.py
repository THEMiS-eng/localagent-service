"""
LocalAgent v2.10.36 Setup
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from VERSION file
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
else:
    version = "0.0.0"

setup(
    name="localagent",
    version=version,
    author="THEMiS-eng",
    description="Smart Agent Orchestrator",
    packages=find_packages(),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "localagent-dev=localagent.main:main",
        ],
    },
)
