# Code Quality Dashboard

Analyze Python code quality and get AI-powered recommendations powered by Groq (Llama 3.3 70B).

## Features

- Upload Python projects as .zip or analyze GitHub repos
- Quality score 0-10 with animated ring chart
- Issue detection — long functions, missing docstrings, large files, syntax errors
- AI recommendations — specific, actionable improvement suggestions
- Previous analysis history

## Tech Stack

- **Backend** — Python, Flask, SQLAlchemy, SQLite, AST parsing
- **AI** — Groq API (Llama 3.3 70B)
- **Frontend** — Vanilla JS, custom CSS

## Setup

1. Clone the repo
2. `python -m venv venv` then activate
3. `pip install -r requirements.txt`
4. Add `GROQ_API_KEY=your_key` to `.env`
5. `python app.py`
6. Open `http://localhost:5008`

## What It Analyzes

- Functions exceeding 50 lines
- Missing docstrings across all functions
- Files exceeding 300 lines
- Syntax errors
- OOP usage patterns

## Screenshots

<img width="1920" height="980" alt="Screenshot (49)" src="https://github.com/user-attachments/assets/4de87768-a98d-440d-a151-eef5ca1127e2" />
<img width="1920" height="982" alt="Screenshot (50)" src="https://github.com/user-attachments/assets/9ee70ba2-9255-4898-bb0e-cb61db833843" />
