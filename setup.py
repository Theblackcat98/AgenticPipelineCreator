import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="agentic-pipeline-framework",
    version="0.1.0",
    author="theblackcat98",
    author_email="[your_email@example.com]", # Placeholder - User advised to update
    description="A framework to design, orchestrate, and execute LLM and tool-based workflows using JSON.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/theblackcat98/agentic-pipeline-framework",
    py_modules=["main", "orchestrator", "json_creator"],
    packages=setuptools.find_packages(include=['llm', 'llm.*', 'tools', 'tools.*'], exclude=("tests*", "docs*", "examples*")),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha", # Or 4 - Beta if more mature
    ],
    python_requires='>=3.8',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'apf-run=main:main_cli', # Assuming main.py will have a main_cli function
        ],
    },
    project_urls={
        "Documentation": "https://github.com/theblackcat98/agentic-pipeline-framework/blob/main/docs/index.md", # Placeholder
        "Source Code": "https://github.com/theblackcat98/agentic-pipeline-framework", # Placeholder
        "Bug Tracker": "https://github.com/theblackcat98/agentic-pipeline-framework/issues", # Placeholder
    },
)
