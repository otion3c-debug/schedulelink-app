#!/bin/bash
# ScheduleLink - Production Start Script v2.1.0
# Starts backend + ngrok tunnel (if available)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       ${BOLD}📅 ScheduleLink v2.1.0${NC}${CYAN}              ║${NC}"
echo -e "${CYAN}║    Production-Ready Scheduling SaaS        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$NGROK_PID" ]; then
        kill $NGROK_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Stopped all services${NC}"
    exit 0
}
trap cleanup INT TERM

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

# Check for virtual environment
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    cd ..
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    source backend/venv/bin/activate
fi

# Initialize database
echo -e "${BLUE}Initializing database...${NC}"
cd backend
python -c "from app.database import init_db; init_db()" 2>/dev/null
cd ..
echo -e "${GREEN}✓ Database ready${NC}"

# Kill any existing process on port 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null || true

# Start backend
echo -e "${BLUE}Starting backend on port 8080...${NC}"
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level warning &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Backend failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"

# Check for ngrok
if command -v ngrok &> /dev/null; then
    # Check if ngrok is configured
    if ngrok config check 2>&1 | grep -q "Valid"; then
        echo -e "${BLUE}Starting ngrok tunnel...${NC}"
        
        # Kill any existing ngrok
        pkill ngrok 2>/dev/null || true
        sleep 1
        
        # Start ngrok in background
        ngrok http 8080 --log=stdout > /tmp/ngrok.log 2>&1 &
        NGROK_PID=$!
        
        # Wait for ngrok to start
        sleep 3
        
        # Get ngrok URL
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)
        
        if [ -n "$NGROK_URL" ]; then
            echo -e "${GREEN}✓ ngrok tunnel active${NC}"
            
            # Update .env with ngrok URL
            if [ -f backend/.env ]; then
                # macOS compatible sed
                sed -i '' "s|^FRONTEND_URL=.*|FRONTEND_URL=$NGROK_URL|" backend/.env 2>/dev/null || \
                sed -i "s|^FRONTEND_URL=.*|FRONTEND_URL=$NGROK_URL|" backend/.env
                
                # Update Google redirect URI
                sed -i '' "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=$NGROK_URL/api/auth/google/callback|" backend/.env 2>/dev/null || \
                sed -i "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=$NGROK_URL/api/auth/google/callback|" backend/.env
            fi
            
            # Restart backend to pick up new URL
            kill $BACKEND_PID 2>/dev/null
            sleep 1
            cd backend
            uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level warning &
            BACKEND_PID=$!
            cd ..
            sleep 2
            
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════${NC}"
            echo ""
            echo -e "  ${GREEN}${BOLD}✓ ScheduleLink is running!${NC}"
            echo ""
            echo -e "  ${CYAN}Public URL:${NC}    ${BOLD}$NGROK_URL${NC}"
            echo -e "  ${CYAN}Booking Page:${NC}  $NGROK_URL/#/book/YOUR_USERNAME"
            echo -e "  ${CYAN}API Docs:${NC}      $NGROK_URL/docs"
            echo ""
            echo -e "  ${CYAN}Local URL:${NC}     http://localhost:8080"
            echo ""
            echo -e "${GREEN}════════════════════════════════════════════${NC}"
            echo ""
            echo -e "  ${YELLOW}Share the Public URL with anyone to let them${NC}"
            echo -e "  ${YELLOW}book meetings on your calendar!${NC}"
            echo ""
            
            # Open in browser
            if command -v open &> /dev/null; then
                open "$NGROK_URL"
            fi
            
        else
            echo -e "${YELLOW}⚠ ngrok started but could not get URL${NC}"
            echo -e "  Check ngrok status at: http://localhost:4040"
            echo ""
            echo -e "  ${CYAN}Local URL:${NC} ${BOLD}http://localhost:8080${NC}"
            
            if command -v open &> /dev/null; then
                open "http://localhost:8080"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ ngrok not configured${NC}"
        echo ""
        echo -e "  To configure ngrok:"
        echo -e "    1. Sign up at ${CYAN}https://ngrok.com${NC} (free)"
        echo -e "    2. Get your authtoken from the dashboard"
        echo -e "    3. Run: ${BOLD}ngrok config add-authtoken YOUR_TOKEN${NC}"
        echo ""
        echo -e "  ${CYAN}Local URL:${NC} ${BOLD}http://localhost:8080${NC}"
        echo ""
        
        if command -v open &> /dev/null; then
            open "http://localhost:8080"
        fi
    fi
else
    echo -e "${YELLOW}⚠ ngrok not installed - running locally only${NC}"
    echo ""
    echo -e "  To install ngrok:"
    echo -e "    brew install ngrok  (macOS)"
    echo -e "  Then sign up at ngrok.com and:"
    echo -e "    ngrok config add-authtoken YOUR_TOKEN"
    echo ""
    echo -e "  ${CYAN}Local URL:${NC} ${BOLD}http://localhost:8080${NC}"
    echo ""
    
    if command -v open &> /dev/null; then
        open "http://localhost:8080"
    fi
fi

echo -e "Press ${RED}Ctrl+C${NC} to stop all services."
echo ""

# Wait for processes
wait $BACKEND_PID
