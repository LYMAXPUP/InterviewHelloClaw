"""面试数据 API 路由"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from ..database.mongodb_config import MongoConfig

router = APIRouter(prefix="/interviews", tags=["interviews"])

COLLECTION_NAME = "interviews"

CHINA_TZ = timezone(timedelta(hours=8))


class InterviewRecord(BaseModel):
    unique_id: str
    company_department: str
    position: str
    start_time: str
    review: str = ""
    status: str = "DOING"
    interview_type: str
    source: str = "manual add"
    created_at: str
    updated_at: str


class InterviewCreateRequest(BaseModel):
    company_department: str
    position: str
    start_time: str
    interview_type: str
    review: str = ""


class ReviewUpdateRequest(BaseModel):
    review: str


class InterviewUpdateRequest(BaseModel):
    company_department: Optional[str] = None
    position: Optional[str] = None
    start_time: Optional[str] = None
    interview_type: Optional[str] = None
    review: Optional[str] = None
    status: Optional[str] = None


def _serialize_doc(doc: dict) -> dict:
    result = {}
    for key, value in doc.items():
        if value is None:
            result[key] = ''
        elif hasattr(value, '__class__'):
            if value.__class__.__name__ == 'ObjectId':
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        else:
            result[key] = value

    # 处理旧字段兼容
    if 'start_time' not in result and 'email_time' in result:
        result['start_time'] = result.pop('email_time')
    if 'start_time' not in result:
        result['start_time'] = ''
    for field in ('unique_id', 'company_department', 'position', 'interview_type', 'created_at', 'updated_at'):
        if result.get(field) is None:
            result[field] = ''
    if 'source' not in result:
        result['source'] = 'email'

    return result


def _generate_unique_id(company_department: str, position: str, start_time: str) -> str:
    safe_company = company_department.replace(" ", "_").replace("（", "_").replace("）", "").replace("(", "_").replace(")", "")
    safe_position = position.replace(" ", "_")
    # 提取日期部分
    date_part = start_time.split()[0] if start_time else ""
    safe_time = date_part.replace(":", "-").replace("+", "")
    return f"{safe_company}_{safe_position}_{safe_time}"


def _get_collection():
    if not MongoConfig.is_connected():
        MongoConfig.initialize()
    return MongoConfig.get_collection(COLLECTION_NAME)


@router.get("", response_model=List[InterviewRecord])
async def get_all_interviews():
    coll = _get_collection()
    docs = list(coll.find().sort([("company_department", 1), ("start_time", 1)]))
    return [_serialize_doc(doc) for doc in docs]


@router.post("", response_model=InterviewRecord)
async def create_interview(req: InterviewCreateRequest):
    coll = _get_collection()

    unique_id = _generate_unique_id(req.company_department, req.position, req.start_time)
    now = datetime.now(CHINA_TZ)
    now_iso = now.isoformat()

    doc = {
        "unique_id": unique_id,
        "company_department": req.company_department,
        "position": req.position,
        "start_time": req.start_time,
        "review": req.review,
        "status": "DOING",
        "interview_type": req.interview_type,
        "source": "manual add",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    existing = coll.find_one({"unique_id": unique_id})
    if existing:
        raise HTTPException(status_code=409, detail=f"面试记录已存在: {unique_id}")

    coll.insert_one(doc)
    return _serialize_doc(doc)


@router.put("/{unique_id}/review")
async def update_review(unique_id: str, req: ReviewUpdateRequest):
    coll = _get_collection()

    now_iso = datetime.now(CHINA_TZ).isoformat()

    result = coll.update_one(
        {"unique_id": unique_id},
        {"$set": {"review": req.review, "updated_at": now_iso}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到面试记录: {unique_id}")

    return {"status": "updated", "unique_id": unique_id}


@router.put("/{unique_id}", response_model=InterviewRecord)
async def update_interview(unique_id: str, req: InterviewUpdateRequest):
    coll = _get_collection()

    existing = coll.find_one({"unique_id": unique_id})
    if not existing:
        raise HTTPException(status_code=404, detail=f"未找到面试记录: {unique_id}")

    now_iso = datetime.now(CHINA_TZ).isoformat()

    update_fields = {"updated_at": now_iso}
    if req.company_department is not None:
        update_fields["company_department"] = req.company_department
    if req.position is not None:
        update_fields["position"] = req.position
    if req.start_time is not None:
        update_fields["start_time"] = req.start_time
    if req.interview_type is not None:
        update_fields["interview_type"] = req.interview_type
    if req.review is not None:
        update_fields["review"] = req.review
    if req.status is not None:
        update_fields["status"] = req.status

    coll.update_one({"unique_id": unique_id}, {"$set": update_fields})

    updated_doc = coll.find_one({"unique_id": unique_id})
    return _serialize_doc(updated_doc)


@router.delete("/{unique_id}")
async def delete_interview(unique_id: str):
    coll = _get_collection()

    result = coll.delete_one({"unique_id": unique_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到面试记录: {unique_id}")

    return {"status": "deleted", "unique_id": unique_id}
