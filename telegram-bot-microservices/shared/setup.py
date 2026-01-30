from setuptools import setup, find_packages

setup(
    name="vitte-shared",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy[asyncio]>=2.0.25",
        "asyncpg>=0.29.0",
        "pydantic>=2.5.3",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.0",
        "redis>=5.0.1",
        "minio>=7.2.3",
        "python-json-logger>=2.0.7",
    ],
)
