"""
Setup configuration for AI service package.
"""
from setuptools import setup, find_packages

setup(
    name="ai-service",
    version="1.0.0",
    description="AI service package for handling AI-related functionality",
    author="Your Team",
    packages=find_packages(exclude=["tests", ".venv", "__pycache__"]),
    python_requires=">=3.9",
    include_package_data=True,
    install_requires=[
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "dependency-injector>=4.41.0",
        "structlog>=24.0.0",
        "python-dotenv>=1.0.0",
        "fastapi>=0.109.0",
        "starlette>=0.35.0",
        "uvicorn[standard]>=0.27.0",
        "groq>=0.4.0",
        "openai>=1.0.0",
        "redis>=5.0.0",
        "motor>=3.3.0",
    ],
    entry_points={
        "console_scripts": [
            "ai-service=__main__:main",
        ],
    },
)
