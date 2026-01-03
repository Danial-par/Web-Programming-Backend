# Django + DRF Backend - HW2

## Requirements
- Python 3.11+
- SQLite (default)
- Django + DRF only

## Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
