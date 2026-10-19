"""FastAPI — practical single-file examples.

Install:  pip install fastapi "uvicorn[standard]" httpx
Run:      python fastapi_examples.py                 # self-test via TestClient
          uvicorn fastapi_examples:app --reload      # live server + /docs

Demonstrates typed path/query/body parameters, Pydantic models, response
models, dependencies, routers, error handling, lifespan hooks, and testing.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Domain models (Pydantic v2)
# ---------------------------------------------------------------------------
class Genre(str, Enum):
    fiction = "fiction"
    nonfiction = "nonfiction"
    technical = "technical"


class BookBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200, examples=["Refactoring"])
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1450, le=2100)
    genre: Genre = Genre.technical
    price: float = Field(default=0.0, ge=0, le=10_000)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=100)
    year: int | None = Field(default=None, ge=1450, le=2100)
    genre: Genre | None = None
    price: float | None = Field(default=None, ge=0, le=10_000)


class Book(BookBase):
    id: int
    created_at: datetime


class BookList(BaseModel):
    count: int
    items: list[Book]


class Health(BaseModel):
    status: str
    time: datetime
    version: str


# ---------------------------------------------------------------------------
# In-memory store and dependency
# ---------------------------------------------------------------------------
class BookStore:
    def __init__(self) -> None:
        self._books: dict[int, Book] = {}
        self._next_id = 1
        self._seed()

    def _seed(self) -> None:
        samples = [
            BookCreate(title="The Pragmatic Programmer", author="Hunt & Thomas", year=1999, price=39.95),
            BookCreate(title="Designing Data-Intensive Applications", author="Kleppmann", year=2017, price=49.99),
            BookCreate(title="Structure and Interpretation of Computer Programs", author="Abelson & Sussman", year=1985, genre=Genre.nonfiction, price=55.00),
        ]
        for sample in samples:
            self.create(sample)

    def list(self) -> list[Book]:
        return list(self._books.values())

    def get(self, book_id: int) -> Book | None:
        return self._books.get(book_id)

    def create(self, payload: BookCreate) -> Book:
        book = Book(
            id=self._next_id,
            created_at=datetime.now(timezone.utc),
            **payload.model_dump(),
        )
        self._books[book.id] = book
        self._next_id += 1
        return book

    def replace(self, book_id: int, payload: BookCreate) -> Book | None:
        existing = self._books.get(book_id)
        if existing is None:
            return None
        updated = Book(id=book_id, created_at=existing.created_at, **payload.model_dump())
        self._books[book_id] = updated
        return updated

    def update(self, book_id: int, payload: BookUpdate) -> Book | None:
        existing = self._books.get(book_id)
        if existing is None:
            return None
        changes = payload.model_dump(exclude_unset=True)
        updated = existing.model_copy(update=changes)
        self._books[book_id] = updated
        return updated

    def delete(self, book_id: int) -> bool:
        return self._books.pop(book_id, None) is not None


store = BookStore()


def get_store() -> BookStore:
    """Dependency; swap this for a database session in a real app."""
    return store


StoreDep = Annotated[BookStore, Depends(get_store)]


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown work
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("startup: seeding store")
    yield
    print("shutdown: releasing resources")


app = FastAPI(
    title="FastAPI Examples",
    version="1.0.0",
    description="Single-file demonstration of common FastAPI features.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", response_model=Health, tags=["system"])
async def health() -> Health:
    return Health(status="ok", time=datetime.now(timezone.utc), version=app.version)


@app.get("/books", response_model=BookList, tags=["books"])
def list_books(
    store: StoreDep,
    genre: Annotated[Genre | None, Query(description="Filter by genre")] = None,
    min_price: Annotated[float, Query(ge=0, description="Minimum price")] = 0.0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BookList:
    books = [book for book in store.list() if book.price >= min_price]
    if genre is not None:
        books = [book for book in books if book.genre == genre]
    return BookList(count=len(books), items=books[:limit])


@app.get("/books/{book_id}", response_model=Book, tags=["books"])
def get_book(
    store: StoreDep,
    book_id: Annotated[int, Path(ge=1, description="Book identifier")],
) -> Book:
    book = store.get(book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.post(
    "/books",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    tags=["books"],
)
def create_book(payload: BookCreate, store: StoreDep) -> Book:
    duplicate = next(
        (book for book in store.list()
         if book.title.casefold() == payload.title.casefold()
         and book.author.casefold() == payload.author.casefold()),
        None,
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Book already exists")
    return store.create(payload)


@app.put("/books/{book_id}", response_model=Book, tags=["books"])
def replace_book(book_id: int, payload: BookCreate, store: StoreDep) -> Book:
    book = store.replace(book_id, payload)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.patch("/books/{book_id}", response_model=Book, tags=["books"])
def update_book(book_id: int, payload: BookUpdate, store: StoreDep) -> Book:
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(status_code=400, detail="No fields supplied")
    book = store.update(book_id, payload)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["books"])
def delete_book(book_id: int, store: StoreDep) -> None:
    if not store.delete(book_id):
        raise HTTPException(status_code=404, detail="Book not found")


@app.get("/search", response_model=BookList, tags=["books"])
def search(
    store: StoreDep,
    q: Annotated[str, Query(min_length=1, max_length=100, description="Free-text query")],
) -> BookList:
    needle = q.casefold()
    matches = [
        book for book in store.list()
        if needle in book.title.casefold() or needle in book.author.casefold()
    ]
    return BookList(count=len(matches), items=matches)


# ---------------------------------------------------------------------------
# Router with its own prefix and tags
# ---------------------------------------------------------------------------
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/stats")
def admin_stats(store: StoreDep) -> dict:
    books = store.list()
    return {
        "books": len(books),
        "genres": {genre.value: sum(1 for b in books if b.genre == genre) for genre in Genre},
        "average_price": round(sum(book.price for book in books) / len(books), 2) if books else 0.0,
    }


@admin_router.delete("/books", status_code=204)
def clear_books() -> None:
    store._books.clear()  # demonstration only; never expose this in production


app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Self-test without a live server
# ---------------------------------------------------------------------------
def run_demo() -> None:
    with TestClient(app) as client:
        print("GET /health:", client.get("/health").json())

        listing = client.get("/books", params={"limit": 2}).json()
        print("\nfirst two books:", [book["title"] for book in listing["items"]])

        technical = client.get("/books", params={"genre": "technical"}).json()
        print("technical count:", technical["count"])

        created = client.post(
            "/books",
            json={
                "title": "Refactoring",
                "author": "Martin Fowler",
                "year": 2018,
                "genre": "technical",
                "price": 44.5,
            },
        )
        print("\nPOST status:", created.status_code)
        book = created.json()
        print("created:", book["id"], book["title"])

        print("PATCH:", client.patch(f"/books/{book['id']}", json={"price": 41.0}).json()["price"])
        print("PUT:", client.put(
            f"/books/{book['id']}",
            json={"title": "Refactoring (2nd ed.)", "author": "Martin Fowler", "year": 2018, "price": 47.0},
        ).status_code)

        print("\nvalidation error status:", client.post("/books", json={"title": "x"}).status_code)
        print("missing book status:", client.get("/books/9999").status_code)
        print("duplicate status:", client.post(
            "/books",
            json={"title": "Refactoring (2nd ed.)", "author": "Martin Fowler", "year": 2018},
        ).status_code)
        print("search:", client.get("/search", params={"q": "fowler"}).json()["count"])

        print("\nadmin stats:", client.get("/admin/stats").json())
        print("DELETE status:", client.delete(f"/books/{book['id']}").status_code)

        openapi = client.get("/openapi.json").json()
        print("\nOpenAPI title:", openapi["info"]["title"])
        print("documented paths:", len(openapi["paths"]))


def main() -> None:
    print("FastAPI version:", __import__("fastapi").__version__)
    print("Interactive docs: http://127.0.0.1:8000/docs")
    run_demo()
    print("\nAll FastAPI example sections completed.")


if __name__ == "__main__":
    main()
