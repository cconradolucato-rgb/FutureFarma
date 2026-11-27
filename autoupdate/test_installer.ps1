param([string]$Python='python')
$ErrorActionPreference='Stop'
$scriptPath=Join-Path $PSScriptRoot 'install.ps1'
$tokens=$null;$parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($scriptPath,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors | Out-String)}
foreach($path in @((Join-Path $PSScriptRoot 'restart_panel.ps1'))){
 $t=$null;$e=$null
 [void][System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$t,[ref]$e)
 if($e.Count){throw ($e | Out-String)}
}
$assignments=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst]},$true)
foreach($a in $assignments){if($a.Left.Extent.Text -ieq '$home'){throw 'Variavel HOME reservada ainda existe'}}
$fn=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-PythonCaptured'},$true)
. ([scriptblock]::Create($fn.Extent.Text))
$testDir=Join-Path ([IO.Path]::GetTempPath()) ('futurefarma-installer-test-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
$logPath=Join-Path $testDir 'installer-test.log'
Set-Content -LiteralPath $logPath -Value ''
$python=$Python
$bad=Invoke-PythonCaptured -Executable $python -Arguments @('-c',"import sys; print('Traceback (most recent call last):',file=sys.stderr); print('ModuleNotFoundError: cryptography',file=sys.stderr); sys.exit(3)")
if($bad.ExitCode -ne 3 -or $bad.Output -notmatch 'ModuleNotFoundError'){throw 'Erro Python truncado ou ExitCode incorreto'}
$good=Invoke-PythonCaptured -Executable $python -Arguments @('-c',"print('PROBE_OK')")
if($good.ExitCode -ne 0 -or $good.Output -notmatch 'PROBE_OK'){throw 'Instalador nao prosseguiu apos probe com falha'}
$spacePath=Join-Path $testDir 'path with spaces'
New-Item -ItemType Directory -Path $spacePath -Force | Out-Null
$arg=Invoke-PythonCaptured -Executable $python -Arguments @('-c','import sys; print(sys.argv[1])',$spacePath)
if($arg.Output.Trim() -ne $spacePath){throw 'Caminho com espacos perdeu argumentos'}
$log=Get-Content -LiteralPath $logPath -Raw
if($log -notmatch 'Traceback' -or $log -notmatch 'ModuleNotFoundError' -or $log -notmatch 'PROBE_OK'){throw 'Log incompleto'}
Write-Output 'OK: sintaxe PowerShell, ausencia de HOME reservado, captura de traceback completa, ExitCode, continuacao apos dependencia ausente e caminhos com espacos.'

Remove-Item -LiteralPath $testDir -Recurse -Force
