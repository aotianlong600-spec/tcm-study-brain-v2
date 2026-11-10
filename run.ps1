param([switch]$NoBrowser)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not $NoBrowser) {
  Start-Process "http://127.0.0.1:8768"
}
python -m uvicorn app.main:app --host 127.0.0.1 --port 8768
