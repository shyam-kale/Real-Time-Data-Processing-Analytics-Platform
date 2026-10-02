# Railway Deployment Guide

## Project Structure on Railway

Create **5 separate Railway services** in one project:

| Service Name | Root Directory | Type |
|---|---|---|
| `dataflow-api` | `/backend` | Web Service |
| `dataflow-frontend` | `/frontend` | Web Service |
| `dataflow-worker` | `/worker` | Worker Service |
| `dataflow-mysql` | — | MySQL Plugin |
| `dataflow-redis` | — | Redis Plugin |

---

## Step 1 — Create a new Railway project

1. Go to [railway.app](https://railway.app) → New Project
2. Connect your GitHub repo

---

## Step 2 — Add MySQL and Redis plugins

In your Railway project:
- Click **+ New** → **Database** → **MySQL**
- Click **+ New** → **Database** → **Redis**

Railway auto-generates `DATABASE_URL` and `REDIS_URL` variables.

---

## Step 3 — Backend service (`dataflow-api`)

**Settings → Source → Root Directory:** `/backend`

**Environment Variables:**
```
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate with: openssl rand -hex 32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=${{MySQL.DATABASE_URL}}
DATABASE_URL_SYNC=${{MySQL.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
ALLOWED_ORIGINS=https://<your-frontend>.up.railway.app
UPLOAD_DIR=./uploads
```

> Railway injects `${{MySQL.DATABASE_URL}}` automatically from the MySQL plugin.
> Change the async URL prefix: `mysql+aiomysql://` for DATABASE_URL

**Build Command:** `pip install -r requirements.txt`  
**Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## Step 4 — Frontend service (`dataflow-frontend`)

**Settings → Source → Root Directory:** `/frontend`

**Environment Variables:**
```
VITE_API_BASE_URL=https://<your-backend>.up.railway.app
VITE_WS_BASE_URL=wss://<your-backend>.up.railway.app
```

**Build Command:** `npm ci && npm run build`  
**Start Command:** `npx serve -s dist -l $PORT`

---

## Step 5 — Worker service (`dataflow-worker`)

**Settings → Source → Root Directory:** `/backend`

**Environment Variables:** (same as backend)

**Start Command:** `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2`

---

## Step 6 — Run migrations on Railway

After deploying backend, open Railway shell for `dataflow-api`:
```bash
python create_tables.py
python seed.py
```

---

## Important Notes

- MySQL URL from Railway uses `mysql://` — change to `mysql+aiomysql://` for async
- Set `DEBUG=false` in production
- Generate a strong `SECRET_KEY`: `openssl rand -hex 32`
- CORS: set `ALLOWED_ORIGINS` to your actual frontend Railway URL
