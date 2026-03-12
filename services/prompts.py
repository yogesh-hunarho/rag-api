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

MINDMAP_PROMPT = """
You are an NCERT curriculum expert and diagram generator.
Your task is to create a Mermaid mind map using ONLY the official Mermaid mindmap syntax.

STRICT RULES (VERY IMPORTANT):

CONTENT RULES
- Use ONLY concepts that appear in the given text
- Do NOT introduce new concepts, relationships, or examples
- Use textbook terminology only
- Do NOT explain anything
- Do NOT summarize
- Only extract hierarchy

STRUCTURE RULES
- Root must be the chapter/topic
- Level 1 = main concepts
- Level 2 = related terms or processes
- Maximum depth = 3 levels
- Keep hierarchy simple and readable

MERMAID SYNTAX RULES
- Output MUST start with: mindmap
- Use indentation to define hierarchy
- Do NOT output JSON
- Do NOT output markdown
- Do NOT add comments
- Do NOT add explanations

ALLOWED NODE SHAPES (USE ONLY THESE)
Root:
  root((Chapter Topic))

Main concepts:
  (Concept)

Subtopics:
  [Subtopic]

DO NOT use:
- icons
- class definitions
- custom styling
- Mermaid config blocks
- unsupported shapes

VALID EXAMPLE FORMAT (FOLLOW EXACTLY):

mindmap
  root((Matter in Our Surroundings))
    (Matter)
      [Particles]
      [States of matter]
    (Properties)
      [Mass]
      [Volume]

OUTPUT RULES
- Output ONLY the Mermaid code
- No markdown code blocks
- No extra text
- No explanations

Text:
{context}
"""

LESSON_PLAN_PROMPT = """Create an NCERT-based lesson plan for classroom teaching.

RULES (STRICT):
- Use ONLY information present in the given text
- Do NOT add external activities or examples
- Teaching steps must follow the order of concepts as they appear in the chapter text.
- Focus on teacher delivery and student understanding
- Language must be clear and instructional
- JSON output ONLY

LESSON PLAN STRUCTURE:
- Learning objectives: what students should understand
- Teaching steps: logical flow of concepts from the text
- Assessment: simple oral or written checks based on the text.

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

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question


WORKSHEET STRUCTURE:
- Fill in the Blanks: key terms or concepts
- True / False: clear factual statements
- Match the Following: terms with correct descriptions

OUTPUT JSON FORMAT (STRICT):
{{
  "title": "",
  "fill_in_the_blanks": [
    {{ "question": "", "answer":"" }}
  ],
  "true_false": [
    {{ "statement": "", "answer":"" }}
  ],
  "match_the_following": [
    {{ "column_A": "", "column_B": "", "match":"" }}
  ]
}}

Text:
{context}
"""


QUESTION_PAPER_PROMPT ="""
You are a CBSE/NCERT exam paper setter.
DIFFICULTY RULES (STRICT):
- easy: direct definition, one-line fact, naming
- medium: explanation using 2-3 sentences from text
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

MATH / FORMULA RULES:
- For mathematics, represent equations using LaTeX
- LaTeX MUST be compatible with KaTeX
- Do NOT invent formulas
- Use ONLY formulas present in the text
- If the text contains [FORMULA]...[/FORMULA] tags, copy the formula content EXACTLY as-is
- Use standard JSON string escaping: one backslash becomes two in JSON (e.g. \\frac not \\\\frac)
- For inline math use $...$ and for display math use $$...$$

FIGURE HANDLING (MANDATORY):
- If a question refers to any diagram, experiment, or illustration:
  - Set "figure_reference": "Fig. X"
- If figure number is mentioned in text, copy it exactly
- If no figure is referenced, set null

QUESTION TYPE RULES:

MCQ:
- Exactly 4 options
- The correct option MUST exist verbatim in the text.
- Distractors may be short phrases derived from the same sentence but must not introduce new knowledge.
- One and only one correct option
- Provide "correct_index"
- All keys MUST be quoted using double quotes.

Fill in the blanks:
- Remove EXACTLY ONE word or phrase
- The removed text must exist verbatim in the chapter
- All keys MUST be quoted using double quotes.

Short / Long Answer:
- Question sentence MUST match one of these patterns AND exist in text:
  - "Define ..."
  - "What is ..."
  - "Explain ..."
  - "Write ..."
  - "Name ..."
- Answer MUST be copied verbatim from the chapter text
- If figure is referenced in question, set "figure_reference" in json directly,
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
      "difficulty": "easy"
    }}
  ],
  "fill_in_the_blanks": [
    {{
      "question": "",
      "answer": "",
      "marks": 1,
      "difficulty": "easy"
    }}
  ],
  "short_question": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy"
    }}
  ],
  "long_question": [
    {{
      "question": "",
      "answer": "",
      "figure_reference": null,
      "marks": 1,
      "difficulty": "easy"
    }}
  ]
}}

Chapter Text:
{context}
"""

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


COMMON_RULES = """
DIFFICULTY RULES (STRICT):
- easy: direct definition, one-line fact, or naming from the text
- medium: explanation requiring 2-3 related sentences from the text
- hard: reasoning or comparison explicitly stated in the text

ABSOLUTE CONTEXT RULES (NO EXCEPTIONS):
- Use ONLY information present in the provided Chapter Text
- Do NOT introduce outside knowledge
- Do NOT use prior knowledge
- Do NOT invent examples, explanations, or relationships
- If the required answer sentence is not present in the Chapter Text, DO NOT generate the question
- Prefer copying phrases or sentences exactly from the Chapter Text whenever possible

TEXT FIDELITY RULES:
- Do NOT paraphrase definitions
- Do NOT summarize content
- Do NOT introduce synonyms for key terms
- Preserve scientific terms exactly as written in the Chapter Text
- Preserve capitalization of key terms if present in the text

QUESTION SAFETY RULES:
- Questions must be directly supported by the Chapter Text
- Each question must be answerable using the Chapter Text alone
- Do NOT generate duplicate questions
- Avoid trivial repetition of the same concept

FIGURE HANDLING (MANDATORY):
- If a question refers to any diagram, experiment, or illustration:
  - Set "figure_reference": "Fig. X"
- If the figure number appears in the text, copy it exactly
- If no figure is referenced, set "figure_reference": null

STEM SAFETY RULES (MANDATORY):
- All mathematical expressions MUST be written in LaTeX
- LaTeX MUST be compatible with KaTeX rendering
- LaTeX MUST appear inside JSON strings
- Do NOT introduce formulas not present in the Chapter Text
- Copy formulas exactly as written in the Chapter Text
- Preserve subscripts, superscripts, arrows, and units exactly
- If the Chapter Text contains [FORMULA]...[/FORMULA] tags, copy the formula content EXACTLY
- Use $...$ for inline math and $$...$$ for display math

KaTeX COMPATIBILITY (USE ONLY THESE):
- Fractions: \\frac{a}{b}
- Square root: \\sqrt{x}, \\sqrt[n]{x}
- Superscript: x^{2}, x^{n+1}
- Subscript: x_{1}, a_{n}
- Greek letters: \\alpha, \\beta, \\gamma, \\theta, \\lambda, \\mu, \\pi, \\sigma, \\omega
- Vectors: \\vec{F}, \\hat{i}
- Operators: \\times, \\div, \\pm, \\cdot, \\leq, \\geq, \\neq, \\approx
- Arrows: \\rightarrow, \\leftarrow, \\Rightarrow
- Functions: \\sin, \\cos, \\tan, \\log, \\ln
- Integrals/Sums: \\int, \\sum, \\prod, \\lim
- DO NOT USE: \\ce{} (mhchem), \\chemfig, \\tikz, \\cancel, environments like align* or equation*
- For chemical formulas use subscripts: H_2O not \\ce{H2O}

CONTEXT SAFETY RULE:
- If sufficient information is not present in the Chapter Text, return an empty JSON structure instead of guessing.

JSON OUTPUT RULES (STRICT):
- Output MUST be valid JSON
- JSON output ONLY
- NO markdown
- NO comments
- NO explanations
- NO wrapper objects unless explicitly required
- NO extra keys
- NO trailing commas
- Use standard JSON escaping for backslashes: \\frac is correct (NOT \\\\frac)
- Do NOT include unescaped newline characters inside JSON strings
- Use plain ASCII text outside LaTeX
"""

MCQ_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Multiple Choice Questions (MCQs) from the given text.
""" + COMMON_RULES + """
MCQ RULES:
- Exactly 4 options
- The correct option MUST exist verbatim in the text.
- Distractors may be short phrases derived from the same sentence but must not introduce new knowledge.
- One and only one correct option
- Provide "correct_index"
- Generate the maximum possible questions WITHOUT repeating concepts.

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "options": ["", "", "", ""],
    "correct_index": 0 | 1 | 2 | 3,
    "marks": 1,
    "source_sentence":"",
    "difficulty": "easy"
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
- Generate the maximum possible questions WITHOUT repeating concepts.

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question

QUESTION FORMAT:
- Replace the removed text with exactly "_________"
- The sentence must remain grammatically correct

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "marks": 1,
    "source_sentence":"",
    "difficulty": "easy"
  }}
]

Chapter Text:
{context}
"""

SHORT_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Short Answer Questions from the given chapter text.
Generate the maximum possible questions WITHOUT repeating concepts.
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
- "figure_reference" in json directly

ANSWER RULES:
- Answers MUST NOT mention or depend on:
  "Fig.", "Figure", diagram numbers, or image labels
- Answers MUST be fully understandable without seeing the image
- Answers must be copied exactly from the chapter text (no paraphrasing)

QUESTION QUALITY RULES:
- Use NCERT-style phrasing:
  "What happens when…", "Why does…", "Explain how…", "What is observed when…"
- The image reference (if any) should only provide context, not essential data

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "figure_reference": null,
    "marks": 2,
    "difficulty": "easy"
  }}
]

Chapter Text:
{context}

IMPORTANT:
Return ONLY valid JSON.
Do NOT wrap JSON in markdown.
Do NOT add explanations.
Ensure the JSON array is complete and properly closed.

"""

LONG_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate only Long Answer Questions from the given text.
""" + COMMON_RULES + """
LONG ANSWER RULES:
- Answer MUST be copied verbatim from the chapter text
- Length should be a detailed explanation or multiple paragraphs.

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "question": "",
    "answer": "",
    "figure_reference": null,
    "marks": 5,
    "difficulty": "easy"
  }}
]

Chapter Text:
{context}
"""

CASE_BASE_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate Case-based Questions from the given text. A case-based question includes a context (passage) followed by multiple sub-questions.
""" + COMMON_RULES + """

QUESTION DISTRIBUTION RULE:
- Generate questions covering ALL concepts
- Each concept should produce at least one question

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
         "difficulty": "easy"
       }}
    ]
  }}
]

Chapter Text:
{context}
"""

CONCEPT_EXTRACTION_PROMPT = """
You are an NCERT textbook analyzer.

Extract the important concepts from the chapter text.

RULES:
- Use ONLY concepts present in the text
- Do NOT summarize
- Extract only core concepts
- Minimum 15 concepts
- Avoid duplicates

OUTPUT JSON FORMAT:
{{
  "concepts": [""]
}}

Text:
{context}
"""