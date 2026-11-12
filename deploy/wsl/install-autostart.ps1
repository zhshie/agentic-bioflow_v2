# install-autostart.ps1 - register (or remove) the Windows logon task that starts the
# supervisor inside WSL, so the platform comes back after a reboot without anyone typing.
#
# Not the Task Scheduler window or NSSM: those are clicks or an extra install that nobody can read
# first; this is one command you can read, and it changes nothing unless you add -Apply.
#
# 用法 (一般 PowerShell 視窗, 不要用系統管理員):
#   .\install-autostart.ps1 -Script <WSL 裡 abf-supervise.sh 的完整路徑>   只印出將要做什麼, 沒有更動
#   .\install-autostart.ps1 -Script <路徑> -Apply                         註冊 (重複執行結果相同)
#   .\install-autostart.ps1 -Remove                                       移除這個工作
# 選用: -Distro <WSL 發行版名稱, 預設 Ubuntu>  -User <WSL 使用者, 預設用該發行版目前的使用者>
#
# 工作名稱 abf-platform-autostart; 觸發: 目前這位使用者登入時; 動作: wsl.exe -d <distro> -u <user> --exec <腳本>;
# 一般權限; 失敗時每分鐘重試, 不限時間長度。它不需要系統管理員權限, 權限不夠時會說明白並停手。
# -Apply 會先確認 -Script 在該發行版裡存在且可執行, 不然停手說明, 不註冊。
# 若 PowerShell 的執行原則擋下這個檔案, 只對這一支放行 (不改系統設定): powershell -ExecutionPolicy Bypass -File .\install-autostart.ps1 ...
[CmdletBinding()]
param(
    [string]$Distro = 'Ubuntu',
    [string]$User = '',
    [string]$Script = '',
    [switch]$Apply,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$TaskName = 'abf-platform-autostart'
$Me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

function Stop-Here([string]$Message, [int]$Code) {
    Write-Host $Message
    exit $Code
}

function Test-Token([string]$Value) {
    return ($Value -match '^[A-Za-z0-9_./-]+$')
}

function Resolve-Inputs {
    if (-not (Test-Token $Distro)) { Stop-Here "發行版名稱「$Distro」只能用英文字母、數字與 _ . / - ; 請改用 -Distro 重新指定。" 2 }
    if ([string]::IsNullOrEmpty($Script)) {
        Stop-Here "沒有指定看守腳本的路徑; 請加上 -Script <WSL 裡 abf-supervise.sh 的完整路徑> 再執行。" 2
    }
    if (-not $Script.StartsWith('/') -or -not (Test-Token $Script)) {
        Stop-Here "看守腳本的路徑「$Script」要是 WSL 裡以 / 開頭的完整路徑, 且不含空白; 請改用 -Script 重新指定。" 2
    }
    if ([string]::IsNullOrEmpty($script:User)) {
        try { $script:User = ((& wsl.exe -d $Distro --exec whoami) | Out-String).Trim() } catch { $script:User = '' }
    }
    if ([string]::IsNullOrEmpty($script:User) -or -not (Test-Token $script:User)) {
        Stop-Here "查不到 WSL 發行版 $Distro 裡的使用者; 請加上 -User <WSL 使用者名稱> 再執行。" 2
    }
}

function Get-ActionArgument {
    return "-d $Distro -u $User --exec $Script"
}

function Show-Plan {
    Resolve-Inputs
    Write-Host '[預設模式 / dry run] 沒有更動 (no change made). 這是它將要做的事:'
    Write-Host "  工作名稱 (task name): $TaskName"
    Write-Host "  觸發條件 (trigger)  : 使用者 $Me 登入時 (at logon of $Me)"
    Write-Host "  動作 (action)       : wsl.exe $(Get-ActionArgument)"
    Write-Host '  權限 (rights)       : 一般權限 (Limited), 失敗時每分鐘重試, 不限時間長度'
    Write-Host '要真的註冊, 請加上 -Apply; 要移除, 請用 -Remove。'
}

function Invoke-Apply {
    Resolve-Inputs
    # the script has to be there and be runnable inside the distro, or the logon task would fail every minute
    $code = 1
    try { & wsl.exe -d $Distro -u $User --exec test -x $Script 2>$null; $code = $LASTEXITCODE } catch { $code = 1 }
    if ($code -ne 0) { Stop-Here "在 WSL 發行版 ${Distro} 裡找不到 ${Script}，或它不能執行; 這次沒有註冊任何工作。請確認 -Script 的路徑 (可用 wsl.exe -d $Distro --exec ls -l ${Script} 看)，並先在 WSL 裡 chmod +x 它，再重新執行 -Apply。" 2 }
    $action = New-ScheduledTaskAction -Execute 'wsl.exe' -Argument (Get-ActionArgument)
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $Me
    $principal = New-ScheduledTaskPrincipal -UserId $Me -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -Hidden
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    } catch {
        $msg = $_.Exception.Message
        if ($_.Exception -is [System.UnauthorizedAccessException] -or $msg -match '0x80070005' -or $msg -match 'denied') {
            Stop-Here '權限不足: 這台電腦不讓一般使用者註冊登入工作。請請有系統管理員權限的人在他的 PowerShell 裡執行同一行指令 (加 -Apply), 或回報給維護者; 這個腳本不會自己提升權限。' 3
        }
        throw
    }
    Write-Host "已註冊工作 $TaskName (使用者 $Me 登入時執行: wsl.exe $(Get-ActionArgument))。重複執行 -Apply 結果相同。"
}

function Invoke-Remove {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        Write-Host "本來就沒有這個工作 ($TaskName), 沒有更動。"
        exit 0
    }
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    } catch {
        $msg = $_.Exception.Message
        if ($_.Exception -is [System.UnauthorizedAccessException] -or $msg -match '0x80070005' -or $msg -match 'denied') {
            Stop-Here '權限不足: 這個工作不是這位使用者能移除的。請請有系統管理員權限的人移除它, 或回報給維護者; 這個腳本不會自己提升權限。' 3
        }
        throw
    }
    Write-Host "已移除工作 $TaskName。"
}

if ($Apply -and $Remove) {
    Stop-Here '-Apply 與 -Remove 不能一起用; 請擇一。' 2
}
if ($Remove) {
    Invoke-Remove
}
elseif ($Apply) {
    Invoke-Apply
}
else {
    Show-Plan
}
