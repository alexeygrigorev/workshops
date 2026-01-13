# Makefile for OpenCode prototype
# Usage: make <target>

.PHONY: help install test test-v test-skills test-agent-skills test-commands test-cov lint format clean run
.PHONY: run-hello run-joke run-standards list-skills list-commands


# Python commands
PYTHON := uv run python
PYTEST := uv run pytest

install:
	@echo "Installing dependencies..."
	uv sync

test:
	@echo "Running tests with verbose output..."
	$(PYTEST) tests/ -vv -s


run:
	@echo "Starting interactive agent session..."
	$(PYTHON) tests/test_agent_run.py --interactive

