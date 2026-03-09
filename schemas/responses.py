from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict


# ---------------------------------------------------------------------------
# Session Responses
# ---------------------------------------------------------------------------

class SessionStartResponse(BaseModel):
    session_id: str


class UploadResponse(BaseModel):
    status: str = "uploaded"


class DeleteResponse(BaseModel):
    status: str = "deleted"


# ---------------------------------------------------------------------------
# Content Generation Responses (based on prompts.py JSON formats)
# ---------------------------------------------------------------------------

class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    marks: int = 1
    figure_reference: Optional[str] = None
    source_sentence: Optional[str] = None
    difficulty: str = "easy"


class FillInTheBlank(BaseModel):
    question: str
    answer: str
    marks: int = 1
    difficulty: str = "easy"


class ShortQuestion(BaseModel):
    question: str
    answer: str
    figure_reference: Optional[str] = None
    marks: int = 2
    difficulty: str = "easy"


class LongQuestion(BaseModel):
    question: str
    answer: str
    figure_reference: Optional[str] = None
    marks: int = 5
    difficulty: str = "easy"


class SubQuestion(BaseModel):
    question: str
    answer: str
    figure_reference: Optional[str] = None
    marks: int = 1
    difficulty: str = "easy"


class CaseBaseQuestion(BaseModel):
    case_title: str
    context: str
    sub_questions: List[SubQuestion]


class SummaryResponse(BaseModel):
    summary: List[str]


class NoteItem(BaseModel):
    heading: str
    points: List[str]


class NotesResponse(BaseModel):
    title: str
    small_description: str
    notes: List[NoteItem]


class WorksheetMatchItem(BaseModel):
    column_A: str
    column_B: str
    match: str


class WorksheetItem(BaseModel):
    question: str
    answer: str


class WorksheetResponse(BaseModel):
    title: str
    fill_in_the_blanks: List[WorksheetItem]
    true_false: List[WorksheetItem]
    match_the_following: List[WorksheetMatchItem]


class LessonPlanResponse(BaseModel):
    learning_objectives: List[str]
    teaching_steps: List[str]
    assessment: List[str]


class QuestionPaperResponse(BaseModel):
    mcq: List[MCQ]
    fill_in_the_blanks: List[FillInTheBlank]
    short_question: List[ShortQuestion]
    long_question: List[LongQuestion]


# Generic type for /{question_type} endpoint
GenerateResponse = Union[
    List[MCQ],
    List[FillInTheBlank],
    List[ShortQuestion],
    List[LongQuestion],
    List[CaseBaseQuestion],
    SummaryResponse,
    NotesResponse,
    WorksheetResponse,
    LessonPlanResponse
]
