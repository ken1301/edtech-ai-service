"""
Setup configuration for Socratic AI Chat API
"""
from setuptools import setup, find_packages

setup(
    name="socratic-ai-chat",
    version="1.0.0",
    description="Socratic method-based educational AI chat API",
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
            "socratic-ai-chat=__main__:main",
        ],
    },
)
