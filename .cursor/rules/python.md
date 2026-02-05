---
description: Python code standards
globs: ["**/*.py"]
---

# Python Rules

## Style

- Use type hints for all function signatures
- Follow PEP 8 naming conventions
- Use dataclasses for data structures
- Prefer pathlib over os.path

## Imports

```python
# Standard library
import os
from pathlib import Path

# Third-party
import click
from rich.console import Console

# Local
from mypackage.module import function
```

## Documentation

```python
def function_name(param: str, count: int = 0) -> bool:
    """Brief description.
    
    Args:
        param: Description of param
        count: Description with default
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param is invalid
    """
```

## Testing

- Use pytest
- Name test files `test_*.py`
- Use fixtures for setup
- Aim for >80% coverage

## Common Patterns

### Error Handling
```python
try:
    result = operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Configuration
```python
@dataclass
class Config:
    debug: bool = False
    timeout: int = 30
```
