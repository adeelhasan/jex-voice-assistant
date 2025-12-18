#!/bin/bash

# JEX Reset Script
# Usage:
#   ./reset.sh agent      # Restart only agent
#   ./reset.sh frontend   # Restart only frontend
#   ./reset.sh both       # Restart both (default)
#   ./reset.sh kill       # Kill all processes without restarting

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
AGENT_DIR="$SCRIPT_DIR/agent"
WEBAPP_DIR="$SCRIPT_DIR/webapp"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[JEX]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[JEX]${NC} $1"
}

print_error() {
    echo -e "${RED}[JEX]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[JEX]${NC} $1"
}

# Function to kill agent processes
kill_agent() {
    print_status "Killing agent processes..."

    # Kill Python agent processes
    pkill -f "python main.py" 2>/dev/null && print_success "Agent processes killed" || print_warning "No agent processes found"

    # Give it a moment
    sleep 1
}

# Function to kill frontend processes
kill_frontend() {
    print_status "Killing frontend processes..."

    # Kill Next.js dev server on port 3000
    lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null && print_success "Frontend processes killed" || print_warning "No frontend processes found on port 3000"

    # Also kill any node processes running next dev
    pkill -f "next dev" 2>/dev/null || true

    # Give it a moment
    sleep 1
}

# Function to start agent
start_agent() {
    print_status "Starting agent..."

    if [ ! -d "$AGENT_DIR" ]; then
        print_error "Agent directory not found: $AGENT_DIR"
        exit 1
    fi

    cd "$AGENT_DIR"

    # Check if virtual environment exists
    if [ -d "venv" ]; then
        print_status "Activating virtual environment..."
        source venv/bin/activate
    fi

    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_error "Agent .env file not found!"
        exit 1
    fi

    print_status "Starting Python agent in background..."
    nohup python main.py dev > agent.log 2>&1 &
    AGENT_PID=$!

    print_success "Agent started (PID: $AGENT_PID)"
    print_status "Logs: $AGENT_DIR/agent.log"
    print_status "View logs: tail -f $AGENT_DIR/agent.log"
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend..."

    if [ ! -d "$WEBAPP_DIR" ]; then
        print_error "Webapp directory not found: $WEBAPP_DIR"
        exit 1
    fi

    cd "$WEBAPP_DIR"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found, running npm install..."
        npm install
    fi

    # Check if .env.local exists
    if [ ! -f ".env.local" ]; then
        print_error "Frontend .env.local file not found!"
        exit 1
    fi

    print_status "Starting Next.js dev server in background..."
    nohup npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!

    print_success "Frontend started (PID: $FRONTEND_PID)"
    print_status "Logs: $WEBAPP_DIR/frontend.log"
    print_status "View logs: tail -f $WEBAPP_DIR/frontend.log"
    print_status "Open browser: http://localhost:3000"
}

# Function to show running processes
show_status() {
    print_status "Checking running processes..."
    echo ""

    # Check agent
    if pgrep -f "python main.py" > /dev/null; then
        AGENT_PID=$(pgrep -f "python main.py")
        print_success "Agent running (PID: $AGENT_PID)"
    else
        print_warning "Agent not running"
    fi

    # Check frontend
    if lsof -ti:3000 > /dev/null 2>&1; then
        FRONTEND_PID=$(lsof -ti:3000)
        print_success "Frontend running (PID: $FRONTEND_PID)"
    else
        print_warning "Frontend not running"
    fi

    echo ""
}

# Main script logic
case "${1:-both}" in
    agent)
        print_status "=== Restarting Agent Only ==="
        kill_agent
        start_agent
        echo ""
        show_status
        ;;

    frontend)
        print_status "=== Restarting Frontend Only ==="
        kill_frontend
        start_frontend
        echo ""
        show_status
        ;;

    both)
        print_status "=== Restarting Both Agent and Frontend ==="
        kill_agent
        kill_frontend
        echo ""
        start_agent
        echo ""
        start_frontend
        echo ""
        show_status
        ;;

    kill)
        print_status "=== Killing All Processes ==="
        kill_agent
        kill_frontend
        echo ""
        show_status
        ;;

    status)
        show_status
        ;;

    *)
        print_error "Unknown command: $1"
        echo ""
        echo "Usage:"
        echo "  ./reset.sh agent      # Restart only agent"
        echo "  ./reset.sh frontend   # Restart only frontend"
        echo "  ./reset.sh both       # Restart both (default)"
        echo "  ./reset.sh kill       # Kill all processes without restarting"
        echo "  ./reset.sh status     # Show running processes"
        exit 1
        ;;
esac

print_success "Done!"
