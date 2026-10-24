# Urja Meter Ops Adapter

This project is a read-only REST API adapter for the legacy Urja Meter Ops portal. It authenticates to the portal using the actual browser-based login flow, preserves the upstream session, and exposes clean JSON endpoints for searching meters, fetching details, and reading consumption history.

## Problem statement

The legacy portal is a browser UI intended for internal operations. Downstream systems need a stable API contract without depending on brittle HTML scraping or direct browser automation. This project wraps the legacy portal in a small FastAPI service and exposes a documented API under `/api/v1`.

## Features

- Server-side login to the upstream portal using the discovered same-origin flow
- Session cookie preservation through a single httpx client
- Search endpoint for meters with pagination
- Meter detail endpoint with normalized metadata
- Consumption endpoint returning parsed readings
- Validation, timeout, and upstream error translation
- Auto-generated OpenAPI schema and Swagger UI

## Architecture and data flow

The service uses a narrow adapter pattern:

1. FastAPI receives a request and validates input.
2. The service layer calls the portal client.
3. The client handles upstream authentication and session management.
4. The portal client fetches `/login`, `/portal/meters/search`, `/portal/meters/{id}/geo`, and `/portal/meters/{id}/energy`.
5. Meter details are normalized from the server-rendered HTML page and the geo response.
6. API responses are returned as consistent JSON with sanitized error envelopes.

## Repository structure

```text
.
├── app/
│   ├── __init__.py
│   ├── client.py
│   ├── config.py
│   ├── exceptions.py
│   ├── main.py
│   ├── models.py
│   └── services.py
├── docs/
│   └── example-responses.json
├── tests/
│   ├── test_error_handling.py
│   ├── test_health.py
│   └── test_meters.py
├── .env.example
├── .gitignore
├── PROTOCOL.md
├── README.md
├── REFLECTION.md
├── requirements.txt
├── openapi.json
└── app.py
```

## Technology stack

- Python 3.10+
- FastAPI
- Uvicorn
- httpx
- BeautifulSoup4
- Pydantic
- python-dotenv
- pytest

## Prerequisites

- Python 3.10+
- pip
- Network access to https://urja-ops.flockenergy.tech

## Windows PowerShell setup

```powershell
cd "C:\Users\KUSUMA\OneDrive\Desktop\Engineering take home"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Then set the environment variables in `.env`:

```env
URJA_BASE_URL=https://urja-ops.flockenergy.tech
URJA_USERNAME=operator@urja.local
URJA_PASSWORD=your-password-here
REQUEST_TIMEOUT=10
LOG_LEVEL=INFO
```

## macOS/Linux setup

```bash
cd /path/to/Engineering\ take\ home
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

## How to start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service exposes:

- http://localhost:8000/docs
- http://localhost:8000/redoc
- http://localhost:8000/openapi.json

## How to run automated tests

```bash
pytest -q
```

## Implemented API endpoints

### GET /health

Returns the adapter status.

### POST /api/v1/auth/login

Body:

```json
{
  "email": "operator@urja.local",
  "password": "your-password-here"
}
```

The endpoint falls back to environment variables if the request body omits values.

### GET /api/v1/meters

Query parameters:

- `q` (optional, string)
- `page` (optional, integer >= 1)

Example:

```bash
curl "http://localhost:8000/api/v1/meters?q=&page=1"
```

### GET /api/v1/meters/{meter_id}

Example:

```bash
curl http://localhost:8000/api/v1/meters/J100000
```

### GET /api/v1/meters/{meter_id}/consumption

Example:

```bash
curl http://localhost:8000/api/v1/meters/J100000/consumption
```

### GET /api/v1/hierarchy

Returns a small normalized hierarchy payload assembled from the upstream meter metadata.

## Sample curl requests

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"operator@urja.local","password":"your-password-here"}'
curl "http://localhost:8000/api/v1/meters?q=&page=1"
curl http://localhost:8000/api/v1/meters/J100000
curl http://localhost:8000/api/v1/meters/J100000/consumption
```

## Sample Python requests

```python
import requests

base = 'http://localhost:8000'
print(requests.get(f'{base}/health').json())
print(requests.post(f'{base}/api/v1/auth/login', json={
    'email': 'operator@urja.local',
    'password': 'your-password-here',
}).json())
print(requests.get(f'{base}/api/v1/meters', params={'q': '', 'page': 1}).json())
```

## OpenAPI and Swagger docs

- docs: http://localhost:8000/docs
- redoc: http://localhost:8000/redoc
- schema: http://localhost:8000/openapi.json

## Authentication and security considerations

- No secrets are returned in API responses.
- Session cookies are kept server-side inside the upstream client.
- Environment variables are used for credentials, not hardcoded values.
- The service avoids exposing raw HTML error pages or full upstream payloads.
- Upstream authentication is treated as a critical dependency and is validated before returning service data.

## Assumptions

- The portal behaves as a browser-authenticated read-only app rather than a pure JSON API.
- The same-origin login flow is the supported path for establishing a session.
- The meter detail page contains enough embedded metadata to reconstruct a reliable normalized detail record.
- The energy endpoint exposes all consumption values without a dedicated time-range filter.

## Design decisions and trade-offs

This adapter favors a simple, explicit shape over complex generic parsing. It keeps authentication, upstream transport, and normalization in separate components so it remains understandable in an interview and easier to maintain. The main trade-off is that it relies on a single server-side session rather than per-request tokens, which matches the legacy app’s actual behaviour but means the adapter is responsible for renewing invalidated sessions.

## Intentional omissions

- No destructive writes are attempted.
- No downstream database is introduced.
- No tests call the live portal during normal CI runs.
- The project does not implement unsupported filters that the upstream portal never exposed.

## Known limitations

- The upstream portal is not a formal API product; it is a browser UI with authenticated JSON routes.
- Meter detail metadata is reconstructed from the page payload rather than from a dedicated API schema.
- The adapter is compatible with the observed behaviour, not every future UI change.

## Improvements possible with another day

- Add a small response cache with explicit refresh TTLs.
- Add richer structured logs and operational metrics.
- Expand end-to-end integration fixtures for live portal regression testing.
- Investigate additional metering hierarchy endpoints or official data contracts if they are later exposed by the portal.

## Regenerating openapi.json

```bash
python -c "from app.main import app; import json; open('openapi.json','w').write(json.dumps(app.openapi(), indent=2))"
```

## Current verification status

- Verified: login page inspection, same-origin form submission behaviour, session cookie creation, authenticated meter search JSON responses, geo endpoint, and energy endpoint.
- Verified: project tests are designed to run without calling the live portal.
- Not verified: any route or field that was not directly observed in the browser or network trace.

See [PROTOCOL.md](PROTOCOL.md) and [REFLECTION.md](REFLECTION.md) for the full findings and implementation notes.
