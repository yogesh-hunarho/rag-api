from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from typing import List, Optional, Union, Dict


# ---------------------------------------------------------------------------
# Session Responses
# ---------------------------------------------------------------------------

class SessionStartResponse(BaseModel):
    session_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )

class LessionMindMapResponse(BaseModel):
    session_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "root": "MATTER IN OUR SURROUNDINGS",
                "branches": [
                    {
                        "topic": "Matter",
                        "subtopics": [
                            "Everything in this universe is made up of material which scientists have named “matter”",
                            "occupy space",
                            "have mass"
                        ]
                    },
                    {
                        "topic": "Physical Nature of Matter",
                        "subtopics": [
                            "MATTER IS MADE UP OF PARTICLES"
                        ]
                    },
                    {
                        "topic": "States of Matter",
                        "subtopics": [
                            "arrangement of particles is most ordered in the case of solids"
                        ]
                    }
                ]
            }
        }
    )

class UploadResponse(BaseModel):
    status: str = "uploaded"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Chapter uploaded successfully"
            }
        }
    )


class DeleteResponse(BaseModel):
    status: str = "deleted"


# ---------------------------------------------------------------------------
# Content Generation Responses (based on prompts.py JSON formats)
# ---------------------------------------------------------------------------

class CSVQuestionRow(BaseModel):
    topics_name: Optional[str] = Field(
        default=None,
        alias="Topics Name",
        validation_alias=AliasChoices("Topics Name", "TopicsName", "topics_name"),
    )
    subtopic_name: Optional[str] = Field(
        default=None,
        alias="Subtopic Name",
        validation_alias=AliasChoices("Subtopic Name", "SubtopicName", "subtopic_name"),
    )
    question_type: str = Field(
        alias="Question Type",
        validation_alias=AliasChoices("Question Type", "QuestionType", "question_type"),
    )
    difficulty_level: Optional[str] = Field(
        default=None,
        alias="Difficulty Level",
        validation_alias=AliasChoices("Difficulty Level", "DifficultyLevel", "difficulty_level"),
    )
    question: Optional[str] = Field(
        default=None,
        alias="Question",
        validation_alias=AliasChoices("Question", "question"),
    )
    sub_question_type: Optional[str] = Field(
        default=None,
        alias="sub question type",
        validation_alias=AliasChoices("sub question type", "subquestiontype", "sub_question_type"),
    )
    sub_question: Optional[str] = Field(
        default=None,
        alias="sub question",
        validation_alias=AliasChoices("sub question", "subquestion", "sub_question"),
    )
    question_image: Optional[str] = Field(
        default=None,
        alias="Question Image",
        validation_alias=AliasChoices("Question Image", "QuestionImage", "question_image"),
    )
    option_a: Optional[str] = Field(
        default=None,
        alias="Option A",
        validation_alias=AliasChoices("Option A", "OptionA", "option_a"),
    )
    option_b: Optional[str] = Field(
        default=None,
        alias="Option B",
        validation_alias=AliasChoices("Option B", "OptionB", "option_b"),
    )
    option_c: Optional[str] = Field(
        default=None,
        alias="Option C",
        validation_alias=AliasChoices("Option C", "OptionC", "option_c"),
    )
    option_d: Optional[str] = Field(
        default=None,
        alias="Option D",
        validation_alias=AliasChoices("Option D", "OptionD", "option_d"),
    )
    correct_option: Optional[str] = Field(
        default=None,
        alias="Correct Option",
        validation_alias=AliasChoices("Correct Option", "CorrectOption", "correct_option"),
    )
    answer: Optional[str] = Field(
        default=None,
        alias="Answer",
        validation_alias=AliasChoices("Answer", "answer"),
    )
    explanation: Optional[str] = Field(
        default=None,
        alias="Explanation",
        validation_alias=AliasChoices("Explanation", "explanation"),
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "Topics Name": "Matter",
                "Subtopic Name": "States of Matter",
                "Question Type": "mcq",
                "Difficulty Level": "easy",
                "Question": "Which state has fixed shape and fixed volume?",
                "sub question type": None,
                "sub question": None,
                "Question Image": None,
                "Option A": "Solid",
                "Option B": "Liquid",
                "Option C": "Gas",
                "Option D": "Plasma",
                "Correct Option": "A",
                "Answer": "Solid",
                "Explanation": "Solid has fixed shape and fixed volume as per chapter text."
            }
        }
    )

class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    marks: int = 1
    figure_reference: Optional[str] = None
    source_sentence: Optional[str] = None
    difficulty: str = "easy"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is the standard unit of temperature?",
                "options": ["Celsius", "Kelvin", "Fahrenheit", "Pascal"],
                "correct_index": 1,
                "marks": 1,
                "figure_reference": "null",
                "source_sentence": "The SI unit of temperature is Kelvin (K).",
                "difficulty": "easy"
            }
        }
    )


class FillInTheBlank(BaseModel):
    question: str
    answer: str
    marks: int = 1
    difficulty: str = "easy"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Everything in this universe is made up of material which scientists have named ________.",
                "answer": "matter",
                "marks": 1,
                "difficulty": "easy"
            }
        }
    )


class ShortQuestion(BaseModel):
    question: str
    answer: str
    figure_reference: Optional[str] = None
    marks: int = 2
    difficulty: str = "easy"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "What is evaporation?",
                "answer": "Evaporation is a surface phenomenon where particles from the surface gain enough energy to change into the vapour state.",
                "figure_reference": "null",
                "marks": 2,
                "difficulty": "easy"
            }
        }
    )


class LongQuestion(BaseModel):
    question: str
    answer: str
    figure_reference: Optional[str] = None
    marks: int = 5
    difficulty: str = "easy"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Explain the three states of matter with their characteristics.",
                "answer": "Matter exists in three states: Solid, Liquid, and Gas. Solids have fixed shape and volume. Liquids have fixed volume but no fixed shape. Gases have neither fixed shape nor fixed volume.",
                "figure_reference": "Fig. 1.1",
                "marks": 5,
                "difficulty": "medium"
            }
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "case_title": "Interconversion of States",
                "context": "We have learnt that substances around us change state from solid to liquid and from liquid to gas on application of heat.",
                "sub_questions": [
                    {"question": "How can the state of matter be changed?", "answer": "By changing temperature or pressure.", "marks": 1}
                ]
            }
        }
    )


class SummaryResponse(BaseModel):
    summary: List[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": [
                    "Matter is anything that occupies space and has mass.",
                    "Matter exists in three states: solid, liquid, and gas.",
                    "Particles of matter are continuously moving."
                ]
            }
        }
    )


class NoteItem(BaseModel):
    heading: str
    points: List[str]


class NotesResponse(BaseModel):
    title: str
    small_description: str
    notes: List[NoteItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Matter in Our Surroundings",
                "small_description": "Comprehensive notes covering physical nature and states of matter.",
                "notes": [
                    {
                        "heading": "Physical Nature",
                        "points": ["Matter is made of particles", "Particles are very small"]
                    }
                ]
            }
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Matter in Our Surroundings - Worksheet",
                "fill_in_the_blanks": [
                    {"question": "The SI unit of volume is ________.", "answer": "cubic metre"}
                ],
                "true_false": [
                    {"question": "Matter is made up of particles.", "answer": "True"}
                ],
                "match_the_following": [
                    {"column_A": "Solid", "column_B": "Fixed shape", "match": "A-B"}
                ]
            }
        }
    )


class LessonPlanResponse(BaseModel):
    learning_objectives: List[str]
    teaching_steps: List[str]
    assessment: List[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "learning_objectives": ["Understand the physical nature of matter", "Distinguish between states of matter"],
                "teaching_steps": ["Introduce matter through day-to-day examples", "Perform activities for particles"],
                "assessment": ["Define matter", "What are Panch Tatva?"]
            }
        }
    )


class QuestionPaperResponse(BaseModel):
    mcq: List[MCQ]
    fill_in_the_blanks: List[FillInTheBlank]
    short_question: List[ShortQuestion]
    long_question: List[LongQuestion]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mcq": [
                    {
                        "question": "The SI unit of temperature is:",
                        "options": ["Kelvin", "Celsius", "Pascal", "Newton"],
                        "correct_index": 0,
                        "marks": 1
                    }
                ],
                "fill_in_the_blanks": [
                    {"question": "Matter is made of _______.", "answer": "particles", "marks": 1}
                ],
                "short_question": [
                    {"question": "What is mass?", "answer": "Quantity of matter in an object.", "marks": 2}
                ],
                "long_question": [
                    {"question": "Describe states of matter.", "answer": "Solid, Liquid, Gas...", "marks": 5}
                ]
            }
        }
    )


# Generic type for /{question_type} endpoint
GenerateResponse = Union[
    List[CSVQuestionRow],
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
