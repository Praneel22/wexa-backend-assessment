import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import certifi
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError

# Ensure .env is loaded reliably from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Ensure Python's SSL verification finds the certifi CA bundle
os.environ.setdefault("SSL_CERT_FILE", certifi.where())


def get_connection_config():
    """Extract and normalize CognoDB connection configuration from environment."""
    raw_uri = os.getenv("COGNODB_URI")
    user = os.getenv("COGNODB_USERNAME") or os.getenv("COGNODB_USER") or "cognodb"
    password = os.getenv("COGNODB_PASSWORD")

    if not raw_uri:
        raise ValueError("Missing required environment variable: COGNODB_URI")
    if not password:
        raise ValueError("Missing required environment variable: COGNODB_PASSWORD")

    # CognoDB cloud instances require TLS (bolt+s:// or neo4j+s://)
    uri = raw_uri.strip()
    if uri.startswith("bolt://") and "databases.cognodb." in uri:
        uri = "bolt+s://" + uri[len("bolt://"):]
    elif uri.startswith("neo4j://") and "databases.cognodb." in uri:
        uri = "neo4j+s://" + uri[len("neo4j://"):]

    return uri, user, password


def test_connection():
    """Verify CognoDB connectivity, measure latency, and execute a validation query."""
    try:
        uri, user, password = get_connection_config()
    except ValueError as e:
        print(f"[CONFIGURATION ERROR] {e}")
        return False

    # Mask host and URI details safely (never print password)
    safe_uri = uri.split("@")[-1]
    print(f"==================================================")
    print(f" CognoDB Connectivity & Verification Diagnostic")
    print(f"==================================================")
    print(f" Target URI  : {safe_uri}")
    print(f" User        : {user}")
    print(f" SSL CA Path : {certifi.where()}")
    print(f"--------------------------------------------------")

    driver = None
    try:
        start_time = time.perf_counter()
        driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=15.0,
            max_connection_lifetime=300,
        )

        # 1. Verify basic socket & protocol connectivity
        print("[1/3] Verifying protocol handshake & TLS connectivity...")
        driver.verify_connectivity()
        handshake_ms = (time.perf_counter() - start_time) * 1000
        print(f"      Connected successfully! (Handshake latency: {handshake_ms:.2f} ms)")

        # 2. Run a simple validation query
        print("[2/3] Executing validation Cypher query (RETURN 1 AS test)...")
        query_start = time.perf_counter()
        with driver.session() as session:
            result = session.run("RETURN 1 AS test, 'CognoDB' AS engine, datetime() AS server_time")
            record = result.single()
            query_ms = (time.perf_counter() - query_start) * 1000
            print(f"      Query succeeded in {query_ms:.2f} ms")
            print(f"      Result: test={record['test']}, engine={record['engine']}")

        # 3. Check graph metadata / counts
        print("[3/3] Checking graph storage status...")
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
            print(f"      Current Graph State: {node_count:,} nodes, {rel_count:,} relationships")

        print("--------------------------------------------------")
        print("[SUCCESS] All CognoDB connection tests passed!")
        print("==================================================")
        return True

    except ServiceUnavailable as e:
        print(f"[SERVICE UNAVAILABLE] Could not connect to CognoDB at {safe_uri}")
        print(f"Details: {e}")
        return False
    except AuthError as e:
        print(f"[AUTHENTICATION FAILED] Credentials rejected for user '{user}'.")
        print(f"Details: {e}")
        return False
    except Neo4jError as e:
        print(f"[CYPHER ERROR] Database returned an error: {e.code}")
        print(f"Details: {e.message}")
        return False
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        return False
    finally:
        if driver is not None:
            driver.close()


def main():
    success = test_connection()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()