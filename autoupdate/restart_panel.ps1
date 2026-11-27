param([Parameter(Mandatory=$true)][string]$Root)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $Root
$listeners=@(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
$ids=@($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
if($ids.Count -gt 0){
 $response=Invoke-WebRequest -Uri 'http://127.0.0.1:8765/' -UseBasicParsing -TimeoutSec 5
 if($response.Content -notmatch '(?i)FUTURE\s*FARMA'){throw 'Porta 8765 pertence a outro aplicativo.'}
 foreach($processId in $ids){
  $p=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
  if($p.Name -notlike 'python*.exe' -or $p.CommandLine -notmatch '(?i)server\.py(?:["\s]|$)'){throw 'Processo do painel nao confirmado.'}
 }
 foreach($processId in $ids){Stop-Process -Id $processId -Force}
 for($i=0;$i -lt 30;$i++){
  if(-not(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)){break}
  Start-Sleep -Milliseconds 200
 }
}
if(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue){throw 'Porta 8765 ainda esta ocupada.'}
$python=Join-Path $Root '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Python do painel nao encontrado em .venv\Scripts\python.exe.'}
$env:DASH_OPEN_BROWSER='0'
Start-Process -FilePath $python -ArgumentList @('"'+(Join-Path $Root 'server.py')+'"') -WorkingDirectory $Root -WindowStyle Hidden
