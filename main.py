import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import app
import routes  # noqa: F401

if __name__ == '__main__':
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    port = int(os.environ.get("PORT", 8080))

    app.run(host='0.0.0.0', debug=debug, port=port)
