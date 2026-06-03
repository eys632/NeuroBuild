@echo off
setlocal
cd /d %~dp0
set PORT=8502
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port %PORT% --server.fileWatcherType none
