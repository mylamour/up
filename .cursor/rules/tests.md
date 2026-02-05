---
description: Testing standards
globs: ["tests/**/*", "**/*.test.*", "**/*.spec.*"]
---

# Testing Rules

## Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test fixtures
└── conftest.py     # Shared fixtures (pytest)
```

## Naming

- Test files: `test_*.py` or `*.test.ts`
- Test functions: `test_[what]_[condition]_[expected]`
- Example: `test_login_with_invalid_password_returns_401`

## AAA Pattern

```python
def test_example():
    # Arrange
    user = create_user()
    
    # Act
    result = user.login("password")
    
    # Assert
    assert result.success is True
```

## Fixtures

```python
@pytest.fixture
def user():
    return User(name="test", email="test@example.com")

def test_with_fixture(user):
    assert user.name == "test"
```

## Mocking

```python
from unittest.mock import Mock, patch

@patch('module.external_service')
def test_with_mock(mock_service):
    mock_service.return_value = {'status': 'ok'}
    result = function_under_test()
    assert result == 'ok'
```

## Coverage

- Aim for >80% coverage
- Focus on critical paths
- Don't test trivial code
