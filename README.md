# 🎓 Kelajak — AI-Powered Study Abroad Platform for Uzbekistan High School Students

**Kelajak** is a full-stack Django MVP designed specifically for 9th–11th grade high school students in Uzbekistan who aspire to win international scholarships and exchange programs (such as **Global UGRAD**, **Türkiye Bursları**, **DAAD**, **Chevening**, and **El-Yurt Umidi**).

---

## 🌟 Key Features

1. **Phone-Based Authentication (`apps/accounts`)**:
   - Frictionless phone registration with canonical Uzbek format (`+998XXXXXXXXX`).
   - Normalization and validation across all major national operators (90, 91, 93, 94, 95, 97, 98, 99, 33, 50, 71, 77, 88).
   - Superuser-only protection for student personal identifiable information (PII).

2. **Onboarding & Diagnostic Engine (`apps/onboarding`)**:
   - Multi-step intake wizard capturing student grade (9–11), target countries, goal, and English level.
   - Comprehensive diagnostic assessment evaluating 5 skill dimensions: **Reading, Writing, Listening, Speaking, Grammar**.
   - Immediate baseline score generation and `overall_ready_score` (0–100) calculation.

3. **AI Study Plan Generator (`apps/study_plans`)**:
   - Generates personalized study plans via Claude 3.5 Sonnet structured JSON.
   - Auto-configures timeline (up to 1 year for 9th graders, 6 months for 10th graders, 3–4 months for 11th graders).
   - Atomically transitions active plans so each student has exactly one active roadmap.

4. **Daily Task Engine & Claude Grading (`apps/tasks`)**:
   - Daily automated generation of targeted practice tasks (e.g. grammar drills and reading comprehension passages) focused on the student's weakest skill.
   - Intelligent grading via Claude with mandatory **explanatory reasoning** (`ai_feedback`) breaking down why an answer is correct or incorrect.

5. **Gamified Dashboard & Score Decay (`apps/dashboard`)**:
   - Real-time **Ready Score** (0–100) and consecutive daily active **streak counter** (🔥).
   - 5-skill visual progress bars with level badges (Boshlang'ich, O'rta, Kuchli).
   - `python manage.py decay_scores` management command to simulate real-world score decay and streak reset for inactive days.

6. **Context-Injected AI Mentor Chat (`apps/mentor`)**:
   - Personal AI mentor with full context injection: student profile, 5 skill scores, active study plan, recent task performance, and admin-verified programs.
   - **Admission Safety Guardrails**: Strict refusal to guarantee admissions, framing suggestions as guidance, and deferring decisions to the family.
   - **Unverified Program Fallback**: Explicitly responds with `"Men bu haqda tasdiqlangan ma'lumotga ega emasman"` when asked about unknown/unverified programs.

7. **Verified Programs Directory (`apps/programs`)**:
   - Admin-verified catalog of scholarships and exchange programs.
   - Mandatory verification integrity: each program must have a verified `source_url` and `last_verified_date`.
   - Seed command `python manage.py seed_programs` populated with real Uzbekistan-eligible programs.

8. **Trust & Safety & 100% Uzbek Latin UI (`apps/core`)**:
   - Visible disclaimer across all AI mentor chat, tasks, and program recommendation pages:
     > *"AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."*
   - 100% Uzbek Latin script UI templates with mobile-first responsive layout (bottom navigation on mobile, top bar on desktop).

---

## 🏗️ Architecture & Tech Stack

- **Backend Framework**: Django 5.x (Python 3.11+)
- **Database**: SQLite (Development / Testing) / PostgreSQL (Production ready)
- **Frontend / Styling**: Server-rendered Django templates with Tailwind CSS (standalone CSS fallback + CDN)
- **AI Integration**: Claude 3.5 Sonnet (`anthropic` SDK) with robust `MockClaudeClient` fallback for deterministic offline execution
- **Security**: Strict PII protection, CSRF protection, PBKDF2 password hashing, zero hardcoded API keys

---

## 🚀 Installation & Quickstart

### 1. Prerequisites
- Python 3.11 or higher
- Git

### 2. Setup Virtual Environment & Dependencies
```bash
# Clone repository
git clone <repository_url>
cd study

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root:
```ini
SECRET_KEY=your-secure-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DISCLAIMER_TEXT="AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
```
*(Note: If `ANTHROPIC_API_KEY` is not provided or empty, the platform automatically runs in deterministic offline mock mode via `MockClaudeClient`.)*

### 4. Database Setup & Seeding
```bash
# Run database migrations
python manage.py migrate

# Seed verified scholarship programs (Global UGRAD, DAAD, Türkiye Bursları, Chevening, El-Yurt Umidi)
python manage.py seed_programs

# Create an administrator account
python manage.py createsuperuser
```

### 5. Run the Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🛠️ Management Commands

### Seed Verified Programs
```bash
python manage.py seed_programs
```
Populates or updates verified scholarship programs with official sources, deadlines, and verification timestamps.

### Score Decay Engine
```bash
python manage.py decay_scores --points 2
```
Checks for students who did not complete any daily tasks yesterday, decays their skill scores by the specified amount (default: 2 points), resets their streak to 0, and records a progress log entry. Can be scheduled via cron or Celery beat.

---

## 🧪 Testing & Verification

The project includes an exhaustive 5-tier opaque-box test suite:

- **Tier 1 (Features)**: `tests/test_tier1_features.py` — Verifies core features (F1 through F12).
- **Tier 2 (Boundaries)**: `tests/test_tier2_boundaries.py` — Tests phone normalization variations, score clamping [0, 100], and empty/extreme inputs.
- **Tier 3 (Combinations)**: `tests/test_tier3_combinations.py` — Tests multi-day streak progressions, decay recovery, and atomic study plan transitions.
- **Tier 4 (Scenarios)**: `tests/test_tier4_scenarios.py` — Tests end-to-end real-world journeys (9th grader Malika, 11th grader Jasur, admin audit).
- **Tier 5 (Adversarial Hardening)**: `tests/test_tier5_adversarial.py` — Tests prompt injection defenses, seed command idempotency, unauthenticated access blocks.
- **Trust & Safety Audit**: `tests/test_trust_safety.py` — Scans for zero hardcoded API keys (`sk-ant-`), 100% Uzbek Latin script, and mandatory disclaimers.

### Run All Tests:
```bash
python manage.py test tests
```

---

## 🛡️ Trust & Safety Compliance Summary

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| **Mandatory Disclaimer** | Rendered via `templates/includes/disclaimer.html` on all AI chat, task, and program pages. | Tested in `test_trust_safety.py` and `test_m4_mentor_programs_localization.py`. |
| **Zero Hardcoded Keys** | Keys loaded strictly from `os.environ` / `.env`. | Automated regex scan in `test_trust_safety.py`. |
| **Safety Guardrails** | System prompt instructs AI never to guarantee admission and to use `"Men bu haqda tasdiqlangan ma'lumotga ega emasman"` for unverified programs. | Tested in `test_m4_mentor_programs_localization.py` and `test_tier5_adversarial.py`. |
| **100% Uzbek Latin UI** | All UI strings, navigation, labels, and error messages in Latin-script Uzbek. | Verified across all templates and tested in `test_trust_safety.py`. |
| **Admin PII Security** | Student profiles and personal diagnostic data restricted to superusers only. | Tested in `test_m1_adversarial.py` and `test_trust_safety.py`. |
