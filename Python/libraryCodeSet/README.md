# libraryCodeSet — examples for popular Python libraries

> ## ⚠️ STRICT NOTICE — READ THIS FIRST
>
> **These files are illustrative examples, NOT a tested library.**
>
> - They have **not been tested line-by-line**, and they have **not been executed
>   against every supported library version**.
> - Only **syntax compilation** was performed when they were added. Runtime
>   behaviour depends on the library versions you install.
> - Library APIs change. A call that is correct for one version may warn, change,
>   or fail on another. **Check the installed version before assuming a bug.**
> - Some examples are intentionally simplified: no authentication, no database
>   migrations, no production error handling, no security hardening.
> - Do **not** copy these into production without review, tests, and version
>   pinning.
>
> Each file is nevertheless written to be **run individually**, is self-contained,
> and has a `main()` that walks through its examples. Run a file, read the output,
> and adapt it. If it fails, inspect the traceback and the library version first.

---

## What is in this folder

15 single-file examples covering libraries that appear constantly in Python
work. Each file is a guided tour with runnable sections, not a snippet dump.

| File | Library | Focus | Extra requirements |
|---|---|---|---|
| [`numpy_examples.py`](numpy_examples.py) | NumPy | arrays, broadcasting, linalg, FFT, persistence | numpy |
| [`pandas_examples.py`](pandas_examples.py) | pandas | Series/DataFrame, cleaning, groupby, merges, time series, I/O | pandas, numpy |
| [`matplotlib_examples.py`](matplotlib_examples.py) | Matplotlib | line/scatter/bar/distribution plots, subplots, annotations, export | matplotlib, numpy |
| [`seaborn_examples.py`](seaborn_examples.py) | Seaborn | relational, categorical, distribution, matrix, facet plots | seaborn, pandas, matplotlib |
| [`scipy_examples.py`](scipy_examples.py) | SciPy | integration, optimization, interpolation, stats, signals, sparse | scipy, numpy |
| [`sklearn_examples.py`](sklearn_examples.py) | scikit-learn | preprocessing, classification, regression, clustering, PCA, tuning | scikit-learn, pandas, numpy |
| [`requests_examples.py`](requests_examples.py) | requests | sessions, verbs, retries, streaming, auth, errors | requests + internet |
| [`bs4_examples.py`](bs4_examples.py) | Beautiful Soup | parsing, selectors, navigation, tables, tree editing | beautifulsoup4 (lxml optional) |
| [`flask_examples.py`](flask_examples.py) | Flask | routes, JSON APIs, blueprints, hooks, error handlers, test client | flask |
| [`fastapi_examples.py`](fastapi_examples.py) | FastAPI | typed routes, Pydantic models, dependencies, routers, TestClient | fastapi, httpx |
| [`sqlalchemy_examples.py`](sqlalchemy_examples.py) | SQLAlchemy | ORM 2.0 models, relationships, joins, transactions, Core | sqlalchemy |
| [`pytest_examples.py`](pytest_examples.py) | pytest | assertions, fixtures, parametrize, tmp_path, monkeypatch, marks | pytest |
| [`pillow_examples.py`](pillow_examples.py) | Pillow | drawing, geometry, filters, blending, text, GIF | pillow |
| [`openpyxl_examples.py`](openpyxl_examples.py) | openpyxl | styling, formulas, charts, validation, conditional formats, read-back | openpyxl |
| [`pydantic_examples.py`](pydantic_examples.py) | Pydantic v2 | models, validators, nested/discriminated models, serialization, schema | pydantic |

## Quick start

Use a virtual environment so these libraries do not pollute your system Python.

```powershell
cd Python\libraryCodeSet
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run any single example
python numpy_examples.py
python pandas_examples.py
python bs4_examples.py
```

On macOS/Linux the activation command is `source .venv/bin/activate`.

Install only what you need if you prefer a smaller environment:

```powershell
pip install numpy pandas matplotlib
pip install fastapi "uvicorn[standard]" httpx
```

## Running notes

- **Working directory:** run each file directly (`python numpy_examples.py`).
  Matplotlib, Pillow, openpyxl, and the streaming request example write into
  `output/`, which is git-ignored.
- **Headless plotting:** Matplotlib and Seaborn force the `Agg` backend and save
  PNG/PDF/SVG files. Delete the `matplotlib.use("Agg")` line for interactive
  windows.
- **Network:** `requests_examples.py` uses `https://httpbin.org` and degrades
  gracefully when offline. Everything else runs offline.
- **Seaborn datasets:** the file generates its own DataFrame. If you want the
  classic `tips`/`penguins` datasets, `sns.load_dataset("tips")` downloads them
  from GitHub on first use.
- **Flask / FastAPI:** each file self-tests with the framework's test client and
  exits. To start a real server:
  - `flask --app flask_examples run --debug`
  - `uvicorn fastapi_examples:app --reload`
- **pytest:** run `pytest pytest_examples.py -v`, or `python pytest_examples.py`.
- **SQLAlchemy:** uses an in-memory SQLite database; nothing is written to disk.
- **Pillow / openpyxl:** outputs go to `output/` and can be opened normally.

## Version assumptions

The examples target reasonably current releases:

| Library | Assumed API family |
|---|---|
| NumPy | 1.26+ / 2.x |
| pandas | 2.2+ (`resample("ME")`, nullable dtypes) |
| Matplotlib | 3.8+ (`tick_labels`, `Figure` OO API) |
| Seaborn | 0.13+ (`errorbar=`, `map_dataframe`) |
| SciPy | 1.11+ (`integrate.trapezoid`, `solve_ivp`) |
| scikit-learn | 1.4+ (`sparse_output=`, `n_init=`) |
| requests | 2.31+ (urllib3 2.x retry API) |
| Flask | 3.x |
| FastAPI | 0.110+ with Pydantic v2 |
| SQLAlchemy | 2.0+ (`DeclarativeBase`, `Mapped`) |
| Pydantic | 2.6+ (v2 API only) |
| Pillow | 10+ (`Image.Resampling`, `Image.Transpose`) |
| openpyxl | 3.1+ |

If a line fails, compare the installed version with this table before filing it
as a bug in the example.

## Status and limitations

- **Compiled:** all 15 files pass `python -m py_compile`.
- **Runtime-tested:** no. Dependencies are optional and were not installed as
  part of the dataset build. Treat runtime output as unverified.
- **Coverage:** each file shows the most common 20% of each library, not the
  entire API. There are no exhaustive parameter matrices.
- **Security:** the Flask/FastAPI examples use development settings and an
  in-memory store. Never deploy them as-is.
- **Data:** sample data is synthetic or built into the library, except the
  `httpbin.org` requests. No personal or scraped data is included.

This folder is therefore best used for **reading, teaching, and prompting**, and
for training code models on *library usage patterns* — not as a correctness
oracle or a test suite.
