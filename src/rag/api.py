"""
Flask API server for ParkSight RAG chatbot.
"""

import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from .chatbot import generate_response
from .retriever import health_check

PARKING_LOTS_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'outputs', 'parking_lots_cleaned (1).geojson'
)

app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    vector_db_ok = health_check()
    return jsonify({
        "status": "ok" if vector_db_ok else "degraded",
        "vector_db": "connected" if vector_db_ok else "disconnected"
    }), 200 if vector_db_ok else 503


@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat endpoint for business advisor.

    Request body:
    {
        "message": "Where should I open a coffee shop?",
        "history": [  // optional
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }

    Response:
    {
        "response": "Based on parking and neighborhood data, I recommend..."
    }
    """
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        user_message = data['message']

        if not user_message.strip():
            return jsonify({"error": "Empty message"}), 400

        # Get conversation history if provided
        conversation_history = data.get('history', [])

        # Generate response with history
        response_text = generate_response(user_message, conversation_history)

        return jsonify({"response": response_text}), 200

    except Exception as e:
        print(f"Error in /chat: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/remove-lot', methods=['POST'])
def remove_lot():
    """
    Permanently remove a parking lot from parking_lots.geojson.

    Request body: { "lot_id": 42 }
    Response:     { "removed": true, "remaining": 1930 }
    """
    try:
        data = request.get_json()
        if not data or 'lot_id' not in data:
            return jsonify({"error": "Missing 'lot_id' field"}), 400

        lot_id = data['lot_id']
        path = os.path.normpath(PARKING_LOTS_PATH)

        with open(path, 'r') as f:
            geojson = json.load(f)

        before = len(geojson['features'])
        geojson['features'] = [
            feat for feat in geojson['features']
            if feat.get('properties', {}).get('lot_id') != lot_id
        ]
        after = len(geojson['features'])

        if before == after:
            return jsonify({"error": f"lot_id {lot_id} not found"}), 404

        with open(path, 'w') as f:
            json.dump(geojson, f)

        return jsonify({"removed": True, "remaining": after}), 200

    except Exception as e:
        print(f"Error in /remove-lot: {e}")
        return jsonify({"error": "Internal server error"}), 500


def run_server(host='0.0.0.0', port=5001, debug=False):
    """Run the Flask server."""
    print(f"Starting ParkSight RAG API on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
