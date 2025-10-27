from typing import Optional, List, Dict, Any
from bson import ObjectId
from db.utils import get_db

def _build_match(project_id=None, timestamp_gte=None, timestamp_lte=None, levels=None, visibility=None):
    match_stage: Dict[str, Any] = {}
    if visibility:
        match_stage.update(visibility)
    if project_id:
        match_stage["project_id"] = ObjectId(project_id)
    if timestamp_gte or timestamp_lte:
        match_stage["timestamp"] = {}
        if timestamp_gte:
            match_stage["timestamp"]["$gte"] = timestamp_gte
        if timestamp_lte:
            match_stage["timestamp"]["$lte"] = timestamp_lte
    if levels:
        match_stage["level"] = {"$in": [lvl.upper() for lvl in levels]}
    return {"$match": match_stage} if match_stage else {}

async def dash_level_counts(project_id=None, timestamp_gte=None, timestamp_lte=None, levels=None, visibility=None):
    db = await get_db()
    pipeline = []
    match_stage = _build_match(project_id, timestamp_gte, timestamp_lte, levels, visibility)
    if match_stage:
        pipeline.append(match_stage)
    pipeline += [
        {"$addFields": {"_norm_level": {"$toUpper": "$level"}}},
        {"$group": {"_id": "$_norm_level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"level": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50}
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]

async def dash_top_users(visibility=None):
    db = await get_db()
    pipeline = []
    if visibility:
        pipeline.append({"$match": visibility})
    pipeline += [
        {"$group": {"_id": "$data.userId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"userId": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50}
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]

async def dash_top_endpoints(visibility=None):
    db = await get_db()
    pipeline = []
    if visibility:
        pipeline.append({"$match": visibility})
    pipeline += [
        {"$group": {"_id": "$data.endpoint", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"endpoint": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50}
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]
