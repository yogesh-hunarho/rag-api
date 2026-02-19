from pydantic import BaseModel, Field
from typing import Dict, Literal

class MarksConfig(BaseModel):
    count: int = Field(..., ge=1)
    marks_each: int = Field(..., ge=1)

class PaperBlueprint(BaseModel):
    class_: int = Field(..., ge=1, le=12, description="CBSE class")
    subject: str = Field(..., min_length=2)
    difficulty: Literal["easy", "medium", "hard"]
    marks: Dict[str, MarksConfig]
