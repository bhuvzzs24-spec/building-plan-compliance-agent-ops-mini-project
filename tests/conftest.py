import os
from pathlib import Path
import tempfile

# Isolate SQLite and Redis behavior from a developer's local state.
os.environ.pop("REDIS_URL", None)
os.environ["RUN_DB_PATH"] = str(Path(tempfile.mkdtemp(prefix="bpc-tests-")) / "runs.sqlite3")
os.environ["CHROMA_PERSIST_DIR"] = str(Path(tempfile.gettempdir()) / "bpc-empty-test-index")
