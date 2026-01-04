# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Iraq Education AI Assistant - A Flask-based web application for Iraqi schools providing AI-powered educational tools. Full Arabic language support with RTL interface.

## Development Commands

```bash
# Environment setup
conda env create -f environment.yml
conda activate iraq-edu-ai

# Configure environment
cp .env.example .env
# Set FLASK_SECRET_KEY in .env

# Run development server (http://127.0.0.1:5000)
python run.py
```

## Architecture

### Tech Stack
- **Backend**: Flask 3.x, Python 3.11, SQLite
- **Frontend**: Bootstrap 5.3.3 RTL, Jinja2 templates, vanilla JavaScript
- **NLP**: scikit-learn (TF-IDF), custom Arabic tokenization

### Core Modules (`app/services/`)

| Module | Purpose |
|--------|---------|
| `lesson_planner.py` | Teacher lesson plan generation with 3 templates (concepts, problem-solving, reading comprehension) |
| `quiz_generator.py` | TF-IDF-based quiz generation (MCQ, fill-blank, true/false, short answer) |
| `study_planner.py` | Student study plans with spaced repetition (review at days 1, 3, 7, 14) |
| `reading_analyzer.py` | Arabic text difficulty scoring and analysis |
| `adaptive_quiz.py` | Adaptive difficulty quiz engine for computer lab (levels 1-3) |
| `arabic_nlp.py` | Arabic text normalization, tokenization, stopword removal |

### Application Structure
- `app/__init__.py` - Flask app factory (`create_app()`)
- `app/routes.py` - All endpoints in single blueprint
- `app/db.py` - SQLite operations (tables: study_plans, reading_results, quiz_runs)
- `app/data/` - Seed data (curriculum config, question bank)
- `run.py` - Application entry point

### API Endpoints

```
POST /api/teacher/lesson-plan    - Generate lesson plans
POST /api/teacher/quiz-generate  - Generate quizzes from text
POST /api/student/study-plan     - Build study schedules
POST /api/student/reading-analyze - Analyze text difficulty
GET  /api/lab/next-question      - Get adaptive quiz question
POST /api/lab/answer             - Submit answer
POST /api/lab/reset              - Reset quiz session
```

## Key Implementation Details

- **Quiz Generation**: Extracts top terms via TF-IDF, creates questions cyclically across 4 types
- **Difficulty Formula**: `0.4*avg_words_per_sent + 0.3*avg_chars_per_word + 0.3*(1-TTR)*20`
- **Adaptive Quiz**: Level calculated as `clamp(2 + score//2, 1..3)`, tracks asked questions to prevent repeats
- **Arabic NLP**: Normalizes alef/ya/ta-marbuta variants, removes diacritics, 58+ stopwords

## Language Considerations

All user-facing content is in Arabic. Templates use `lang="ar" dir="rtl"`. The Cairo font is used for Arabic typography.
