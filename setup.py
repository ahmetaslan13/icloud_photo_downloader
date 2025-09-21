"""Setup configuration for iCloud Photo Downloader."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="icloud-photo-downloader",
    version="1.0.0",
    author="Ahmet Aslan",
    author_email="ahmetaslan13@github.com",
    description="A tool to download and organize your iCloud photos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ahmetaslan13/icloud_photo_downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "pyicloud",
        "Pillow",
        "piexif",
        "tqdm",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "icloud-photo-downloader=icloud_photo_downloader.cli:main",
        ],
    },
    package_data={
        "icloud_photo_downloader": ["config/*.yml"],
    },
)