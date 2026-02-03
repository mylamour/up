# Publishing to PyPI

This guide covers how to publish the `up-cli` package to PyPI (Python Package Index).

## Prerequisites

### 1. Create a PyPI Account

1. Go to https://pypi.org/account/register/
2. Fill in username, email, and password
3. Verify your email address

### 2. Get an API Token

**Step-by-step:**

1. Log in to https://pypi.org
2. Click your username (top right) → **Account settings**
3. Scroll down to **API tokens** section
4. Click **Add API token**
5. Enter a token name (e.g., "up-cli-publish")
6. Set scope to "Entire account" (first upload) or specific project (subsequent uploads)
7. Click **Create token**
8. **Copy the token immediately** - it starts with `pypi-` and is only shown once

> **Important:** Store your token securely. If lost, delete it and create a new one.

## Setup

### Install Build Tools

```bash
pip install build twine
```

### Configure Authentication

**Option A: Environment variable (CI/CD friendly)**
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_API_TOKEN
```

**Option B: Create `~/.pypirc` file**
```ini
[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN

[testpypi]
username = __token__
password = pypi-YOUR_TEST_API_TOKEN
```

## Publishing Workflow

### 1. Update Project Metadata

Edit `pyproject.toml` before first publish:

```toml
[project]
name = "up-cli"
version = "0.1.0"  # Bump this for each release
authors = [
    { name = "Your Actual Name", email = "your@email.com" }
]

[project.urls]
Homepage = "https://github.com/yourusername/up-cli"
Repository = "https://github.com/yourusername/up-cli"
```

### 2. Build the Package

```bash
# Clean previous builds
rm -rf dist/

# Build source distribution and wheel
python -m build
```

This creates:
- `dist/up_cli-0.1.0.tar.gz` (source)
- `dist/up_cli-0.1.0-py3-none-any.whl` (wheel)

### 3. Verify the Build

```bash
twine check dist/*
```

### 4. Test on TestPyPI (Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ up-cli
```

> Get a separate API token for TestPyPI at https://test.pypi.org/manage/account/token/

### 5. Publish to PyPI

```bash
twine upload dist/*
```

Or with explicit credentials:
```bash
twine upload -u __token__ -p pypi-YOUR_API_TOKEN dist/*
```

## Version Management

Before each release, bump the version in `pyproject.toml`:

```toml
version = "0.1.0"  # Initial release
version = "0.1.1"  # Patch (bug fixes)
version = "0.2.0"  # Minor (new features)
version = "1.0.0"  # Major (breaking changes)
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `403 Forbidden` | Check API token is correct and has proper scope |
| `400 File already exists` | Bump version number - can't overwrite existing versions |
| `Invalid distribution` | Run `twine check dist/*` to diagnose |
| `Package name taken` | Choose a different name in `pyproject.toml` |

## Quick Reference

```bash
# Full publish workflow
rm -rf dist/
python -m build
twine check dist/*
twine upload dist/*
```
