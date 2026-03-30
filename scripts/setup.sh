#!/bin/bash
# Quick setup script for development

set -e

echo "=== Polymarket AI Trading Platform Setup ==="

# Backend
echo ""
echo "--- Setting up backend ---"
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env || echo ".env already exists"
deactivate
cd ..

# Web frontend
echo ""
echo "--- Setting up web frontend ---"
cd frontend/web
npm install
cp -n src/app/.env.example .env.local || echo ".env.local already exists"
cd ../..

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "2. Start services: docker compose up -d postgres redis"
echo "3. Start backend: cd backend && uvicorn src.main:app --reload"
echo "4. Start web: cd frontend/web && npm run dev"
echo ""
echo "Or run everything with: docker compose up --build"
