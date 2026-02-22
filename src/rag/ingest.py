"""
Knowledge base ingestion for ParkSight RAG chatbot.
Scrapes Wikipedia, parking data, and OSM amenities to build vector database.
Uses Actian VectorAI DB (CortexClient) instead of FAISS.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np
from cortex import CortexClient, DistanceMetric

# Constants
DIMENSION = 384
CHUNK_SIZE = 300  # words
COLLECTION_NAME = "parksight_knowledge"
ACTIAN_HOST = "localhost:50051"

# Atlanta neighborhoods to scrape
NEIGHBORHOODS = [
    "Midtown_Atlanta",
    "Buckhead",
    "Old_Fourth_Ward",
    "Inman_Park",
    "Virginia-Highland",
    "Little_Five_Points"
]

# Neighborhoods for OSM amenity data
OSM_NEIGHBORHOODS = {
    "Midtown": {"lat": 33.7838, "lon": -84.3830},
    "Buckhead": {"lat": 33.8490, "lon": -84.3780},
    "Old Fourth Ward": {"lat": 33.7620, "lon": -84.3680}
}


def get_model():
    """Load sentence transformer model."""
    return SentenceTransformer('all-MiniLM-L6-v2')


def scrape_wikipedia(page_name: str) -> str:
    """Scrape Wikipedia page content."""
    url = f"https://en.wikipedia.org/wiki/{page_name}"
    try:
        headers = {
            'User-Agent': 'ParkSight/1.0 (Educational hackathon project; contact@parksight.app)'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Get main content
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            return ""

        # Extract paragraphs
        paragraphs = content.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs if p.get_text().strip()])

        # Clean up
        text = ' '.join(text.split())  # Normalize whitespace
        return text
    except Exception as e:
        print(f"Error scraping {page_name}: {e}")
        return ""


def fetch_osm_amenities(neighborhood: str, lat: float, lon: float) -> str:
    """Fetch amenity data from OpenStreetMap."""
    overpass_url = "http://overpass-api.de/api/interpreter"

    # Query for amenities within 1km radius
    query = f"""
    [out:json];
    (
      node["amenity"](around:1000,{lat},{lon});
      way["amenity"](around:1000,{lat},{lon});
      relation["amenity"](around:1000,{lat},{lon});
    );
    out center;
    """

    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Aggregate amenity counts
        amenities = {}
        for element in data.get('elements', []):
            amenity_type = element.get('tags', {}).get('amenity')
            if amenity_type:
                amenities[amenity_type] = amenities.get(amenity_type, 0) + 1

        # Format as text
        if amenities:
            amenity_list = ', '.join([f"{count} {name}" for name, count in sorted(amenities.items(), key=lambda x: -x[1])[:10]])
            return f"{neighborhood} amenities include: {amenity_list}."
        return ""
    except Exception as e:
        print(f"Error fetching OSM data for {neighborhood}: {e}")
        return ""


def process_parking_data() -> str:
    """Aggregate parking data by neighborhood."""
    parking_file = Path(__file__).parent.parent.parent / "outputs" / "parking_lots.geojson"

    if not parking_file.exists():
        print(f"Warning: {parking_file} not found")
        return ""

    with open(parking_file) as f:
        data = json.load(f)

    # Aggregate stats
    total_lots = len(data['features'])
    total_spots = sum(f['properties'].get('estimated_spots', 0) for f in data['features'])

    # Size categories
    small = sum(1 for f in data['features'] if f['properties'].get('estimated_spots', 0) < 50)
    medium = sum(1 for f in data['features'] if 50 <= f['properties'].get('estimated_spots', 0) < 200)
    large = sum(1 for f in data['features'] if f['properties'].get('estimated_spots', 0) >= 200)

    text = f"""Atlanta parking data: {total_lots} surface parking lots detected with {total_spots:,} total estimated spaces.
Size distribution: {small} small lots (under 50 spaces), {medium} medium lots (50-200 spaces), {large} large lots (200+ spaces).
Average lot size is approximately {total_spots // total_lots if total_lots > 0 else 0} spaces."""

    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split text into chunks of approximately chunk_size words."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks


def build_documents() -> List[Dict[str, str]]:
    """Build all documents for the knowledge base."""
    documents = []

    print("Scraping Wikipedia articles...")
    for neighborhood in NEIGHBORHOODS:
        print(f"  - {neighborhood}")
        text = scrape_wikipedia(neighborhood)
        if text:
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                documents.append({
                    "text": chunk,
                    "source": f"wikipedia_{neighborhood}",
                    "chunk_id": i
                })

    print("\nFetching OSM amenity data...")
    for neighborhood, coords in OSM_NEIGHBORHOODS.items():
        print(f"  - {neighborhood}")
        text = fetch_osm_amenities(neighborhood, coords['lat'], coords['lon'])
        if text:
            documents.append({
                "text": text,
                "source": f"osm_{neighborhood}",
                "chunk_id": 0
            })

    print("\nProcessing parking data...")
    parking_text = process_parking_data()
    if parking_text:
        documents.append({
            "text": parking_text,
            "source": "parking_analysis",
            "chunk_id": 0
        })

    print(f"\nTotal documents: {len(documents)}")
    return documents


def ingest_to_vectordb(documents: List[Dict[str, str]]):
    """Embed documents and store in Actian VectorAI DB."""
    print("\nLoading embedding model...")
    model = get_model()

    texts = [doc['text'] for doc in documents]
    payloads = [
        {
            "text": doc['text'],
            "source": doc['source'],
            "chunk_id": doc['chunk_id']
        }
        for doc in documents
    ]

    print("Generating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings_normalized = (embeddings / norms).tolist()

    ids = list(range(len(documents)))

    print(f"\nConnecting to Actian VectorAI DB at {ACTIAN_HOST}...")
    with CortexClient(ACTIAN_HOST) as client:
        version, uptime = client.health_check()
        print(f"Connected: {version} (uptime {uptime}s)")

        # Drop and recreate collection for a clean ingest
        if client.has_collection(COLLECTION_NAME):
            print(f"Dropping existing collection '{COLLECTION_NAME}'...")
            client.delete_collection(COLLECTION_NAME)

        client.create_collection(
            name=COLLECTION_NAME,
            dimension=DIMENSION,
            distance_metric=DistanceMetric.COSINE,
        )
        print(f"Created collection '{COLLECTION_NAME}' (dim={DIMENSION}, metric=COSINE)")

        print(f"Inserting {len(documents)} documents...")
        client.batch_upsert(
            COLLECTION_NAME,
            ids=ids,
            vectors=embeddings_normalized,
            payloads=payloads,
        )

        count = client.count(COLLECTION_NAME)
        print(f"\n[OK] Knowledge base built: {count} documents indexed in Actian VectorAI DB")
        print(f"  Collection: {COLLECTION_NAME} @ {ACTIAN_HOST}")


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("ParkSight Knowledge Base Builder")
    print("Using Actian VectorAI DB")
    print("=" * 60)

    # Build documents
    documents = build_documents()

    if not documents:
        print("Error: No documents created")
        sys.exit(1)

    # Ingest to vector DB
    ingest_to_vectordb(documents)

    print("\n" + "=" * 60)
    print("Knowledge base ready!")
    print("=" * 60)


if __name__ == "__main__":
    main()
