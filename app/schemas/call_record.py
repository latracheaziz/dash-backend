from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class CallRecordCreate(BaseModel):
    employee_id:  Optional[int]  = None
    visitor_name: Optional[str]  = "Unknown"
    duration:     Optional[str]  = "0m 0s"
    transcript:   str
    rating:       int
    explanation:  str
    strengths:    List[str]
    weaknesses:   List[str]
    suggestions:  List[str]
    status:       Optional[str]  = "Completed"
    # NLP classifier fields
    sentiment:    Optional[str]  = "neutral"    # positive | negative | neutral
    intent:       Optional[str]  = "other"      # complaint | request | information | other
    priority:     Optional[str]  = "medium"     # low | medium | high


class CallRecordOut(BaseModel):
    id:           int
    user_id:      int
    employee_id:  Optional[int]
    visitor_name: Optional[str]
    duration:     Optional[str]
    transcript:   str
    rating:       int
    explanation:  str
    strengths:    List[str]
    weaknesses:   List[str]
    suggestions:  List[str]
    status:       str
    created_at:   datetime
    # NLP classifier fields
    sentiment:    Optional[str] = "neutral"
    intent:       Optional[str] = "other"
    priority:     Optional[str] = "medium"

    model_config = ConfigDict(from_attributes=True)
