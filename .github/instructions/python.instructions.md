---
applyTo: '**/*.py'
---

# Python Coding Instructions

## Project Configuration
- **Python Version**: 3.11+ (as specified in `.python-version` and `pyproject.toml`)
- **Package Manager**: uv (as configured in `build-system`)
- **Testing Framework**: pytest with asyncio auto mode

## Code Style & Imports
- Follow ruff configuration with isort rules enabled
- Use `hornet_flow` as known first-party package
- Combine imports with `as` statements when appropriate

## Naming Conventions
Follow [PEP8](https://peps.python.org/pep-0008/) for naming conventions:

| Type     | Example                                       |
|----------|-----------------------------------------------|
| Function | `function`, `my_function`                     |
| Variable | `x`, `var`, `my_variable`                     |
| Class    | `Model`, `MyClass`                            |
| Method   | `class_method`, `method`                      |
| Constant | `CONSTANT`, `MY_CONSTANT`, `MY_LONG_CONSTANT` |
| Module   | `module.py`, `my_module.py`                   |
| Package  | `package`, `my_package`                       |

- Mark protected/private entities with leading underscore: `_PROTECTED_CONSTANT`, `A._private_func`
- Protected/private constants use ALL_CAPS with leading underscore

## Type Annotations
- **DO**: Annotate all function/method parameters and return values
- **DO**: Annotate fixture return types
- **DO NOT**: Annotate test function return types (but do annotate test parameters)
- **DO**: Use `Final` from `typing` for constants
- Use modern type hints (`list[str]` instead of `List[str]`)
- Prioritize clear type annotations and naming over docstrings

## Constants
- All constants must be annotated with `Final` from `typing`
- Place constants at module top by default

## Logging Best Practices
- **No print statements**: Always use `logging` module for output
- **Lazy formatting**: Use `%` formatting (`logger.info("Value is %d", value)`) not f-strings
- Use `logger = logging.getLogger(__name__)` at module level

## Testing Patterns
- Use standalone functions, not test classes
- Leverage pytest fixtures for setup
- Split complex fixtures into coordinate fixtures for modularity
- No need for `@pytest.mark.asyncio` (asyncio_mode = "auto")
- Prefer minimal, focused test functions

## Async/Threading
- Use `asyncio.Event` for coordination between sync/async contexts
- Prefer `asyncio.to_thread()` for sync operations in async contexts
- Use proper event loop handling with `asyncio.get_event_loop()`

## Documentation
- Add docstrings **only when needed** for non-obvious rationale or context
- Always list exceptions raised with concise explanations
- Prefer single-line docstrings for simple functions
- Useful docstring content:
  - Raised exceptions (always required)
  - Design rationale
  - Extra parameter/variable information not clear from name/type
- Do **not** restate obvious function/class behavior
