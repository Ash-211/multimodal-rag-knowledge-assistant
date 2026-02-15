@echo off

echo Starting both frontend and backend development servers

REM Start the backend in a new cmd and keep it open
start cmd /k "cd backend && uvicorn main:app --reload"

REM Start the frontend in a new cmd and keep it open
start cmd /k "cd frontend && npm run dev"