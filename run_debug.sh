#!/bin/bash

# Run web server with DEBUG logging enabled
# Usage: ./run_debug.sh

echo "🔍 Starting web server with DEBUG logging..."
echo "📝 Logs will be saved to: logs/web.log"
echo "📊 Press Ctrl+C to stop"
echo ""

# Set DEBUG log level
export LOG_LEVEL=DEBUG

# Run web server with unbuffered output
python3 -u web.py 2>&1 | tee -a logs/debug_$(date +%Y%m%d_%H%M%S).log
