import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    # On Windows/VS Code: open http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5000, debug=debug)
