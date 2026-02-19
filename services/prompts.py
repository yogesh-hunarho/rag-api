SUMMARY_PROMPT = """You are an NCERT textbook summarizer.
Rules:
- Use only text words
- JSON only
Output:
{"summary":[]}
Text:
{context}
"""

NOTES_PROMPT = """Create student notes.
Rules:
- Textbook language only
- JSON only
Output:
{"notes":[{"heading":"","points":[]}]}
Text:
{context}
"""

MINDMAP_PROMPT = """Create a mind map.
Rules:
- Hierarchy only
- JSON only
Output:
{"root":"","branches":[{"topic":"","subtopics":[]}]}
Text:
{context}
"""

WORKSHEET_PROMPT = """Create worksheet.
Rules:
- NCERT only
- JSON only
Output:
{"fill_in_the_blanks":[],"true_false":[],"match_the_following":[]}
Text:
{context}
"""

LESSON_PLAN_PROMPT = """Create lesson plan.
Rules:
- Teacher focused
- JSON only
Output:
{"learning_objectives":[],"teaching_steps":[],"assessment":[]}
Text:
{context}
"""

QUESTION_PAPER_PROMPT = """You are a CBSE/NCERT exam paper setter.

DIFFICULTY: {difficulty}

DIFFICULTY RULES:
- easy: direct recall, definitions
- medium: explanation, examples
- hard: reasoning, application

STRICT RULES:
- Use ONLY words present in the chapter text
- Do NOT invent facts
- Do not introduce new wording.
- Match EXACT marks distribution
- Follow blueprint strictly
- If a question refers to a figure, return its figure number
- JSON ONLY

MARKS BLUEPRINT:
{marks_json}

JSON FORMAT:
{
  "mcq": [
    {
      "question": "",
      "options": [],
      "correct_index": 0,
      "marks": 1,
      "difficulty": "easy",
      "figure_reference": null
    }
  ],
  "very_short": [],
  "short": [],
  "long": []
}

Chapter Text:
{context}
"""

