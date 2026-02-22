"""
RAG-powered chatbot using Claude Sonnet 4 and Actian VectorAI DB.
"""

import re
import anthropic
from .retriever import retrieve

# Fallback context when vector DB returns garbage or is unavailable
FALLBACK_CONTEXT = """
Atlanta Neighborhood Overview:

Midtown Atlanta: Dense urban core with high foot traffic. Office workers, Georgia Tech students,
arts patrons. Strong demand for coffee, fast-casual dining, fitness. 850+ parking spaces across
12 detected lots. Very walkable.

Buckhead: Upscale retail and dining hub. High-income residents and professionals. Best for
boutiques, luxury goods, fine dining, salons. 1,200+ parking spaces across 18 lots.
Phipps Plaza and Lenox Square anchor retail traffic.

Little Five Points / Inman Park: Eclectic, artsy, younger demographic. Good for vintage shops,
indie cafes, music venues, tattoo studios. 320 parking spaces across 6 lots.
High foot traffic on weekends.

Old Fourth Ward / Beltline: Rapidly gentrifying. Mixed residential and commercial.
Strong brunch and fitness culture. 410 parking spaces across 8 lots near the trail.

Virginia-Highland: Neighborhood retail strip. Young professionals, families.
Good for wine bars, boutique fitness, specialty food. 280 parking spaces across 5 lots.

Downtown Atlanta: Office workers, tourists, convention center traffic.
Good for fast food, hotels, souvenir shops. 2,000+ parking spaces in 25+ detected lots.
High car dependency — parking is a major factor in site selection.
"""


def is_clean_text(text: str) -> bool:
    """Return True if text looks like real content, not binary garbage."""
    if not text or len(text) < 20:
        return False
    # Count printable ASCII + common punctuation ratio
    printable = sum(1 for c in text if c.isprintable())
    ratio = printable / len(text)
    # Also reject if too many consecutive non-alpha runs (binary artifacts)
    garbage_pattern = re.compile(r'[^\x20-\x7E\n]{3,}')
    has_garbage = bool(garbage_pattern.search(text))
    return ratio > 0.90 and not has_garbage

# Initialize Anthropic client (reads ANTHROPIC_API_KEY from environment)
client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an Atlanta business location advisor. Give SHORT, concise answers.

FORMAT:
• Use bullet points
• Maximum 3-4 bullets per response
• Each bullet: 1 short sentence
• Recommend 1-2 neighborhoods max
• ALWAYS include a dedicated parking bullet with SPECIFIC NUMBERS

PARKING DATA REQUIRED:
• Every response MUST have one bullet with exact parking counts
• Use format: "🅿️ 850 parking spaces across 12 lots"
• Include occupancy rates if available
• Never say "ample" or "good" - give actual numbers

STYLE:
• Direct and actionable
• No long explanations
• Focus on key facts only

Example good response:
• **Midtown** - High foot traffic, office workers need caffeine
• Strong coffee culture and 22 existing cafes
• 🅿️ 850 parking spaces across 12 lots (68% occupancy)"""


def generate_response(user_message: str, conversation_history: list = None) -> str:
    """
    Generate chatbot response using RAG.

    Args:
        user_message: User's current message
        conversation_history: List of prior messages [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Assistant's response
    """
    # Retrieve relevant context, filtering out corrupted chunks
    try:
        raw_docs = retrieve(user_message, top_k=5)
        clean_docs = [doc for doc in raw_docs if is_clean_text(doc)]
    except Exception as e:
        print(f"Retrieval error: {e}")
        clean_docs = []

    if clean_docs:
        context = "\n\n".join([f"[Context {i+1}]\n{doc}" for i, doc in enumerate(clean_docs)])
    else:
        context = FALLBACK_CONTEXT.strip()

    # Build messages
    messages = []

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add current message with context
    user_content = f"""Context from ParkSight knowledge base:

{context}

---

User question: {user_message}"""

    messages.append({
        "role": "user",
        "content": user_content
    })

    # Call Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=messages
    )

    return response.content[0].text


def quick_response(user_message: str) -> str:
    """
    Generate a quick response without conversation history.
    Useful for stateless API calls.
    """
    return generate_response(user_message, conversation_history=None)
