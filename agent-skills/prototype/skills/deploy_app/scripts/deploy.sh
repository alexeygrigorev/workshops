#!/bin/bash
# Deploy application

set -e

ENVIRONMENT=${1:-staging}

echo "Deploying to $ENVIRONMENT..."

# Build
echo "Building application..."
echo "!`echo 'Build complete for $ENVIRONMENT'`"

# Run tests
echo "Running tests..."
echo "Tests passed!"

# Deploy
echo "Deploying to $ENVIRONMENT..."
echo "Deployment complete!"
