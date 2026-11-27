$ErrorActionPreference='Stop'
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File',('"'+$PSCommandPath+'"'))
 exit
}
$logPath=Join-Path $PSScriptRoot 'instalacao.log'
Set-Content -LiteralPath $logPath -Value ('Instalador 2026.11.27.2 - '+(Get-Date -Format o)) -Encoding UTF8
function Invoke-PythonCaptured {
 param([string]$Executable,[string[]]$Arguments,[int]$TimeoutMs=300000)
 $info=New-Object System.Diagnostics.ProcessStartInfo
 $info.FileName=$Executable
 # Argumentos sao constantes ou caminhos Windows (que nao admitem aspas no nome).
 $info.Arguments=($Arguments | ForEach-Object {'"'+$_.Replace('"','\"')+'"'}) -join ' '
 $info.UseShellExecute=$false
 $info.CreateNoWindow=$true
 $info.RedirectStandardOutput=$true
 $info.RedirectStandardError=$true
 $process=New-Object System.Diagnostics.Process
 $process.StartInfo=$info
 try{
  [void]$process.Start()
  $outTask=$process.StandardOutput.ReadToEndAsync()
  $errTask=$process.StandardError.ReadToEndAsync()
  if(-not $process.WaitForExit($TimeoutMs)){
   $process.Kill()
   throw 'Tempo limite executando Python. Confira instalacao.log.'
  }
  $output=$outTask.GetAwaiter().GetResult()+$errTask.GetAwaiter().GetResult()
  Add-Content -LiteralPath $logPath -Value $output -Encoding UTF8
  return [pscustomobject]@{ExitCode=$process.ExitCode;Output=$output}
 }finally{$process.Dispose()}
}
try{
 # A tarefa precisa rodar no servidor, nao apenas em um PC que le a pasta de rede.
 $local=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty IPAddress)
 if($local -notcontains '192.168.0.32'){throw 'Execute esta instalacao DENTRO da Area de Trabalho Remota do servidor 192.168.0.32.'}
 Add-Type -AssemblyName System.Windows.Forms
 $dialog=New-Object System.Windows.Forms.FolderBrowserDialog
 $dialog.Description='Selecione a pasta PRINCIPAL FutureFarma_Servidor que contem server.py, config.json, static e data.'
 $candidate=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'FutureFarma_Servidor'
 if(Test-Path -LiteralPath $candidate){$dialog.SelectedPath=$candidate}
 if($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){Write-Host 'Instalacao cancelada; nada alterado.';exit 0}
 $root=$dialog.SelectedPath
 foreach($file in @('server.py','config.json','static\index.html','.venv\Scripts\python.exe','history_reference.py')){
  if(-not(Test-Path -LiteralPath (Join-Path $root $file))){throw "Pasta incorreta ou incompleta; arquivo ausente: $file"}
 }
 $panelConfig=Get-Content -LiteralPath (Join-Path $root 'config.json') -Raw | ConvertFrom-Json
 if($panelConfig.public_key -and $panelConfig.decrypt_key -and -not $panelConfig.sql_server){throw 'O config.json desta pasta e do pacote antigo, nao do painel. Restaure o config.json original do painel antes de prosseguir; nenhum dado foi apagado pelo instalador.'}
 $python=Join-Path $root '.venv\Scripts\python.exe'
 $versionProbe=Invoke-PythonCaptured -Executable $python -Arguments @('-c','import sys;print(sys.version);sys.exit(0 if sys.version_info>=(3,8) else 1)')
 if($versionProbe.ExitCode -ne 0){throw 'Python 3.8 ou superior necessario; veja instalacao.log.'}
 $probeCode='import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey; from cryptography.hazmat.primitives.ciphers.aead import AESGCM'
 $probe=Invoke-PythonCaptured -Executable $python -Arguments @('-c',$probeCode)
 if($probe.ExitCode -ne 0){
  Write-Host 'Preparando biblioteca de verificacao das atualizacoes...'
  $pip=Invoke-PythonCaptured -Executable $python -Arguments @('-m','pip','install','cryptography>=42,<47') -TimeoutMs 600000
  if($pip.ExitCode -ne 0){Write-Host $pip.Output;throw 'Nao foi possivel instalar cryptography. Detalhes completos em instalacao.log.'}
  $probe=Invoke-PythonCaptured -Executable $python -Arguments @('-c',$probeCode)
  if($probe.ExitCode -ne 0){Write-Host $probe.Output;throw 'A biblioteca nao carregou apos a instalacao. Veja instalacao.log.'}
 }
 $updateDir=Join-Path $root 'automatic_updates'
 New-Item -ItemType Directory -Path $updateDir -Force | Out-Null
 foreach($file in @('updater.py','restart_panel.ps1','update_channel.json')){
  $source=Join-Path $PSScriptRoot $file
  if(-not(Test-Path -LiteralPath $source)){throw "Extraia todo o pacote; arquivo ausente: $file"}
  $targetName=if($file -eq 'update_channel.json'){'config.json'}else{$file}
  if(Test-Path -LiteralPath (Join-Path $updateDir $targetName)){Copy-Item -LiteralPath (Join-Path $updateDir $targetName) -Destination (Join-Path $updateDir ($targetName+'.backup-'+(Get-Date -Format yyyyMMddHHmmss))) -Force}
  Copy-Item -LiteralPath $source -Destination (Join-Path $updateDir $targetName) -Force
 }
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 & icacls $updateDir '/inheritance:r' '/grant:r' "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Nao foi possivel proteger os arquivos do atualizador.'}
 $action=New-ScheduledTaskAction -Execute $python -Argument ('"'+(Join-Path $updateDir 'updater.py')+'" "'+$root+'"') -WorkingDirectory $root
 $trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 2)
 $principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Highest
 $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
 $taskName='FutureFarma-Atualizacao-Automatica'
 Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Atualizacoes assinadas do painel comercial; preserva configuracoes e dados.' -Force | Out-Null
 Write-Host 'Tarefa automatica registrada. Instalando a primeira versao...'
 $firstRun=Invoke-PythonCaptured -Executable $python -Arguments @((Join-Path $updateDir 'updater.py'),$root)
 if($firstRun.ExitCode -ne 0){
  Write-Host $firstRun.Output
  $errorFile=Join-Path $updateDir 'last_error.txt'
  if(Test-Path -LiteralPath $errorFile){Write-Host (Get-Content -LiteralPath $errorFile -Raw)}
  throw "A tarefa foi criada, mas a primeira verificacao falhou. Consulte $updateDir\last_error.txt e updater.log"
 }
 Write-Host 'INSTALACAO CONCLUIDA. Atualizacoes verificadas a cada 2 minutos.' -ForegroundColor Green
 Write-Host 'Mantenha esta conta do Windows conectada; pode desconectar o RDP sem encerrar a sessao.'
 Write-Host 'No navegador: Ctrl+F5. Confirme Comissao: regra 27/11 ativa.'
 Write-Host "Status: $updateDir\status.json"
}catch{
 Add-Content -LiteralPath $logPath -Value ($_ | Out-String) -Encoding UTF8
 Write-Host ('Nao concluido: '+$_.Exception.Message) -ForegroundColor Red
 Write-Host ('Erro completo salvo em: '+$logPath)
 exit 1
}
