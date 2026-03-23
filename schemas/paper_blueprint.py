from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from typing import Dict, Literal

class MarksConfig(BaseModel):
    count: int = Field(..., ge=0)
    marks_each: int = Field(default=1, ge=1)

class PaperBlueprint(BaseModel):
    class_: int = Field(
        ...,
        ge=1,
        le=12,
        description="CBSE class",
        validation_alias=AliasChoices("class_", "class", "grade", "Grade"),
    )
    subject: str = Field(..., min_length=2)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    marks: Dict[str, MarksConfig]

    model_config = ConfigDict(populate_by_name=True)
