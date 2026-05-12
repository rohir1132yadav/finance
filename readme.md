# Finance Options Flow Screener

## Run Locally

```powershell
docker compose up --build
```

Open:

- Frontend: http://localhost:8501/
- Backend scan: http://localhost:8000/scan
- Backend alerts: http://localhost:8000/alerts

## Deploy And Share A Public Link

This repo includes `render.yaml`, so the easiest deployment path is Render Blueprint deployment.

1. Push this project to GitHub.
2. Go to Render Dashboard.
3. Choose **New** -> **Blueprint**.
4. Connect the GitHub repo.
5. Render will create two services:
   - `finance-backend`
   - `finance-frontend`
6. When Render asks for environment variables, add your Alpaca keys:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET`
7. After deploy finishes, open the public URL for `finance-frontend`.

Share the `finance-frontend` Render URL. That is the app link people should use.

## Deployment Notes

- The frontend talks to the backend through Render private networking using `BACKEND_HOSTPORT`.
- The backend falls back to Yahoo Finance data when Alpaca data is unavailable.
- The current database is SQLite inside the backend container. It is fine for testing and demos, but saved alerts may reset when the service redeploys.
