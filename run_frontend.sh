#!/bin/bash

# ParkSight Frontend Launcher

echo "============================================================"
echo "ParkSight - Launching Web Interface"
echo "============================================================"
echo ""
echo "Opening frontend at http://localhost:8000"
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================================"
echo ""

cd frontend
python3 -m http.server 8000
