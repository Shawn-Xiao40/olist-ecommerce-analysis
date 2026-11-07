import os

# Required: used to sign sessions and encrypt connection details. Set it in superset/.env.
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# Allow connections to local file databases (the DuckDB file). Local development only.
PREVENT_UNSAFE_DB_CONNECTIONS = False

# English UI only
BABEL_DEFAULT_LOCALE = "en"
LANGUAGES = {"en": {"flag": "us", "name": "English"}}
