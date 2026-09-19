Set-Location $PSScriptRoot
$PORT = 8502
if (!(Test-Path .venv)) {
  py -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.fileWatcherType none
