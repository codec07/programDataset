"""Pydantic — practical single-file examples (v2 API).

Install:  pip install pydantic
Run:      python pydantic_examples.py

Covers BaseModel, Field constraints, validators, computed fields, nested and
discriminated models, serialization, JSON Schema, TypeAdapter, aliases,
immutable models, and validation error handling.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    TypeAdapter,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic import StringConstraints


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Basic models and field constraints
# ---------------------------------------------------------------------------
class User(BaseModel):
    """A user record with built-in validation."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    id: int = Field(gt=0, description="Positive database identifier")
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    age: int = Field(ge=13, le=130)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    active: bool = True


def basics() -> None:
    section("1. Construction and validation")

    user = User(id=1, name="  Ada Lovelace  ", email="ada@example.com", age=36, score=97.5)
    print("user:", user)
    print("name stripped:", repr(user.name))
    print("as dict:", user.model_dump())
    print("as JSON:", user.model_dump_json(indent=2))

    # Coercion: strings that look like numbers are converted
    coerced = User(id="2", name="Linus", email="linus@example.com", age="54")
    print("\ncoerced id/age:", coerced.id, type(coerced.id).__name__, coerced.age)

    # Validation errors are collected per field
    try:
        User(id=0, name="X", email="not-an-email", age=200, extra_field="nope")
    except ValidationError as exc:
        print("\nvalidation failed with", exc.error_count(), "errors")
        for error in exc.errors():
            print(" ", error["loc"], error["type"], "-", error["msg"])

    # model_copy for partial updates
    updated = user.model_copy(update={"score": 88.0})
    print("\nupdated copy:", updated.score, "original:", user.score)

    # Equality is value-based
    print("same values equal:", user == User(**user.model_dump()))


# ---------------------------------------------------------------------------
# 2. Validators
# ---------------------------------------------------------------------------
class Account(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str
    password_confirm: str
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator("username")
    @classmethod
    def username_must_be_alphanumeric(cls, value: str) -> str:
        if not value.replace("_", "").isalnum():
            raise ValueError("username may contain only letters, digits, and underscores")
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        if not any(char.isdigit() for char in value):
            raise ValueError("password must contain a digit")
        if not any(char.isalpha() for char in value):
            raise ValueError("password must contain a letter")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("password_confirm does not match password")
        return self

    @computed_field
    @property
    def is_wealthy(self) -> bool:
        return self.balance >= Decimal("100000")


def validators() -> None:
    section("2. Field and model validators")

    account = Account(
        username="Ada_2026",
        password="Secure123",
        password_confirm="Secure123",
        balance=Decimal("250000.00"),
    )
    print("username normalized:", account.username)
    print("computed is_wealthy:", account.is_wealthy)
    print("serialized:\n", account.model_dump_json(indent=2))

    for payload in (
        {"username": "bad name", "password": "Secure123", "password_confirm": "Secure123"},
        {"username": "ada", "password": "short", "password_confirm": "short"},
        {"username": "ada", "password": "Secure123", "password_confirm": "Different1"},
    ):
        try:
            Account(**payload)
        except ValidationError as exc:
            print("\nexpected failure:", exc.errors()[0]["msg"])


# ---------------------------------------------------------------------------
# 3. Nested models
# ---------------------------------------------------------------------------
class Address(BaseModel):
    street: str
    city: str
    country: str = "US"
    postal_code: str = Field(pattern=r"^\d{5}(-\d{4})?$")


class Customer(BaseModel):
    id: int
    name: str
    address: Address
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


def nested() -> None:
    section("3. Nested models and collections")

    customer = Customer(
        id=7,
        name="Grace Hopper",
        address={"street": "1 Compiler Way", "city": "Arlington", "postal_code": "22201"},
        tags=["vip", "early-adopter"],
        metadata={"source": "conference"},
    )
    print(customer)
    print("\ncity:", customer.address.city)
    print("tags:", customer.tags)
    print("nested dump:", customer.model_dump())

    # Nested JSON round-trip
    restored = Customer.model_validate_json(customer.model_dump_json())
    print("round-trip equal:", restored == customer)

    # List validation
    customers = TypeAdapter(list[Customer]).validate_python([customer.model_dump()])
    print("adapter parsed customers:", len(customers))


# ---------------------------------------------------------------------------
# 4. Enums, literals, and discriminated unions
# ---------------------------------------------------------------------------
class Plan(str, Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class CardPayment(BaseModel):
    method: Literal["card"]
    last4: str = Field(pattern=r"^\d{4}$")
    brand: Literal["visa", "mastercard", "amex"]


class BankPayment(BaseModel):
    method: Literal["bank"]
    iban: str = Field(min_length=15, max_length=34)
    country: str = Field(min_length=2, max_length=2)


class Invoice(BaseModel):
    id: int
    plan: Plan = Plan.free
    amount: Decimal = Field(gt=0)
    payment: Annotated[CardPayment | BankPayment, Discriminator("method")]


def unions() -> None:
    section("4. Enums, literals, and discriminated unions")

    card = Invoice(
        id=1,
        plan="pro",
        amount=Decimal("49.00"),
        payment={"method": "card", "last4": "4242", "brand": "visa"},
    )
    bank = Invoice.model_validate(
        {
            "id": 2,
            "plan": "enterprise",
            "amount": 999,
            "payment": {"method": "bank", "iban": "DE89370400440532013000", "country": "DE"},
        }
    )
    print("card payment type:", type(card.payment).__name__, card.payment)
    print("bank payment type:", type(bank.payment).__name__, bank.payment)
    print("plan value:", card.plan.value, "is enum:", isinstance(card.plan, Plan))

    try:
        Invoice(
            id=3,
            amount=10,
            payment={"method": "crypto", "wallet": "abc"},
        )
    except ValidationError as exc:
        print("\ninvalid union rejected:", exc.errors()[0]["type"])


# ---------------------------------------------------------------------------
# 5. Aliases and population options
# ---------------------------------------------------------------------------
class ApiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    status_code: int = Field(alias="statusCode")
    body: dict | None = None


def aliases() -> None:
    section("5. Aliases")

    response = ApiResponse.model_validate({"requestId": "abc-123", "statusCode": 200})
    print("parsed by alias:", response)
    print("dump by field name:", response.model_dump())
    print("dump by alias:", response.model_dump(by_alias=True))
    print("dump JSON by alias:", response.model_dump_json(by_alias=True))


# ---------------------------------------------------------------------------
# 6. Immutable and strict models
# ---------------------------------------------------------------------------
class Point(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: float
    y: float


class StrictPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    count: int
    ratio: float
    label: str


def immutability() -> None:
    section("6. Frozen and strict models")

    point = Point(x=1.0, y=2.0)
    print("point:", point, "hash:", hash(point))
    try:
        point.x = 5.0
    except ValidationError as exc:
        print("frozen assignment rejected:", exc.errors()[0]["type"])

    strict = StrictPayload(count=3, ratio=0.5, label="ok")
    print("\nstrict parsed:", strict)
    try:
        StrictPayload(count="3", ratio=1, label="bad")
    except ValidationError as exc:
        print("strict rejected string count:", exc.errors()[0]["type"])


# ---------------------------------------------------------------------------
# 7. TypeAdapter and schema generation
# ---------------------------------------------------------------------------
OrderId = Annotated[str, StringConstraints(pattern=r"^ORD-\d{6}$", to_upper=True)]


def adapters_and_schema() -> None:
    section("7. TypeAdapter and JSON Schema")

    order_adapter = TypeAdapter(OrderId)
    print("normalized order id:", order_adapter.validate_python("ord-123456"))

    try:
        order_adapter.validate_python("123456")
    except ValidationError as exc:
        print("invalid order id:", exc.errors()[0]["msg"])

    numbers = TypeAdapter(list[Annotated[int, Field(gt=0)]])
    print("validated list:", numbers.validate_python(["1", 2, 3]))
    print("JSON schema:", numbers.json_schema())

    print("\nUser JSON Schema:")
    import json

    print(json.dumps(User.model_json_schema(), indent=2)[:900])

    print("\nInvoice schema title:", Invoice.model_json_schema().get("title"))


# ---------------------------------------------------------------------------
# 8. Validation helpers
# ---------------------------------------------------------------------------
def validation_helpers() -> None:
    section("8. Safe parsing helpers")

    def parse_user(data: dict) -> tuple[User | None, list[str]]:
        try:
            return User.model_validate(data), []
        except ValidationError as exc:
            messages = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in exc.errors()]
            return None, messages

    good, errors = parse_user(
        {"id": 10, "name": "Alan Turing", "email": "alan@example.com", "age": 41}
    )
    print("good user:", good.name if good else None, "errors:", errors)

    bad, errors = parse_user({"id": -1, "name": "A", "email": "bad", "age": 5})
    print("\nbad user:", bad)
    for message in errors:
        print(" -", message)

    # model_construct skips validation: useful only for trusted data
    trusted = User.model_construct(id=11, name="Trusted", email="trusted@example.com", age=30)
    print("\nmodel_construct skips validation:", trusted.id, trusted.email)


def main() -> None:
    import pydantic

    print("pydantic version:", pydantic.__version__)
    basics()
    validators()
    nested()
    unions()
    aliases()
    immutability()
    adapters_and_schema()
    validation_helpers()

    print("\nAll Pydantic example sections completed.")


if __name__ == "__main__":
    main()
