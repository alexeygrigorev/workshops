# Function Template

## Required Elements

Every function in this project MUST include:

```python
def function_name(param1: type, param2: type) -> return_type:
    """Brief description of what the function does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        SpecificException: When something goes wrong
    """
    # Implementation here
    pass
```

## Type Hint Requirements

- All parameters must have type hints
- Return type must always be specified (-> None if void)
- Use `typing` module for complex types:
  - `Optional[str]` for nullable strings
  - `List[int]` for lists
  - `Dict[str, Any]` for dictionaries

## Docstring Format

- Use Google-style docstrings (as shown above)
- First line: brief summary
- Args section: document all parameters
- Returns section: document return value
- Raises section: document exceptions
