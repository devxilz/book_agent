from ollama import chat

response = chat(
    model="qwen2.5vl:7b",
    messages=[
        {
            "role": "user",
            "content": """
Extract every handwritten word from this notebook page.

Return plain text only.

Do not summarize.
Do not interpret.
Keep line breaks exactly as seen.
If something is unreadable, write [UNCLEAR].
""",
            "images": [r"C:\Users\user\Documents\ai_book_teacher\Screenshot 2026-07-03 015335.png"],
        }
    ],
)

print(response["message"]["content"])