from setuptools import setup, find_packages
from pathlib import Path

version = Path("VERSION").read_text().strip()

setup(
    name="localagent",
    version=version,
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.6",
        "websockets>=11.0",
    ],
    extras_require={
        "claude": ["anthropic>=0.20.0"],
    },
    entry_points={
        "console_scripts": [
            "localagent=localagent.main:main",
        ],
    },
    python_requires=">=3.9",
)
