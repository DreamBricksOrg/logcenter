# LogCenter  v0.1.5.1-dev (Validations)
# Setup local, Secrets e Guia da API

## 1) Pré-requisitos

- **Python 3.10+** e **pip**
- **Docker** e **Docker Compose** (para rodar via containers)
- **MongoDB Atlas** (ou outro cluster Mongo com conexão SRV)
- (Opcional) **curl** ou **HTTP client** (Postman/Insomnia)

## 2) Estrutura (resumo)

```
src/
  api/
    logs.py
    projects.py
    users.py
    stream.py
  core/
    config.py
    auth.py
    security.py
  db/
    utils.py
  models/
    log.py
    project.py
    user.py
  services/
    log_service.py
    project_service.py
    user_service.py
    stream_service.py
Dockerfile
docker-compose.yml
.env.example
```

## 3) Variáveis de ambiente (`.env`)

Copie o `.env.example` para `.env` e preencha:

```ini
ENV=dev
APP_NAME=logcenter
PORT=8000

# Mongo Atlas (SRV)
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority&appName=<app>
MONGO_DB=logcenter_dev
MONGO_DEBUG=false

# Segurança
SECRET_KEY=<uma-string-secreta-aleatória>  # usada p/ gerar "admin keys"
REQUIRE_API_KEY=true                       # true = exige auth em produção
SENTRY_DSN=                                # opcional, pode ficar vazio
```

### Gerando uma SECRET_KEY rápida
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 4) Subindo localmente

### 4.1 Com Docker
```bash
docker compose up -d --build
# API em http://localhost:8000
# Docs em http://localhost:8000/docs
```

### 4.2 Sem Docker (bare Python)
```bash
python -m venv .venv
source .venv/bin/activate     # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## 5) Autenticação

Há **dois** modos:

1) **Admin Key (header)**: uma chave “de operador” para endpoints administrativos (CRUD de projetos/usuários).  
   - Gerar uma admin key **a partir do `SECRET_KEY`**:
     ```bash
     python gen_admin_key.py
     ```
   - Em chamadas admin, envie:
     ```
     X-Admin-Key: <ADMIN_KEY>
     ```

2) **API Key do Projeto**: clientes enviam `X-API-Key` gerada a partir de uma “api_key_plain” definida no **projeto** (hash+salt guardados no banco).
   - Para criar/atualizar projeto com `api_key_plain`, use os endpoints de Projetos (abaixo).
   - Em chamadas do cliente (ex.: postar logs), envie:
     ```
     X-API-Key: <api_key_plain_do_projeto>
     ```

> Em produção, deixe `REQUIRE_API_KEY=true`. Em dev você pode flexibilizar.

## 6) Fluxo inicial

1) **Gerar ADMIN_KEY**:
   ```bash
   python gen_admin_key.py
   ```

2) **Criar um projeto (admin)**:
   ```bash
   curl -X POST http://localhost:8000/projects/      -H "Content-Type: application/json"      -H "X-Admin-Key: <ADMIN_KEY>"      -d '{
       "name": "Skyn Totem",
       "code": "skyn_totem",
       "api_key_plain": "skyn-secret-123"
     }'
   ```

3) **Postar log (cliente)**:
   ```bash
   curl -X POST http://localhost:8000/logs/      -H "Content-Type: application/json"      -H "X-API-Key: skyn-secret-123"      -d '{
       "project": "68c80f558918c510d2ca3eb4",
       "status": "INFO",
       "level": "info",
       "message": "User logged in",
       "tags": ["auth","user"],
       "data": {"userId":"abc123","ip":"192.168.0.10"},
       "request_id": "9c7f4e0f-..."
     }'
   ```

4) **Listar logs (admin)**:
   ```bash
   curl -H "X-Admin-Key: <ADMIN_KEY>" http://localhost:8000/logs/
   ```

## 7) Endpoints da API (resumo)

### Logs (`/logs`)
- `POST /logs/`
- `GET /logs/?project=<oid>`
- `GET /logs/latest?project=<oid>`
- `GET /logs/levels?project=<oid>`

### Projetos (`/projects`)
- `POST /projects/`
- `GET /projects/`
- `PATCH /projects/{project_id}`
- `DELETE /projects/{project_id}`

### Usuários (`/users`)
- CRUD admin (`email`, `name`, `role`, `project_codes`, `password_plain`).

### Streaming (tempo real)
- WebSocket `/ws/{project_code}` transmite logs em tempo real.

## 8) CI/CD — Secrets do GitHub

### 8.1 Secrets necessários (Prod)
| Nome | Descrição |
|------|------------|
| `SSH_KEY` | Chave privada SSH |
| `HOST_PROD` | IP/DNS Prod |
| `USER_PROD` | Usuário SSH |
| `PORT` | Porta SSH |
| `REMOTE_PATH_PROD` | Caminho destino |
| `KNOWN_HOSTS_PROD` | Saída de ssh-keyscan |
| `ENV_PROD` | Valor ENV prod |

### 8.2 Secrets necessários (Dev)
| Nome | Descrição |
|------|------------|
| `HOST_DEV` | IP/DNS Dev |
| `USER_DEV` | Usuário SSH |
| `REMOTE_PATH_DEV` | Caminho destino |
| `KNOWN_HOSTS_DEV` | ssh-keyscan Dev |
| `ENV_DEV` | Valor ENV dev |
| `SSH_KEY` / `PORT` | Reuso |

### 8.3 Geração de Tag
```bash
git checkout main
git pull origin main
git tag -a v0.1.5 -m "Release 0.1.5"
git push origin v0.1.5
```

## 9) Troubleshooting

- “Invalid API key” → Gere e envie `X-Admin-Key` ou `X-API-Key` válida.
- “description/config null” → Rebuild do container.
- “Permission denied (publickey)” → Corrija `SSH_KEY`.
- “Could not resolve hostname” → `HOST_*` vazio.
