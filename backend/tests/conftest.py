import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Isolate every test process from the developer's local database, even when
# an individual test module is executed on its own.
_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="scrapshift-tests-")
os.environ["SCRAPSHIFT_DB_PATH"] = str(Path(_TEST_DIRECTORY.name) / "scrapshift-test.db")
