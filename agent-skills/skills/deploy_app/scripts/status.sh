#!/bin/bash
# Check deployment status

echo "Checking deployment status..."

# Check if web server is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ Web server is running"
else
    echo "✗ Web server is down"
fi

# Check database
if nc -z localhost 5432; then
    echo "✓ Database is accessible"
else
    echo "✗ Database is down"
fi
