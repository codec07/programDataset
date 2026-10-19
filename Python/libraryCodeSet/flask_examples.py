"""Flask — practical single-file examples.

Install:  pip install flask
Run:      python flask_examples.py            # runs a self-test with test_client
          flask --app flask_examples run        # starts the development server

Demonstrates routing, path converters, query/form/JSON input, responses,
templates, blueprints, error handlers, request hooks, and testing without a
live server.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from flask import (
    Blueprint,
    Flask,
    abort,  # noqa: F401  (shown in comments)
    jsonify,
    make_response,
    redirect,
    render_template_string,
    request,
    url_for,
)

# ---------------------------------------------------------------------------
# In-memory data (replace with a database in real applications)
# ---------------------------------------------------------------------------
@dataclass
class Book:
    id: int
    title: str
    author: str
    year: int

    def to_dict(self) -> dict:
        return asdict(self)


BOOKS: dict[int, Book] = {
    1: Book(1, "Structure and Interpretation of Computer Programs", "Abelson & Sussman", 1985),
    2: Book(2, "The Pragmatic Programmer", "Hunt & Thomas", 1999),
    3: Book(3, "Designing Data-Intensive Applications", "Kleppmann", 2017),
}
NEXT_ID = 4


# ---------------------------------------------------------------------------
# Main routes
# ---------------------------------------------------------------------------
def register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        return jsonify(
            service="flask-examples",
            routes={
                "books": url_for("list_books"),
                "book": url_for("get_book", book_id=1),
                "search": url_for("search"),
                "health": url_for("health"),
                "admin": url_for("admin.dashboard"),
            },
            time=datetime.now(timezone.utc).isoformat(),
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/books")
    def list_books():
        # Query parameters: /books?author=Kleppmann&year=2017
        author = request.args.get("author")
        year = request.args.get("year", type=int)

        results = list(BOOKS.values())
        if author:
            results = [book for book in results if author.lower() in book.author.lower()]
        if year is not None:
            results = [book for book in results if book.year == year]

        return jsonify(count=len(results), books=[book.to_dict() for book in results])

    @app.get("/books/<int:book_id>")
    def get_book(book_id: int):
        book = BOOKS.get(book_id)
        if book is None:
            abort(404, description=f"book {book_id} not found")
        return jsonify(book.to_dict())

    @app.post("/books")
    def create_book():
        global NEXT_ID

        if not request.is_json:
            return jsonify(error="Content-Type must be application/json"), 415

        payload = request.get_json(silent=True) or {}
        missing = [field for field in ("title", "author", "year") if field not in payload]
        if missing:
            return jsonify(error="missing fields", fields=missing), 400

        try:
            year = int(payload["year"])
        except (TypeError, ValueError):
            return jsonify(error="year must be an integer"), 422

        book = Book(NEXT_ID, str(payload["title"]), str(payload["author"]), year)
        BOOKS[book.id] = book
        NEXT_ID += 1

        response = jsonify(book.to_dict())
        response.status_code = 201
        response.headers["Location"] = url_for("get_book", book_id=book.id)
        return response

    @app.put("/books/<int:book_id>")
    def update_book(book_id: int):
        book = BOOKS.get(book_id)
        if book is None:
            return jsonify(error="not found"), 404

        payload = request.get_json(silent=True) or {}
        book.title = payload.get("title", book.title)
        book.author = payload.get("author", book.author)
        if "year" in payload:
            try:
                book.year = int(payload["year"])
            except (TypeError, ValueError):
                return jsonify(error="year must be an integer"), 422
        return jsonify(book.to_dict())

    @app.delete("/books/<int:book_id>")
    def delete_book(book_id: int):
        if BOOKS.pop(book_id, None) is None:
            return jsonify(error="not found"), 404
        return "", 204

    @app.get("/search")
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify(error="query parameter q is required"), 400
        matches = [
            book.to_dict()
            for book in BOOKS.values()
            if query.lower() in f"{book.title} {book.author}".lower()
        ]
        return jsonify(query=query, matches=matches)

    @app.route("/old-books")
    def old_books():
        # Permanent redirect to the canonical URL
        return redirect(url_for("list_books"), code=301)

    @app.route("/files/<path:subpath>")
    def catch_path(subpath: str):
        # <path:...> allows slashes; validate it before touching the filesystem.
        return jsonify(subpath=subpath)

    @app.route("/methods", methods=["GET", "POST", "PUT"])
    def methods():
        return jsonify(method=request.method)

    @app.get("/html")
    def html_page():
        template = """
        <!doctype html>
        <html>
          <head><title>{{ title }}</title></head>
          <body>
            <h1>{{ title }}</h1>
            <ul>
            {% for book in books %}
              <li>{{ loop.index }}. {{ book.title }} ({{ book.year }})</li>
            {% else %}
              <li>No books.</li>
            {% endfor %}
            </ul>
            <p>{{ books|length }} book(s).</p>
          </body>
        </html>
        """
        page = render_template_string(template, title="Book list", books=BOOKS.values())
        response = make_response(page)
        response.headers["X-Example"] = "flask"
        return response

    @app.get("/set-cookie")
    def set_cookie():
        response = make_response(jsonify(message="cookie set"))
        response.set_cookie("example", "value", httponly=True, samesite="Lax")
        return response


# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------
api = Blueprint("api", __name__, url_prefix="/api")
admin = Blueprint("admin", __name__)


@api.get("/ping")
def ping():
    return {"pong": True, "blueprint": "api"}


@api.get("/books")
def api_books():
    return jsonify([book.to_dict() for book in BOOKS.values()])


@admin.get("/")
def dashboard():
    return jsonify(section="admin", books=len(BOOKS), env=request.path)


# ---------------------------------------------------------------------------
# Hooks and error handlers
# ---------------------------------------------------------------------------
def register_hooks(app: Flask) -> None:
    @app.before_request
    def stamp_start() -> None:
        request.start_time = datetime.now(timezone.utc)  # type: ignore[attr-defined]

    @app.after_request
    def add_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Example-App"] = "flask_examples"
        return response

    @app.teardown_request
    def log_teardown(exc: BaseException | None) -> None:
        if exc is not None:
            app.logger.warning("request failed: %s", exc)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(error="not_found", message=str(getattr(error, "description", error))), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify(error="method_not_allowed", path=request.path), 405

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify(error="bad_request", message=str(error)), 400

    @app.errorhandler(500)
    def server_error(error):
        return jsonify(error="internal_server_error"), 500


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------
def build_app() -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="dev-only", JSON_SORT_KEYS=False)
    register_routes(app)
    app.register_blueprint(api)
    app.register_blueprint(admin, url_prefix="/admin")
    register_hooks(app)
    register_error_handlers(app)
    return app


app = build_app()


# ---------------------------------------------------------------------------
# Self-test without a network server
# ---------------------------------------------------------------------------
def demo_with_test_client() -> None:
    client = app.test_client()

    print("GET /:", client.get("/").get_json()["service"])
    print("GET /health:", client.get("/health").get_json())

    listing = client.get("/books?author=Klepp")
    print("\nfiltered books:", listing.get_json())

    created = client.post(
        "/books",
        json={"title": "Refactoring", "author": "Fowler", "year": 2018},
    )
    print("\nPOST /books status:", created.status_code, "location:", created.headers.get("Location"))
    new_id = created.get_json()["id"]

    print("GET new book:", client.get(f"/books/{new_id}").get_json())
    print("PUT new book:", client.put(f"/books/{new_id}", json={"year": 2019}).get_json())
    print("DELETE new book status:", client.delete(f"/books/{new_id}").status_code)
    print("GET deleted status:", client.get(f"/books/{new_id}").status_code)

    print("\nmissing book:", client.get("/books/9999").get_json())
    print("bad payload:", client.post("/books", json={"title": "x"}).status_code)
    print("wrong content type:", client.post("/books", data="x").status_code)
    print("method not allowed:", client.patch("/books").status_code)

    print("\nblueprint /api/ping:", client.get("/api/ping").get_json())
    print("admin dashboard:", client.get("/admin/").get_json())
    print("search:", client.get("/search?q=pragmatic").get_json())

    html = client.get("/html")
    print("\nHTML status:", html.status_code, "content-type:", html.content_type)
    print("HTML contains books:", b"Pragmatic" in html.data)
    print("security header:", html.headers.get("X-Content-Type-Options"))

    redirect_response = client.get("/old-books")
    print("\nredirect status:", redirect_response.status_code, "location:", redirect_response.headers.get("Location"))


def main() -> None:
    print("Flask version:", __import__("flask").__version__)
    print("routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda item: str(item)):
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        print(f"  {methods:18s} {rule}")

    demo_with_test_client()
    print("\nTo run the live development server:")
    print("  flask --app flask_examples run --debug")


if __name__ == "__main__":
    main()
