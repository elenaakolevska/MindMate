MindMate — Setup & Quick Start

This README explains how to set up the project locally (Windows) and common next steps for developing the Django + AI-agent code.

Prerequisites
- Python 3.10 or newer (3.11 recommended)
- pip
- Git
- Optional but recommended: Docker & Docker Compose or WSL2/Conda for machine learning packages on Windows

Local Development (without Docker)
1) Create a virtual environment (recommended)
   - python -m venv .venv
   - .venv\Scripts\activate
2) Install Python dependencies
   - pip install --upgrade pip
   - pip install -r requirements.txt
3) Database migrations and initial run
   - python manage.py migrate
   - python manage.py createsuperuser
   - python manage.py runserver

Notes on heavy ML packages (Windows)
- torch and faiss-cpu can be difficult on Windows. If pip install fails, use:
  - Official PyTorch selector: https://pytorch.org/get-started/locally/ (pick the correct CUDA/CPU wheel)
  - Or install via conda: conda install -c pytorch faiss-cpu
- Consider using WSL2 or Docker if you encounter build issues.

Docker Compose Setup (recommended for production or team development)
1) Copy .env.example to .env and fill in your secrets and database credentials.
2) Build and start the containers:
   - docker compose up --build
3) The following services will start:
   - db: PostgreSQL database
   - web: Django app (served by Gunicorn)
4) Access the app at http://localhost:8000
5) To stop the containers:
   - docker compose down

.env file
- Required for both local and Docker Compose setups.
- See .env.example for all required variables.
- Never commit your real .env to version control.

Troubleshooting
- If you see errors about static files, make sure STATIC_ROOT is set in settings.py.
- If dependencies reinstall every time, check your Dockerfile for unnecessary COPY or RUN steps.
- For database connection issues, verify your .env matches .env.example and the docker-compose.yml environment variables.

AI Agent Setup
- Add your AI service keys (OpenAI, Pinecone, etc.) to .env if needed.
- Install extra dependencies for AI agents as required (see requirements.txt).

For more info, see:
- Django docs: https://docs.djangoproject.com/
- Docker Compose docs: https://docs.docker.com/compose/
- AI agent frameworks: LangChain, OpenAI, etc.
