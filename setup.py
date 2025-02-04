from setuptools import setup, find_packages

setup(
    name="mechanismaf",
    version="0.1.2",
    description="A wrapper around the 'mechanism' library for the 'Algorithm Folding' lecture @ HPI for creating and transforming linkage mechanisms.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Tobias Görgens",
    author_email="tobiasg-privat@proton.me",
    url="https://github.com/TobiPeterG/mechanismaf",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy",
        "networkx",
        "mechanism",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

