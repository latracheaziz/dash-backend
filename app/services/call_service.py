import json
from sqlalchemy.orm import Session
from app.models.call_record import CallRecord
from app.models.employee import Employee
from app.schemas.call_record import CallRecordCreate


# ─────────────────────────────────────────────────────────────────────────────
# Serialisation helper
# ─────────────────────────────────────────────────────────────────────────────

def parse_call_record(db_call: CallRecord) -> dict:
    """Deserialise a CallRecord ORM row into a plain dict, expanding JSON text columns."""
    return {
        "id":           db_call.id,
        "user_id":      db_call.user_id,
        "employee_id":  db_call.employee_id,
        "visitor_name": db_call.visitor_name,
        "duration":     db_call.duration,
        "status":       db_call.status,
        "transcript":   db_call.transcript,
        "rating":       db_call.rating,
        "explanation":  db_call.explanation,
        "strengths":    json.loads(db_call.strengths)  if db_call.strengths  else [],
        "weaknesses":   json.loads(db_call.weaknesses) if db_call.weaknesses else [],
        "suggestions":  json.loads(db_call.suggestions) if db_call.suggestions else [],
        # NLP classifier fields (default to safe values when column is NULL for old rows)
        "sentiment":    db_call.sentiment or "neutral",
        "intent":       db_call.intent    or "other",
        "priority":     db_call.priority  or "medium",
        "created_at":   db_call.created_at,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_call_record(db: Session, user_id: int, data: CallRecordCreate) -> dict:
    new_call = CallRecord(
        user_id      = user_id,
        employee_id  = data.employee_id,
        visitor_name = data.visitor_name,
        duration     = data.duration,
        status       = data.status,
        transcript   = data.transcript,
        rating       = data.rating,
        explanation  = data.explanation,
        strengths    = json.dumps(data.strengths),
        weaknesses   = json.dumps(data.weaknesses),
        suggestions  = json.dumps(data.suggestions),
        # NLP fields
        sentiment    = data.sentiment,
        intent       = data.intent,
        priority     = data.priority,
    )
    db.add(new_call)
    db.commit()
    db.refresh(new_call)
    return parse_call_record(new_call)


def get_calls_by_user(db: Session, user_id: int) -> list[dict]:
    calls = db.query(CallRecord).filter(CallRecord.user_id == user_id).all()
    return [parse_call_record(c) for c in calls]


def get_calls_by_employee(db: Session, employee_id: int) -> list[dict]:
    calls = db.query(CallRecord).filter(CallRecord.employee_id == employee_id).all()
    return [parse_call_record(c) for c in calls]


def get_all_calls(db: Session) -> list[dict]:
    calls = db.query(CallRecord).all()
    return [parse_call_record(c) for c in calls]


def get_dashboard_stats(
    db: Session,
    user_role: str = "admin",
    user_id: int | None = None,
) -> dict:
    query = db.query(CallRecord)
    if user_role == "user" and user_id is not None:
        query = query.filter(CallRecord.user_id == user_id)

    calls = query.all()
    total_calls   = len(calls)
    global_rating = 0.0
    if total_calls > 0:
        global_rating = sum(c.rating for c in calls if c.rating is not None) / total_calls

    from collections import defaultdict
    employee_stats: dict = defaultdict(lambda: {"totalCalls": 0, "totalRating": 0})
    for c in calls:
        if c.employee_id:
            employee_stats[c.employee_id]["totalCalls"]  += 1
            employee_stats[c.employee_id]["totalRating"] += (c.rating or 0)

    employees = db.query(Employee).all()
    emp_dict  = {e.id: e.name for e in employees}

    leaderboard = []
    for emp_id, stats in employee_stats.items():
        if stats["totalCalls"] > 0:
            avg_rating = stats["totalRating"] / stats["totalCalls"]
            leaderboard.append({
                "id":            emp_id,
                "name":          emp_dict.get(emp_id, f"Employee {emp_id}"),
                "totalCalls":    stats["totalCalls"],
                "averageRating": round(avg_rating, 1),
            })

    leaderboard.sort(key=lambda x: x["averageRating"], reverse=True)

    return {
        "total_calls":    total_calls,
        "global_rating":  round(global_rating, 1),
        "leaderboard":    leaderboard,
        "calls":          [parse_call_record(c) for c in calls],
    }
