#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
PYBIN="${PYBIN:-python3}"
PORT="${NEUROBUILD_PORT:-8502}"

cat <<'MSG'
[Neurobuild] Linux/Ubuntu no-sudo 실행 스크립트
- sudo 권한 없이 사용자 영역(~/.local)에 패키지를 설치합니다.
- 기존 Streamlit 앱이 포트를 잡고 있으면 종료합니다.
MSG

if ! "$PYBIN" - <<'PY' >/dev/null 2>&1
import sys
print(sys.version_info[:2])
PY
then
  echo "python3를 찾지 못했습니다. Python 3.8 이상이 필요합니다."
  exit 1
fi

if ! "$PYBIN" -m pip --version >/dev/null 2>&1; then
  echo "pip이 없어 사용자 영역에 pip을 설치합니다."
  PYVER=$("$PYBIN" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)
  if [ "$PYVER" = "3.8" ] || [ "$PYVER" = "3.9" ]; then
    GETPIP_URL="https://bootstrap.pypa.io/pip/$PYVER/get-pip.py"
  else
    GETPIP_URL="https://bootstrap.pypa.io/get-pip.py"
  fi
  "$PYBIN" - <<PY
import urllib.request
url = "$GETPIP_URL"
print("download:", url)
urllib.request.urlretrieve(url, "get-pip.py")
PY
  "$PYBIN" get-pip.py --user "pip<25.1" setuptools wheel
fi

"$PYBIN" -m pip install --user --upgrade "pip<25.1" setuptools wheel
"$PYBIN" -m pip install --user -r requirements.txt

# Kill previous Streamlit apps to avoid AI Tutor/old app on the same port.
pkill -f "streamlit" 2>/dev/null || true
sleep 1

echo ""
echo "[Neurobuild] 실행 주소: http://localhost:${PORT}"
echo "브라우저에서 위 주소를 여세요. 터미널은 닫지 마세요."
echo ""
"$PYBIN" -m streamlit run app.py --server.address 0.0.0.0 --server.port "$PORT" --server.fileWatcherType none
