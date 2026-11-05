# Exceptions

## hilda.exceptions

### HildaException

Bases: `Exception`

A domain exception for hilda errors.

Source code in `hilda/exceptions.py`

```
class HildaException(Exception):
    """A domain exception for hilda errors."""

    pass
```

### LLDBError

Bases: `HildaException`

Wrapper for RAW LLDB errors

Source code in `hilda/exceptions.py`

```
class LLDBError(HildaException):
    """Wrapper for RAW LLDB errors"""

    pass
```

### SymbolAbsentError

Bases: `HildaException`

Raise when trying to get a symbol that doesn't exist.

Source code in `hilda/exceptions.py`

```
class SymbolAbsentError(HildaException):
    """Raise when trying to get a symbol that doesn't exist."""

    pass
```

### EvaluatingExpressionError

Bases: `HildaException`

Raise when failing to evaluate an expression.

Source code in `hilda/exceptions.py`

```
class EvaluatingExpressionError(HildaException):
    """Raise when failing to evaluate an expression."""

    pass
```

### CreatingObjectiveCSymbolError

Bases: `HildaException`

Raise when failing to create an ObjectiveC Symbol.

Source code in `hilda/exceptions.py`

```
class CreatingObjectiveCSymbolError(HildaException):
    """Raise when failing to create an ObjectiveC Symbol."""

    pass
```

### ConvertingToNsObjectError

Bases: `HildaException`

Raise when failing to convert python object to NS object.

Source code in `hilda/exceptions.py`

```
class ConvertingToNsObjectError(HildaException):
    """Raise when failing to convert python object to NS object."""

    pass
```

### ConvertingFromNSObjectError

Bases: `HildaException`

Raise when failing to convert NS object to python object.

Source code in `hilda/exceptions.py`

```
class ConvertingFromNSObjectError(HildaException):
    """Raise when failing to convert NS object to python object."""

    pass
```

### DisableJetsamMemoryChecksError

Bases: `HildaException`

Raise when failing to disable jetsam memory checks.

Source code in `hilda/exceptions.py`

```
class DisableJetsamMemoryChecksError(HildaException):
    """Raise when failing to disable jetsam memory checks."""

    pass
```

### GettingObjectiveCClassError

Bases: `HildaException`

Raise when failing to get an ObjectiveC class.

Source code in `hilda/exceptions.py`

```
class GettingObjectiveCClassError(HildaException):
    """Raise when failing to get an ObjectiveC class."""

    pass
```

### AccessingRegisterError

Bases: `HildaException`

Raise when failing to access a register.

Source code in `hilda/exceptions.py`

```
class AccessingRegisterError(HildaException):
    """Raise when failing to access a register."""

    pass
```

### AccessingMemoryError

Bases: `HildaException`

Raise when failing to access memory.

Source code in `hilda/exceptions.py`

```
class AccessingMemoryError(HildaException):
    """Raise when failing to access memory."""

    pass
```

### AddingLldbSymbolError

Bases: `HildaException`

Raise when failing to convert a LLDB symbol to Hilda's symbol.

Source code in `hilda/exceptions.py`

```
class AddingLldbSymbolError(HildaException):
    """Raise when failing to convert a LLDB symbol to Hilda's symbol."""

    pass
```

### InvalidThreadIndexError

Bases: `HildaException`

Raise when thread idx invalid

Source code in `hilda/exceptions.py`

```
class InvalidThreadIndexError(HildaException):
    """Raise when thread idx invalid"""

    pass
```
