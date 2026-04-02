# Taste Travel Backend

Production-style FastAPI backend for an MVP travel restaurant recommendation app. The stack uses FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Pydantic settings, pytest, and Docker Compose.

## Structure

```text
app/
  api/
  core/
  db/
  integrations/
  models/
  repositories/
  schemas/
  services/
  tests/
alembic/
scripts/
```

## Local setup

1. Copy `.env.example` to `.env`.
2. Start the app and database:

```bash
docker compose up --build
```

3. Open the API docs at `http://localhost:8000/docs`.

## Local development without Docker

1. Create a Python 3.12 virtual environment.
2. Install dependencies:

```bash
pip install -e .[dev]
```

3. Start PostgreSQL and update `DATABASE_URL` in `.env` if needed.
4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## Implemented endpoints

- `GET /api/v1/health`
- `GET /api/v1/me`
- `PATCH /api/v1/me`
- `GET /api/v1/me/seeds`
- `POST /api/v1/me/seeds`
- `DELETE /api/v1/me/seeds/{seed_id}`
- `POST /api/v1/me/taste-profile:generate`
- `GET /api/v1/me/taste-profile`
- `POST /api/v1/recommendations:generate`
- `GET /api/v1/recommendations/{recommendation_id}`
- `POST /api/v1/recommendations/{recommendation_id}/feedback`

## Notes

- Authentication is stubbed with a default demo user for MVP development.
- Recommendation generation uses mocked data but persists results in the database so the API contract behaves like a real service.
