"""Entry point for the Oral Surgeon Recruiting ATS.

Usage:
    python run.py            # start the dev server on http://127.0.0.1:5000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
