from setuptools import setup

setup(
    name="no_implicit_optional",
    version="1.2",
    author="Shantanu Jain",
    author_email="hauntsaninja@gmail.com",
    description="A codemod to make your implicit optional type hints PEP 484 compliant.",
    url="https://github.com/hauntsaninja/no_implicit_optional",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
    py_modules=["no_implicit_optional"],
    entry_points={"console_scripts": ["no_implicit_optional=no_implicit_optional:main"]},
    install_requires=["libcst"],
    python_requires=">=3.7",
)
