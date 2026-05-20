<#
.SYNOPSIS
    Register or unregister ARGO (the argo-brain IPC server) as a background
    service on Windows.  BETA.

.DESCRIPTION
    ARGO on Windows can run unattended in two ways:

      * Windows Service  - the cleanest option, but creating a service
        requires Administrator rights. This script uses the built-in
        `sc.exe` to create a service that runs `argo ipc`.

      * Scheduled Task   - the fallback when the script is not running
        elevated. A task with an "at logon" trigger starts `argo ipc`
        for the current user without needing Administrator rights.

    By default the script auto-selects: a Windows Service when elevated,
    a Scheduled Task otherwise. Use -Mode to force one or the other.

    The argo-brain IPC server is what argo-core (the Rust gateway) connects
    to. NOTE: on Windows the IPC transport relies on the AF_UNIX support
    that Windows 10 (build 17063+) and Windows 11 provide. See the Windows
    README for the caveats.

    This script is idempotent: -Action Install refreshes an existing
    service/task, and -Action Uninstall is safe to run when nothing is
    registered.

.PARAMETER Action
    Install   - register the service/task and start it (default).
    Uninstall - stop and remove the service/task.
    Status    - report whether the service/task exists and is running.

.PARAMETER Mode
    Service   - force a Windows Service (needs Administrator).
    Task      - force a Scheduled Task.
    Auto      - Service when elevated, Task otherwise (default).

.PARAMETER ArgoHome
    Data / configuration directory. Default: %USERPROFILE%\.argo

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Install

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Uninstall
#>

[CmdletBinding()]
param(
    [ValidateSet('Install', 'Uninstall', 'Status')]
    [string] $Action = 'Install',

    [ValidateSet('Auto', 'Service', 'Task')]
    [string] $Mode = 'Auto',

    [string] $ArgoHome = (Join-Path $env:USERPROFILE '.argo')
)

$ErrorActionPreference = 'Stop'

# Shared identifiers for the service and the scheduled task.
$ServiceName = 'ArgoBrain'
$TaskName    = 'ArgoBrainIPC'
$DisplayName = 'ARGO Agent - brain IPC server'

# --- output helpers ----------------------------------------------------------
function Write-Info { param([string] $Message) Write-Host "       $Message" }
function Write-Ok   { param([string] $Message) Write-Host "  OK   $Message" -ForegroundColor Green }
function Write-Warn { param([string] $Message) Write-Host "  WARN $Message" -ForegroundColor Yellow }
function Write-Err  { param([string] $Message) Write-Host "  ERR  $Message" -ForegroundColor Red }

# --- locate the argo launcher ------------------------------------------------
# install.ps1 places argo.cmd under %USERPROFILE%\.argo\bin.
function Get-ArgoLauncher {
    $candidate = Join-Path $ArgoHome 'bin\argo.cmd'
    if (Test-Path $candidate) { return $candidate }
    $onPath = Get-Command 'argo.cmd' -ErrorAction SilentlyContinue
    if ($null -ne $onPath) { return $onPath.Source }
    $onPath = Get-Command 'argo' -ErrorAction SilentlyContinue
    if ($null -ne $onPath) { return $onPath.Source }
    return $null
}

# --- privilege check ---------------------------------------------------------
function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

$IsAdmin = Test-Admin

# Decide which backend to use.
$Backend = switch ($Mode) {
    'Service' { 'Service' }
    'Task'    { 'Task' }
    default   { if ($IsAdmin) { 'Service' } else { 'Task' } }
}

if ($Backend -eq 'Service' -and -not $IsAdmin) {
    Write-Err 'A Windows Service can only be managed by an elevated shell.'
    Write-Info 'Re-run this script "As Administrator", or pass -Mode Task'
    Write-Info 'to use a per-user Scheduled Task instead.'
    exit 1
}

Write-Host '=============================================='
Write-Host '  ARGO Agent - Windows service helper (BETA)'
Write-Host '=============================================='
Write-Host "Action:    $Action"
Write-Host "Backend:   $Backend"
Write-Host "ARGO_HOME: $ArgoHome"
Write-Host ''

# ============================================================================
#  Windows Service backend
# ============================================================================
function Service-Exists {
    return ($null -ne (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue))
}

function Install-Service {
    param([string] $Launcher)

    # `cmd.exe /c argo.cmd ipc` is the command the service runs. sc.exe
    # treats everything after binPath= literally, so the whole command is
    # quoted as one argument.
    $binPath = 'cmd.exe /c "' + $Launcher + '" ipc'

    if (Service-Exists) {
        Write-Info "Service '$ServiceName' already exists - refreshing it."
        & sc.exe stop $ServiceName | Out-Null
        Start-Sleep -Seconds 1
        & sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 1
    }

    # start= auto so the brain comes up at boot.
    & sc.exe create $ServiceName binPath= $binPath start= auto DisplayName= $DisplayName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "sc.exe create failed (exit $LASTEXITCODE)" }
    & sc.exe description $ServiceName 'ARGO Agent brain - IPC server for the argo-core gateway.' | Out-Null

    & sc.exe start $ServiceName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn 'Service created but did not start - check it with -Action Status.'
    } else {
        Write-Ok "Windows Service '$ServiceName' created and started."
    }
    Write-Info "Manage it with: sc.exe {start|stop|query} $ServiceName"
    Write-Info 'NOTE: a plain sc.exe service has no auto-restart and runs `argo`'
    Write-Info 'in a console-less context. For production use, wrap it with a'
    Write-Info 'service host such as NSSM or WinSW. This is a beta convenience.'
}

function Uninstall-Service {
    if (-not (Service-Exists)) {
        Write-Ok "No Windows Service '$ServiceName' is registered."
        return
    }
    & sc.exe stop $ServiceName | Out-Null
    Start-Sleep -Seconds 1
    & sc.exe delete $ServiceName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Windows Service '$ServiceName' removed."
    } else {
        Write-Err "Failed to remove service '$ServiceName' (exit $LASTEXITCODE)."
        exit 1
    }
}

function Status-Service {
    if (-not (Service-Exists)) {
        Write-Info "Windows Service '$ServiceName': not registered."
        return
    }
    $svc = Get-Service -Name $ServiceName
    Write-Info "Windows Service '$ServiceName': $($svc.Status)"
}

# ============================================================================
#  Scheduled Task backend (no Administrator rights required)
# ============================================================================
function Task-Exists {
    return ($null -ne (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue))
}

function Install-Task {
    param([string] $Launcher)

    if (Task-Exists) {
        Write-Info "Scheduled task '$TaskName' already exists - refreshing it."
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    # The task runs `cmd.exe /c "<launcher>" ipc`.
    $action = New-ScheduledTaskAction -Execute 'cmd.exe' `
        -Argument ('/c "' + $Launcher + '" ipc')

    # Start the brain when the current user logs on.
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    # Run only while the user is logged in; no stored password needed.
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
        -LogonType Interactive

    # Let it run indefinitely and restart a few times on failure.
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0)

    Register-ScheduledTask -TaskName $TaskName `
        -Description 'ARGO Agent brain - IPC server (beta).' `
        -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings | Out-Null
    Write-Ok "Scheduled task '$TaskName' registered (runs at logon)."

    # Start it now so the user does not have to log out and back in.
    Start-ScheduledTask -TaskName $TaskName
    Write-Ok "Scheduled task '$TaskName' started."
    Write-Info "Manage it with: schtasks /Query /TN $TaskName"
    Write-Info '             or the Task Scheduler GUI (taskschd.msc).'
}

function Uninstall-Task {
    if (-not (Task-Exists)) {
        Write-Ok "No scheduled task '$TaskName' is registered."
        return
    }
    # Stop a running instance first, then remove the definition.
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Ok "Scheduled task '$TaskName' removed."
}

function Status-Task {
    if (-not (Task-Exists)) {
        Write-Info "Scheduled task '$TaskName': not registered."
        return
    }
    $task = Get-ScheduledTask -TaskName $TaskName
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Info "Scheduled task '$TaskName': state=$($task.State), lastResult=$($info.LastTaskResult)"
}

# ============================================================================
#  Dispatch
# ============================================================================
switch ($Action) {
    'Install' {
        $launcher = Get-ArgoLauncher
        if ($null -eq $launcher) {
            Write-Err 'The argo launcher was not found.'
            Write-Info 'Run install.ps1 first to install ARGO.'
            exit 1
        }
        Write-Info "Using launcher: $launcher"
        if ($Backend -eq 'Service') { Install-Service -Launcher $launcher }
        else                        { Install-Task    -Launcher $launcher }
    }
    'Uninstall' {
        # Remove whichever backend(s) are present so cleanup is thorough.
        if ($IsAdmin) { Uninstall-Service }
        Uninstall-Task
    }
    'Status' {
        if ($IsAdmin) { Status-Service }
        Status-Task
    }
}

Write-Host ''
Write-Host 'Done.'
