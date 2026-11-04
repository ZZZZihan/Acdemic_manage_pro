import os
import sys

import dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    dotenv.load_dotenv(dotenv_path)

from app import create_app  # noqa: E402

try:
    app = create_app(os.getenv("FLASK_CONFIG") or "default")
except RuntimeError as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5003")), debug=app.config["DEBUG"])
