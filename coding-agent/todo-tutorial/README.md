# Running the Django App

This project uses [uv](https://github.com/astral-sh/uv) for Python environment and dependency management, and Django as the web framework.

## Prerequisites
- Python 3.8+
- [uv](https://github.com/astral-sh/uv) installed globally (`pip install uv`)

## Setup and Running

1. **Install dependencies** (if not already):
   ```sh
   uv sync --dev
   ```

2. **Apply database migrations:**
   ```sh
   uv run python manage.py migrate
   ```

3. **Run the development server:**
   ```sh
   uv run python manage.py runserver
   ```

4. Open your browser and go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
