"""
Refined prompt templates for NCERT/CBSE chapter workflows.

Drop-in notes:
- Variable names are kept compatible with your current code.
- JSON examples use double braces so `.format(...)` will preserve literal braces.
- All prompts enforce context-only generation and clean structured output.
"""


SUMMARY_PROMPT = """You are an NCERT textbook summarizer for students.
TASK:
Create concise chapter summary points from the given text.

STRICT RULES:
- Use ONLY information present in the given text
- Do NOT add outside facts, examples, or explanations
- Keep language simple, clear, and textbook-level
- Paraphrase only to shorten long sentences without changing meaning
- No opinions, interpretations, or commentary
- No numbering or bullet symbols inside sentences
- JSON output ONLY
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the answer in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

QUALITY RULES:
- Each item in "summary" must be exactly one complete sentence
- Prefer definitions, processes, cause-effect, and key ideas
- Avoid repeating the same concept across multiple lines

FAILSAFE:
- If text is empty or insufficient, return {{"summary":[]}}

OUTPUT JSON FORMAT (STRICT):
{{ "summary": [""] }}

Text:
{context}
"""


NOTES_PROMPT = """Create NCERT-based classroom study notes from the given text.

STRICT RULES:
- Use ONLY information present in the given text
- Do NOT introduce outside terminology, examples, or explanations
- Keep NCERT textbook tone (clear, factual, neutral)
- Paraphrase only to simplify sentence structure
- JSON output ONLY
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the answer in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

NOTES STRUCTURE:
- "title" should reflect the chapter/topic in the text
- "small_description" should be 1-2 simple sentences
- Each heading must represent a main concept from the text
- Each point must be short, factual, and directly supported by the text

FAILSAFE:
- If text is empty or insufficient, return:
  {{"title":"","small_description":"","notes":[]}}

OUTPUT JSON FORMAT (STRICT):
{{
  "title": "",
  "small_description": "",
  "notes": [{{ "heading": "", "points": [""] }}]
}}

Text:
{context}
"""


MINDMAP_PROMPT = """You are an NCERT curriculum expert and Mermaid mindmap generator.
TASK:
Extract concept hierarchy from the text and output Mermaid mindmap code.
CONTENT RULES (STRICT):
- Use ONLY concepts present in the given text
- Do NOT add external concepts, relations, or examples
- Do NOT explain or summarize
- Extract hierarchy only
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the mindmap labels in Devanagari (Hindi/Marathi).

STRUCTURE RULES (STRICT):
- Root = chapter/topic
- Level 1 = major concepts only
- Level 2 = subtopics directly under Level 1
- DO NOT create Level 3 under Level 2
- ABSOLUTE MAX DEPTH = 3 (root included)
- If a concept has deeper hierarchy, FLATTEN it to Level 2
- Do NOT nest subtopics under subtopics

MERMAID RULES (STRICT):
- Output MUST start with: mindmap
- Output ONLY Mermaid code
- Do NOT output JSON
- Do NOT output markdown code fences
- Do NOT add comments or explanations
- Use only these node styles:
  - root((Topic))
  - (Main Concept)
  - [Subtopic]

VALID FORMAT EXAMPLE:
mindmap
  root((Matter in Our Surroundings))
    (Matter)
      [Particles]
      [States of matter]
    (Properties)
      [Mass]
      [Volume]

INVALID EXAMPLE (DO NOT DO THIS):
mindmap
  root((Topic))
    (Concept)
      (Subconcept)
        [Detail]   ❌ Too deep

CORRECT VERSION:
mindmap
  root((Topic))
    (Concept)
      [Subconcept]
      [Detail]

- All leaf nodes MUST use [Subtopic]
- Do NOT use ( ) beyond Level 1
Text:
{context}
"""

LESSON_PLAN_PROMPT = """Create an NCERT-based lesson plan for classroom teaching.

STRICT RULES:
- Use ONLY information present in the given text
- Do NOT add external activities, examples, or facts
- Follow chapter concept order as it appears in the text
- Language must be clear, instructional, and teacher-friendly
- JSON output ONLY
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the answer in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

LESSSON PLAN REQUIREMENTS:
- learning_objectives: specific student learning outcomes from chapter content
- teaching_steps: logical concept flow in chapter order
- assessment: short oral/written checks answerable from chapter text

FAILSAFE:
- If text is empty or insufficient, return:
  {{"learning_objectives":[],"teaching_steps":[],"assessment":[]}}

OUTPUT JSON FORMAT (STRICT):
{{
  "learning_objectives": [""],
  "teaching_steps": [""],
  "assessment": [""]
}}

Text:
{context}
"""


WORKSHEET_PROMPT = """You are an NCERT worksheet creator for classroom teaching.
STRICT RULES:
- Use ONLY information present in the given text
- Do NOT introduce new facts, examples, or terminology
- Language must be simple and NCERT-level
- Paraphrasing is allowed ONLY to form clear questions
- Do NOT refer to figure numbers (Fig., Figure 1.1, etc.)
- Questions must be answerable without seeing any image
- JSON output ONLY
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the questions and answers in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

QUESTION COVERAGE RULE:
- Cover all major concepts from the chapter
- Avoid duplicate questions testing the same exact point

WORKSHEET STRUCTURE:
- Fill in the Blanks: key terms and factual concepts
- True/False: clear factual statements
- Match the Following: term-to-description pairs

OUTPUT JSON FORMAT (STRICT):
{{
  "title": "",
  "fill_in_the_blanks": [ {{ "question": "", "answer": "" }}],
  "true_false": [ {{ "statement": "", "answer": "" }}],
  "match_the_following": [ {{ "column_A": "", "column_B": "", "match": "" }}]
}}

Text:
{context}
"""


QUESTION_PAPER_PROMPT = """You are a CBSE/NCERT exam paper setter.
TASK:
Generate a question paper from the chapter text using the marks blueprint.

DIFFICULTY RULES (STRICT):
- easy: direct definition, one-line fact, naming
- medium: explanation requiring 2-3 related sentences from text
- hard: reasoning/comparison explicitly stated in text

ABSOLUTE RULES:
- Use ONLY information present in the Chapter Text
- Do NOT use outside knowledge or invented examples
- Keep key scientific terms exactly as in chapter text
- Question stems may be lightly rephrased for grammar
- Answers must remain text-faithful and context-supported
- Match marks blueprint EXACTLY
- Match required question counts EXACTLY for: mcq, fill_in_the_blanks, short_question, long_question
- JSON output ONLY
- No extra keys, no comments, no markdown
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the questions and answers in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

CSV JSON ROW RULES:
- Output MUST be a JSON array of flat row objects
- Every row MUST contain ALL of these exact keys:
  "Topics Name", "Subtopic Name", "Question Type", "Difficulty Level", "Question",
  "sub question type", "sub question", "Question Image",
  "Option A", "Option B", "Option C", "Option D", "Correct Option",
  "Answer", "Explanation"
- For non-applicable fields, use null (do not omit keys)
- Do NOT add a marks field (not part of CSV columns)

EXPLANATION FIELD RULES (TOKEN OPTIMIZATION):
- Generate "Explanation" ONLY for rows where:
  - "Question Type" is "mcq" or "fill_in_the_blank", OR
  - "Question Type" is "case_base_question" and "sub question type" is "mcq" or "fill_in_the_blank"
- For all other rows, set "Explanation": null

MATH / FORMULA RULES:
- Use KaTeX-compatible LaTeX for mathematical expressions
- Do NOT invent formulas not in the text
- If [FORMULA]...[/FORMULA] exists, copy formula content exactly
- Use JSON-safe escaping for backslashes (example: \\\\frac)

FIGURE HANDLING:
- If a question depends on a diagram/illustration, set "Question Image" accordingly
- If figure number exists in text, copy it exactly
- If no figure dependency, set null

QUESTION TYPE RULES:

MCQ:
- Exactly 4 options
- Exactly one correct option
- Correct option must be directly supported by text
- "Question Type" must be "mcq"
- "sub question type" and "sub question" must be null
- "Correct Option" must be one of: "A", "B", "C", "D"
- "Answer" must contain the correct option text
- "Explanation" must be one short context-supported reason

Fill in the Blanks:
- Remove exactly one key term/phrase supported by text
- "Question Type" must be "fill_in_the_blank"
- "sub question type" and "sub question" must be null
- Options A-D and Correct Option must be null
- "Explanation" must be one short context-supported reason

Short Answer:
- Prefer NCERT stems: Define, What is, Explain, Write, Name
- "Question Type" must be "short_question"
- "sub question type" and "sub question" must be null
- Options A-D and Correct Option must be null
- "Explanation" must be null

Long Answer:
- Prefer NCERT stems: Define, What is, Explain, Write, Name
- "Question Type" must be "long_question"
- "sub question type" and "sub question" must be null
- Options A-D and Correct Option must be null
- "Explanation" must be null

Case-based rows (optional, only if blueprint requires):
- "Question Type" must be "case_base_question"
- "Question" must contain case passage
- "sub question type" must be one of: "mcq", "fill_in_the_blank", "short_question", "long_question"
- "sub question" must contain the sub-question
- If "sub question type" is "mcq", fill options and correct option
- Else set options and correct option to null
- If "sub question type" is "mcq" or "fill_in_the_blank", include short "Explanation"
- Else set "Explanation" to null
- Answers should be fully derivable from chapter text

DIFFICULTY FIELD:
- For every row, "Difficulty Level" must be one of: "easy", "medium", "hard"
- Assign difficulty by cognitive demand:
  - easy: direct recall/definition
  - medium: explanation with 2-3 linked facts
  - hard: reasoning/comparison/inference explicitly supported by text
- Do NOT label all questions as "easy" unless the user explicitly asks for easy-only
- Keep a balanced spread of difficulty across the full paper whenever context allows

MARKS BLUEPRINT (STRICT):
{marks_json}

BLUEPRINT INTERPRETATION RULES:
- "mcq" -> rows with "Question Type": "mcq"
- "fill_in_the_blanks" -> rows with "Question Type": "fill_in_the_blank"
- "short_question" -> rows with "Question Type": "short_question"
- "long_question" -> rows with "Question Type": "long_question"
- "case_base_question" -> rows with "Question Type": "case_base_question"
- For case-based rows, "marks_each" applies per case sub-question row.

CASE-BASE POLICY (IMPORTANT):
- If blueprint includes "case_base_question" with count > 0:
  try to generate at least 1 valid case-based row.
- If chapter context does not support a valid case-based row, return 0 case-based rows (remove case rows), do NOT hallucinate.
- If blueprint does not include "case_base_question", do NOT generate any case-based rows.

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "mcq",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": null,
    "sub question": null,
    "Question Image": null,
    "Option A": "",
    "Option B": "",
    "Option C": "",
    "Option D": "",
    "Correct Option": "A",
    "Answer": "",
    "Explanation": ""
  }}
]

FAILSAFE:
- If blueprint cannot be satisfied from context, return [].

Chapter Text:
{context}
"""


ANSWER_KEY_PROMPT = """You are an exam evaluator.
TASK:
Generate an answer key for the provided question paper using ONLY the chapter context.
QUESTION PAPER:
{paper_json}

CONTEXT:
{context}

STRICT RULES:
- Provide an answer for EVERY question in the paper
- Use ONLY chapter-supported information
- Keep wording concise and factual
- JSON output ONLY
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the answers in Devanagari (Hindi/Marathi) while maintaining the structural JSON format.

OUTPUT JSON FORMAT (STRICT):
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
- easy: direct definition, one-line fact, naming from text
- medium: explanation from 2-3 related text sentences
- hard: explicit reasoning/comparison present in text
- Every question must include one value only: "easy" OR "medium" OR "hard" (never multiple values)
- Do NOT assign "easy" to all questions by default
- Maintain a difficulty mix across generated output whenever context supports it

ABSOLUTE CONTEXT RULES:
- Use ONLY information in the provided Chapter Text
- Do NOT use outside knowledge or invented content
- Preserve key scientific terms exactly as written
- Avoid duplicate or near-duplicate questions

TEXT FIDELITY RULES:
- Keep definitions text-faithful
- Do NOT alter meaning while simplifying language
- Do NOT replace key terms with synonyms if term precision matters

TOPIC / SUBTOPIC RULES:
- Derive topic and subtopic only from chapter text
- If not clearly available, set those fields to null

CSV JSON ROW RULES:
- Output MUST be a JSON array of flat row objects
- Every row MUST contain ALL of these exact keys:
  "Topics Name", "Subtopic Name", "Question Type", "Difficulty Level", "Question",
  "sub question type", "sub question", "Question Image",
  "Option A", "Option B", "Option C", "Option D", "Correct Option",
  "Answer", "Explanation"
- For non-applicable fields, use null (do not omit keys)

EXPLANATION FIELD RULES (TOKEN OPTIMIZATION):
- Generate "Explanation" ONLY for:
  - "Question Type" = "mcq" or "fill_in_the_blank"
  - OR "Question Type" = "case_base_question" with "sub question type" = "mcq" or "fill_in_the_blank"
- For all other rows, set "Explanation": null

MATH / LATEX RULES:
- Use KaTeX-compatible LaTeX only
- Do NOT invent formulas
- Preserve symbols, subscripts, superscripts, and units
- If [FORMULA]...[/FORMULA] exists, copy formula content exactly

JSON OUTPUT RULES:
- Output valid JSON only
- No markdown/code fences/comments
- No extra keys beyond requested schema
- No trailing commas
- Use proper escaping for backslashes in JSON strings

FAILSAFE:
- If sufficient support is missing in Chapter Text, return empty JSON structure for that task.
- MULTILINGUAL SUPPORT: If the Chapter Text is in Devanagari (Hindi/Marathi), generate the output in Devanagari (Hindi/Marathi) while maintaining the structural JSON format. Render Unicode characters as actual characters, not escape sequences.
"""

MCQ_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate ONLY Multiple Choice Questions (MCQs) from the chapter text.
""" + COMMON_RULES + """
MCQ RULES:
- Exactly 4 options per question
- Correct option must be directly supported by chapter text
- "Question Type" must be "mcq"
- "sub question type" and "sub question" must be null
- "Correct Option" must be one value from: "A", "B", "C", "D"
- "Answer" must contain the correct option text (not the letter)
- "Explanation" should justify why correct option is correct from chapter text
- "Difficulty Level" must be one of: "easy", "medium", "hard"

QUESTION DISTRIBUTION:
- Cover all major concepts
- At least one question per major concept whenever possible

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "mcq",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": null,
    "sub question": null,
    "Question Image": null,
    "Option A": "",
    "Option B": "",
    "Option C": "",
    "Option D": "",
    "Correct Option": "A",
    "Answer": "",
    "Explanation": ""
  }}
]

Chapter Text:
{context}
"""

FILL_BLANK_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate ONLY Fill in the Blanks questions from the chapter text.
""" + COMMON_RULES + """

FILL IN THE BLANK RULES:
- Remove exactly one key word/phrase from a meaningful sentence
- Removed word/phrase must exist verbatim in chapter text
- Blank should test concept or fact, not labels/references

FORBIDDEN:
- Figure numbers/references (Fig., Figure, etc.)
- Diagram labels/captions/table numbers
- Sentences that require visual interpretation

QUESTION FORMAT:
- Replace removed segment with exactly "_________"
- Keep sentence grammatically correct
- Generate maximum concept coverage without repetition
- "Question Type" must be "fill_in_the_blank"
- "sub question type" and "sub question" must be null
- Options and Correct Option must be null
- "Explanation" should be one short context-supported reason
- "Difficulty Level" must be one of: "easy", "medium", "hard"

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "fill_in_the_blank",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": null,
    "sub question": null,
    "Question Image": null,
    "Option A": null,
    "Option B": null,
    "Option C": null,
    "Option D": null,
    "Correct Option": null,
    "Answer": "",
    "Explanation": ""
  }}
]

Chapter Text:
{context}
"""

SHORT_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate ONLY Short Answer Questions from the chapter text.
""" + COMMON_RULES + """

SHORT ANSWER RULES:
- Questions should test understanding of concept/process/observation
- Answers must be directly derivable from chapter text
- Keep answers concise and textbook-faithful
- "Question Type" must be "short_question"
- "sub question type" and "sub question" must be null
- Options and Correct Option must be null
- "Explanation" must be null

FIGURE HANDLING:
- Questions may mention "given diagram/illustration" only when needed
- Do NOT include explicit figure numbers unless present in text
- Answers must remain understandable even without image access

QUESTION DISTRIBUTION:
- Cover all major concepts
- At least one question per major concept whenever possible
- "Difficulty Level" must be one of: "easy", "medium", "hard"

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "short_question",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": null,
    "sub question": null,
    "Question Image": null,
    "Option A": null,
    "Option B": null,
    "Option C": null,
    "Option D": null,
    "Correct Option": null,
    "Answer": "",
    "Explanation": null
  }}
]

Chapter Text:
{context}

IMPORTANT:
Return valid JSON array only. No markdown. No explanation.
"""

LONG_QUESTION_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate ONLY Long Answer Questions from the chapter text.
""" + COMMON_RULES + """
LONG ANSWER RULES:
- Questions should require connected multi-point explanation
- Answers must be fully supported by chapter text
- Keep answer flow coherent and text-faithful
- "Question Type" must be "long_question"
- "sub question type" and "sub question" must be null
- Options and Correct Option must be null
- "Explanation" must be null

QUESTION DISTRIBUTION:
- Cover all major concepts
- At least one long question per major concept cluster when possible
- "Difficulty Level" must be one of: "easy", "medium", "hard"

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "long_question",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": null,
    "sub question": null,
    "Question Image": null,
    "Option A": null,
    "Option B": null,
    "Option C": null,
    "Option D": null,
    "Correct Option": null,
    "Answer": "",
    "Explanation": null
  }}
]

Chapter Text:
{context}
"""

CASE_BASE_ONLY_PROMPT = """You are a CBSE/NCERT exam paper setter.
Generate ONLY case-based questions from the chapter text.
A case-based item must include one context passage and sub-questions.
""" + COMMON_RULES + """

CASE-BASED RULES:
- Case context must be derived from chapter content only
- Sub-questions must be answerable from the case and chapter text
- Avoid unsupported assumptions and outside scenarios
- Return FLAT rows (one row per sub-question), not nested objects
- "Question Type" must be "case_base_question"
- "Question" must contain the case passage (or case title + passage)
- "sub question" must contain the sub-question text
- "sub question type" must be one of: "mcq", "fill_in_the_blank", "short_question", "long_question"
- If sub question type is "mcq": fill options A-D and Correct Option
- If sub question type is not "mcq": set options A-D and Correct Option to null
- "Answer" must be for the sub-question
- If sub question type is "mcq" or "fill_in_the_blank": include short "Explanation"
- Else set "Explanation" to null
- "Difficulty Level" must match sub-question difficulty

QUESTION DISTRIBUTION:
- Cover all major concepts through multiple case sets

OUTPUT JSON FORMAT (STRICT):
[
  {{
    "Topics Name": "",
    "Subtopic Name": null,
    "Question Type": "case_base_question",
    "Difficulty Level": "easy",
    "Question": "",
    "sub question type": "short_question",
    "sub question": "",
    "Question Image": null,
    "Option A": null,
    "Option B": null,
    "Option C": null,
    "Option D": null,
    "Correct Option": null,
    "Answer": "",
    "Explanation": null
  }}
]

Chapter Text:
{context}
"""


CONCEPT_EXTRACTION_PROMPT = """You are an NCERT textbook analyzer.
TASK:
Extract important chapter concepts from the given text.
RULES:
- Use ONLY concepts present in the text
- Do NOT summarize or explain
- Extract core, non-duplicate concepts
- Minimum 15 concepts when text length allows
- Prefer textbook terms over generic words
- JSON output ONLY
FAILSAFE:
- If text is insufficient, return {{"concepts":[]}}
OUTPUT JSON FORMAT:
{{ "concepts": [""] }}
Text:
{context}
"""
