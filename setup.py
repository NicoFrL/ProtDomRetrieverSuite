from setuptools import setup, find_packages

# Read the long description from the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="protdomretrieversuite",
    version="0.1.0",
    author="Nicolas-Frederic Lipp",
    author_email="nlipp@ucsd.edu",
    description="A tool for protein domain extraction and structure processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NicoFrL/ProtDomRetrieverSuite",
    packages=find_packages(where="src"),  # Locate all packages in the `src` directory
    package_dir={"": "src"},  # Map the root package to the `src` directory
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.1",  # Required for API calls
        "ttkthemes>=3.2.2",  # Required for GUI dark theme
    ],
    entry_points={
        "console_scripts": [
            "protdomretrieversuite=gui.main_gui:main",  # Entry point for the CLI
        ],
    },
    extras_require={
        'dev': [
            'pytest>=6.0',  # For testing
            'black>=22.0',  # For code formatting
            'flake8>=3.9',  # For code linting
        ],
    },
    include_package_data=True,  # Include non-code files if specified in package_data
    package_data={
        'gui': ['config/*.json'],  # Adjust the path to match your actual structure
    },
    zip_safe=False,  # Indicates the package cannot run from a zip archive
)
