from setuptools import setup, find_packages

setup(
    name="XForge-Trader",
    version="9.2.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "yfinance>=0.2.0",
        "matplotlib>=3.7.0",
        "requests>=2.31.0",
    ],
    python_requires=">=3.9",
)
