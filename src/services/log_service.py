import io
import csv
import zipfile
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from db import db
from util import pkey_manager, crypto, helpers

pkey_mgr = pkey_manager.PKeyManager(directory="pkeys")

def create_log(time_played_str: str, status: str, project: str, additional: str = None):
    """Insere um novo log no Mongo."""
    # Parse do timestamp de origem
    try:
        time_played = datetime.strptime(time_played_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError("timePlayed must be in format YYYY-MM-DDTHH:MM:SSZ")
    # Timestamp de upload (UTC, sem microsegundos)
    uploaded_data = datetime.utcnow().replace(microsecond=0)
    # Valida projeto
    try:
        project_oid = ObjectId(project)
    except (InvalidId, TypeError):
        raise ValueError("Invalid project ID")
    log_doc = {
        "uploadedData": uploaded_data,
        "timePlayed": time_played,
        "status": status,
        "project": project_oid,
        "additional": additional or ""
    }
    result = db["logs"].insert_one(log_doc)
    return result.inserted_id

def get_logs(project: str = None):
    """Busca logs, opcionalmente filtrando por projeto (id ou nome)."""
    query = {}
    if project:
        try:
            project_oid = ObjectId(project)
            query["project"] = project_oid
        except InvalidId:
            project_doc = db["project"].find_one({"name": project})
            if project_doc:
                query["project"] = project_doc["_id"]
            else:
                return []
    docs = list(db["logs"].find(query))
    # Normaliza para JSON
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        if "uploadedData" in doc and hasattr(doc["uploadedData"], "strftime"):
            doc["uploadedData"] = helpers.format_datetime(doc["uploadedData"])
        if "timePlayed" in doc and hasattr(doc["timePlayed"], "strftime"):
            doc["timePlayed"] = helpers.format_datetime(doc["timePlayed"])
        if "project" in doc and isinstance(doc["project"], ObjectId):
            doc["project"] = str(doc["project"])
    return docs

def get_latest_log_time(project: str = None):
    """Retorna o uploadedData mais recente em ISO string."""
    query = {}
    if project:
        try:
            project_oid = ObjectId(project)
            query["project"] = project_oid
        except InvalidId:
            project_doc = db["project"].find_one({"name": project})
            if project_doc:
                query["project"] = project_doc["_id"]
    latest = db["logs"].find_one(query, sort=[("uploadedData", -1)])
    if not latest:
        return None
    latest_time = latest["uploadedData"]
    return helpers.format_datetime(latest_time)

def get_status_counts(project: str = None):
    """Agrupa contagem por status."""
    match_stage = {}
    if project:
        try:
            project_oid = ObjectId(project)
            match_stage["project"] = project_oid
        except InvalidId:
            project_doc = db["project"].find_one({"name": project})
            if project_doc:
                match_stage["project"] = project_doc["_id"]
    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.extend([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"status": "$_id", "_id": 0, "count": 1}}
    ])
    return list(db["logs"].aggregate(pipeline))

def get_all_documents(project_oid=None):
    """Busca logs com join de projeto (apenas campos necessários)."""
    match_stage = {"$match": {}}
    if project_oid:
        match_stage["$match"]["project"] = ObjectId(project_oid) if not isinstance(project_oid, ObjectId) else project_oid
    pipeline = [
        match_stage,
        {
            "$lookup": {
                "from": "project",
                "localField": "project",
                "foreignField": "_id",
                "as": "project_info"
            }
        },
        {
            "$project": {
                "_id": 1,
                "uploadedData": 1,
                "timePlayed": 1,
                "status": 1,
                "projectName": {"$arrayElemAt": ["$project_info.name", 0]},
                "additional": 1
            }
        }
    ]
    documents = list(db["logs"].aggregate(pipeline))
    for doc in documents:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        if "uploadedData" in doc and hasattr(doc["uploadedData"], "strftime"):
            doc["uploadedData"] = helpers.format_datetime(doc["uploadedData"])
        if "timePlayed" in doc and hasattr(doc["timePlayed"], "strftime"):
            doc["timePlayed"] = helpers.format_datetime(doc["timePlayed"])
    return documents

def get_oid_by_project_name(name: str):
    project_doc = db["project"].find_one({"name": name})
    return project_doc["_id"] if project_doc else None

def get_project_by_id(project_id: str):
    try:
        oid = ObjectId(project_id)
    except Exception:
        return None
    project_doc = db["project"].find_one({"_id": oid})
    if project_doc and "createdAt" in project_doc and hasattr(project_doc["createdAt"], "strftime"):
        project_doc["createdAt"] = helpers.format_datetime(project_doc["createdAt"])
    if project_doc:
        project_doc["_id"] = str(project_doc["_id"])
    return project_doc

def get_project_private_key_index(project_oid: str):
    project = get_project_by_id(project_oid)
    if not project or "pkeyIndex" not in project:
        return -1
    return project["pkeyIndex"]

def get_project_is_encrypted(project_oid: str):
    return get_project_private_key_index(project_oid) != -1

def get_project_separator(project_oid: str):
    project = get_project_by_id(project_oid)
    if not project or "separator" not in project:
        return ","
    return project["separator"]

def get_project_add_headers(project_oid: str):
    project = get_project_by_id(project_oid)
    if not project or "addHeaders" not in project:
        return []
    separator = get_project_separator(project_oid)
    return project["addHeaders"].split(separator)

def generate_csv(documents: list):
    output = io.StringIO()
    writer = csv.writer(output)
    if documents:
        writer.writerow(documents[0].keys())
    for doc in documents:
        writer.writerow(doc.values())
    output.seek(0)
    return output

def generate_csv_with_private_key(documents: list, project_oid: str):
    output = io.StringIO()
    writer = csv.writer(output, quotechar='|', quoting=csv.QUOTE_NONE, escapechar='\\')
    priv_key_idx = get_project_private_key_index(project_oid)
    separator = get_project_separator(project_oid)
    add_headers = get_project_add_headers(project_oid)
    priv_key_pem = pkey_mgr.get_content(priv_key_idx)
    if documents:
        header = ["upload time", "play time", "status"] + [h for h in add_headers]
        writer.writerow(header)
    for doc in documents:
        row = [
            doc.get("uploadedData", "N/A"),
            doc.get("timePlayed", "N/A"),
            doc.get("status", "N/A")
        ]
        additional_enc = doc.get("additional", "")
        if not additional_enc or not str(additional_enc).endswith("="):
            continue
        decrypted = crypto.decrypt_string(additional_enc, priv_key_pem)
        if decrypted == "":
            continue
        if decrypted.endswith('\r'):
            decrypted = decrypted[:-1]
        for val in decrypted.split(separator):
            row.append(val)
        writer.writerow(row)
    output.seek(0)
    return output

def generate_logs_csv(project: str = None):
    project_oid = None
    if project:
        try:
            project_oid = ObjectId(project)
        except Exception:
            project_oid = get_oid_by_project_name(project)
    docs = get_all_documents(project_oid)
    if project_oid and get_project_is_encrypted(str(project_oid)):
        csv_io = generate_csv_with_private_key(docs, str(project_oid))
    else:
        csv_io = generate_csv(docs)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("logs.csv", csv_io.getvalue())
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime("%d%m%y_%H%M%S")
    zip_filename = f"logs_{timestamp}.zip"
    return zip_buffer, zip_filename
