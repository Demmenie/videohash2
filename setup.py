import os.path

from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

about = {}
with open(os.path.join(os.path.dirname(__file__), "videohash2", "__version__.py")) as f:
    exec(f.read(), about)

version = str(about["__version__"])

download_url = f"https://github.com/demmenie/videohash2/archive/{version}.tar.gz"

setup(
    name=about["__title__"],
    packages=["videohash2"],
    version=version,
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=about["__license__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    download_url=download_url,
    install_requires=[
        "Pillow",
        "ImageHash",
        "imagedominantcolour",
        "yt-dlp",
    ],
    python_requires=">=3.6",
)
