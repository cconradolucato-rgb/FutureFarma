$ErrorActionPreference='Stop'
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File',('"'+$PSCommandPath+'"'))
 exit
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
 $python=Join-Path $root '.venv\Scripts\python.exe'
 & $python -c 'import cryptography; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey; from cryptography.hazmat.primitives.ciphers.aead import AESGCM' 2>$null
 if($LASTEXITCODE -ne 0){
  Write-Host 'Preparando biblioteca de verificacao das atualizacoes...'
  & $python -m pip install 'cryptography>=42,<47'
  if($LASTEXITCODE -ne 0){throw 'Nao foi possivel instalar cryptography. Confira a internet do servidor.'}
 }
 $home=Join-Path $root 'automatic_updates'
 New-Item -ItemType Directory -Path $home -Force | Out-Null
 foreach($file in @('updater.py','restart_panel.ps1','config.json')){
  $source=Join-Path $PSScriptRoot $file
  if(-not(Test-Path -LiteralPath $source)){throw "Extraia todo o pacote; arquivo ausente: $file"}
  if(Test-Path -LiteralPath (Join-Path $home $file)){Copy-Item -LiteralPath (Join-Path $home $file) -Destination (Join-Path $home ($file+'.backup-'+(Get-Date -Format yyyyMMddHHmmss))) -Force}
  Copy-Item -LiteralPath $source -Destination (Join-Path $home $file) -Force
 }
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 & icacls $home '/inheritance:r' '/grant:r' "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
 if($LASTEXITCODE -ne 0){throw 'Nao foi possivel proteger os arquivos do atualizador.'}
 $action=New-ScheduledTaskAction -Execute $python -Argument ('"'+(Join-Path $home 'updater.py')+'" "'+$root+'"') -WorkingDirectory $root
 $trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 2)
 $principal=New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Highest
 $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
 $taskName='FutureFarma-Atualizacao-Automatica'
 Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Atualizacoes assinadas do painel comercial; preserva configuracoes e dados.' -Force | Out-Null
 Write-Host 'Tarefa automatica registrada. Instalando a primeira versao...'
 & $python (Join-Path $home 'updater.py') $root
 if($LASTEXITCODE -ne 0){throw "A tarefa foi criada, mas a primeira verificacao falhou. Consulte $home\last_error.txt e updater.log"}
 Write-Host 'INSTALACAO CONCLUIDA. Atualizacoes verificadas a cada 2 minutos.' -ForegroundColor Green
 Write-Host 'Mantenha esta conta do Windows conectada; pode desconectar o RDP sem encerrar a sessao.'
 Write-Host 'No navegador: Ctrl+F5. Confirme Comissao: regra 27/11 ativa.'
 Write-Host "Status: $home\status.json"
}catch{
 Write-Host ('Nao concluido: '+$_.Exception.Message) -ForegroundColor Red
 exit 1
}
