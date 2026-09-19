#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
backend_python="$project_root/.conda/bin/python"
if [[ ! -x "$backend_python" ]]; then
  printf 'Backend .conda Python is missing; create the planned Python 3.12 environment first.\n' >&2
  exit 1
fi
cd "$project_root"
export PYTHONNOUSERSITE=1
export PYTHONPATH="$project_root/src"
"$backend_python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Backend requires Python 3.12"'
exec "$backend_python" -B -m unittest discover -s tests -v "$@"
