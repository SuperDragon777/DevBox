[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$IsAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Start-Process powershell `
        -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" `
        -Verb RunAs
    exit
}


$LogFile = "$PSScriptRoot\WindowsOptimizer.log"
Start-Transcript -Path $LogFile -Append

function Pause {
    Read-Host "Press Enter to continue"
}

function Clear-Temp {
    Write-Host "Cleaning temp files..."
    $paths = @(
        "$env:TEMP\*",
        "$env:LOCALAPPDATA\Temp\*",
        "C:\Windows\Temp\*"
    )
    foreach ($p in $paths) {
        Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Clear-Recycle {
    Write-Host "Cleaning recycle bin..."
    Clear-RecycleBin -Force -ErrorAction SilentlyContinue
}

function Clear-WindowsUpdate {
    Write-Host "Cleaning Windows Update cache..."
    Stop-Service wuauserv -Force
    Remove-Item "C:\Windows\SoftwareDistribution\Download\*" -Recurse -Force -ErrorAction SilentlyContinue
    Start-Service wuauserv
}

function Clear-DNS {
    Write-Host "Flushing DNS cache..."
    ipconfig /flushdns | Out-Null
}

function Optimize-Disks {
    Write-Host "Optimizing disks..."

    Get-Volume |
    Where-Object {
        $_.DriveType -eq 'Fixed' -and
        $_.DriveLetter -match '^[A-Z]$'
    } |
    ForEach-Object {
        Optimize-Volume -DriveLetter $_.DriveLetter -Verbose
    }
}

function Disable-Telemetry {
    Write-Host "Disabling telemetry..."
    $services = @("DiagTrack","dmwappushservice")
    foreach ($s in $services) {
        Stop-Service $s -ErrorAction SilentlyContinue
        Set-Service $s -StartupType Disabled -ErrorAction SilentlyContinue
    }
}

function Disable-Startup {
    Write-Host "Optimizing startup..."

    $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if (Test-Path $key) {
        Remove-ItemProperty -Path $key -Name "OneDrive" -ErrorAction SilentlyContinue
    }
}


function System-Check {
    Write-Host "System file check..."
    sfc /scannow
}

do {
    Clear-Host
    Write-Host "==============================="
    Write-Host "   Windows Optimizer 10 / 11   "
    Write-Host "==============================="
    Write-Host "1 - Clean temp files"
    Write-Host "2 - Clean recycle bin"
    Write-Host "3 - Clean Windows Update cache"
    Write-Host "4 - Flush DNS cache"
    Write-Host "5 - Optimize disks"
    Write-Host "6 - Disable telemetry"
    Write-Host "7 - Optimize startup"
    Write-Host "8 - System file check (SFC)"
    Write-Host "9 - RUN ALL (recommended)"
    Write-Host "0 - Exit"
    Write-Host "==============================="

    $choice = Read-Host "Select option"

    switch ($choice) {
        "1" { Clear-Temp; Pause }
        "2" { Clear-Recycle; Pause }
        "3" { Clear-WindowsUpdate; Pause }
        "4" { Clear-DNS; Pause }
        "5" { Optimize-Disks; Pause }
        "6" { Disable-Telemetry; Pause }
        "7" { Disable-Startup; Pause }
        "8" { System-Check; Pause }
        "9" {
            Clear-Temp
            Clear-Recycle
            Clear-WindowsUpdate
            Clear-DNS
            Optimize-Disks
            Disable-Telemetry
            Disable-Startup
            Pause
        }
        "0" {
            Stop-Transcript
            exit
        }

    }
} while ($true)

Stop-Transcript
