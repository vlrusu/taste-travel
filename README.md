# Taste Travel

MVP travel restaurant recommendation app with a FastAPI backend and a Next.js frontend.

## Stack

- Backend: FastAPI, SQLAlchemy 2.x, Alembic, Pydantic settings
- Frontend: Next.js App Router, TypeScript
- Local database: SQLite by default
- Production database: PostgreSQL
- External data: Google Places API

## Repo structure

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
frontend/
scripts/
```

## Local development

### Backend

1. Create a Python 3.12 virtual environment.
2. Install dependencies:

```bash
pip install -e .[dev]
```

Or:

```bash
pip install -r requirements-dev.txt
```

3. Copy the env template if you want local overrides:

```bash
cp .env.example .env
```

4. Start the API:

```bash
uvicorn app.main:app --reload --reload-dir app
```

Local development defaults to `sqlite:///./test.db`. SQLite tables are auto-created on startup for local use. If you want Alembic-managed local schema setup instead, run:

```bash
alembic upgrade head
```

API docs are available at `http://127.0.0.1:8000/docs`.

### Frontend

1. Install Node.js if `npm` is not available.
2. Copy the frontend env template:

```bash
cp frontend/.env.example frontend/.env.local
```

3. Install dependencies and start the app:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

## Environment variables

### Backend

Use these in local development or Railway:

- `APP_ENV`
- `APP_HOST`
- `APP_PORT`
- `APP_DEBUG`
- `DATABASE_URL`
- `BACKEND_CORS_ORIGINS`
- `DEFAULT_USER_EMAIL`
- `DEFAULT_USER_NAME`
- `GOOGLE_PLACES_API_KEY`
- `GOOGLE_PLACES_BASE_URL`
- `GOOGLE_PLACES_TEXT_SEARCH_BASE_URL`
- `GOOGLE_GEOCODING_BASE_URL`
- `GOOGLE_PLACES_TIMEOUT_SECONDS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT_SECONDS`

Notes:

- Local default database: `sqlite:///./test.db`
- Production expects PostgreSQL through `DATABASE_URL`
- Railway-style `postgres://...` URLs are normalized automatically for SQLAlchemy/Psycopg
- Production startup does not rely on SQLite

### Frontend

Use these in local development or Vercel:

- `NEXT_PUBLIC_API_BASE_URL`

Example:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Deployment

### Railway backend

1. Create a Railway project from this repo.
2. Add a PostgreSQL database in Railway.
3. Set backend environment variables in Railway:

```env
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=${{Railway PostgreSQL DATABASE_URL}}
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
GOOGLE_PLACES_API_KEY=your_google_places_key
```

4. Railway will use the provided `railway.json` start command:

```bash
sh ./scripts/start.sh
```

That command runs:

1. `alembic upgrade head`
2. `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Notes:

- `DATABASE_URL` is read from the environment
- PostgreSQL is the expected production database
- SQLite is blocked in production mode

### Vercel frontend

1. Create a Vercel project from the `frontend/` directory.
2. Set the root directory to `frontend`.
3. Add this environment variable in Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app/api/v1
```

4. Deploy.

Notes:

- The frontend no longer hardcodes localhost
- API calls are fully environment-driven through `NEXT_PUBLIC_API_BASE_URL`

## Docker Compose

Local Docker Compose remains available:

```bash
docker compose up --build
```

## Tests

Run backend tests with:

```bash
python3 -m pytest
```

## Common setup issue

If you see `ModuleNotFoundError: No module named 'pydantic_settings'`, install dependencies into your active environment:

```bash
pip install -e .[dev]
```

or:

```bash
pip install -r requirements-dev.txt
```

## Notes

- Authentication remains stubbed with a default demo user
- Google Places is used when configured and available
- Verified seed restaurants can optionally run a narrow AI extraction step for structured trait enrichment when `OPENAI_API_KEY` is configured
- Seed restaurants can be verified against Google Places before saving, with a manual fallback when no match is selected
- If Google data is unavailable or too weak, recommendations fall back to the internal mock catalog
- Secrets should live in runtime environment variables only; do not commit `.env` files
