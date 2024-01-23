from setuptools import setup, find_packages

setup(
    name="meshexchange",
    version="0.0.1",
    author="Grigory Ilizirov",
    author_email="sguyalef@gmail.com",
    description="Package Read and write OSGB files",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)