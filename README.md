# LogCenter v0.1.5-dev (Refactor)

API para ingestão e consulta de logs com FastAPI, MongoDB Atlas, Sentry opcional e configuração centralizada.

## Stack
- FastAPI + Uvicorn
- MongoDB (Atlas)
- Pydantic Settings (configuração)
- Sentry (opcional)

## Rodando local
1. Duplique `.env.example` para `.env` e ajuste `MONGO_URI`.
2. Com Docker:
   ```bash
   docker compose build
   docker compose up
   # http://localhost:8000/docs
   ```
3. Sem Docker (Python 3.10+):
   ```bash
   pip install -r requirements.txt
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

## Endpoints
- `GET /health`
- `POST /logs` (JSON: project, level, message, tags[], data{}, request_id?)
- `GET /logs` (filtro opcional ?project=code)
- `GET /logs/latest`
- `GET /logs/levels`
- `POST /projects` (name, code, api_key?)
- `GET /projects`

## Config centralizada
Veja `src/core/config.py`. Todas as variáveis via `settings.<var>`.

## Observabilidade
Se `SENTRY_DSN` definido, a app envia exceções para o Sentry.

## CI/CD (resumo)
Workflows de exemplo:
- `.github/workflows/deploy-dev.yaml`: deploy a cada push na `dev` (scp + ssh no servidor dev)
- `.github/workflows/deploy-prod.yaml`: deploy ao criar tag `v*` na `main`

Configure secrets no GitHub (SSH_KEY, HOST_*, USER_*, REMOTE_PATH_*, ENV_*, KNOWN_HOSTS_*).

## Licença
Interno Dream Bricks.
