"""
Setup configuration for Abliterador Studio.

Supports installation methods:
  pip install .                 # Production install
  pip install -e .              # Development (editable) install
  pip install -e ".[dev]"       # With build tools for executable generation
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="abliterador-studio",
    version="0.4.0",
    description="GUI application for local LLM model loading, abliteration, and text generation with real-time UI feedback.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Azrael",
    author_email="",
    homepage="https://github.com/Azrael-Hagen/abliterador",
    repository="https://github.com/Azrael-Hagen/abliterador",
    license="MIT",
    
    # Package discovery
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "abliterador_app": [],
    },
    
    # Minimum Python version
    python_requires=">=3.10",
    
    # Runtime dependencies
    install_requires=[
        "PySide6>=6.7.0",
        "transformers>=4.40.0",
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "safetensors>=0.4.0",
        "huggingface-hub>=0.20.0",
        "requests>=2.31.0",
        "heretic-llm>=0.1.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
    ],
    
    # Optional dependencies for development/building
    extras_require={
        "dev": [
            "PyInstaller>=6.10.0",  # For building standalone executables
            "pytest>=7.0.0",         # Testing framework
            "black>=23.0.0",         # Code formatter
            "flake8>=6.0.0",         # Linter
            "mypy>=1.0.0",           # Type checker
        ],
    },
    
    # Entry points for command-line scripts
    entry_points={
        "console_scripts": [
            "abliterador-studio=abliterador_studio:main",
        ],
        "gui_scripts": [
            "abliterador-studio-gui=abliterador_studio:main",
        ],
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Spanish",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    
    # Keywords
    keywords="LLM abliteration transformers heretic GUI Qt PySide6",
    
    # Project URLs
    project_urls={
        "Documentation": "https://github.com/Azrael-Hagen/abliterador#readme",
        "Source Code": "https://github.com/Azrael-Hagen/abliterador",
        "Bug Tracker": "https://github.com/Azrael-Hagen/abliterador/issues",
    },
    
    # Zip safety
    zip_safe=False,
)
