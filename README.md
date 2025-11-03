MindMate — Setup & Quick Start

This README explains how to set up the project locally (Windows) and common next steps for developing the Django + AI-agent code.

Prerequisites
- Python 3.10 or newer (3.11 recommended)
- pip
- Git
- Optional but recommended: Docker & Docker Compose or WSL2/Conda for machine learning packages on Windows

1) Create a virtual environment (recommended)
- python -m venv .venv
- .venv\Scripts\activate

2) Install Python dependencies
- pip install --upgrade pip
- pip install -r requirements.txt

Notes on heavy ML packages (Windows)
- torch and faiss-cpu can be difficult on Windows. If pip install fails, use:
  - Official PyTorch selector: https://pytorch.org/get-started/locally/ (pick the correct CUDA/CPU wheel)
  - Or install via conda: conda install -c pytorch faiss-cpu
- Consider using WSL2 or Docker if you encounter build issues.


3) Database migrations and initial run
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py runserver

