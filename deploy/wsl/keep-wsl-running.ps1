# Not NSSM or a Windows service: a service needs administrator rights; this is one Task Scheduler task of the current user, at logon.
# Keeps WSL open after you log in to Windows, so that systemd inside WSL can start and restart the platform.
# It starts and restarts nothing of the platform; that is systemd's job (docs/OPERATIONS.md, "Desktop platform in WSL").
#
#   powershell -ExecutionPolicy Bypass -File keep-wsl-running.ps1            show what would be done (changes nothing)
#   powershell -ExecutionPolicy Bypass -File keep-wsl-running.ps1 -Apply     register the task abf-wsl-keepalive
#   powershell -ExecutionPolicy Bypass -File keep-wsl-running.ps1 -Remove    remove it again
#   add  -Distro <name>  to use one WSL distribution; without it the default one is used (see: wsl -l -v)
#
# Runs as you, with normal rights, and does not ask for administrator rights. Nothing starts while nobody is logged in to Windows.
param(
    [switch]$Apply,
    [switch]$Remove,
    [string]$Distro
)
$ErrorActionPreference = 'Stop'
$TaskName = 'abf-wsl-keepalive'

# the wsl.exe arguments: -d only when a distribution was named (a name with spaces is quoted)
$wslArgs = ''
if ($Distro) { $wslArgs = '-d "' + $Distro + '" ' }
$wslArgs = $wslArgs + '--exec /bin/sleep infinity'

if ($Apply -and $Remove) {
    Write-Host 'Give either -Apply or -Remove, not both.'
    exit 1
}

if ($Remove) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Host "The task ${TaskName} is not there; nothing to remove."
        exit 0
    }
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed the task ${TaskName}."
    } catch {
        Write-Host "Could not remove the task ${TaskName}: $($_.Exception.Message)"
        Write-Host 'If this says access is denied, the task was made by another account or as administrator; remove it from that account.'
        exit 1
    }
    exit 0
}

if ($Apply) {
    try {
        $action   = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument $wslArgs
        $trigger  = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
        $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -MultipleInstances IgnoreNew
        $principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        Write-Host "Registered the task ${TaskName}: at your logon it runs  wsl.exe $wslArgs"
        Write-Host "Undo it with:  -Remove"
    } catch {
        Write-Host "Could not register the task ${TaskName}: $($_.Exception.Message)"
        Write-Host 'This script does not ask for administrator rights. If this says access is denied, your account is not allowed to make scheduled tasks; ask the computer administrator, or do not use this script.'
        exit 1
    }
    exit 0
}

# default: only say what -Apply would do
Write-Host 'Nothing was changed. This is what -Apply would do:'
Write-Host "  register a task named $TaskName"
Write-Host '  when: you log in to Windows (nothing starts while nobody is logged in)'
Write-Host "  what: wsl.exe $wslArgs   (hidden window, no time limit, also on battery, one copy at a time, normal rights)"
Write-Host 'Run it again with -Apply to do it, or with -Remove to take the task away.'
