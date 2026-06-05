# VibeTribe Backend

Production-style FastAPI backend for a smart student collaboration platform.

## Folder structure

```text
app/
  main.py
  core/
    config.py
    security.py
  db/
    database.py
    base.py
  models/
    user.py
    team.py
    request.py
  schemas/
    user.py
    team.py
    request.py
  api/
    v1/
      routes/
        auth.py
        users.py
        teams.py
        requests.py
  services/
  utils/
  migrations/
```

## Environment

Create `.env` from `.env.example`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://vibetribe.vercel.app,https://vibetribe-two.vercel.app
ADMIN_SETUP_KEY=replace-with-a-private-admin-bootstrap-key
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/api/v1/auth/google/callback
FRONTEND_AUTH_SUCCESS_URL=
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
```

Event poster uploads use Supabase Storage bucket `event-posters`. The backend creates one-time signed upload tokens after VibeTribe authentication and club membership checks; the bucket should be public-read so stored poster URLs can render in event cards.

## Install and migrate

```powershell
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
```

## Run

```powershell
venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

API docs are available at `http://127.0.0.1:8001/docs`.

Health check:

```text
GET /health
```

## Render Deployment

Use the included `Procfile`:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

Render setup:

1. Create a new **Web Service** connected to this repository.
2. Set the root directory to `vibetribe-backend` if deploying from a monorepo.
3. Build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start command, if not using the `Procfile`:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
   ```
5. Add environment variables in Render:
   ```env
   DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres?sslmode=require
   SECRET_KEY=<long-random-secret>
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://vibetribe.vercel.app,https://vibetribe-two.vercel.app
   ADMIN_SETUP_KEY=<private-admin-bootstrap-key>
   GOOGLE_CLIENT_ID=<google-client-id>
   GOOGLE_CLIENT_SECRET=<google-client-secret>
   GOOGLE_REDIRECT_URI=https://vibetribe-t07f.onrender.com/api/v1/auth/google/callback
   FRONTEND_AUTH_SUCCESS_URL=https://vibetribe-two.vercel.app/auth/success
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
   ```
6. Run migrations after deploy from a Render shell or locally against the production database:
   ```bash
   alembic upgrade head
   ```
7. Set Render health check path to:
   ```text
   /health
   ```

Google OAuth production redirect URI:

Add this exact URI in Google Cloud Console for the deployed backend:

```text
https://vibetribe-t07f.onrender.com/api/v1/auth/google/callback
```

Keep the local redirect URI too if you still test locally:

```text
http://127.0.0.1:8001/api/v1/auth/google/callback
```

## Main endpoints

- `GET /` health message
- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`
- `POST /api/v1/teams/`
- `GET /api/v1/teams/`
- `POST /api/v1/requests/`
- `PATCH /api/v1/requests/{request_id}/respond`
- `GET /match/recommendations`
