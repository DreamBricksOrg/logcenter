import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    print("Instale python-dotenv: pip install python-dotenv")
    sys.exit(1)


# ------------------------------
# 1. Carregar .env
# ------------------------------
load_dotenv()

BASE_URL = os.getenv("LOGCENTER_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("LOGCENTER_API_KEY")
DEFAULT_PROJECT_ID = os.getenv("LOGCENTER_PROJECT_ID")  # fallback se criação falhar

HEADERS: Dict[str, str] = {
    "Content-Type": "application/json",
}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY


def log_step(title: str) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")


def safe_request(method: str, url: str, **kwargs) -> requests.Response:
    """Wrapper com prints de debug básicos."""
    print(f"[HTTP] {method.upper()} {url}")
    if "params" in kwargs and kwargs["params"]:
        print("       params =", kwargs["params"])
    if "json" in kwargs and kwargs["json"]:
        print("       json   =", kwargs["json"])
    resp = requests.request(method, url, headers=HEADERS, timeout=20, **kwargs)
    print(f"       -> status {resp.status_code}")
    try:
        print("       resp   =", resp.json())
    except Exception:
        print("       resp   =", resp.text[:300])
    return resp


# ------------------------------
# 2. Criar projeto de teste
# ------------------------------
def create_test_project() -> Optional[str]:
    """
    Cria um novo projeto de teste.
    Ajuste o endpoint/body de acordo com o openapi.json se necessário.
    """
    log_step("Criando projeto de teste")

    url = f"{BASE_URL}/projects"
    now = datetime.now(timezone.utc)

    payload = {
        "name": f"Test Dash Filters {now.isoformat()}",
        "code": f"test-dash-{now.strftime('%Y%m%d%H%M%S')}",  # <- NOVO
        "status": "active",
        "description": "Projeto de teste criado automaticamente para validar filtros do /dash.",
    }

    resp = safe_request("post", url, json=payload)
    if resp.status_code // 100 != 2:
        print("Falha ao criar projeto, usando LOGCENTER_PROJECT_ID do .env (se existir).")
        return DEFAULT_PROJECT_ID

    data = resp.json()
    project_id = data.get("_id") or data.get("id") or data.get("projectId")
    if not project_id:
        print("Não consegui extrair o ID do projeto da resposta, usando LOGCENTER_PROJECT_ID do .env.")
        return DEFAULT_PROJECT_ID

    print(f"Projeto criado com ID: {project_id}")
    return project_id


# ------------------------------
# 3. Enviar logs de teste
# ------------------------------
def generate_test_logs(project_id: str) -> List[Dict[str, Any]]:
    """
    Gera uma lista de logs bem variados para exercitar todos os filtros:
    - níveis diferentes
    - tags variadas
    - data.* com várias chaves
    - mensagens repetidas e com padrões
    - timestamps espalhados
    """
    now = datetime.now(timezone.utc)
    logs: List[Dict[str, Any]] = []

    def iso(dt: datetime) -> str:
        return dt.isoformat()

    # Log base INFO
    logs.append(
        {
            "project_id": project_id,
            "timestamp": iso(now - timedelta(minutes=30)),
            "level": "INFO",
            "status": "ok",
            "message": "User logged in successfully",
            "tags": ["auth", "backend"],
            "user_email": "alice@example.com",
            "data": {
                "campaign": "BlackFriday",
                "flow": "login",
                "step": "success",
                "region": "BR",
            },
            "request": {
                "path": "/api/login",
                "url": "https://example.com/api/login?utm=blackfriday",
            },
        }
    )

    # Warning com timeout (pra regex em message)
    logs.append(
        {
            "project_id": project_id,
            "timestamp": iso(now - timedelta(minutes=25)),
            "level": "warning",  # casing diferente
            "status": "warning",
            "message": "Payment service timeout after 30s",
            "tags": ["payment", "timeout", "backend"],
            "user": "bob",
            "data": {
                "campaign": "Christmas",
                "flow": "checkout",
                "step": "payment",
                "region": "BR",
            },
            "endpoint": "/api/checkout",
        }
    )

    # Error de DB, com actor e data.num
    logs.append(
        {
            "project_id": project_id,
            "timestamp": iso(now - timedelta(minutes=20)),
            "level": "ERROR",
            "status": "error",
            "message": "DB error: connection refused",
            "tags": ["db", "critical"],
            "actor": {"email": "service-account@example.com"},
            "data": {
                "campaign": "Christmas",
                "flow": "report",
                "step": "db_query",
                "num_attempts": 3,
            },
            "request": {
                "path": "/internal/reporting",
                "url": "https://example.com/internal/reporting?page=1",
            },
        }
    )

    # Info sem tags, com user.id e endpoint
    logs.append(
        {
            "project_id": project_id,
            "timestamp": iso(now - timedelta(minutes=10)),
            "level": "info",
            "status": "ok",
            "message": "Background job completed",
            "user": {"id": "user-123"},
            "data": {
                "job_type": "email_digest",
                "duration_ms": 1532,
            },
            "endpoint": "/jobs/email-digest",
            "path": "/jobs/email-digest",
        }
    )

    # Repetido de message para testar agregação de top-messages
    for i in range(5):
        logs.append(
            {
                "project_id": project_id,
                "timestamp": iso(now - timedelta(minutes=5 - i)),
                "level": "INFO",
                "status": "ok",
                "message": "Cache miss for key session",  # mesma mensagem
                "tags": ["cache"],
                "data": {
                    "cache_key": f"session:{i}",
                    "cache_region": "redis",
                },
                "request": {
                    "path": "/api/session",
                    "url": f"https://example.com/api/session?id={i}",
                },
            }
        )

    # Log com timestamp bem antigo
    logs.append(
        {
            "project_id": project_id,
            "timestamp": iso(now - timedelta(days=2)),
            "level": "INFO",
            "status": "ok",
            "message": "Legacy log outside main test window",
            "tags": ["legacy"],
            "data": {"campaign": "OldCampaign"},
        }
    )

    # Log com timestamp "igualdade" (a gente vai usar esse exato valor num filtro timestamp=)
    exact_ts = iso(now - timedelta(minutes=2))
    logs.append(
        {
            "project_id": project_id,
            "timestamp": exact_ts,
            "level": "INFO",
            "status": "ok",
            "message": "Special timestamp equality test",
            "tags": ["special", "equality"],
            "data": {"marker": "TS_EQ"},
        }
    )

    # Guarda esse valor em um arquivo pra você ver facilmente se quiser
    with open("last_exact_timestamp.txt", "w", encoding="utf-8") as fp:
        fp.write(exact_ts + "\n")
    print(f"Timestamp exato para teste de igualdade salvo em last_exact_timestamp.txt: {exact_ts}")

    return logs


def send_logs(logs: List[Dict[str, Any]]) -> None:
    """
    Envia logs um a um no endpoint /logs.
    Ajuste o path se na sua API for diferente.
    """
    log_step("Enviando logs de teste")

    url = f"{BASE_URL}/logs"

    for i, log in enumerate(logs):
        print(f"Log {i+1}/{len(logs)}")
        safe_request("post", url, json=log)
        time.sleep(0.1)  # só pra não floodar


# ------------------------------
# 4. Exercitar os endpoints /dash
# ------------------------------
def call_dash_endpoints(project_id: str) -> None:
    log_step("Chamando endpoints /dash com diversos filtros")

    # Janela principal (última 1h)
    now = datetime.now(timezone.utc)
    gte = (now - timedelta(hours=1)).isoformat()
    lte = now.isoformat()

    # 4.1 /dash/levels – com level__in e janela de tempo
    safe_request(
        "get",
        f"{BASE_URL}/dash/levels",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "level__in": ["INFO", "error"],  # testar case-insensitive
            "limit": 10,
            # Filtro extra via build_filter: só logs de campaign=Christmas
            "data.campaign": "Christmas",
        },
    )

    # 4.2 /dash/top-users – regex em usuário
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-users",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
            "user_email__regex": "@example.com$",  # build_filter -> {"user_email": {"$regex": ...}}
        },
    )

    # 4.3 /dash/top-endpoints – sem filtros extras
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-endpoints",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
        },
    )

    # 4.4 /dash/top-tags – com tags__in
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-tags",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
            "tags__in": "backend,timeout",  # build_filter -> {"tags": {"$in": ["backend","timeout"]}}
        },
    )

    # 4.5 /dash/top-data/keys – sem extra, só pra ver chaves
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-data/keys",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
        },
    )

    # 4.6 /dash/top-data/values – todas as chaves (sem item)
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-data/values",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
        },
    )

    # 4.7 /dash/top-data/values – focado em campaign
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-data/values",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "item": "campaign",
            "limit": 10,
            "data.campaign__regex": "Christmas|BlackFriday",
        },
    )

    # 4.8 /dash/top-messages – regex em message
    # (ajuste o path se você usou outro nome para o endpoint no router)
    safe_request(
        "get",
        f"{BASE_URL}/dash/top-messages",
        params={
            "project_id": project_id,
            "timestamp__gte": gte,
            "timestamp__lte": lte,
            "limit": 10,
            "message__regex": "timeout|cache miss",
        },
    )

    # 4.9 Exemplo de igualdade em timestamp
    #    Lê o valor que gravamos antes em last_exact_timestamp.txt e filtra exatamente ele.
    try:
        with open("last_exact_timestamp.txt", "r", encoding="utf-8") as fp:
            exact_ts = fp.read().strip()
    except FileNotFoundError:
        exact_ts = None

    if exact_ts:
        safe_request(
            "get",
            f"{BASE_URL}/dash/top-tags",
            params={
                "project_id": project_id,
                "timestamp": exact_ts,  # build_filter -> {"timestamp": "<exact ts>"}
                "limit": 10,
            },
        )


# ------------------------------
# main
# ------------------------------
def main() -> None:
    log_step("Iniciando demo do LogCenter /dash")

    project_id = create_test_project()
    if not project_id:
        print("Não há project_id válido (nem criado nem vindo do .env). Abortando.")
        sys.exit(1)

    logs = generate_test_logs(project_id)
    send_logs(logs)

    # Dá um pequeno tempo pro backend processar/gravar (se tiver qualquer fila)
    time.sleep(2)

    call_dash_endpoints(project_id)


if __name__ == "__main__":
    main()
