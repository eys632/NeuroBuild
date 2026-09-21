#!/usr/bin/env python3
"""Manage only this checkout's private, peer-authenticated PostgreSQL cluster."""

import argparse
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / ".conda/bin"
DATA = ROOT / "var/postgres"
SOCKET = ROOT / "var/run/postgresql"
MARKER = DATA / ".neurobuild-local.json"
PORT = "55432"
USER = pwd.getpwuid(os.getuid()).pw_name


def run(tool, *args, capture=False, check=True):
    return subprocess.run([str(BIN / tool), *map(str, args)], check=check,
                          text=True, capture_output=capture)


def checked_path(path):
    if path.resolve() != path.absolute():
        raise RuntimeError("Managed PostgreSQL paths must not contain symlinks")
    if path.exists() and path.stat().st_uid != os.getuid():
        raise RuntimeError("Managed PostgreSQL paths must belong to the current user")


def validate_owner():
    for path in (DATA, SOCKET, MARKER):
        checked_path(path)
    expected = {"uid": os.getuid(), "data": str(DATA), "socket": str(SOCKET), "port": PORT}
    if not MARKER.is_file() or json.loads(MARKER.read_text()) != expected:
        raise RuntimeError("Refusing to manage an unmarked or different PostgreSQL cluster")


def initialize():
    for path in (DATA, SOCKET):
        checked_path(path)
    if (DATA / "PG_VERSION").exists():
        validate_owner()
        print("Existing project cluster retained")
        return
    if DATA.exists() and any(DATA.iterdir()):
        raise RuntimeError("Refusing to initialize a nonempty data directory")
    SOCKET.mkdir(parents=True, mode=0o700, exist_ok=True)
    SOCKET.chmod(0o700)
    run("initdb", "-D", DATA, "-U", USER, "--auth-local=peer", "--auth-host=reject",
        "--encoding=UTF8", "--locale=C", "--data-checksums")
    socket_literal = str(SOCKET).replace("'", "''")
    if "\n" in socket_literal or "\r" in socket_literal:
        raise RuntimeError("Unsupported newline in project path")
    with (DATA / "postgresql.conf").open("a") as config:
        config.write("\n# NeuroBuild private local development cluster\n")
        config.write("listen_addresses = ''\n")
        config.write("unix_socket_directories = '" + socket_literal + "'\n")
        config.write("unix_socket_permissions = 0700\n")
        config.write("port = " + PORT + "\nmax_connections = 16\nshared_buffers = '64MB'\n")
        config.write("max_wal_size = '256MB'\nmin_wal_size = '80MB'\n")
        config.flush()
        os.fsync(config.fileno())
    MARKER.write_text(json.dumps({"uid": os.getuid(), "data": str(DATA),
                                  "socket": str(SOCKET), "port": PORT}))
    MARKER.chmod(0o600)


def status():
    return run("pg_ctl", "-D", DATA, "status", capture=True, check=False)


def start():
    validate_owner()
    if status().returncode:
        run("pg_ctl", "-D", DATA, "-l", DATA / "server.log", "-o", "-c listen_addresses=''", "-w", "start")
    args = ("-h", SOCKET, "-p", PORT, "-U", USER)
    exists = run("psql", *args, "-d", "postgres", "-Atc",
                 "SELECT 1 FROM pg_database WHERE datname = 'neurobuild'", capture=True)
    if exists.stdout.strip() != "1":
        run("createdb", *args, "neurobuild")
    print("Private PostgreSQL ready; no TCP listener configured")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "start", "status", "stop", "dsn"))
    args = parser.parse_args()
    try:
        if args.action == "init":
            initialize()
        elif args.action == "start":
            start()
        elif args.action == "dsn":
            # psycopg renders/quotes a libpq conninfo; no password is used.
            from psycopg.conninfo import make_conninfo
            print(make_conninfo(host=str(SOCKET), port=PORT, dbname="neurobuild", user=USER))
        else:
            validate_owner()
            current = status()
            if args.action == "status":
                print(current.stdout.strip() or "Project PostgreSQL is stopped")
                return current.returncode
            if current.returncode == 0:
                run("pg_ctl", "-D", DATA, "-m", "fast", "-w", "stop")
            else:
                print("Project PostgreSQL already stopped")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print("PostgreSQL management failed: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
