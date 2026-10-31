"""Manage only the ignored, project-local PostgreSQL cluster. Never touches system databases."""

import argparse
import os
import secrets
import shutil
import subprocess
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local"
DATA = LOCAL / "postgres"
ENV = ROOT / ".env"
PORT = "55432"


def binary(name):
    suffix = ".exe" if os.name == "nt" else ""
    configured = os.environ.get("POSTGRES_BIN")
    candidates = [Path(configured) / (name + suffix)] if configured else []
    installed = shutil.which(name)
    if installed:
        candidates.append(Path(installed))
    if os.name == "nt":
        candidates.append(Path("C:/Program Files/PostgreSQL/17/bin") / (name + suffix))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("Install PostgreSQL 17 and set POSTGRES_BIN to its bin directory.")


def pg_ctl(*args, check=True):
    return subprocess.run([binary("pg_ctl"), "-D", str(DATA), *args], check=check)


def start():
    if not (DATA / "PG_VERSION").exists():
        raise SystemExit("Run init first.")
    if pg_ctl("status", check=False).returncode == 0:
        return
    pg_ctl("-l", str(LOCAL / "postgres.log"), "-w", "start")


def init():
    if ENV.exists() or DATA.exists():
        raise SystemExit(
            "Existing .env or cluster found; refusing to overwrite. Use start or README."
        )
    LOCAL.mkdir(exist_ok=True)
    admin_password = secrets.token_urlsafe(48)
    password_file = LOCAL / "postgres-init-password"
    password_file.write_text(admin_password, encoding="utf-8")
    try:
        subprocess.run(
            [
                binary("initdb"),
                "-D",
                str(DATA),
                "-U",
                "postgres",
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
                f"--pwfile={password_file}",
            ],
            check=True,
        )
    finally:
        password_file.unlink(missing_ok=True)
    with (DATA / "postgresql.conf").open("a", encoding="utf-8") as config:
        config.write(f"\nlisten_addresses = '127.0.0.1'\nport = {PORT}\n")
    # Retain recovery credentials locally, never print them or add them to Git.
    (LOCAL / "postgres-admin-password").write_text(admin_password, encoding="utf-8")
    start()
    app_password = secrets.token_urlsafe(48)
    with psycopg.connect(
        host="127.0.0.1",
        port=PORT,
        dbname="postgres",
        user="postgres",
        password=admin_password,
        autocommit=True,
    ) as connection:
        # CREATEDB is local-only for Django's disposable test database.
        connection.execute(
            sql.SQL("CREATE ROLE brightloop LOGIN CREATEDB PASSWORD {}").format(
                sql.Literal(app_password)
            )
        )
        connection.execute("CREATE DATABASE brightloop OWNER brightloop")
    ENV.write_text(
        f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n"
        "DJANGO_DEBUG=true\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
        "POSTGRES_DB=brightloop\nPOSTGRES_USER=brightloop\n"
        f"POSTGRES_PASSWORD={app_password}\nPOSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT={PORT}\n"
        "EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend\n",
        encoding="utf-8",
    )
    print("Local database and ignored .env created. Run manage.py migrate next.")


def check():
    config = dotenv_values(ENV)
    with psycopg.connect(
        host=config["POSTGRES_HOST"],
        port=config["POSTGRES_PORT"],
        dbname=config["POSTGRES_DB"],
        user=config["POSTGRES_USER"],
        password=config["POSTGRES_PASSWORD"],
        connect_timeout=5,
    ) as connection:
        assert connection.execute("SELECT 1").fetchone() == (1,)
    print("Local PostgreSQL connection verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "start", "stop", "status", "check"])
    action = parser.parse_args().action
    if action == "init":
        init()
    elif action == "start":
        start()
    elif action == "stop":
        pg_ctl("-m", "fast", "-w", "stop")
    elif action == "status":
        raise SystemExit(pg_ctl("status", check=False).returncode)
    else:
        check()
