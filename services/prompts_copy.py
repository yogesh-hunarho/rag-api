# SUMMARY_PROMPT = """You are an NCERT textbook summarizer.
# Rules:
# - Use only text words
# - JSON only
# Output:
# {{ "summary": [] }}
# Text:
# {context}
# """

# NOTES_PROMPT = """Create student notes.
# Rules:
# - Textbook language only
# - JSON only
# Output:
# {{ "notes": [{{ "heading": "", "points": [] }}] }}
# Text:
# {context}
# """

# MINDMAP_PROMPT = """Create a mind map.
# Rules:
# - Hierarchy only
# - JSON only
# Output:
# {{ "root": "", "branches": [{{ "topic": "", "subtopics": [] }}] }}
# Text:
# {context}
# """

# WORKSHEET_PROMPT = """Create worksheet.
# Rules:
# - NCERT only
# - JSON only
# Output:
# {{ "fill_in_the_blanks": [], "true_false": [], "match_the_following": [] }}
# Text:
# {context}
# """

# LESSON_PLAN_PROMPT = """Create lesson plan.
# Rules:
# - Teacher focused
# - JSON only
# Output:
# {{ "learning_objectives": [], "teaching_steps": [], "assessment": [] }}
# Text:
# {context}
# """


SUMMARY_PROMPT = """You are an NCERT textbook summarizer for students.

RULES (STRICT):
- Use ONLY information present in the given text
- Do NOT add new facts, examples, or explanations
- Keep language simple and textbook-level
- Paraphrasing is allowed only to shorten content
- Do NOT use bullet symbols or numbering
- JSON output ONLY

SUMMARY RULES:
- Each summary point must be one clear sentence
- Focus on definitions, processes, and key ideas
- Avoid opinions or interpretations

OUTPUT JSON FORMAT (STRICT):
{{
  "summary": [""]
}}

Text:
{context}
"""

NOTES_PROMPT = """Create NCERT-based student notes for classroom study.

RULES (STRICT):
- Use ONLY information present in the given text
- Do NOT introduce new terminology or examples
- Language must match NCERT textbook tone
- Paraphrasing is allowed only to simplify sentences
- JSON output ONLY

NOTES STRUCTURE:
- Each heading represents a main concept
- Points must be short, clear, and factual
- No extra explanation beyond textbook meaning

OUTPUT JSON FORMAT (STRICT):
{{
  "title":"",
  "small_description":"",
  "notes": [
    {{
      "heading": "",
      "points": [""]
    }}
  ]
}}

Text:
{context}
"""

MINDMAP_PROMPT = """Create an NCERT-aligned mind map for teaching.

RULES (STRICT):
- Use ONLY concepts present in the given text
- Do NOT introduce new relationships or examples
- Use textbook terminology only
- Focus on hierarchy, not explanation
- JSON output ONLY

MIND MAP RULES:
- Root must be the chapter topic
- Branches must be main concepts
- Subtopics must be directly related terms or processes
- Keep hierarchy shallow and clear

OUTPUT JSON FORMAT (STRICT):
{{
  "root": "",
  "branches": [
    {{
      "topic": "",
      "subtopics": [""]
    }}
  ]
}}

Text:
{context}
"""


LESSON_PLAN_PROMPT = """Create an NCERT-based lesson plan for classroom teaching.

RULES (STRICT):
- Use ONLY information present in the given text
- Do NOT add external activities or examples
- Focus on teacher delivery and student understanding
- Language must be clear and instructional
- JSON output ONLY

LESSON PLAN STRUCTURE:
- Learning objectives: what students should understand
- Teaching steps: logical flow of concepts from the text
- Assessment: simple oral or written checks based on the text

OUTPUT JSON FORMAT (STRICT):
{{
  "learning_objectives": [""],
  "teaching_steps": [""],
  "assessment": [""]
}}

Text:
{context}
"""

# - Do NOT include answers
WORKSHEET_PROMPT = """You are an NCERT worksheet creator for classroom teaching.

RULES (STRICT):
- Use ONLY information present in the given text
- Do NOT introduce new facts, examples, or terminology
- Language must be NCERT textbook level (simple and clear)
- Paraphrasing is allowed ONLY to form questions
- Do NOT refer to figure numbers (Fig., Figure 1.1, etc.)
- Questions must be answerable without seeing any image
- JSON output ONLY

WORKSHEET STRUCTURE:
- Fill in the Blanks: key terms or concepts
- True / False: clear factual statements
- Match the Following: terms with correct descriptions

OUTPUT JSON FORMAT (STRICT):
{{
  "title": "",
  "fill_in_the_blanks": [
    {{ "question": "", answer:"" }}
  ],
  "true_false": [
    {{ "statement": "", answer:"" }}
  ],
  "match_the_following": [
    {{ "column_A": "", "column_B": "", match:"" }}
  ]
}}

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
  "short_question": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy",
    }}
  ],
  "long_question": [
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

# Specialized Question Generation Prompts

COMMON_RULES = """
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
- JSON output ONLY
- NO extra keys
- NO wrapper objects
- NO comments
- NO trailing commas
- NO markdown

FIGURE HANDLING (MANDATORY):
- If a question refers to any diagram, experiment, or illustration:
  - Set "figure_reference": "Fig. X"
- If figure number is mentioned in text, copy it exactly
- If no figure is referenced, set null

STEM SAFETY RULES (MANDATORY):
- All mathematical expressions MUST be written in LaTeX
- LaTeX MUST be compatible with KaTeX
- LaTeX MUST be enclosed in double quotes as valid JSON strings
- Do NOT introduce or derive formulas
- Use ONLY formulas exactly as written in the chapter text
- Do NOT simplify, rearrange, or restate formulas
- Preserve all symbols, subscripts, superscripts, arrows, and units exactly

JSON SAFETY RULES:
- Escape all backslashes in LaTeX as double backslashes (\\)
- Do NOT use unescaped newline characters inside strings
- Use plain ASCII text outside LaTeX
"""

MCQ_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Multiple Choice Questions (MCQs) from the given text.
""" + COMMON_RULES + """
MCQ RULES:
- Exactly 4 options
- ALL options must be copied EXACTLY from the text
- One and only one correct option
- Provide "correct_index"

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "options": ["", "", "", ""],
    "correct_index": 0 | 1 | 2 | 3,
    "marks": 1,
    "difficulty": "easy",
    "figure_reference": null
  }}
]

Chapter Text:
{context}
"""

FILL_BLANK_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Fill in the Blanks questions from the given chapter text.
""" + COMMON_RULES + """

FILL IN THE BLANKS RULES (STRICT):
- Remove EXACTLY ONE word or phrase from a meaningful sentence
- The removed word or phrase MUST exist verbatim in the chapter text
- The removed word or phrase MUST be a CONCEPT, TERM, or FACT — NOT a label

ABSOLUTELY FORBIDDEN (DO NOT USE):
- Figure numbers or references (e.g., Fig., Fig. 1.9, Figure 2.1)
- Image captions
- Diagram labels
- Table numbers
- Any sentence containing the words:
  "Fig.", "Figure", "diagram", "image", "shown", "illustrated", "table"

IMPORTANT:
- Do NOT generate questions derived from figure captions
- Do NOT remove or use figure references as answers
- If a sentence refers to a figure, SKIP that sentence entirely
- The blank must test conceptual understanding, not identification of figures

QUESTION FORMAT:
- Replace the removed text with exactly "_________"
- The sentence must remain grammatically correct

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "marks": 1,
    "difficulty": "easy",
  }}
]

Chapter Text:
{context}
"""

# FILL_BLANK_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
# Generate only Fill in the Blanks questions from the given text.
# """ + COMMON_RULES + """
# FILL IN THE BLANKS RULES:
# - Remove EXACTLY ONE word or phrase
# - In this don't refer to fig. 
# - The removed text must exist verbatim in the chapter

# OUTPUT JSON FORMAT (STRICT):
# [
#   {{
#     "question": "",
#     "answer": "",
#     "marks": 1,
#     "difficulty": "easy",
#   }}
# ]

# Chapter Text:
# {context}
# """

SHORT_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Short Answer Questions from the given chapter text.
Generate the maximum possible number of valid questions.
""" + COMMON_RULES + """

SHORT ANSWER RULES (STRICT):
- Answers MUST be copied verbatim from the chapter text
- Questions should test understanding of concepts, processes, or observations

IMAGE / DIAGRAM HANDLING RULES:
- Questions MAY refer to an image or diagram INDIRECTLY
  (e.g., "the above diagram", "the given illustration", "the diagram shown")
- Questions MUST NOT mention:
  "Fig.", "Figure", figure numbers (e.g., 1.1, 2.3), or image labels
- Do NOT use exact figure captions as questions

ANSWER RULES:
- Answers MUST NOT mention or depend on:
  "Fig.", "Figure", diagram numbers, or image labels
- Answers MUST be fully understandable without seeing the image
- Answers must be copied exactly from the chapter text (no paraphrasing)

QUESTION QUALITY RULES:
- Use NCERT-style phrasing:
  "What happens when…", "Why does…", "Explain how…", "What is observed when…"
- The image reference (if any) should only provide context, not essential data

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "figure_reference": null,
    "marks": 2,
    "difficulty": "easy",
  }}
]

Chapter Text:
{context}
"""

# SHORT_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
# Generate only Short Answer Questions from the given text maximum number of questions could be genearete so return all questions.
# """ + COMMON_RULES + """
# SHORT ANSWER RULES:
# - Answer MUST be copied verbatim from the chapter text
# - Length should be 2-3 sentences.

# OUTPUT JSON FORMAT (STRICT):
# [
#   {{
#     "question": "",
#     "answer": "",
#     "figure_reference": null,
#     "marks": 2,
#     "difficulty": "easy",
#   }}
# ]

# Chapter Text:
# {context}
# """

LONG_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Long Answer Questions from the given text.
""" + COMMON_RULES + """
LONG ANSWER RULES:
- Answer MUST be copied verbatim from the chapter text
- Length should be a detailed explanation or multiple paragraphs.

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "figure_reference": null,
    "marks": 5,
    "difficulty": "easy",
  }}
]

Chapter Text:
{context}
"""

CASE_BASE_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate Case-based Questions from the given text. A case-based question includes a context (passage) followed by multiple sub-questions.
""" + COMMON_RULES + """

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "case_title": "",
    "context": "",
    "sub_questions": [
       {{
         "question": "",
         "answer": "",
         "figure_reference": null,
         "marks": 1,
         "difficulty": "easy",
       }}
    ]
  }}
]

Chapter Text:
{context}
"""
