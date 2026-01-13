#!/bin/bash
# Check if code follows project coding standards

echo "Checking coding standards..."

# Check for type hints
echo "Checking for type hints..."
grep -r "def " --include="*.py" src/ | grep -v " -> " | grep -v "# type: ignore" && echo "ERROR: Functions without type hints found!" || echo "✓ Type hints present"

# Check for docstrings
echo "Checking for docstrings..."
python -m py_docstyle src/ || echo "WARNING: Some functions missing docstrings"

# Check line length
echo "Checking line length..."
python -m pycodestyle --max-line-length=100 src/

echo "Standards check complete!"
