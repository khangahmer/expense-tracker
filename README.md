# Expense Tracker API

A small REST service for recording personal expenses. It stores expenses in PostgreSQL, validates every request, returns a consistent JSON error format, and can convert an expense into another currency using a free public exchange-rate API (Frankfurter). It contains no AI or LLM component.

Built with Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL and Docker.

## Features

- Create, read, update (partial), delete and list expenses, with filtering and pagination
- Money stored as integer minor units (no floating-point errors)
- Currency conversion through an external API, called asynchronously with a timeout
- One error format for every failure: validation errors, missing resources, upstream-service failures and unexpected server errors
- Database migrations with Alembic
- Automated tests against a real PostgreSQL test database, with the external API mocked
- Configuration through environment variables, and application logging

## Endpoints

Interactive documentation is served at `/docs` (Swagger UI) and `/redoc`; the raw schema is at `/openapi.json`.

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| GET | `/health` | Liveness check | 200 |
| POST | `/expenses` | Create an expense | 201 |
| GET | `/expenses` | List expenses. Query: `category`, `limit` (1-200, default 50), `offset` (default 0) | 200 |
| GET | `/expenses/{id}` | Get one expense | 200 |
| PATCH | `/expenses/{id}` | Update only the fields you send | 200 |
| DELETE | `/expenses/{id}` | Delete an expense | 204 (no body) |
| GET | `/expenses/{id}/converted?to=EUR` | Convert the expense into another currency | 200 |

### Expense fields

| Field | Type | Rules |
|-------|------|-------|
| `description` | string | Required. 1-200 characters; surrounding whitespace is trimmed, so blank is rejected |
| `amount_minor` | integer | Required. Greater than 0. In minor units: `45050` means 450.50 |
| `category` | string | Optional, 1-50 characters, default `other` |
| `currency` | string | Optional, three uppercase letters, default `USD` |
| `notes` | string or null | Optional, up to 500 characters |
| `id` | integer | Read-only. Assigned by the server |
| `created_at` | datetime | Read-only. Assigned by the database (UTC) |

Fields the server controls are ignored if a client sends them.

## Requirements

- Python 3.12 or newer
- Docker with Docker Compose (runs PostgreSQL)
- Git

## Quick start

**1. Clone the repository**

```
git clone https://github.com/khangahmer/expense-tracker.git
cd expense-tracker
```

**2. Create and activate a virtual environment**

Windows (PowerShell):

```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` and activate again.

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```
pip install -r requirements-dev.txt
```

(`requirements.txt` alone contains only what the app needs to run; `requirements-dev.txt` adds the test and lint tools.)

**4. Create your settings file**

Windows (PowerShell):

```
Copy-Item .env.example .env
```

macOS / Linux:

```
cp .env.example .env
```

The defaults match `docker-compose.yml`, so no edits are needed for local development.

**5. Start PostgreSQL**

```
docker compose up -d
```

On its first start, this creates two databases: `expenses` (the app) and `expenses_test` (the tests). Wait about 10 seconds for PostgreSQL to finish starting; `docker compose ps` should show the `db` service as running.

**6. Create the tables**

```
alembic upgrade head
```

**7. Run the API**

```
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs, or check from a second terminal:

```
curl http://127.0.0.1:8000/health
```

(On Windows PowerShell, type `curl.exe` instead of `curl`; plain `curl` is a different command.)

## Using the API

### Create an expense

macOS / Linux:

```
curl -i -X POST http://127.0.0.1:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"description": "Lunch", "amount_minor": 45050, "category": "food"}'
```

Windows (PowerShell). JSON quoting is awkward in PowerShell, so put the body in a file:

```
Set-Content -Path lunch.json -Value '{"description": "Lunch", "amount_minor": 45050, "category": "food"}'
curl.exe -i -X POST http://127.0.0.1:8000/expenses -H "Content-Type: application/json" -d "@lunch.json"
```

Response (`201 Created`; `id` and `created_at` will differ):

```json
{
  "description": "Lunch",
  "amount_minor": 45050,
  "category": "food",
  "notes": null,
  "currency": "USD",
  "id": 1,
  "created_at": "2026-10-28T11:04:13.682848Z"
}
```

### Read, list, update, delete

```
curl http://127.0.0.1:8000/expenses/1
curl "http://127.0.0.1:8000/expenses?category=food&limit=10&offset=0"
curl -X DELETE -i http://127.0.0.1:8000/expenses/1
```

A partial update sends only what changes (PowerShell users: use a JSON file as above):

```
curl -X PATCH http://127.0.0.1:8000/expenses/1 \
  -H "Content-Type: application/json" \
  -d '{"amount_minor": 50000}'
```

### Convert to another currency

```
curl "http://127.0.0.1:8000/expenses/1/converted?to=EUR"
```

```json
{
  "expense_id": 1,
  "original_amount_minor": 45050,
  "original_currency": "USD",
  "target_currency": "EUR",
  "rate": "0.89509",
  "converted_amount_minor": 40324
}
```

(Example values; rates change daily.) `rate` is a string on purpose, so no client parses it as an imprecise float. The converted amount is rounded half-up to a whole minor unit. If the expense is already in the target currency, no external call is made and the rate is `"1"`.

## Error format

Every error response has the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {"field": "body.amount_minor", "message": "Input should be greater than 0"}
    ]
  }
}
```

`details` is present only when there is extra information to give.

| Situation | Status | `code` |
|-----------|--------|--------|
| Invalid body, path or query parameter | 422 | `validation_error` |
| Expense does not exist | 404 | `not_found` |
| Unknown route or wrong method | 404 / 405 | `http_404` / `http_405` |
| Duplicate of a unique value | 409 | `conflict` |
| Database unreachable | 503 | `database_unavailable` |
| Currency the exchange-rate service does not support | 422 | `unsupported_currency` |
| Exchange-rate service unreachable | 502 | `upstream_unavailable` |
| Exchange-rate service returned an error | 502 | `upstream_error` |
| Exchange-rate service sent unusable data | 502 | `upstream_bad_response` |
| Exchange-rate service too slow | 504 | `upstream_timeout` |
| Any unexpected failure | 500 | `internal_error` |

For `internal_error`, the response never contains the exception text. It contains an `error_id` in `details`, and the full traceback is written to the server log under the same id, so a reported id can be matched to its log entry.

## Configuration

Settings are read from environment variables, or from a `.env` file in the project root. Real environment variables take precedence over `.env`. The `.env` file is ignored by Git; `.env.example` shows every setting.

| Variable | Required | Default | Meaning |
|----------|----------|---------|---------|
| `DATABASE_URL` | yes | none | SQLAlchemy URL, e.g. `postgresql+psycopg://user:password@host:5432/dbname` |
| `LOG_LEVEL` | no | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `FX_BASE_URL` | no | `https://api.frankfurter.dev/v1` | Base URL of the exchange-rate API |
| `FX_TIMEOUT_SECONDS` | no | `5.0` | Timeout for each exchange-rate request |
| `TEST_DATABASE_URL` | tests only | local `expenses_test` database | Database used by the test suite |

The password in `docker-compose.yml` and `.env.example` is for local development only. Never commit a real secret.

## Database migrations

The schema is managed by Alembic. After changing `app/models.py`:

```
alembic revision --autogenerate -m "describe the change"
```

Read the generated file in `alembic/versions/` before applying it (autogenerate is a draft, not a guarantee), then:

```
alembic upgrade head      # apply
alembic downgrade -1      # undo the last migration
alembic current           # which migration this database is at
```

## Running the checks

With the virtual environment active and the database container running:

```
ruff check .
ruff format --check .
mypy
pytest -q
```

On Windows, `.\scripts\check.ps1` runs all four in order and stops at the first failure.

The tests use a separate PostgreSQL database (`expenses_test`) and rebuild its tables from the real migrations, so migrations are tested too. Each test starts from an empty table. The test setup refuses to run against any database whose name does not end in `_test`. The exchange-rate API is mocked with `respx`, which also makes any unmocked network call fail the test, so the suite never touches the internet.

If tests report that `expenses_test` does not exist (it was not created because your database volume predates the init script), create it once:

```
docker compose exec db psql -U expense -d expenses -c "CREATE DATABASE expenses_test;"
```

## Project structure

```
.
├── app/
│   ├── main.py          # routes and dependencies
│   ├── config.py        # settings from environment variables
│   ├── database.py      # engine and session factory
│   ├── models.py        # SQLAlchemy table definitions
│   ├── schemas.py       # Pydantic request/response models
│   ├── errors.py        # error format and exception handlers
│   └── fx.py            # async exchange-rate client
├── alembic/             # database migrations
├── tests/
│   ├── conftest.py      # test database and shared fixtures
│   ├── test_expenses.py
│   └── test_conversion.py
├── scripts/check.ps1    # runs every check (Windows)
├── docker/initdb/       # creates the test database on first start
├── docker-compose.yml   # local PostgreSQL
├── alembic.ini
├── pyproject.toml       # ruff and mypy configuration
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Design decisions and known limitations

- **Money is stored as integers in minor units**, never as floats. `0.1 + 0.2` is not `0.3` in floating point, which is unacceptable for money.
- **Every currency is assumed to have two decimal places.** That is wrong for some (JPY has none, KWD has three). Handling it would need a per-currency table.
- **Conversion uses Frankfurter's v1 API** (European Central Bank reference rates, around 33 currencies, updated on working days). These are indicative daily rates, not live trading rates. PKR is not available in v1.
- **Currency codes are checked for format only** (three uppercase letters). Whether the currency is supported is decided by the exchange-rate service, and unsupported codes return a 422.
- **Categories are free text and case-sensitive**: `food` and `Food` are different categories.
- **Pagination uses `limit` and `offset`** and does not return a total count.
- **A new HTTP client is created for each conversion request.** It is simple and correct; a shared client would reuse connections.
- **There is no authentication or authorization.** Anyone who can reach the API can read and change every expense, so it is not suitable for public multi-user use as it stands.
- **Unexpected database constraint violations return a generic 500**, not a 4xx, because reaching a database `CHECK` means the API's own validation missed something, which is the server's fault.
- **Two layers of validation on purpose**: Pydantic rejects bad input at the front door, and database constraints (`CHECK`, `NOT NULL`) remain the last line of defense.

## Docker image and deployment

<!-- TODO (Lessons 14-15): document building the app image, running the full
     stack with Docker Compose, the public URL, required environment variables
     on the host, and how the deployed API was verified. -->

Not yet documented.

## AI-assisted development

<!-- TODO (Lesson 16): note which parts were built with a coding agent, how each
     change was reviewed through its Git diff and validated (tests, mypy, ruff,
     logs, manual calls), and link to the written account of one agent failure. -->

Not yet documented.