from setuptools import setup, find_packages

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
    packages=find_packages(),
    classifiers=[...],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.1",
        "ttkthemes>=3.2.2",
    ],
    entry_points={
        "console_scripts": [
            "protdomretrieversuite=protdomretrieversuite.gui.main_gui:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
