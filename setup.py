from setuptools import setup, find_packages

setup(
    name="api-nepse",
    version="2.2.0",
    author="Gunpark",
    author_email="gunpark@example.com",
    description="The Ultimate Unofficial NEPSE API for real-time Nepal Stock Exchange data.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/BalochLeader/NEPSE-API",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "httpx[http2]",
        "pywasm",
        "tqdm",
        "requests"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'api-nepse=api_nepse.main:main',
        ],
    },
)
