param(
    [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-UninstallProgramsFromRegistry {
    param(
        [Microsoft.Win32.RegistryKey]$RootKey,
        [string]$SubKeyPath,
        [string]$Source
    )

    $result = @()

    try {
        $baseKey = $RootKey.OpenSubKey($SubKeyPath, $false)
        if (-not $baseKey) {
            return @()
        }

        foreach ($subName in $baseKey.GetSubKeyNames()) {
            try {
                $subKey = $baseKey.OpenSubKey($subName, $false)
                if (-not $subKey) { continue }

                $displayName   = $subKey.GetValue('DisplayName')
                $displayVer    = $subKey.GetValue('DisplayVersion')
                $publisher     = $subKey.GetValue('Publisher')
                $installDate   = $subKey.GetValue('InstallDate')
                $installLoc    = $subKey.GetValue('InstallLocation')
                $uninstallStr  = $subKey.GetValue('UninstallString')
                $estimatedSize = $subKey.GetValue('EstimatedSize')

                if ([string]::IsNullOrWhiteSpace($displayName)) {
                    continue
                }

                $installDateParsed = $null
                if ($installDate -and ($installDate -is [string]) -and $installDate.Length -eq 8) {
                    [DateTime]::TryParseExact($installDate, 'yyyyMMdd', $null, [System.Globalization.DateTimeStyles]::None, [ref]$installDateParsed) | Out-Null
                }

                $sizeMB = $null
                if ($estimatedSize -and $estimatedSize -is [int]) {
                    $sizeMB = [Math]::Round($estimatedSize / 1024, 2)
                }

                $obj = [PSCustomObject]@{
                    ComputerName   = $env:COMPUTERNAME
                    UserName       = $env:USERNAME
                    Name           = $displayName
                    Version        = $displayVer
                    Publisher      = $publisher
                    InstallDate    = if ($installDateParsed) { $installDateParsed } else { $installDate }
                    InstallLocation= $installLoc
                    UninstallString= $uninstallStr
                    SizeMB         = $sizeMB
                    Source         = $Source
                    Architecture   = if ($SubKeyPath -like '*Wow6432Node*') { 'x86' } else { 'x64/neutral' }
                    Type           = 'Win32'
                }

                $result += $obj
            }
            catch {
                continue
            }
        }
    }
    catch {
        Write-Verbose "Failed to read registry key $SubKeyPath : $_"
    }

    return $result
}

function Get-InstalledWin32Programs {
    [CmdletBinding()]
    param()

    $reg = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,
                                                      [Microsoft.Win32.RegistryView]::Registry64)
    $reg32 = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::LocalMachine,
                                                        [Microsoft.Win32.RegistryView]::Registry32)

    $hku = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::Users,
                                                      [Microsoft.Win32.RegistryView]::Default)
    $hkcu = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::CurrentUser,
                                                       [Microsoft.Win32.RegistryView]::Default)

    $all = @()

    $all += Get-UninstallProgramsFromRegistry -RootKey $reg  -SubKeyPath 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'           -Source 'HKLM-64'
    $all += Get-UninstallProgramsFromRegistry -RootKey $reg32 -SubKeyPath 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'           -Source 'HKLM-32'
    $all += Get-UninstallProgramsFromRegistry -RootKey $reg  -SubKeyPath 'SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall' -Source 'HKLM-Wow64'

    $all += Get-UninstallProgramsFromRegistry -RootKey $hkcu -SubKeyPath 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'            -Source 'HKCU'

    foreach ($sid in $hku.GetSubKeyNames()) {
        if ($sid -notmatch '^\S-\d-\d+(-\d+)+$') { continue }
        $subPath = "$sid\Software\Microsoft\Windows\CurrentVersion\Uninstall"
        $all += Get-UninstallProgramsFromRegistry -RootKey $hku -SubKeyPath $subPath -Source "HKU-$sid" 
    }

    $deduped = $all | Sort-Object Name, Version, Publisher, Source -Unique
    return $deduped
}

function Get-UwpApps {
    [CmdletBinding()]
    param()

    $apps = @()
    try {
        $packages = Get-AppxPackage -ErrorAction SilentlyContinue
        foreach ($pkg in $packages) {
            $apps += [PSCustomObject]@{
                ComputerName    = $env:COMPUTERNAME
                UserName        = $env:USERNAME
                Name            = $pkg.Name
                Version         = $pkg.Version.ToString()
                Publisher       = $pkg.PublisherDisplayName
                InstallDate     = $null
                InstallLocation = $pkg.InstallLocation
                UninstallString = $null
                SizeMB          = $null
                Source          = 'AppxPackage'
                Architecture    = $pkg.ProcessorArchitecture
                Type            = 'UWP'
            }
        }
    }
    catch {
        Write-Verbose "Error while getting UWP applications: $_"
    }
    return $apps
}

function Invoke-SoftwareAudit {
    [CmdletBinding()]
    param(
        [string]$OutputPath
    )

    Write-Host "=== Installed software audit on computer $env:COMPUTERNAME ===" -ForegroundColor Cyan

    Write-Host "Collecting Win32 applications from registry..." -ForegroundColor Yellow
    $win32 = Get-InstalledWin32Programs
    $win32Count = @($win32).Count
    Write-Host "Found Win32 applications: $win32Count" -ForegroundColor Green

    Write-Host "Collecting UWP / Store applications..." -ForegroundColor Yellow
    $uwp = Get-UwpApps
    $uwpCount = @($uwp).Count
    Write-Host "Found UWP applications: $uwpCount" -ForegroundColor Green

    $all = @()
    $all += $win32
    $all += $uwp

    if (-not $OutputPath -or [string]::IsNullOrWhiteSpace($OutputPath)) {
        $ts = (Get-Date).ToString('yyyyMMdd_HHmmss')

        $scriptDir = $PSScriptRoot
        if (-not $scriptDir -or [string]::IsNullOrWhiteSpace($scriptDir)) {
            $scriptDir = (Get-Location).Path
        }

        $OutputPath = Join-Path $scriptDir ("software_audit_{0}_{1}.csv" -f $env:COMPUTERNAME, $ts)
    }

    Write-Host "Saving result to CSV: $OutputPath" -ForegroundColor Yellow
    try {
        $all | Sort-Object Type, Name | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8
        Write-Host "File saved successfully." -ForegroundColor Green
    }
    catch {
        Write-Warning "Failed to save CSV: $_"
    }

    Write-Host ""
    Write-Host "First 50 records:" -ForegroundColor Cyan
    $table = $all |
        Sort-Object Type, Name |
        Select-Object Type, Name, Version, Publisher, InstallDate, SizeMB, Source |
        Select-Object -First 50 |
        Format-Table -AutoSize |
        Out-String
    Write-Host $table

    return $all
}

try {
    Invoke-SoftwareAudit -OutputPath $OutputPath | Out-Null
}
catch {
    Write-Error "Audit failed with error: $_"
    exit 1
}

exit 0

