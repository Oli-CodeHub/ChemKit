param(
    [string]$Target,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $ScriptDir "scripts\install_chemkit.py"
$Arguments = @($Installer)
if ($Target) { $Arguments += @("--target", $Target) }
if ($SkipDeps) { $Arguments += "--skip-deps" }

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCommand) { $PythonCommand = Get-Command py -ErrorAction SilentlyContinue }
if ($PythonCommand) {
    & $PythonCommand.Source @Arguments
    exit $LASTEXITCODE
}

$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCommand) {
    Write-Host "No Python found; using uv to bootstrap Python 3.11."
    $UvArguments = @("run", "--python", "3.11", "--no-project", $Installer)
    if ($Target) { $UvArguments += @("--target", $Target) }
    if ($SkipDeps) { $UvArguments += "--skip-deps" }
    & $UvCommand.Source @UvArguments
    exit $LASTEXITCODE
}

Write-Error "ChemKit could not find Python or uv. Install Python 3.9+ or uv, then run install.ps1 again."
