# Learn Python by This Codebase

This document is designed for beginners to learn Python programming concepts by studying the XRate codebase. Each section explains a Python concept with examples from this project.

---

## Table of Contents

1. [Basic Python Syntax](#1-basic-python-syntax)
2. [Import Statements](#2-import-statements)
3. [Functions and Methods](#3-functions-and-methods)
4. [Classes and Objects](#4-classes-and-objects)
5. [Data Types](#5-data-types)
6. [Error Handling](#6-error-handling)
7. [Async/Await](#7-asyncawait)
8. [Decorators](#8-decorators)
9. [Type Hints](#9-type-hints)
10. [Modules and Packages](#10-modules-and-packages)
11. [Best Practices](#11-best-practices)

---

## 1. Basic Python Syntax

### Comments
```python
# This is a single-line comment
# Comments explain what the code does

"""
This is a multi-line comment (docstring)
It can span multiple lines
Used for documenting functions and classes
"""
```

**Example from codebase:**
```python
# src/xrate/app.py (line 24)
import logging  # Standard library for logging messages and errors
```

### Variables
```python
# Variables store data
name = "XRate"  # String (text)
version = 1.1  # Float (decimal number)
count = 10  # Integer (whole number)
is_active = True  # Boolean (True/False)
```

**Example from codebase:**
```python
# src/xrate/adapters/telegram/jobs.py (line 43)
_breach_history: dict[str, Optional[str]] = {}  # Dictionary to track breach history
```

---

## 2. Import Statements

### Standard Library Imports
```python
import logging  # Import entire module
from datetime import datetime  # Import specific function/class
from typing import Optional  # Import type hints
```

**Example from codebase:**
```python
# src/xrate/app.py (lines 24-30)
import logging  # Standard library for logging messages and errors
import os  # Operating system interface
from datetime import timedelta, time  # Date and time utilities
```

### Third-Party Imports
```python
import requests  # External library (must be installed via pip)
from bs4 import BeautifulSoup  # BeautifulSoup library for HTML parsing
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (line 26)
import requests  # HTTP library for making web requests
```

### Local Imports (Your Project)
```python
from xrate.config import settings  # Import from your own project
from xrate.domain.models import IrrSnapshot  # Import from domain layer
```

**Example from codebase:**
```python
# src/xrate/app.py (lines 35-38)
from xrate.shared.logging_conf import setup_logging  # Configure logging
from xrate.adapters.crawlers.bonbast_crawler import BonbastCrawler  # Web crawler for market data
```

---

## 3. Functions and Methods

### Defining Functions
```python
def function_name(parameter1, parameter2):
    """Documentation string explaining what the function does."""
    # Function body
    result = parameter1 + parameter2
    return result  # Return a value
```

**Example from codebase:**
```python
# src/xrate/application/crawler_service.py (lines 34-51)
def get_crawler_snapshot() -> Optional[IrrSnapshot]:
    """
    Fetch USD/EUR/Gold prices from crawlers.
    
    Returns:
        IrrSnapshot with prices, or None if crawlers fail
    """
    # Try Crawler1 (Bonbast) first
    try:
        crawler1 = BonbastCrawler(...)
        result1 = crawler1.fetch()
        # ... more code ...
        return IrrSnapshot(...)
    except Exception as e:
        log.warning("Crawler failed: %s", e)
    return None
```

### Function Parameters with Type Hints
```python
def calculate_price(amount: int, rate: float) -> float:
    """Calculate price with type hints."""
    return amount * rate
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (lines 112-125)
def _parse_price(self, text: str) -> Optional[int]:
    """
    Parse price from text string.
    
    Args:
        text: Text containing price
        
    Returns:
        Integer price or None if parsing fails
    """
    if not text:
        return None
    # ... parsing logic ...
```

---

## 4. Classes and Objects

### Class Definition
```python
class MyClass:
    """Class documentation."""
    
    def __init__(self, parameter):
        """Constructor - called when object is created."""
        self.parameter = parameter  # Instance variable
    
    def method(self):
        """Instance method - operates on object data."""
        return self.parameter
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (lines 44-60)
class BaseCrawler(ABC):
    """
    Base class for web crawlers with TTL-based caching.
    """
    
    def __init__(self, url: str, cache_minutes: int, timeout: int = 10):
        """Initialize base crawler."""
        self.url = url
        self.timeout = timeout
        self.ttl = timedelta(minutes=cache_minutes)
```

### Inheritance
```python
class ParentClass:
    def method(self):
        return "parent"

class ChildClass(ParentClass):
    def method(self):
        return "child"
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/bonbast_crawler.py (line 30)
class BonbastCrawler(BaseCrawler):
    """
    Crawler for bonbast.com website.
    Inherits from BaseCrawler.
    """
    def _parse_html(self, html: str) -> CrawlerResult:
        # Implementation specific to Bonbast
        ...
```

### Abstract Classes
```python
from abc import ABC, abstractmethod

class Base(ABC):
    @abstractmethod
    def must_implement(self):
        """Subclasses must implement this."""
        raise NotImplementedError
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (lines 99-109)
@abstractmethod
def _parse_html(self, html: str) -> CrawlerResult:
    """
    Parse HTML content and extract prices.
    Subclasses must implement this method.
    """
    raise NotImplementedError
```

---

## 5. Data Types

### Strings
```python
text = "Hello World"
formatted = f"Price: {price}"  # f-string formatting
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (line 137)
log.info("Crawler data updated for %s (ttl=%s minutes)", self.url, self.ttl.total_seconds() / 60)
```

### Lists
```python
prices = [100, 200, 300]
prices.append(400)  # Add item
first = prices[0]  # Access first item
```

### Dictionaries
```python
data = {
    "usd": 108400,
    "eur": 126000,
    "gold": 10498
}
usd_price = data["usd"]  # Access by key
```

**Example from codebase:**
```python
# src/xrate/adapters/telegram/jobs.py (line 43)
_breach_history: dict[str, Optional[str]] = {}  # Track breach directions
```

### Tuples
```python
point = (10, 20)  # Immutable (cannot change)
x, y = point  # Unpacking
```

### Dataclasses
```python
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int
```

**Example from codebase:**
```python
# src/xrate/domain/models.py (lines 26-40)
@dataclass(frozen=True)
class IrrSnapshot:
    """Iranian market snapshot."""
    usd_toman: int
    eur_toman: int
    gold_1g_toman: int
    provider: Optional[str] = None
```

---

## 6. Error Handling

### Try-Except Blocks
```python
try:
    # Code that might fail
    result = risky_operation()
except Exception as e:
    # Handle the error
    print(f"Error: {e}")
```

**Example from codebase:**
```python
# src/xrate/application/crawler_service.py (lines 34-55)
try:
    crawler1 = BonbastCrawler(...)
    result1 = crawler1.fetch()
    if result1.usd_sell and result1.eur_sell:
        return IrrSnapshot(...)
except Exception as e:
    log.warning("Crawler1 failed, trying Crawler2: %s", e)
```

### Multiple Exception Types
```python
try:
    # Code
except ValueError as e:
    # Handle ValueError
except TypeError as e:
    # Handle TypeError
except Exception as e:
    # Handle any other exception
```

**Example from codebase:**
```python
# src/xrate/app.py (lines 239-279)
try:
    app.run_polling(...)
except Conflict as e:
    logger.error("Telegram Conflict error: %s", e)
except (TimedOut, NetworkError) as e:
    logger.error("Network error: %s", e)
except KeyboardInterrupt:
    logger.info("Bot stopped by user")
except Exception as e:
    logger.exception("Unexpected error: %s", e)
```

---

## 7. Async/Await

### Async Functions
```python
async def fetch_data():
    """Async function - can pause and resume."""
    result = await some_async_operation()
    return result
```

**Example from codebase:**
```python
# src/xrate/adapters/telegram/jobs.py (line 203)
async def post_rate_job(context: ContextTypes.DEFAULT_TYPE, svc: RatesService) -> None:
    """
    Scheduled job that monitors market changes and posts updates.
    """
    async with _post_rate_job_lock:
        # Fetch data
        snap = get_irr_snapshot()
        # Post to Telegram
        await context.bot.send_message(...)
```

### Await
```python
result = await async_function()  # Wait for async operation to complete
```

**Example from codebase:**
```python
# src/xrate/adapters/telegram/jobs.py (line 283)
await context.bot.send_message(
    chat_id=settings.channel_id,
    text=market_lines(...),
)
```

---

## 8. Decorators

### Function Decorators
```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        # Do something before
        result = func(*args, **kwargs)
        # Do something after
        return result
    return wrapper

@my_decorator
def my_function():
    pass
```

**Example from codebase:**
```python
# src/xrate/domain/models.py (line 26)
@dataclass(frozen=True)  # Decorator makes this a dataclass
class IrrSnapshot:
    usd_toman: int
    eur_toman: int
```

### Abstractmethod Decorator
```python
from abc import abstractmethod

class Base(ABC):
    @abstractmethod  # Decorator marks method as abstract
    def must_implement(self):
        raise NotImplementedError
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (line 99)
@abstractmethod
def _parse_html(self, html: str) -> CrawlerResult:
    """Subclasses must implement this."""
    raise NotImplementedError
```

---

## 9. Type Hints

### Function Type Hints
```python
def add(a: int, b: int) -> int:
    """Type hints specify parameter and return types."""
    return a + b
```

**Example from codebase:**
```python
# src/xrate/application/crawler_service.py (line 34)
def get_crawler_snapshot() -> Optional[IrrSnapshot]:
    """Returns IrrSnapshot or None."""
    ...
```

### Variable Type Hints
```python
name: str = "John"
age: int = 25
prices: list[int] = [100, 200, 300]
```

**Example from codebase:**
```python
# src/xrate/adapters/crawlers/base.py (line 44)
def __init__(self, url: str, cache_minutes: int, timeout: int = 10):
    self.url = url  # Type is str
    self.timeout = timeout  # Type is int
```

### Optional Types
```python
from typing import Optional

def get_price() -> Optional[int]:
    """Returns int or None."""
    return None  # or return 100
```

**Example from codebase:**
```python
# src/xrate/domain/models.py (line 40)
provider: Optional[str] = None  # Can be string or None
```

---

## 10. Modules and Packages

### Module Structure
```
xrate/
├── __init__.py  # Makes directory a Python package
├── app.py  # Module file
└── config/
    ├── __init__.py
    └── settings.py
```

### Importing from Modules
```python
# Import entire module
import xrate.config

# Import specific item
from xrate.config import settings

# Import with alias
from xrate.config import settings as config
```

**Example from codebase:**
```python
# src/xrate/app.py (line 35)
from xrate.shared.logging_conf import setup_logging  # Import function
from xrate.config import settings  # Import module-level variable
```

### Package __init__.py
```python
# src/xrate/application/__init__.py
from xrate.application.rates_service import RatesService
from xrate.application.state_manager import StateManager

__all__ = ["RatesService", "StateManager"]  # Public API
```

---

## 11. Best Practices

### 1. Use Docstrings
```python
def calculate_price(amount: int, rate: float) -> float:
    """
    Calculate total price.
    
    Args:
        amount: Quantity of items
        rate: Price per item
        
    Returns:
        Total price as float
    """
    return amount * rate
```

### 2. Type Hints
```python
def process_data(data: list[str]) -> dict[str, int]:
    """Always use type hints for clarity."""
    ...
```

### 3. Error Handling
```python
try:
    result = risky_operation()
except SpecificError as e:
    log.error("Specific error occurred: %s", e)
    # Handle appropriately
except Exception as e:
    log.exception("Unexpected error: %s", e)
    # Fallback handling
```

### 4. Logging
```python
import logging

log = logging.getLogger(__name__)

log.debug("Debug message")  # Detailed info
log.info("Info message")  # General info
log.warning("Warning message")  # Warning
log.error("Error message")  # Error
```

**Example from codebase:**
```python
# src/xrate/application/crawler_service.py (line 31)
log = logging.getLogger(__name__)

# Usage
log.info("Successfully fetched prices")
log.warning("Crawler failed, trying fallback")
```

### 5. Constants and Configuration
```python
# Use constants for magic numbers
CACHE_TTL_MINUTES = 15
MAX_RETRIES = 3

# Use settings for configuration
from xrate.config import settings
timeout = settings.http_timeout_seconds
```

### 6. Code Organization
- **Domain Layer**: Pure business logic, no dependencies
- **Application Layer**: Use cases and services
- **Adapters Layer**: External integrations (APIs, databases)
- **Shared Layer**: Utilities and common code

---

## Learning Path

### Beginner Level
1. Start with `src/xrate/domain/models.py` - Simple data structures
2. Study `src/xrate/application/crawler_service.py` - Functions and error handling
3. Look at `src/xrate/adapters/crawlers/base.py` - Classes and inheritance

### Intermediate Level
1. Explore `src/xrate/application/rates_service.py` - Service layer patterns
2. Study `src/xrate/adapters/telegram/jobs.py` - Async programming
3. Review `src/xrate/config/settings.py` - Configuration management

### Advanced Level
1. Analyze `src/xrate/app.py` - Application composition and startup
2. Study test files in `tests/` - Testing patterns
3. Review error handling and logging throughout

---

## Key Concepts Demonstrated

### Object-Oriented Programming
- Classes and inheritance (`BaseCrawler`, `BonbastCrawler`)
- Abstract methods (`@abstractmethod`)
- Encapsulation (private methods with `_` prefix)

### Functional Programming
- Pure functions (`_to_int`)
- Higher-order functions (`partial`)
- Immutable data structures (`@dataclass(frozen=True)`)

### Design Patterns
- **Strategy Pattern**: Different providers for same interface
- **Singleton Pattern**: `state_manager`, `stats_tracker`
- **Factory Pattern**: `build_handlers`
- **Observer Pattern**: Telegram bot callbacks

### Clean Architecture
- Separation of concerns (domain, application, adapters)
- Dependency inversion (interfaces, not implementations)
- Testability (mocked dependencies)

---

## Exercises for Practice

1. **Create a simple crawler**: Extend `BaseCrawler` to crawl a new website
2. **Add a new provider**: Create a new API provider following existing patterns
3. **Write a test**: Add a test case for a function you understand
4. **Refactor code**: Extract duplicate code into a shared function
5. **Add logging**: Add appropriate log statements to a new feature

---

## Resources

- [Python Official Documentation](https://docs.python.org/3/)
- [Real Python Tutorials](https://realpython.com/)
- [Python Type Hints Guide](https://docs.python.org/3/library/typing.html)
- [Async/Await Guide](https://docs.python.org/3/library/asyncio.html)

---

**Happy Learning! 🐍**

This codebase is a great example of production-ready Python code following best practices. Study it, experiment with it, and apply these concepts to your own projects!

