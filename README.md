# LogCenter – Central de Logs Estruturados

O LogCenter é uma API de logging estruturado e observabilidade, desenvolvida em FastAPI com MongoDB e Structlog, voltada para centralizar e analisar logs de múltiplas aplicações.
O sistema permite multi-tenant seguro, suporte a dashboards analíticos, exportação de logs e integração via SDK. Este README documenta arquitetura, setup local com Docker, variáveis de ambiente, autenticação unificada, endpoints (com cURLs), dashboards, exportação, pipeline e um roteiro de testes manuais, além de troubleshooting.

---

## Sumário

1. Arquitetura
2. Tecnologias
3. Estrutura do Projeto
4. Configuração e Deploy
5. Variáveis de Ambiente
6. Autenticação e Autorização
7. Modelos Principais
8. Endpoints Principais
   - Auth
   - Projetos
   - Logs
   - Dashboards
9. SDK de Integração
10. Dashboards e Filtros
11. Exportação de Dados
12. Pipeline e Fluxo de Deploy
13. Testes Manuais (cURLs)
14. Troubleshooting e Debug

---

## 1. Arquitetura

A aplicação é modular e segue arquitetura service-based, com separação clara entre:

- `api/` – rotas FastAPI (camada HTTP)
- `models/` – modelos Pydantic
- `services/` – lógica de negócio e persistência MongoDB
- `core/` – configuração, autenticação/autorização e utilitários globais
- `middleware/` – integração SDK e auditoria
- `db/` – inicialização da conexão MongoDB
- `util/` – helpers (datas, formatação, etc.)

O sistema é preparado para ambientes multi-tenant: cada cliente possui escopo de acesso apenas aos projetos vinculados e somente a projetos com `status: "active"` participam das listagens e agregações.

---

## 2. Tecnologias

| Componente | Versão (ref.) | Função |
|-----------|----------------|--------|
| Python | 3.10 | Linguagem |
| FastAPI | 0.115.x | Framework web |
| Uvicorn | 0.30.x | ASGI Server |
| MongoDB | 6.x | Banco NoSQL |
| Motor | 3.7.x | Driver assíncrono Mongo |
| Pydantic | 2.11.x | Validação/schemas |
| Structlog | latest | Logging estruturado |
| OpenPyXL | 3.1.x | Exportação Excel |
| Sentry SDK | 2.14.x | Telemetria/Tracing |
| Docker / Compose | latest | Empacotamento e deploy |

---

## 3. Estrutura do Projeto

```
src/
├── api/
│   ├── auth.py
│   ├── projects.py
│   ├── logs.py
│   └── dash.py
├── core/
│   ├── config.py
│   ├── auth.py
│   └── security.py
├── db/
│   └── utils.py
├── middleware/
│   └── sdk_audit.py
├── models/
│   ├── auth.py
│   ├── log.py
│   └── project.py
├── services/
│   ├── auth_service.py
│   ├── dashboard_service.py
│   ├── log_service.py
│   ├── project_service.py
│   └── stream_service.py
├── util/
│   └── helpers.py
└── main.py
```

---

## 4. Configuração e Deploy (Local)

### 4.1 Clonar
```bash
git clone https://github.com/DreamBricksOrg/logcenter.git
cd logcenter
```

### 4.2 `.env` mínimo
```env
ENV=dev
APP_PORT=8000
MONGO_URI=mongodb://mongo:27017/logcenter

# SDK interno do próprio LogCenter (auto-logs)
LOGCENTER_BASE_URL=http://localhost:8000
LOGCENTER_PROJECT_ID=68ffd088c9a747f5faadd7fb
LOGCENTER_API_KEY=<chave do próprio LogCenter>
LOGCENTER_SDK_ENABLED=true
LOGCENTER_MIN_LEVEL=INFO

# Segurança
REQUIRE_API_KEY=false
SECRET_KEY=<um-segredo-aleatório-hex>
```

### 4.3 Subir com Docker
```bash
docker compose build
docker compose up -d
```

API: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`

---

## 5. Variáveis de Ambiente

| Variável | Descrição |
|---------|-----------|
| `MONGO_URI` | Conexão MongoDB |
| `ENV` | Ambiente (`dev`, `staging`, `prod`) |
| `APP_PORT` | Porta exposta pela aplicação |
| `LOGCENTER_SDK_ENABLED` | Habilita SDK interno para auto-log |
| `LOGCENTER_BASE_URL` | Base URL acessível do serviço |
| `LOGCENTER_PROJECT_ID` | Projeto do próprio LogCenter |
| `LOGCENTER_API_KEY` | API key do SDK interno |
| `LOGCENTER_MIN_LEVEL` | Nível mínimo de log (`INFO`, `ERROR`, etc.) |
| `REQUIRE_API_KEY` | Exige header `X-API-Key` |
| `SECRET_KEY` | Segredo interno para chaves efêmeras (legado) |

---

## 6. Autenticação e Autorização

Autenticação unificada via `/auth/login` com e-mail + senha.  
No login, é gerada/rotacionada uma `api_key` de usuário, persistida no documento `users`.

Modelo de user (coleção `users`):
```json
{
  "_id": "ObjectId",
  "email": "foo@bar.com",
  "name": "User Name",
  "role": "admin" | "client",
  "password_salt": "...",
  "password_hash": "...",
  "api_key_salt": "...",
  "api_key_hash": "...",
  "project_ids": ["ObjectId", "..."]
}
```

- Admin: acesso total (ou escopo opcional se possuir `project_ids`).
- Client: acesso somente aos `project_ids` vinculados e apenas a projetos `status: "active"`.
- O `core/auth.enforce_visibility` transforma o principal em filtro de visibilidade sobre `project_id`.

Header:
```
X-API-Key: <api_key_do_usuario>
```

---

## 7. Modelos Principais

### 7.1 Project
```json
{
  "_id": "ObjectId",
  "name": "Acme App",
  "code": "acme",
  "status": "active" | "inactive",
  "description": "Texto opcional"
}
```

### 7.2 Log
```json
{
  "_id": "ObjectId",
  "uploadedAt": "2025-10-28T14:00:00Z",
  "timestamp": "2025-10-28T13:59:59Z",
  "status": "ok",
  "level": "INFO",
  "message": "Request completed",
  "tags": ["auth", "success"],
  "data": {"ip": "127.0.0.1"},
  "request_id": "abc-123",
  "project_id": "ObjectId"
}
```

---

## 8. Endpoints Principais

### 8.1 Auth

#### `POST /auth/login`
Login unificado para admins e clientes.
```bash
curl -X POST http://localhost:8000/auth/login   -H "Content-Type: application/json"   -d '{"email":"admin@example.com","password":"31773177"}'
```
Resposta:
```json
{
  "api_key": "...",
  "role": "admin",
  "name": "Admin",
  "user_id": "ObjectId",
  "project_ids": [],
  "project_codes": []
}
```

### 8.2 Projetos

#### `POST /projects/` (admin)
```bash
curl -X POST http://localhost:8000/projects/   -H "X-API-Key: <ADMIN_KEY>"   -H "Content-Type: application/json"   -d '{"name":"Acme App","code":"acme","status":"active"}'
```

#### `GET /projects/`
Lista projetos. Apenas ativos para clients. Admin pode ver todos.
```bash
curl -L "http://localhost:8000/projects/"   -H "X-API-Key: <API_KEY>"
```

#### `PATCH /projects/{id}`
Atualiza campos, ex.: status.
```bash
curl -X PATCH http://localhost:8000/projects/<ID>   -H "X-API-Key: <ADMIN_KEY>"   -H "Content-Type: application/json"   -d '{"status":"inactive"}'
```

### 8.3 Logs

#### `POST /logs/`
Cria log.
```bash
curl -X POST http://localhost:8000/logs/   -H "X-API-Key: <CLIENT_KEY>"   -H "Content-Type: application/json"   -d '{
        "project_id":"<PROJECT_ID>",
        "status":"ok",
        "level":"INFO",
        "message":"hello world",
        "tags":["demo"],
        "data":{"endpoint":"/demo","userId":"cliente"}
      }'
```

#### `GET /logs/`
Lista logs, respeitando visibilidade e projetos ativos.
```bash
curl -L "http://localhost:8000/logs/?project_id=<PROJECT_ID>"   -H "X-API-Key: <API_KEY>"
```

#### `GET /logs/levels`
Contagem por nível (versão nos dashboards é preferível).

#### `GET /logs/export?format=xlsx|csv`
Exporta logs em planilha.
```bash
curl -L "http://localhost:8000/logs/export?format=xlsx"   -H "X-API-Key: <API_KEY>" -o logs.xlsx
```

### 8.4 Dashboards

O módulo `/dash/` provê endpoints agregadores sobre os logs, utilizados pelos painéis administrativos.

Todos exigem autenticação via **API Key** (do admin ou de um cliente com acesso ao projeto) e respeitam automaticamente:

* **visibilidade** (restrição de projetos do usuário);
* **status ativo** dos projetos;
* **janela temporal opcional** (`timestamp_gte`, `timestamp_lte`).

#### `GET /dash/levels/`
Contagem de logs por nível (filtrados por projetos ativos e visibilidade).
```bash
curl -L "http://localhost:8000/dash/levels/?project_id=<PROJECT_ID>"   -H "X-API-Key: <API_KEY>"
```

#### `GET /dash/top-users/`
Top usuários por `data.userId`.
```bash
curl -L "http://localhost:8000/dash/top-users/?timestamp__gte=2025-10-01T00:00:00Z"   -H "X-API-Key: <API_KEY>"
```

#### `GET /dash/top-endpoints/`
Top endpoints por `data.endpoint`.
```bash
curl -L "http://localhost:8000/dash/top-endpoints/?timestamp__gte=2025-10-01T00:00:00Z"   -H "X-API-Key: <API_KEY>"
```

#### `GET /dash/top-data/keys`
Retorna a contagem das **chaves** existentes dentro de `data`.
```bash
# 1) Top chaves de todo o período
curl -s "$BASE/dash/top-data/keys?limit=20" \
  -H "X-API-Key: $KEY" | jq

# 2) Somente de um projeto e janela temporal (ISO-8601)
curl -s "$BASE/dash/top-data/keys?project_id=$P1_ID&timestamp__gte=2025-11-02T00:00:00Z&timestamp__lte=2025-11-04T00:00:00Z&limit=20" \
  -H "X-API-Key: $KEY" | jq
```

#### `GET /dash/top-data/values`
Conta **pares (item, valor)** encontrados em `data`.
```bash
# 1) Top pares (item+valor) de todo o período
curl -s "$BASE/dash/top-data/values?limit=20" \
  -H "X-API-Key: $KEY" | jq

# 2) Top valores para UMA chave específica (ex.: method)
curl -s "$BASE/dash/top-data/values?project_id=$P1_ID&item=method&limit=20" \
  -H "X-API-Key: $KEY" | jq

# 3) Com janela temporal (últimos 2 dias, por exemplo)
curl -s "$BASE/dash/top-data/values?project_id=$P1_ID&timestamp__gte=2025-11-02T00:00:00Z&timestamp__lte=2025-11-04T00:00:00Z&limit=20" \
  -H "X-API-Key: $KEY" | jq
```

#### `GET /dash/top-tags`
Conta as ocorrências dos valores de `tags` dentro dos logs (campo `tags[]` em cada documento).
```bash
# Top 10 tags globais
curl -s "$BASE/dash/top-tags?limit=10" \
  -H "X-API-Key: $KEY" | jq

# Somente para o projeto ativo atual
curl -s "$BASE/dash/top-tags?project_id=$P1_ID&timestamp_gte=2025-11-01T00:00:00Z" \
  -H "X-API-Key: $KEY" | jq
```

---

## 9. SDK de Integração

Repositório: https://github.com/DreamBricksOrg/logcenter_sdk

Exemplo mínimo (adaptado ao projeto):
```python
from log_center_sdk.log_sender import LogCenter

logger = LogCenter(
    base_url="http://localhost:8000",
    api_key="<LOGCENTER_API_KEY>",
    project_id="<PROJECT_ID>"
)

logger.info("user_login_success", data={"user": "demo"})
logger.error("payment_failed", data={"order_id": "123", "reason": "card_declined"})
```

O LogCenter utiliza o SDK internamente para registrar eventos do próprio serviço (startup, shutdown, 5xx, etc.).

---

## 10. Dashboards e Filtros

- Dashboards usam pipelines de agregação Mongo: `$match` (com visibilidade e ativos), `$group`, `$sort` e `$project`.
- Níveis são normalizados para maiúsculas.
- `data.userId` e `data.endpoint` são considerados apenas quando existem e não são nulos.
- Sempre há interseção com projetos ativos e com o escopo do usuário (`enforce_visibility`).

---

## 11. Exportação de Dados

- `GET /logs/export?format=csv`
- `GET /logs/export?format=xlsx`

Colunas: `_id, uploadedAt, timestamp, status, level, message, tags, data, request_id, project_id`.

---

## 12. Pipeline e Fluxo de Deploy (Visão Geral)

Mesmo usando docker-compose local, o projeto está pronto para CI/CD simples:

1. Build
   ```bash
   docker build -t logcenter-api .
   ```

2. Push (registro remoto, opcional)
   ```bash
   docker tag logcenter-api registry.example.com/logcenter:latest
   docker push registry.example.com/logcenter:latest
   ```

3. Deploy remoto (EC2, por exemplo)
   - `docker compose pull`
   - `docker compose up -d`
   - Health-check e logs pelo próprio LogCenter

4. Variáveis em Secrets da pipeline (CI)
   - `MONGO_URI`, `SECRET_KEY`, `REQUIRE_API_KEY`, etc.

---

## 13. Testes Manuais (cURLs)

Fluxo completo:

```bash
BASE="http://localhost:8000"

# 1) Login admin
ADMIN_EMAIL="admin@example.com"
ADMIN_PASS="31773177"
ADMIN_LOGIN=$(curl -sS -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d "{"email":"$ADMIN_EMAIL","password":"$ADMIN_PASS"}")
ADMIN_KEY=$(echo "$ADMIN_LOGIN" | jq -r '.api_key')

# 2) Criar projetos (ativo e inativo)
P1=$(curl -sS -L -X POST "$BASE/projects/" -H "Content-Type: application/json" -H "X-API-Key: $ADMIN_KEY" -d '{"name":"Acme App","code":"acme","status":"active","description":"Projeto ativo"}')
P1_ID=$(echo "$P1" | jq -r '._id // .id')

P2=$(curl -sS -L -X POST "$BASE/projects/" -H "Content-Type: application/json" -H "X-API-Key: $ADMIN_KEY" -d '{"name":"Legacy App","code":"legacy","status":"inactive","description":"Projeto inativo"}')
P2_ID=$(echo "$P2" | jq -r '._id // .id')

# 3) Criar usuário client e vincular P1
CLIENT_CREATE=$(curl -sS -L -X POST "$BASE/users/" -H "Content-Type: application/json" -H "X-API-Key: $ADMIN_KEY" -d "{"email":"cliente@example.com","name":"Cliente Demo","role":"client","password_plain":"abc123","project_ids":["$P1_ID"]}")
CLIENT_ID=$(echo "$CLIENT_CREATE" | jq -r '._id // .id // .user_id')

# 4) Login client
CLIENT_LOGIN=$(curl -sS -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d '{"email":"cliente@example.com","password":"abc123"}')
CLIENT_KEY=$(echo "$CLIENT_LOGIN" | jq -r '.api_key')

# 5) Criar log no projeto ativo (P1)
curl -sS -L -X POST "$BASE/logs/" -H "Content-Type: application/json" -H "X-API-Key: $CLIENT_KEY" -d "{"project_id":"$P1_ID","status":"ok","level":"INFO","message":"hello from client","tags":["demo"],"data":{"endpoint":"/demo","userId":"cliente"}}"

# 6) Tentar criar log no projeto inativo (P2) -> deve falhar
curl -sS -L -X POST "$BASE/logs/" -H "Content-Type: application/json" -H "X-API-Key: $CLIENT_KEY" -d "{"project_id":"$P2_ID","status":"err","level":"ERROR","message":"should not insert"}"

# 7) Listagens e dashboards
curl -sS -L "$BASE/logs/?project_id=$P1_ID" -H "Accept: application/json" -H "X-API-Key: $ADMIN_KEY" | jq '.[0:3]'
curl -sS -L "$BASE/logs/?project_id=$P2_ID" -H "Accept: application/json" -H "X-API-Key: $ADMIN_KEY" | jq
curl -sS -L "$BASE/logs/" -H "Accept: application/json" -H "X-API-Key: $CLIENT_KEY" | jq 'if type=="array" then .[0:3] else . end'

curl -sS -L "$BASE/dash/levels/" -H "Accept: application/json" -H "X-API-Key: $ADMIN_KEY" | jq
curl -sS -L "$BASE/dash/levels/?project_id=$P1_ID" -H "Accept: application/json" -H "X-API-Key: $CLIENT_KEY" | jq
```

---

## 14. Troubleshooting e Debug

1) Redirecionamento 307  
Causa: endpoints de coleção exigem barra final.  
Solução: usar `-L` no curl ou chamar `/logs/`, `/projects/`, `/dash/levels/` etc.

2) 403 Forbidden - "No project bound to user"  
Causa: client sem `project_ids` ativos ou vazios.  
Solução: vincular projeto ativo ao usuário e refazer login.

3) 422 Unprocessable Entity ao criar log  
Causa: body faltando campos obrigatórios (ex.: `status`).  
Solução: enviar `status`, `level`, `message` e `project_id` válidos.

4) Logs não aparecem  
Causa: projeto está `"inactive"` ou filtro/visibilidade restringiu.  
Solução: ativar projeto com `PATCH /projects/{id}` e revisar filtros.

5) AtlasError: "project_id is not allowed" nos dashboards  
Causa: estágio do pipeline não era `{ "$match": ... }`.  
Solução: usar a versão corrigida do `_build_match` que retorna sempre `$match`.

6) SDK não envia logs  
Causa: `LOGCENTER_SDK_ENABLED=false`, BASE_URL incorreta ou loopback.  
Solução: confirmar `LOGCENTER_BASE_URL` e `LOGCENTER_API_KEY`, ativar o SDK.

7) Debug local rápido  
```bash
docker compose logs -f api
docker compose exec api bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

Mantenedor: Dream Bricks  
Repositório: https://github.com/DreamBricksOrg/logcenter
