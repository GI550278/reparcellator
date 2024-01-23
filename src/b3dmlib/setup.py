from setuptools import setup, find_packages

setup(
    name="b3dmlib",
    version="1.0.0",
    author="Grigory Ilizirov",
    author_email="sguyalef@gmail.com",
    description="Sub-package for meshexchange to read and write b3dm files",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)