"""
db.py — CognoDB (Neo4j-compatible) connection handling.

Connection details are read from environment variables ONLY.
Never hardcode the URI, username, or password here.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

load_dotenv()
class Database:
    """Thin wrapper around the Neo4j driver with graceful error handling."""

    def __init__(self):
        self._uri = os.environ.get("COGNODB_URI")
        self._user = os.environ.get("COGNODB_USER", "cognodb")
        self._password = os.environ.get("COGNODB_PASSWORD")
        self._driver = None

    def connect(self):
        """Create the driver and verify connectivity. Raises on failure."""
        if not self._uri or not self._password:
            raise RuntimeError(
                "Missing CognoDB credentials. Set COGNODB_URI and "
                "COGNODB_PASSWORD as environment variables (see .env.example)."
            )
        try:
            self._driver = GraphDatabase.driver(
                self._uri, auth=(self._user, self._password)
            )
            self._driver.verify_connectivity()
        except AuthError as exc:
            raise RuntimeError(
                "CognoDB authentication failed. Check COGNODB_USER / "
                "COGNODB_PASSWORD."
            ) from exc
        except ServiceUnavailable as exc:
            raise RuntimeError(
                "CognoDB is unreachable. Check COGNODB_URI and your network, "
                "or confirm the instance is still running in the console."
            ) from exc
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.close()

    def get_driver(self):
        if self._driver is None:
            self.connect()
        return self._driver

    def run_query(self, query, parameters=None):
        """Run a single parameterised Cypher query and return a list of dicts."""
        driver = self.get_driver()
        try:
            with driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except ServiceUnavailable as exc:
            raise RuntimeError(
                "Lost connection to CognoDB while running a query."
            ) from exc


# Singleton used by the Flask app
db = Database()
