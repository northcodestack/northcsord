from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="northcord",
    version="1.0.0",
    author="NorthCodeBase",
    author_email="northcodebase@example.com",
    description="Discord, reimagined for the terminal.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/northcodebase/northcord",
    project_urls={
        "Bug Tracker": "https://github.com/northcodebase/northcord/issues",
        "Documentation": "https://github.com/northcodebase/northcord#readme",
        "Source Code": "https://github.com/northcodebase/northcord",
    },
    packages=find_packages(include=["northcord", "northcord.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Topic :: Communications :: Chat",
        "Topic :: Multimedia :: Sound/Audio :: Players",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.0.0",
            "isort>=5.12.0",
            "pytest>=7.4.0",
            "mypy>=1.5.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "northcord=northcord.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "northcord": ["py.typed"],
    },
    zip_safe=False,
)
