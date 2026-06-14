#!/usr/bin/env python3
"""
sync_prod_to_dev.py

Copies the production Neon PostgreSQL database (NEON_DATABASE_URL) into the
development database (DATABASE_URL), overwriting everything in the dev database.

Usage:
    python scripts/sync_prod_to_dev.py

Requirements:
    - NEON_DATABASE_URL environment variable set to the production connection string
    - DATABASE_URL environment variable set to the development connection string
    - pg_dump and psql available on PATH
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
from urllib.parse import urlparse


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    print(f"[{ts()}] {msg}", flush=True)


def abort(msg):
    print(f"[{ts()}] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def parse_db_url(url, label):
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            abort(f"Could not parse host from {label}.")
        return parsed
    except Exception as e:
        abort(f"Failed to parse {label}: {e}")


def build_env(parsed):
    env = os.environ.copy()
    env["PGHOST"] = parsed.hostname or ""
    env["PGPORT"] = str(parsed.port) if parsed.port else "5432"
    env["PGUSER"] = parsed.username or ""
    env["PGPASSWORD"] = parsed.password or ""
    env["PGDATABASE"] = (parsed.path or "").lstrip("/")
    for key in ("PGSERVICE", "PGSERVICEFILE", "PGPASSFILE"):
        env.pop(key, None)
    return env


def run(cmd, env, description):
    log(f"Starting: {description}")
    result = subprocess.run(cmd, env=env, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        abort(f"{description} failed (exit {result.returncode}):\n{stderr}")
    log(f"Done: {description}")
    return result


def main():
    prod_url = os.environ.get("NEON_DATABASE_URL")
    dev_url = os.environ.get("DATABASE_URL")

    if not prod_url:
        abort("NEON_DATABASE_URL is not set. Cannot locate production database.")
    if not dev_url:
        abort("DATABASE_URL is not set. Cannot locate development database.")

    prod = parse_db_url(prod_url, "NEON_DATABASE_URL")
    dev = parse_db_url(dev_url, "DATABASE_URL")

    if prod.hostname == dev.hostname:
        abort(
            f"NEON_DATABASE_URL and DATABASE_URL point to the same host "
            f"({prod.hostname}). Refusing to overwrite production data."
        )

    log("=== Prod-to-Dev Database Sync ===")
    log(f"Production host : {prod.hostname}")
    log(f"Development host: {dev.hostname}")
    log("Proceeding with sync — dev database will be OVERWRITTEN.")

    pg_dump = shutil.which("pg_dump")
    psql = shutil.which("psql")
    if not pg_dump:
        abort("pg_dump not found on PATH.")
    if not psql:
        abort("psql not found on PATH.")

    dump_file = tempfile.mktemp(prefix="prod_dump_", suffix=".sql")
    log(f"Temporary dump file: {dump_file}")

    prod_env = build_env(prod)
    dev_env = build_env(dev)

    try:
        run(
            [
                pg_dump,
                "--no-password",
                "--format=plain",
                "--clean",
                "--if-exists",
                "--file", dump_file,
            ],
            env=prod_env,
            description="Dumping production database (with DROP statements for clean restore)",
        )

        log("Restoring dump into development database — existing objects will be dropped first...")
        run(
            [
                psql,
                "--no-password",
                "--quiet",
                "--file", dump_file,
                "--variable", "ON_ERROR_STOP=1",
                "--single-transaction",
            ],
            env=dev_env,
            description="Restoring dump to development database",
        )

    except SystemExit:
        raise
    finally:
        if os.path.exists(dump_file):
            os.remove(dump_file)
            log(f"Cleaned up temporary dump file: {dump_file}")

    log("=== Sync complete. Development database now mirrors production. ===")


if __name__ == "__main__":
    main()
