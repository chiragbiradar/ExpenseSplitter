from app import app
import os
import routes  # noqa: F401

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=int(os.environ.get("PORT", 8080)))
