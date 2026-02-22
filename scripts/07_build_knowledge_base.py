#!/usr/bin/env python3
"""
Build ParkSight RAG knowledge base.

This script runs the knowledge base ingestion pipeline:
1. Scrape Wikipedia articles for Atlanta neighborhoods
2. Fetch OSM amenity data
3. Process parking detection results
4. Embed all documents and store in Actian VectorAI DB

Requirements:
- Actian VectorAI DB must be running on localhost:50051
- ANTHROPIC_API_KEY environment variable must be set

Usage:
    python3 scripts/07_build_knowledge_base.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.ingest import main

if __name__ == "__main__":
    main()
