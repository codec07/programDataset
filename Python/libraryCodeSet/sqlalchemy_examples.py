"""SQLAlchemy — practical single-file examples.

Install:  pip install sqlalchemy
Run:      python sqlalchemy_examples.py

Uses the SQLAlchemy 2.0 ORM and Core APIs against an in-memory SQLite database.
Covers models and relationships, CRUD, filtering, joins, aggregates, eager
loading, transactions, Core tables, and schema inspection.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    delete,
    event,
    func,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
)


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(50), default="Unknown")

    books: Mapped[list["Book"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Author(id={self.id!r}, name={self.name!r}, country={self.country!r})"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    year: Mapped[int]
    price: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"))
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id", ondelete="CASCADE"))

    author: Mapped[Author] = relationship(back_populates="books")

    def __repr__(self) -> str:
        return f"Book(id={self.id!r}, title={self.title!r}, year={self.year!r})"


# ---------------------------------------------------------------------------
# Engine and session helpers
# ---------------------------------------------------------------------------
def make_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)

    # Enable foreign-key enforcement in SQLite (off by default)
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def seed(session: Session) -> None:
    ada = Author(name="Ada Lovelace", country="UK")
    grace = Author(name="Grace Hopper", country="US")
    edsger = Author(name="Edsger Dijkstra", country="NL")

    ada.books = [
        Book(title="Notes on the Analytical Engine", year=1843, price=Decimal("12.50")),
    ]
    grace.books = [
        Book(title="The Education of a Computer Programmer", year=1959, price=Decimal("18.00")),
        Book(title="COBOL and the Future", year=1960, price=Decimal("15.75")),
    ]
    edsger.books = [
        Book(title="A Discipline of Programming", year=1976, price=Decimal("42.00")),
        Book(title="Selected Writings on Computing", year=1982, price=Decimal("38.25")),
    ]

    session.add_all([ada, grace, edsger])
    session.commit()


# ---------------------------------------------------------------------------
# 1. Create schema and insert
# ---------------------------------------------------------------------------
def setup(engine) -> None:
    section("1. Schema creation and seeding")

    Base.metadata.create_all(engine)
    print("tables:", inspect(engine).get_table_names())

    with Session(engine) as session:
        seed(session)
        count = session.scalar(select(func.count()).select_from(Author))
        print("authors after seed:", count)


# ---------------------------------------------------------------------------
# 2. Querying
# ---------------------------------------------------------------------------
def querying(engine) -> None:
    section("2. ORM queries")

    with Session(engine) as session:
        authors = session.scalars(select(Author).order_by(Author.name)).all()
        print("all authors:")
        for author in authors:
            print(" ", author)

        # Filtering and scalar results
        us_authors = session.scalars(
            select(Author).where(Author.country == "US")
        ).all()
        print("\nUS authors:", us_authors)

        # first() / one() / one_or_none()
        first_book = session.scalars(select(Book).order_by(Book.year)).first()
        print("earliest book:", first_book)

        # Column selection returns rows, not ORM objects
        rows = session.execute(select(Book.title, Book.year).order_by(Book.year)).all()
        print("\ntitle/year rows:", rows)

        # LIKE, IN, BETWEEN, and comparison operators
        modern = session.scalars(
            select(Book).where(Book.year >= 1960, Book.year < 2000).order_by(Book.year)
        ).all()
        print("\nbooks 1960-1999:", modern)

        pattern = session.scalars(
            select(Book).where(Book.title.ilike("%programming%"))
        ).all()
        print("titles containing 'programming':", pattern)

        selected = session.scalars(
            select(Book).where(Book.year.in_([1843, 1959, 1976]))
        ).all()
        print("years in list:", selected)

        # Parameterized text SQL (never interpolate user input)
        raw = session.execute(
            text("SELECT title, year FROM books WHERE year > :year ORDER BY year"),
            {"year": 1970},
        ).all()
        print("\nraw SQL rows:", raw)


# ---------------------------------------------------------------------------
# 3. Relationships and joins
# ---------------------------------------------------------------------------
def relationships(engine) -> None:
    section("3. Relationships, joins, and eager loading")

    with Session(engine) as session:
        # Lazy loading: the relationship is fetched on access
        author = session.scalars(select(Author).where(Author.name == "Grace Hopper")).one()
        print("Grace's books:", [book.title for book in author.books])

        # Explicit join
        rows = session.execute(
            select(Book.title, Author.name)
            .join(Book.author)
            .order_by(Author.name, Book.year)
        ).all()
        print("\nbook/author join:")
        for title, name in rows:
            print(f"  {name:20s} {title}")

        # Eager loading avoids the N+1 query pattern
        authors = session.scalars(
            select(Author).options(selectinload(Author.books)).order_by(Author.name)
        ).all()
        for author in authors:
            print(f"\n{author.name}: {len(author.books)} book(s)")
            print("  total value:", sum(book.price for book in author.books))

        # Aggregate with GROUP BY / HAVING
        stats = session.execute(
            select(
                Author.name,
                func.count(Book.id).label("book_count"),
                func.avg(Book.price).label("avg_price"),
                func.sum(Book.price).label("total_price"),
            )
            .join(Book)
            .group_by(Author.id)
            .having(func.count(Book.id) > 1)
            .order_by(func.sum(Book.price).desc())
        ).all()
        print("\nauthors with more than one book:")
        for name, book_count, avg_price, total_price in stats:
            print(f"  {name}: {book_count} books, avg {avg_price:.2f}, total {total_price:.2f}")


# ---------------------------------------------------------------------------
# 4. Updating and deleting
# ---------------------------------------------------------------------------
def mutations(engine) -> None:
    section("4. Updates, deletes, and transactions")

    with Session(engine) as session:
        book = session.scalars(select(Book).where(Book.title == "COBOL and the Future")).one()
        book.price = Decimal("19.99")
        session.commit()
        print("updated price:", book.price)

        # Bulk update through the ORM
        session.execute(
            update(Book).where(Book.year < 1900).values(price=Book.price + Decimal("1.00"))
        )
        session.commit()
        print("books priced after bulk update:")
        for title, price in session.execute(
            select(Book.title, Book.price).order_by(Book.year)
        ):
            print(f"  {title}: {price}")

        # Delete one row
        session.delete(book)
        session.commit()
        print("\nafter delete, book count:", session.scalar(select(func.count()).select_from(Book)))

        # Transaction rollback: changes are discarded
        original = session.scalar(select(func.count()).select_from(Book))
        try:
            session.add(Book(title="Temporary", year=2026, price=Decimal("1.00"),
                             author_id=session.scalars(select(Author.id)).first()))
            session.flush()
            raise RuntimeError("simulated failure")
        except RuntimeError:
            session.rollback()
        after_rollback = session.scalar(select(func.count()).select_from(Book))
        print("count before/after rollback:", original, after_rollback)

        # Bulk delete with a Core statement
        session.execute(delete(Book).where(Book.year >= 2000))
        session.commit()
        print("remaining books:", session.scalar(select(func.count()).select_from(Book)))


# ---------------------------------------------------------------------------
# 5. Core API
# ---------------------------------------------------------------------------
def core_api(engine) -> None:
    section("5. Core tables and expressions")

    metadata = MetaData()
    metrics = Table(
        "metrics",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(50), nullable=False),
        Column("value", Numeric(10, 2), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            metrics.insert(),
            [
                {"name": "latency_ms", "value": 12.5},
                {"name": "errors", "value": 3},
                {"name": "throughput", "value": 980.0},
            ],
        )

    with engine.connect() as connection:
        rows = connection.execute(select(metrics).order_by(metrics.c.name)).all()
        print("metric rows:")
        for row in rows:
            print(" ", row)

        total = connection.execute(select(func.sum(metrics.c.value))).scalar_one()
        print("sum of values:", total)

        connection.execute(
            update(metrics).where(metrics.c.name == "errors").values(value=2)
        )
        connection.commit()

        updated = connection.execute(
            select(metrics.c.value).where(metrics.c.name == "errors")
        ).scalar_one()
        print("errors after update:", updated)

    print("inspector columns:", [col["name"] for col in inspect(engine).get_columns("metrics")])


# ---------------------------------------------------------------------------
# 6. Dates, ordering, and pagination
# ---------------------------------------------------------------------------
def ordering_and_pagination(engine) -> None:
    section("6. Ordering, limit/offset, and scalar helpers")

    with Session(engine) as session:
        # Re-seed a little data after the delete section
        author = Author(name="Barbara Liskov", country="US")
        author.books = [
            Book(title="Data Abstraction and Hierarchy", year=1987, price=Decimal("22.00")),
            Book(title="Program Development by Stepwise Refinement", year=1971, price=Decimal("17.50")),
        ]
        session.add(author)
        session.commit()

        page = session.scalars(
            select(Book).order_by(Book.year.desc(), Book.title).limit(3).offset(0)
        ).all()
        print("first page:", page)

        max_year = session.scalar(select(func.max(Book.year)))
        min_year = session.scalar(select(func.min(Book.year)))
        print("year range:", min_year, "-", max_year)

        exists = session.scalar(select(func.count()).select_from(Book).where(Book.year == 1987))
        print("books from 1987:", exists)

        # exists() subquery
        from sqlalchemy import exists

        has_books = session.scalar(
            select(exists().where(Book.author_id == author.id))
        )
        print("Barbara has books:", bool(has_books))

        print("as-of date:", date(2026, 10, 19).isoformat())

        # Newest book per author using a correlated scalar subquery
        newest = session.execute(
            select(Author.name, func.max(Book.year).label("newest"))
            .join(Book)
            .group_by(Author.id)
            .order_by(Author.name)
        ).all()
        print("newest book year by author:", newest)


def main() -> None:
    import sqlalchemy

    print("SQLAlchemy version:", sqlalchemy.__version__)
    engine = make_engine()
    setup(engine)
    querying(engine)
    relationships(engine)
    mutations(engine)
    core_api(engine)
    ordering_and_pagination(engine)
    engine.dispose()
    print("\nAll SQLAlchemy example sections completed.")


if __name__ == "__main__":
    main()
