# Type-Driven Design — Python Examples

Worked Python examples for every technique in the main `SKILL.md`. For Pydantic-based
smart constructors and Python type annotations more broadly, see the `python-development`
skill.

## Technique 1: Newtypes (Branded / Opaque Types)

```python
from typing import NewType

UserID   = NewType('UserID', str)    # mypy enforces distinction
OrderID  = NewType('OrderID', str)

# Runtime enforcement: use a frozen dataclass
@dataclass(frozen=True)
class Email:
    value: str
    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

    @classmethod
    def parse(cls, s: str) -> "Email":
        return cls(value=s)  # __post_init__ validates
```

## Technique 2: Smart Constructors

```python
@dataclass(frozen=True)
class PositiveAmount:
    _value: Decimal  # leading underscore = convention for "don't touch"

    @classmethod
    def of(cls, value: Decimal) -> "PositiveAmount":
        if value <= 0:
            raise ValueError(f"Amount must be positive, got {value}")
        return cls(_value=value)

    @property
    def value(self) -> Decimal: return self._value
```

With Pydantic (recommended for external input):
```python
from pydantic import BaseModel, field_validator

class Email(BaseModel):
    value: str
    model_config = ConfigDict(frozen=True)

    @field_validator("value")
    @classmethod
    def must_be_valid(cls, v: str) -> str:
        if "@" not in v: raise ValueError(f"Invalid email: {v}")
        return v.lower()
```

## Technique 3: Sum Types (Make Invalid States Unrepresentable)

Python 3.10+:
```python
@dataclass(frozen=True)
class Pending:   pass

@dataclass(frozen=True)
class Confirmed: pass

@dataclass(frozen=True)
class Shipped:   pass

@dataclass(frozen=True)
class Cancelled: pass

OrderStatus = Pending | Confirmed | Shipped | Cancelled

def describe(status: OrderStatus) -> str:
    match status:
        case Pending():   return "awaiting confirmation"
        case Confirmed(): return "confirmed"
        case Shipped():   return "on the way"
        case Cancelled(): return "cancelled"
        # mypy warns if a case is missing (with sealed Protocol)
```

Pydantic discriminated unions for API input:
```python
class PendingOrder(BaseModel):
    status: Literal["pending"] = "pending"

class ConfirmedOrder(BaseModel):
    status: Literal["confirmed"] = "confirmed"

class OrderPayload(BaseModel):
    details: PendingOrder | ConfirmedOrder = Field(discriminator="status")
```

## Technique 4: Value Objects

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("amount cannot be negative")
        if self.currency not in ("USD", "EUR", "GBP"):
            raise ValueError(f"unsupported currency: {self.currency}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("currency mismatch")
        return Money(self.amount + other.amount, self.currency)
    # __eq__ and __hash__ provided free by frozen dataclass
```

## Technique 5: Refinement Types (Constrained Primitives)

Pydantic makes this ergonomic:
```python
from pydantic import BaseModel, Field

class OrderItems(BaseModel):
    items: list[OrderItem] = Field(min_length=1)  # non-empty proven at parse time
    model_config = ConfigDict(frozen=True)
```
