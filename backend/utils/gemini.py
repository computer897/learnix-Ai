import os
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

USE_MOCKS = os.getenv("USE_MOCKS", "1") == "1"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def generate_answer_from_context(question: str, contexts: List[str]) -> str:
    if USE_MOCKS or not GEMINI_API_KEY:
        return _generate_mock_answer(question, contexts)
    else:
        return _generate_gemini_answer(question, contexts)


def _generate_mock_answer(question: str, contexts: List[str]) -> str:
    if not contexts or all(not c.strip() for c in contexts):
        return f"🤖 Mock Answer: No relevant content found for '{question}'. Upload materials first!"

    relevant_contexts = [ctx[:500] + "..." if len(ctx) > 500 else ctx for ctx in contexts[:3] if ctx.strip()]
    joined = "\n\n---\n\n".join(relevant_contexts)
    return f"""🤖 Mock Answer for: "{question}"

Based on the uploaded documents:

{joined}

---
💡 Note: This is a mock mode response. Enable USE_MOCKS=0 and set GEMINI_API_KEY for real AI answers."""


def _generate_gemini_answer(question: str, contexts: List[str]) -> str:
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')

        cleaned_contexts = []
        for ctx in contexts[:10]:
            lines = ctx.split('\n')
            clean_lines = [
                line for line in lines if not any(p in line.lower() for p in [
                    'page', 'chapter', 'section', '.pdf', '.docx',
                    'copyright', 'isbn', 'folio', 'compref'
                ])
            ]
            cleaned_contexts.append('\n'.join(clean_lines))
        context_text = "\n\n".join(cleaned_contexts)

        question_lower = question.lower()
        short_keywords = ['define', 'what is', 'list', 'mention', '2 mark', 'brief', 'short note']
        is_short_question = any(k in question_lower for k in short_keywords) and len(question.split()) < 15

        if is_short_question:
            prompt = f"""
You are Learnix — an AI tutor that provides concise academic answers.

Context from uploaded materials:
---
{context_text}
---

**Question:** {question}

This is a SHORT ANSWER (2 marks). Generate a brief, precise, and well-formatted response.

**REQUIREMENTS:**
- Keep answer to 2-4 lines maximum
- Use **bold** for key terms and important concepts
- Be factual and direct - no unnecessary explanation
- Use proper sentence structure with line breaks if needed
- Avoid filler words or repetition

**FORMAT:**
Return the answer in clean Markdown format. You may use:
- **Bold** for emphasis
- Brief bullet points if listing (max 3-4 points)
- Clear, readable structure

Start your answer directly without adding "Answer (2 Marks):" prefix.
"""
        else:
            prompt = f"""
You are Learnix — an advanced academic chatbot that generates well-structured, formatted, and adaptive answers.

Context from uploaded materials:
---
{context_text}
---

**Question:** {question}

This is a DETAILED ANSWER (16 marks). Generate a comprehensive academic response following these requirements:

**STRUCTURE REQUIREMENTS:**
Break the content into clear sections with proper Markdown headings:

## Definition / Concept
Explain the core concept and definition clearly (3-4 sentences)

## Explanation / Implementation / Procedure  
Provide step-by-step explanation or procedure. Include algorithms or implementation details if applicable.

## Advantages / Disadvantages
- Use bullet points for advantages
- Include disadvantages if relevant
- Keep points concise and specific

## Applications / Use Cases
Explain real-world applications and where this concept is used

## Example
Provide a practical example or scenario. If explaining algorithms or code:
```python
# Include properly formatted code blocks with syntax highlighting
# Use appropriate language identifier (python, java, c, etc.)
```

## Summary
Conclude with a brief 2-3 sentence summary

**FORMATTING REQUIREMENTS:**
1. Use ## for main section headings (Definition, Explanation, etc.)
2. Use ### for subheadings within sections if needed
3. Add blank lines between ALL sections and paragraphs
4. Use bullet points (-) for lists, NOT numbered lists in advantages/applications
5. Use **bold** for key terms and important concepts
6. Include code blocks with ```language syntax when explaining algorithms
7. Break long paragraphs - avoid single paragraph responses
8. Write 800-1200 words total
9. Maintain academic and professional tone
10. Avoid repetition and filler content

**CONTENT REQUIREMENTS:**
- Use context from uploaded material FIRST
- If material lacks detail, extend using your knowledge
- Ensure readability with proper line breaks
- Make sure each section has substance (not just 1-2 lines)
- Include technical depth appropriate for 16-mark academic answer

Return ONLY the formatted Markdown response. Start directly with the first ## heading.
"""

        response = model.generate_content(prompt)
        answer = response.text.strip()

        # --- Enhanced Cleanup Formatting ---
        # 1. Ensure proper spacing around ## headings
        answer = re.sub(r'(?<!\n)\n(##\s)', r'\n\n\1', answer)  # blank line before ##
        answer = re.sub(r'(##[^\n]+)\n(?!\n)', r'\1\n\n', answer)  # blank line after ##
        
        # 2. Ensure proper spacing around ### subheadings
        answer = re.sub(r'(?<!\n)\n(###\s)', r'\n\n\1', answer)  # blank line before ###
        answer = re.sub(r'(###[^\n]+)\n(?!\n)', r'\1\n\n', answer)  # blank line after ###
        
        # 3. Ensure proper spacing around **bold section markers** (if AI uses this style)
        answer = re.sub(r'(?<!\n)\n(\*\*[A-Z][^*]+\*\*:?\s*\n)', r'\n\n\1', answer)  # blank line before
        answer = re.sub(r'(\*\*[A-Z][^*]+\*\*:?\s*)\n(?!\n)', r'\1\n\n', answer)  # blank line after
        
        # 4. Break long paragraphs (add line break after sentences if paragraph is too long)
        answer = re.sub(r'(\.\s+)([A-Z][^.]{50,})', r'.\n\n\2', answer)
        
        # 5. Ensure proper spacing around code blocks
        answer = re.sub(r'(?<!\n)\n(```)', r'\n\n\1', answer)  # blank line before code
        answer = re.sub(r'(```)\n(?!\n)', r'\1\n\n', answer)  # blank line after code
        
        # 6. Ensure proper spacing around bullet points
        answer = re.sub(r'(?<!\n)\n(-\s)', r'\n\n\1', answer, count=1)  # blank line before first bullet
        answer = re.sub(r'(\n-[^\n]+)\n\n(##)', r'\1\n\2', answer)  # remove extra space between bullets and next heading
        
        # 7. Prevent excessive blank lines (max 2 newlines)
        answer = re.sub(r'\n{3,}', '\n\n', answer)
        
        # 8. Clean up any remaining formatting issues
        answer = answer.strip()

        logger.info("✅ Gemini answer generated with enhanced formatting")
        return answer

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"Error generating answer: {str(e)}"


def test_gemini_connection() -> bool:
    if not GEMINI_API_KEY:
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        return bool(model.generate_content("Hello").text)
    except:
        return False
