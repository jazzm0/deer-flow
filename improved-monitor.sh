#!/bin/bash
# Enhanced DeerFlow Monitor - Shows errors and active status
# Usage: ./improved-monitor.sh [--watch]

WATCH_MODE=false
if [ "$1" = "--watch" ] || [ "$1" = "-w" ]; then
    WATCH_MODE=true
fi

check_status() {
    clear
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║                    DeerFlow Enhanced Monitor                           ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "⏰ Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # Container Status
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Container Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker ps --filter "name=deer-flow" --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
    echo ""

    # API Health
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 API Health Check"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:2026/api/models 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ API responding (HTTP $HTTP_CODE)"
    else
        echo "❌ API not responding properly (HTTP $HTTP_CODE)"
    fi
    echo ""

    # Check for LangGraph errors
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔥 Recent Critical Errors (last 20 lines)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    ERRORS=$(docker logs deer-flow-langgraph 2>&1 | tail -200 | grep -i "error\|exception\|failed\|ValueError" | tail -20)
    if [ -z "$ERRORS" ]; then
        echo "✅ No recent critical errors"
    else
        echo "$ERRORS" | while IFS= read -r line; do
            # Highlight specific error types
            if echo "$line" | grep -q "multiple non-consecutive system messages"; then
                echo "🚨 CRITICAL: $line"
            elif echo "$line" | grep -q "ValueError"; then
                echo "⚠️  $line"
            elif echo "$line" | grep -q "Background run failed"; then
                echo "❌ $line"
            else
                echo "$line"
            fi
        done
    fi
    echo ""

    # Active runs
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🏃 Run Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    RECENT_LOGS=$(docker logs deer-flow-langgraph 2>&1 | tail -100)

    STARTED=$(echo "$RECENT_LOGS" | grep "Starting background run" | wc -l | tr -d ' ')
    COMPLETED=$(echo "$RECENT_LOGS" | grep "Background run.*completed" | wc -l | tr -d ' ')
    FAILED=$(echo "$RECENT_LOGS" | grep "Background run.*failed" | wc -l | tr -d ' ')

    echo "📊 Last 100 log lines:"
    echo "   • Started: $STARTED"
    echo "   • Completed: $COMPLETED"
    echo "   • Failed: $FAILED"

    # Check if stuck (no logs in last 5 minutes)
    LAST_LOG_TIME=$(docker exec deer-flow-langgraph stat -c %Y /app/logs/langgraph.log 2>/dev/null || echo "0")
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_LOG_TIME))

    if [ "$TIME_DIFF" -gt 300 ] && [ "$LAST_LOG_TIME" != "0" ]; then
        echo ""
        echo "⚠️  WARNING: No activity for ${TIME_DIFF}s (may be stuck)"
    else
        echo "   • Status: Active (last update ${TIME_DIFF}s ago)"
    fi
    echo ""

    # Show last 3 run statuses
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 Last 3 Run Results"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker logs deer-flow-langgraph 2>&1 | grep -E "Background run (completed|failed)" | tail -3 | while read -r line; do
        if echo "$line" | grep -q "completed"; then
            echo "✅ $line"
        else
            echo "❌ $line"
        fi
    done
    echo ""

    # Show recent HTTP requests
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Recent HTTP Activity (last 5)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker logs deer-flow-langgraph 2>&1 | grep "HTTP Request:" | tail -5 | while read -r line; do
        if echo "$line" | grep -q "200 OK"; then
            echo "✅ ${line##*HTTP Request: }"
        else
            echo "⚠️  ${line##*HTTP Request: }"
        fi
    done
    echo ""
}

if [ "$WATCH_MODE" = true ]; then
    echo "🔄 Starting watch mode (updates every 10 seconds, Ctrl+C to exit)..."
    echo ""
    while true; do
        check_status
        sleep 10
    done
else
    check_status
fi
