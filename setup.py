from setuptools import setup, find_packages

setup(
    name="software-change-predictor",
    version="1.0.0",
    description="Software Change Predictor - Final Year Project",
    author="BTech Team",
    packages=find_packages(),
    install_requires=[
        "pydriller",
        "pandas",
        "numpy",
        "scipy",
        "fastapi",
        "uvicorn",
        "scikit-learn",
        "pydantic",
        "python-multipart"
    ],
    entry_points={
        "console_scripts": [
            "scp-cli=main:main",
        ],
    },
)
