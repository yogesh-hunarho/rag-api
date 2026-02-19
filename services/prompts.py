SUMMARY_PROMPT = """You are an NCERT textbook summarizer.
Rules:
- Use only text words
- JSON only
Output:
{{ "summary": [] }}
Text:
{context}
"""

NOTES_PROMPT = """Create student notes.
Rules:
- Textbook language only
- JSON only
Output:
{{ "notes": [{{ "heading": "", "points": [] }}] }}
Text:
{context}
"""

MINDMAP_PROMPT = """Create a mind map.
Rules:
- Hierarchy only
- JSON only
Output:
{{ "root": "", "branches": [{{ "topic": "", "subtopics": [] }}] }}
Text:
{context}
"""

WORKSHEET_PROMPT = """Create worksheet.
Rules:
- NCERT only
- JSON only
Output:
{{ "fill_in_the_blanks": [], "true_false": [], "match_the_following": [] }}
Text:
{context}
"""

LESSON_PLAN_PROMPT = """Create lesson plan.
Rules:
- Teacher focused
- JSON only
Output:
{{ "learning_objectives": [], "teaching_steps": [], "assessment": [] }}
Text:
{context}
"""

QUESTION_PAPER_PROMPT ="""
You are a CBSE/NCERT exam paper setter.
DIFFICULTY RULES (STRICT):
- easy: direct definition, one-line fact, naming
- medium: explanation using 2–3 sentences from text
- hard: reasoning or comparison explicitly present in text

ABSOLUTE RULES (NO EXCEPTIONS):
- Use ONLY exact words, phrases, or sentences copied from the Chapter Text
- Do NOT paraphrase
- Do NOT summarize
- Do NOT introduce synonyms
- Do NOT use prior knowledge
- If an answer sentence is not present verbatim, DO NOT generate the question
- Match the marks blueprint EXACTLY
- Follow question counts EXACTLY
- JSON output ONLY
- NO extra keys
- NO wrapper objects
- NO comments
- NO trailing commas
- NO markdown

MATH RULES:
- For mathematics, represent equations using LaTeX
- LaTeX must be compatible with KaTeX
- Do NOT invent formulas
- Use ONLY formulas present in the text

FIGURE HANDLING (MANDATORY):
- If a question refers to any diagram, experiment, or illustration:
  - Set "figure_reference": "Fig. X"
- If figure number is mentioned in text, copy it exactly
- If no figure is referenced, set null

QUESTION TYPE RULES:

MCQ:
- Exactly 4 options
- ALL options must be copied EXACTLY from the text
- One and only one correct option
- Provide "correct_index"

Fill in the blanks:
- Remove EXACTLY ONE word or phrase
- The removed text must exist verbatim in the chapter

Short / Long Answer:
- Question sentence MUST match one of these patterns AND exist in text:
  - "Define ..."
  - "What is ..."
  - "Explain ..."
  - "Write ..."
  - "Name ..."
- Answer MUST be copied verbatim from the chapter text
- Multi-sentence answers must preserve original order

MARKS BLUEPRINT (STRICT):
{marks_json}

OUTPUT JSON FORMAT (STRICT — DO NOT CHANGE):
{{
  "mcq": [
    {{
      "question": "",
      "options": ["", "", "", ""],
      "correct_index": 0,
      "marks": 1,
      "difficulty": "easy",
      "figure_reference": null
    }}
  ],
  "fill_in_the_blanks": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ],
  "short_answer": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ],
  "long_answer": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ]
}}

Chapter Text:
{context}
"""


# QUESTION_PAPER_PROMPT = """You are a CBSE/NCERT exam paper setter.

# DIFFICULTY: {difficulty}

# DIFFICULTY RULES:
# - easy: direct recall, definitions
# - medium: explanation, examples
# - hard: reasoning, application

# STRICT RULES:
# - Use ONLY words present in the chapter text
# - Do NOT invent facts
# - Do not introduce new wording.
# - Match EXACT marks distribution
# - Follow blueprint strictly
# - If a question refers to a figure, return its figure number
# - JSON ONLY
# - if math include the use can use latex for math
# - Provide answers for EVERY question in the question paper.
# - Answers must be accurate and derived ONLY from the context.

# OUTPUT MUST BE STRICT VALID JSON ONLY.
#   - No comments
#   - No trailing commas
#   - No text outside JSON

# FIGURE HANDLING (MANDATORY)
# If a question refers to a figure mentioned in the text:
# - Set: "figure_reference": "Fig. X"

# QUESTION TYPE RULES
# MCQ:
# - Exactly 4 options
# - ALL options must be exact words or phrases from the text
# - One correct option only
# - Include "correct_index"

# Fill in the blanks:
# - Replace ONLY ONE word or phrase
# - The missing word MUST appear exactly in the text

# Short / Long answer:
# - Use ONLY these sentence patterns IF they exist in the text:
#   - "Define ..."
#   - "What is ..."
#   - "Explain ..."
#   - "Write ..."
#   - "Name ..."

# MARKS BLUEPRINT:
# {marks_json}

# JSON FORMAT:
# {{
#   "mcq": [
#     {{
#       "question": "",
#       "options": ["", "", "", ""],
#       "correct_index": 0,
#       "marks": 1,
#       "difficulty": "easy",
#       "figure_reference": null
#     }}
#   ],
#   "fill_in_the_blanks": [],
#   "short_answer": [],
#   "long_answer": []
# }}

# Chapter Text:
# {context}
# """


ANSWER_KEY_PROMPT = """You are an exam evaluator.
Generate a professional answer key for the provided question paper using the context.

QUESTION PAPER:
{paper_json}

CONTEXT:
{context}

STRICT RULES:
- Provide answers for EVERY question in the question paper.
- JSON ONLY.
- Answers must be accurate and derived ONLY from the context.

JSON FORMAT:
{{
  "answers": [
    {{
      "question": "",
      "answer": "",
      "marks": 0
    }}
  ]
}}
"""