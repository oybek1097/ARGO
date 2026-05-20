<#
.SYNOPSIS
    ARGO Agent v3.0 — native Windows installer (BETA).

.DESCRIPTION
    Installs ARGO directly onto a Windows host:
      1. Checks for the required toolchain (Python 3.12+, optionally Rust/Cargo).
      2. Installs the stdlib-only `argo_brain` Python package under
         %USERPROFILE%\.argo\lib  (no `pip install` is needed — the brain
         has no third-party dependencies).
      3. Builds the `argo-core` Rust gateway with `cargo build --release`
         IF Cargo is present; otherwise it is skipped with a note. The
         stdlib-only brain runs standalone without argo-core.
      4. Creates the %USERPROFILE%\.argo\ directory layout.
      5. Installs an `argo.cmd` launcher into %USERPROFILE%\.argo\bin and
         adds that directory to the per-user PATH.

    The script is idempotent: re-running it refreshes the installed files
    and the launcher without producing duplicates.

    Windows support is BETA. See README.md in this folder for known
    limitations (notably the AF_UNIX / IPC socket caveats and the
    Unix-oriented sandbox backends).

.PARAMETER ArgoHome
    Data / configuration directory. Default: %USERPROFILE%\.argo

.PARAMETER SkipCore
    Do not build argo-core even if Cargo is available.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -SkipCore
#>

[CmdletBinding()]
param(
    [string] $ArgoHome = (Join-Path $env:USERPROFILE '.argo'),
    [switch] $SkipCore
)

# Stop on the first unhandled error so a half-finished install is obvious.
$ErrorActionPreference = 'Stop'

# --- output helpers ----------------------------------------------------------
function Write-Info { param([string] $Message) Write-Host "       $Message" }
function Write-Ok   { param([string] $Message) Write-Host "  OK   $Message" -ForegroundColor Green }
function Write-Warn { param([string] $Message) Write-Host "  WARN $Message" -ForegroundColor Yellow }
function Write-Err  { param([string] $Message) Write-Host "  ERR  $Message" -ForegroundColor Red }

# --- 0. resolve paths --------------------------------------------------------
# This script lives in <repo>\release\windows\install.ps1, so the repo root
# is two directories up.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path

$BinDir = Join-Path $ArgoHome 'bin'
$LibDir = Join-Path $ArgoHome 'lib'

Write-Host '=============================================='
Write-Host '  ARGO Agent v3.0 - Windows installer (BETA)'
Write-Host '=============================================='
Write-Host "Repo:      $RepoRoot"
Write-Host "ARGO_HOME: $ArgoHome"
Write-Host ''

# --- 1. locate a Python 3.12+ interpreter ------------------------------------
# Windows offers several entry points; try them in order of preference.
$PythonExe = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { continue }

    # `py` is the launcher; ask it explicitly for 3.12.
    $probeArgs = if ($candidate -eq 'py') { @('-3', '-c') } else { @('-c') }
    $verScript = 'import sys; print("%d.%d" % sys.version_info[:2])'
    try {
        $ver = (& $cmd.Source @probeArgs $verScript 2>$null)
    } catch {
        continue
    }
    if (-not $ver) { continue }

    $parts = $ver.Trim().Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
        # Record the exact invocation needed to reach this interpreter.
        if ($candidate -eq 'py') {
            $PythonExe  = $cmd.Source
            $PythonArgs = @('-3')
        } else {
            $PythonExe  = $cmd.Source
            $PythonArgs = @()
        }
        Write-Ok "python $ver  ($PythonExe)"
        break
    } else {
        Write-Warn "found Python $ver via '$candidate' - ARGO needs 3.12+"
    }
}

if ($null -eq $PythonExe) {
    Write-Err 'Python 3.12 or newer was not found.'
    Write-Info 'Install it from https://www.python.org/downloads/windows/'
    Write-Info 'or run:  winget install Python.Python.3.12'
    Write-Info 'Make sure "Add python.exe to PATH" is selected during install.'
    exit 1
}

# --- 2. locate Cargo (optional) ----------------------------------------------
$CargoExe = $null
$cargoCmd = Get-Command 'cargo' -ErrorAction SilentlyContinue
if ($null -ne $cargoCmd) {
    $CargoExe = $cargoCmd.Source
    $cargoVer = (& $CargoExe --version) 2>$null
    Write-Ok "cargo found  ($cargoVer)"
} else {
    Write-Warn 'cargo not found - argo-core (the Rust gateway) will be skipped.'
    Write-Info 'The stdlib-only brain runs standalone without argo-core.'
    Write-Info 'To build the gateway later, install Rust from https://rustup.rs'
}

# --- 3. create the ARGO_HOME directory layout --------------------------------
Write-Host ''
Write-Info "Preparing $ArgoHome ..."
foreach ($sub in @('', 'data', 'skills', 'plugins', 'bin', 'lib')) {
    $path = if ($sub) { Join-Path $ArgoHome $sub } else { $ArgoHome }
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}
Write-Ok "$ArgoHome\{data,skills,plugins,bin,lib}"

# --- 4. install the argo-brain Python package --------------------------------
# The brain is stdlib-only: a plain file copy is the whole "install".
Write-Host ''
Write-Info 'Installing the argo-brain Python package...'
$BrainSrc = Join-Path $RepoRoot 'argo-brain\argo_brain'
if (-not (Test-Path $BrainSrc)) {
    Write-Err "argo-brain\argo_brain not found under $RepoRoot"
    Write-Info 'Run this script from inside an ARGO repository checkout.'
    exit 1
}
$BrainDst = Join-Path $LibDir 'argo_brain'
# Remove any previous copy so the install is a clean refresh (idempotent).
if (Test-Path $BrainDst) {
    Remove-Item -Recurse -Force $BrainDst
}
Copy-Item -Recurse -Force $BrainSrc $BrainDst
# Drop stale bytecode caches that may have been copied along.
Get-ChildItem -Path $BrainDst -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
Write-Ok "$BrainDst"

# --- 5. build argo-core (optional) -------------------------------------------
$CoreBin = $null
$CoreToml = Join-Path $RepoRoot 'argo-core\Cargo.toml'
if ($SkipCore) {
    Write-Host ''
    Write-Warn '-SkipCore was passed - not building argo-core.'
} elseif ($null -eq $CargoExe) {
    Write-Host ''
    Write-Warn 'Skipping argo-core build (cargo is not installed).'
} elseif (-not (Test-Path $CoreToml)) {
    Write-Host ''
    Write-Warn 'Skipping argo-core build (argo-core\Cargo.toml not found).'
} else {
    Write-Host ''
    Write-Info 'Building argo-core (Rust gateway) - this may take a few minutes...'
    Push-Location (Join-Path $RepoRoot 'argo-core')
    try {
        & $CargoExe build --release
        if ($LASTEXITCODE -ne 0) {
            throw "cargo build failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
    $built = Join-Path $RepoRoot 'argo-core\target\release\argo-core.exe'
    if (Test-Path $built) {
        Copy-Item -Force $built (Join-Path $BinDir 'argo-core.exe')
        $CoreBin = Join-Path $BinDir 'argo-core.exe'
        Write-Ok "$CoreBin"
    } else {
        Write-Warn 'cargo reported success but argo-core.exe was not found.'
    }
}

# --- 6. install the `argo` launcher ------------------------------------------
# argo.cmd forwards `argo core ...` to the gateway binary (when present) and
# every other subcommand to `python -m argo_brain`. Writing a .cmd file keeps
# the launcher usable from cmd.exe, PowerShell and Explorer alike.
Write-Host ''
Write-Info 'Installing the argo launcher...'

# Build the exact python invocation string for the .cmd file.
$PyInvoke = if ($PythonArgs.Count -gt 0) {
    '"' + $PythonExe + '" ' + ($PythonArgs -join ' ')
} else {
    '"' + $PythonExe + '"'
}

$launcherLines = @(
    '@echo off'
    'rem ARGO Agent launcher (installed by release\windows\install.ps1).'
    'rem `argo core ...` runs the Rust gateway; anything else goes to the brain.'
    "set ""ARGO_HOME=$ArgoHome"""
    "set ""PYTHONPATH=$LibDir;%PYTHONPATH%"""
    'if /I "%~1"=="core" ('
    '    shift'
)
if ($CoreBin) {
    $launcherLines += "    ""$CoreBin"" %1 %2 %3 %4 %5 %6 %7 %8 %9"
} else {
    $launcherLines += '    echo argo-core is not installed on this host.'
    $launcherLines += '    echo Re-run install.ps1 after installing Rust ^(https://rustup.rs^).'
    $launcherLines += '    exit /b 1'
}
$launcherLines += @(
    '    exit /b %ERRORLEVEL%'
    ')'
    "$PyInvoke -m argo_brain %*"
    'exit /b %ERRORLEVEL%'
)
$LauncherPath = Join-Path $BinDir 'argo.cmd'
# Write ASCII so cmd.exe parses the batch file without a BOM.
Set-Content -Path $LauncherPath -Value $launcherLines -Encoding Ascii
Write-Ok "$LauncherPath"

# --- 7. add the launcher directory to the per-user PATH ----------------------
# Per-user PATH avoids needing Administrator rights. The change applies to
# new shells; the current session's PATH is updated below for convenience.
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($null -eq $userPath) { $userPath = '' }
$onPath = $userPath.Split(';') | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') }
if (-not $onPath) {
    $newPath = if ($userPath) { "$userPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Write-Ok "added $BinDir to your user PATH"
    Write-Info 'Open a NEW terminal for the PATH change to take effect.'
} else {
    Write-Ok "$BinDir is already on your user PATH"
}
# Make `argo` usable immediately in this very session too.
if (-not ($env:Path.Split(';') | Where-Object { $_.TrimEnd('\') -ieq $BinDir.TrimEnd('\') })) {
    $env:Path = "$env:Path;$BinDir"
}

# --- 8. summary --------------------------------------------------------------
Write-Host ''
Write-Host '=============================================='
Write-Host '  Installation complete (Windows beta).'
Write-Host '=============================================='
Write-Host ''
Write-Host 'Installed:'
Write-Host "  $LauncherPath   - argo launcher"
if ($CoreBin) {
    Write-Host "  $CoreBin   - Rust gateway"
} else {
    Write-Host '  (argo-core not installed - brain-only mode)'
}
Write-Host "  $BrainDst   - Python brain"
Write-Host ''
Write-Host 'Next steps (in a NEW terminal):'
Write-Host '  argo setup      # interactive setup wizard'
Write-Host '  argo doctor     # diagnostics'
Write-Host '  argo chat       # interactive conversation (no API key needed)'
Write-Host '  argo serve      # HTTP gateway on http://127.0.0.1:8000'
Write-Host ''
Write-Host 'To run ARGO in the background, see argo-service.ps1 in this folder.'
Write-Host 'Windows support is BETA - see README.md for known limitations.'
