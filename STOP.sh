#!/bin/bash
# ScheduleLink - Stop Script
# Stops all running services

echo "Stopping ScheduleLink services..."

# Kill backend
pkill -f "uvicorn app.main" 2>/dev/null && echo "✓ Backend stopped" || echo "Backend not running"

# Kill ngrok
pkill ngrok 2>/dev/null && echo "✓ ngrok stopped" || echo "ngrok not running"

# Kill anything on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null && echo "✓ Port 8080 cleared" || true

echo "Done."
