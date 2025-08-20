# Makefile for Django Template

.PHONY: install migrate run test clean

install:
	uv sync --dev

migrate:
	uv run python manage.py makemigrations
	uv run python manage.py migrate

run:
	uv run python manage.py runserver

test:
	uv run python manage.py test

clean:
	rm -rf __pycache__ myapp/__pycache__ myproject/__pycache__
	rm -rf db.sqlite3
