# LogCenter
Backend FastAPI para ingestão, consulta e exportação de logs com MongoDB, Docker e estrutura modular.

## Como subir com Docker
```bash
cp .env.example .env
docker-compose up --build
```
A API ficará disponível em http://localhost:8000 (Swagger em `/docs`).

## Endpoints principais
- `POST /logs` – ingesta logs (form-data: timePlayed, status, project, additional?)
- `GET /logs` – lista logs (filtros opcionais)
- `GET /logs/latest` – último uploadedData
- `GET /logs/status/count` – contagem por status
- `GET /logs/download` – exporta CSV zipado
- `POST /projects` – cria projeto
- `GET /projects` – lista projetos
- `GET /health` – healthcheck

## Desenvolvimento local (sem Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MONGODB_URI=mongodb://localhost:27017/logcenter
uvicorn src.main:app --reload
```

## Testes
```bash
pytest
```
