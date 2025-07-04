import os

import setuptools

with open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf8") as fh:
    requirements_text = fh.read()

requirements_list = [r.strip() for r in requirements_text.split(os.linesep)]
requirements_list = [r for r in requirements_list if len(r) > 0]

LIB_NAME: str = "infra-storage-python"

setuptools.setup(
    name=LIB_NAME,
    version="1.2.0",
    author="Luis Gerardo Fosado Baños GrupoSid's Tech",
    author_email="developers@gruposid.com.mx",
    description="Infrastructure Storage Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PharmaGobierno/{LIB_NAME}.git",
    include_package_data=True,
    keywords="infra, storage, library, python",
    packages=setuptools.find_packages(),
    package_data={"": ["*.json"]},
    namespace_packages=["infra"],
    install_requires=requirements_list,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.7",
    zip_safe=True,
)
