"""Project type templates for different tech stacks.

Templates available:
- fastapi: FastAPI backend with SQLAlchemy
- nextjs: Next.js frontend with TypeScript
- python-lib: Python library with packaging
- minimal: Minimal project structure
"""

from pathlib import Path
from datetime import date


# Template registry
TEMPLATES = {
    "minimal": "Minimal project structure",
    "fastapi": "FastAPI backend with SQLAlchemy, pytest, and Docker",
    "nextjs": "Next.js 14+ frontend with TypeScript and Tailwind",
    "python-lib": "Python library with pyproject.toml and pytest",
}


def get_available_templates() -> dict:
    """Get dictionary of available templates."""
    return TEMPLATES.copy()


def create_project_from_template(
    target_dir: Path,
    template: str,
    project_name: str,
    force: bool = False
) -> None:
    """Create project from specified template."""
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Available: {list(TEMPLATES.keys())}")
    
    if template == "minimal":
        _create_minimal_template(target_dir, project_name, force)
    elif template == "fastapi":
        _create_fastapi_template(target_dir, project_name, force)
    elif template == "nextjs":
        _create_nextjs_template(target_dir, project_name, force)
    elif template == "python-lib":
        _create_python_lib_template(target_dir, project_name, force)


def _write_file(path: Path, content: str, force: bool) -> None:
    """Write file if it doesn't exist or force is True."""
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# =============================================================================
# Minimal Template
# =============================================================================

def _create_minimal_template(target_dir: Path, project_name: str, force: bool) -> None:
    """Create minimal project structure."""
    # Create directories
    (target_dir / "src").mkdir(parents=True, exist_ok=True)
    (target_dir / "tests").mkdir(parents=True, exist_ok=True)
    
    # Create README
    readme = f"""# {project_name}

> Add project description here

## Getting Started

```bash
# Install dependencies
pip install -e .

# Run tests
pytest
```

## Structure

```
{project_name}/
├── src/           # Source code
├── tests/         # Tests
└── docs/          # Documentation
```
"""
    _write_file(target_dir / "README.md", readme, force)
    
    # Create .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Up CLI
.loop_state.json
.circuit_*.json
"""
    _write_file(target_dir / ".gitignore", gitignore, force)


# =============================================================================
# FastAPI Template
# =============================================================================

def _create_fastapi_template(target_dir: Path, project_name: str, force: bool) -> None:
    """Create FastAPI project template."""
    safe_name = project_name.replace("-", "_").lower()
    
    # Create directories
    dirs = [
        f"src/{safe_name}",
        f"src/{safe_name}/api",
        f"src/{safe_name}/models",
        f"src/{safe_name}/services",
        "tests",
        "alembic/versions",
    ]
    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
    
    # pyproject.toml
    pyproject = f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "FastAPI application"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.24.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{safe_name}"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
'''
    _write_file(target_dir / "pyproject.toml", pyproject, force)
    
    # Main app
    main_app = f'''"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{project_name}",
    description="API description",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {{"message": "Welcome to {project_name}"}}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {{"status": "healthy"}}


# Import and include routers
# from {safe_name}.api import router
# app.include_router(router)
'''
    _write_file(target_dir / f"src/{safe_name}/main.py", main_app, force)
    
    # __init__.py
    _write_file(target_dir / f"src/{safe_name}/__init__.py", '"""Package."""\n', force)
    _write_file(target_dir / f"src/{safe_name}/api/__init__.py", '"""API module."""\n', force)
    _write_file(target_dir / f"src/{safe_name}/models/__init__.py", '"""Models module."""\n', force)
    _write_file(target_dir / f"src/{safe_name}/services/__init__.py", '"""Services module."""\n', force)
    
    # Config
    config = f'''"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "{project_name}"
    debug: bool = False
    database_url: str = "sqlite:///./app.db"
    
    class Config:
        env_file = ".env"


settings = Settings()
'''
    _write_file(target_dir / f"src/{safe_name}/config.py", config, force)
    
    # Test file
    test_main = f'''"""Test main endpoints."""

import pytest
from httpx import AsyncClient
from {safe_name}.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
'''
    _write_file(target_dir / "tests/test_main.py", test_main, force)
    _write_file(target_dir / "tests/__init__.py", "", force)
    
    # Dockerfile
    dockerfile = f'''FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source
COPY src/ src/

# Run
EXPOSE 8000
CMD ["uvicorn", "{safe_name}.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
    _write_file(target_dir / "Dockerfile", dockerfile, force)
    
    # README
    readme = f'''# {project_name}

FastAPI application.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run
uvicorn {safe_name}.main:app --reload

# Test
pytest
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker

```bash
docker build -t {project_name} .
docker run -p 8000:8000 {project_name}
```
'''
    _write_file(target_dir / "README.md", readme, force)
    
    # .env.example
    env_example = """# Environment variables
DEBUG=false
DATABASE_URL=sqlite:///./app.db
"""
    _write_file(target_dir / ".env.example", env_example, force)
    
    # .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# IDE
.idea/
.vscode/

# Testing
.pytest_cache/
.coverage

# Environment
.env
*.db

# Up CLI
.loop_state.json
"""
    _write_file(target_dir / ".gitignore", gitignore, force)


# =============================================================================
# Next.js Template
# =============================================================================

def _create_nextjs_template(target_dir: Path, project_name: str, force: bool) -> None:
    """Create Next.js project template."""
    # Create directories
    dirs = [
        "src/app",
        "src/components",
        "src/lib",
        "src/types",
        "public",
    ]
    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
    
    # package.json
    package_json = f'''{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest"
  }},
  "dependencies": {{
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x"
  }},
  "devDependencies": {{
    "@types/node": "20.x",
    "@types/react": "18.x",
    "@types/react-dom": "18.x",
    "typescript": "5.x",
    "tailwindcss": "3.x",
    "postcss": "8.x",
    "autoprefixer": "10.x",
    "eslint": "8.x",
    "eslint-config-next": "14.x",
    "jest": "29.x",
    "@testing-library/react": "14.x",
    "@testing-library/jest-dom": "6.x"
  }}
}}
'''
    _write_file(target_dir / "package.json", package_json, force)
    
    # tsconfig.json
    tsconfig = '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
'''
    _write_file(target_dir / "tsconfig.json", tsconfig, force)
    
    # tailwind.config.js
    tailwind = '''/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
'''
    _write_file(target_dir / "tailwind.config.js", tailwind, force)
    
    # postcss.config.js
    postcss = '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
    _write_file(target_dir / "postcss.config.js", postcss, force)
    
    # next.config.js
    next_config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
'''
    _write_file(target_dir / "next.config.js", next_config, force)
    
    # src/app/layout.tsx
    layout = f'''import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{project_name}',
  description: 'Generated by up-cli',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}
'''
    _write_file(target_dir / "src/app/layout.tsx", layout, force)
    
    # src/app/page.tsx
    page = f'''export default function Home() {{
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold">{project_name}</h1>
      <p className="mt-4 text-gray-600">
        Edit <code className="bg-gray-100 px-2 py-1 rounded">src/app/page.tsx</code> to get started.
      </p>
    </main>
  )
}}
'''
    _write_file(target_dir / "src/app/page.tsx", page, force)
    
    # src/app/globals.css
    globals_css = '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''
    _write_file(target_dir / "src/app/globals.css", globals_css, force)
    
    # README
    readme = f'''# {project_name}

Next.js application with TypeScript and Tailwind CSS.

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

- `npm run dev` - Development server
- `npm run build` - Production build
- `npm run start` - Start production server
- `npm run lint` - Run linter
- `npm run test` - Run tests
'''
    _write_file(target_dir / "README.md", readme, force)
    
    # .gitignore
    gitignore = """# Dependencies
node_modules/
.pnp/

# Build
.next/
out/
build/
dist/

# Testing
coverage/

# IDE
.idea/
.vscode/

# Env
.env*.local

# Up CLI
.loop_state.json
"""
    _write_file(target_dir / ".gitignore", gitignore, force)


# =============================================================================
# Python Library Template
# =============================================================================

def _create_python_lib_template(target_dir: Path, project_name: str, force: bool) -> None:
    """Create Python library template."""
    safe_name = project_name.replace("-", "_").lower()
    
    # Create directories
    dirs = [
        f"src/{safe_name}",
        "tests",
    ]
    for d in dirs:
        (target_dir / d).mkdir(parents=True, exist_ok=True)
    
    # pyproject.toml
    pyproject = f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "A Python library"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    {{ name = "Your Name", email = "you@example.com" }}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/{project_name}"
Documentation = "https://github.com/yourusername/{project_name}#readme"
Repository = "https://github.com/yourusername/{project_name}"

[tool.hatch.build.targets.wheel]
packages = ["src/{safe_name}"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov={safe_name} --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true
'''
    _write_file(target_dir / "pyproject.toml", pyproject, force)
    
    # Main module
    init_py = f'''"""{project_name} - A Python library.

Example:
    >>> from {safe_name} import hello
    >>> hello("World")
    'Hello, World!'
"""

__version__ = "0.1.0"


def hello(name: str) -> str:
    """Say hello.
    
    Args:
        name: Name to greet
        
    Returns:
        Greeting message
    """
    return f"Hello, {{name}}!"
'''
    _write_file(target_dir / f"src/{safe_name}/__init__.py", init_py, force)
    
    # Tests
    test_main = f'''"""Tests for {project_name}."""

from {safe_name} import hello, __version__


def test_version():
    """Test version is set."""
    assert __version__ == "0.1.0"


def test_hello():
    """Test hello function."""
    assert hello("World") == "Hello, World!"
    assert hello("Python") == "Hello, Python!"
'''
    _write_file(target_dir / "tests/test_main.py", test_main, force)
    _write_file(target_dir / "tests/__init__.py", "", force)
    
    # README
    readme = f'''# {project_name}

A Python library.

## Installation

```bash
pip install {project_name}
```

## Usage

```python
from {safe_name} import hello

print(hello("World"))  # Hello, World!
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

## License

MIT
'''
    _write_file(target_dir / "README.md", readme, force)
    
    # LICENSE
    license_text = f'''MIT License

Copyright (c) {date.today().year} Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
    _write_file(target_dir / "LICENSE", license_text, force)
    
    # .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
dist/
build/

# IDE
.idea/
.vscode/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Up CLI
.loop_state.json
"""
    _write_file(target_dir / ".gitignore", gitignore, force)
