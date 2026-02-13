param(
    [switch]$Scan,
    [switch]$Clean,
    [switch]$Backup,
    [string]$RestoreFrom
)

$ErrorActionPreference = 'Stop'

$IsAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-Host "This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

$BackupDir = "$PSScriptRoot\RegistryBackups"
$LogFile = "$PSScriptRoot\RegistryCleaner.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logEntry
    
    switch ($Level) {
        "ERROR" { Write-Host $Message -ForegroundColor Red }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        default { Write-Host $Message }
    }
}

function Backup-Registry {
    param([string]$BackupName)
    
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $BackupDir "registry_backup_$timestamp.reg"
    
    Write-Log "Creating registry backup: $backupPath"
    
    try {
        reg export HKLM $backupPath /y | Out-Null
        Write-Log "Registry backup created successfully" "SUCCESS"
        return $backupPath
    }
    catch {
        Write-Log "Failed to create registry backup: $_" "ERROR"
        return $null
    }
}

function Restore-RegistryBackup {
    param([string]$BackupPath)
    
    if (-not (Test-Path $BackupPath)) {
        Write-Log "Backup file not found: $BackupPath" "ERROR"
        return $false
    }
    
    Write-Log "Restoring registry from: $BackupPath" "WARNING"
    
    $confirm = Read-Host "Are you sure you want to restore this backup? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Log "Restore cancelled by user"
        return $false
    }
    
    try {
        reg import $BackupPath
        Write-Log "Registry restored successfully" "SUCCESS"
        return $true
    }
    catch {
        Write-Log "Failed to restore registry: $_" "ERROR"
        return $false
    }
}

function Get-InvalidUninstallEntries {
    $issues = @()
    
    $uninstallPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    )
    
    foreach ($path in $uninstallPaths) {
        if (Test-Path $path) {
            Get-ChildItem $path | ForEach-Object {
                $displayName = $_.GetValue('DisplayName')
                $uninstallString = $_.GetValue('UninstallString')
                
                if ($displayName -and $uninstallString) {
                    if ($uninstallString -match '"(.+?)"') {
                        $exePath = $matches[1]
                    } else {
                        $exePath = $uninstallString.Split(' ')[0]
                    }
                    
                    if (-not (Test-Path $exePath)) {
                        $issues += [PSCustomObject]@{
                            Type = 'InvalidUninstaller'
                            Path = $_.PSPath
                            Name = $displayName
                            Details = "Uninstaller not found: $exePath"
                        }
                    }
                }
            }
        }
    }
    
    return $issues
}

function Get-OrphanedStartupEntries {
    $issues = @()
    
    $startupPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
    )
    
    foreach ($path in $startupPaths) {
        if (Test-Path $path) {
            try {
                $props = Get-ItemProperty $path -ErrorAction SilentlyContinue
                if ($props) {
                    $props.PSObject.Properties | Where-Object { 
                        $_.Name -notin @('PSPath', 'PSParentPath', 'PSChildName', 'PSDrive', 'PSProvider') 
                    } | ForEach-Object {
                        $name = $_.Name
                        $value = $_.Value
                        
                        if ($value) {
                            if ($value -match '"(.+?)"') {
                                $exePath = $matches[1]
                            } else {
                                $exePath = $value.Split(' ')[0]
                            }
                            
                            if ($exePath -and -not (Test-Path $exePath)) {
                                $issues += [PSCustomObject]@{
                                    Type = 'OrphanedStartup'
                                    Path = $path
                                    Name = $name
                                    Details = "Startup program not found: $exePath"
                                }
                            }
                        }
                    }
                }
            }
            catch {
                Write-Log "Error scanning startup path ${path}: $_" "WARNING"
            }
        }
    }
    
    return $issues
}

function Get-InvalidSharedDLLs {
    $issues = @()
    
    $sharedDllPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\SharedDLLs'
    
    if (Test-Path $sharedDllPath) {
        try {
            $props = Get-ItemProperty $sharedDllPath -ErrorAction SilentlyContinue
            if ($props) {
                $props.PSObject.Properties | Where-Object { 
                    $_.Name -notin @('PSPath', 'PSParentPath', 'PSChildName', 'PSDrive', 'PSProvider') 
                } | ForEach-Object {
                    $dllPath = $_.Name
                    if ($dllPath -and -not (Test-Path $dllPath)) {
                        $issues += [PSCustomObject]@{
                            Type = 'InvalidSharedDLL'
                            Path = $sharedDllPath
                            Name = $dllPath
                            Details = "DLL file not found"
                        }
                    }
                }
            }
        }
        catch {
            Write-Log "Error scanning shared DLLs: $_" "WARNING"
        }
    }
    
    return $issues
}

function Get-InvalidFileAssociations {
    $issues = @()
    
    $classesPath = 'HKLM:\SOFTWARE\Classes'
    
    if (Test-Path $classesPath) {
        try {
            Get-ChildItem $classesPath -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '\\\..*$' } | ForEach-Object {
                try {
                    $extension = $_.PSChildName
                    $defaultValue = $_.GetValue('')
                    
                    if ($defaultValue) {
                        $progIdPath = Join-Path $classesPath $defaultValue
                        if (-not (Test-Path $progIdPath)) {
                            $issues += [PSCustomObject]@{
                                Type = 'InvalidFileAssociation'
                                Path = $_.PSPath
                                Name = $extension
                                Details = "ProgID not found: $defaultValue"
                            }
                        }
                    }
                }
                catch {
                    # Skip problematic entries
                }
            }
        }
        catch {
            Write-Log "Error scanning file associations: $_" "WARNING"
        }
    }
    
    return $issues
}

function Get-EmptyRegistryKeys {
    $issues = @()
    
    $safePaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
    )
    
    foreach ($path in $safePaths) {
        if (Test-Path $path) {
            try {
                Get-ChildItem $path -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        $props = $_ | Get-ItemProperty -ErrorAction SilentlyContinue
                        $hasValues = $false
                        
                        if ($props) {
                            $hasValues = ($props.PSObject.Properties | Where-Object { 
                                $_.Name -notin @('PSPath', 'PSParentPath', 'PSChildName', 'PSDrive', 'PSProvider')
                            }).Count -gt 0
                        }
                        
                        $hasSubKeys = (Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue).Count -gt 0
                        
                        if (-not $hasValues -and -not $hasSubKeys) {
                            $issues += [PSCustomObject]@{
                                Type = 'EmptyKey'
                                Path = $_.PSPath
                                Name = $_.PSChildName
                                Details = "Empty registry key"
                            }
                        }
                    }
                    catch {
                        # Skip problematic keys
                    }
                }
            }
            catch {
                Write-Log "Error scanning empty keys in ${path}: $_" "WARNING"
            }
        }
    }
    
    return $issues
}

function Scan-Registry {
    Write-Log "Starting registry scan..."
    Write-Log "=" * 60
    
    $allIssues = @()
    
    Write-Log "Scanning for invalid uninstall entries..."
    $allIssues += Get-InvalidUninstallEntries
    
    Write-Log "Scanning for orphaned startup entries..."
    $allIssues += Get-OrphanedStartupEntries
    
    Write-Log "Scanning for invalid shared DLLs..."
    $allIssues += Get-InvalidSharedDLLs
    
    Write-Log "Scanning for invalid file associations..."
    $allIssues += Get-InvalidFileAssociations
    
    Write-Log "Scanning for empty registry keys..."
    $allIssues += Get-EmptyRegistryKeys
    
    Write-Log "=" * 60
    Write-Log "Scan complete. Found $($allIssues.Count) issues" "SUCCESS"
    
    if ($allIssues.Count -gt 0) {
        Write-Log ""
        Write-Log "Issues by type:"
        $allIssues | Group-Object Type | ForEach-Object {
            Write-Log "  $($_.Name): $($_.Count)" "WARNING"
        }
        
        Write-Log ""
        Write-Log "Detailed issues:"
        $allIssues | Format-Table -AutoSize | Out-String | ForEach-Object { Write-Log $_ }
    }
    
    return $allIssues
}

function Clean-Registry {
    param([array]$Issues)
    
    if ($Issues.Count -eq 0) {
        Write-Log "No issues to clean" "SUCCESS"
        return
    }
    
    Write-Log "Creating backup before cleaning..."
    $backupPath = Backup-Registry
    
    if (-not $backupPath) {
        Write-Log "Backup failed. Aborting cleanup." "ERROR"
        return
    }
    
    Write-Log "Backup created: $backupPath" "SUCCESS"
    Write-Log ""
    
    $cleaned = 0
    $failed = 0
    
    foreach ($issue in $Issues) {
        try {
            switch ($issue.Type) {
                'InvalidUninstaller' {
                    Remove-Item -Path $issue.Path -Force -ErrorAction Stop
                    Write-Log "Removed: $($issue.Name)" "SUCCESS"
                    $cleaned++
                }
                'OrphanedStartup' {
                    Remove-ItemProperty -Path $issue.Path -Name $issue.Name -Force -ErrorAction Stop
                    Write-Log "Removed startup entry: $($issue.Name)" "SUCCESS"
                    $cleaned++
                }
                'InvalidSharedDLL' {
                    Remove-ItemProperty -Path $issue.Path -Name $issue.Name -Force -ErrorAction Stop
                    Write-Log "Removed shared DLL entry: $($issue.Name)" "SUCCESS"
                    $cleaned++
                }
                'InvalidFileAssociation' {
                    Remove-Item -Path $issue.Path -Force -ErrorAction Stop
                    Write-Log "Removed file association: $($issue.Name)" "SUCCESS"
                    $cleaned++
                }
                'EmptyKey' {
                    Remove-Item -Path $issue.Path -Force -ErrorAction Stop
                    Write-Log "Removed empty key: $($issue.Name)" "SUCCESS"
                    $cleaned++
                }
            }
        }
        catch {
            Write-Log "Failed to clean $($issue.Name): $_" "ERROR"
            $failed++
        }
    }
    
    Write-Log ""
    Write-Log "=" * 60
    Write-Log "Cleanup complete!" "SUCCESS"
    Write-Log "Cleaned: $cleaned" "SUCCESS"
    Write-Log "Failed: $failed" "WARNING"
    Write-Log "Backup location: $backupPath"
}

function Show-Menu {
    Clear-Host
    Write-Host "╔═══════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         Registry Cleaner                     ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Scan registry for issues" -ForegroundColor White
    Write-Host "2. Scan and clean registry" -ForegroundColor Yellow
    Write-Host "3. Create backup only" -ForegroundColor White
    Write-Host "4. Restore from backup" -ForegroundColor White
    Write-Host "5. View backups" -ForegroundColor White
    Write-Host "6. Exit" -ForegroundColor White
    Write-Host ""
}

function Show-Backups {
    if (-not (Test-Path $BackupDir)) {
        Write-Log "No backups found" "WARNING"
        return
    }
    
    $backups = Get-ChildItem $BackupDir -Filter "*.reg" | Sort-Object LastWriteTime -Descending
    
    if ($backups.Count -eq 0) {
        Write-Log "No backups found" "WARNING"
        return
    }
    
    Write-Host ""
    Write-Host "Available backups:" -ForegroundColor Cyan
    Write-Host ""
    
    for ($i = 0; $i -lt $backups.Count; $i++) {
        $backup = $backups[$i]
        $size = [math]::Round($backup.Length / 1MB, 2)
        Write-Host "$($i + 1). $($backup.Name) - $size MB - $($backup.LastWriteTime)" -ForegroundColor White
    }
    Write-Host ""
}

if ($Backup) {
    Write-Log "Creating manual backup..."
    $backupPath = Backup-Registry
    if ($backupPath) {
        Write-Log "Backup created: $backupPath" "SUCCESS"
    }
    exit 0
}

if ($RestoreFrom) {
    Restore-RegistryBackup -BackupPath $RestoreFrom
    exit 0
}

if ($Scan) {
    $issues = Scan-Registry
    exit 0
}

if ($Clean) {
    $issues = Scan-Registry
    if ($issues.Count -gt 0) {
        Write-Log ""
        $confirm = Read-Host "Clean $($issues.Count) issues? (yes/no)"
        if ($confirm -eq "yes") {
            Clean-Registry -Issues $issues
        } else {
            Write-Log "Cleanup cancelled by user"
        }
    }
    exit 0
}

do {
    Show-Menu
    $choice = Read-Host "Select option"
    
    switch ($choice) {
        "1" {
            $issues = Scan-Registry
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "2" {
            $issues = Scan-Registry
            if ($issues.Count -gt 0) {
                Write-Host ""
                $confirm = Read-Host "Clean $($issues.Count) issues? (yes/no)"
                if ($confirm -eq "yes") {
                    Clean-Registry -Issues $issues
                } else {
                    Write-Log "Cleanup cancelled by user"
                }
            }
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "3" {
            $backupPath = Backup-Registry
            if ($backupPath) {
                Write-Log "Backup created: $backupPath" "SUCCESS"
            }
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "4" {
            Show-Backups
            $backupNum = Read-Host "Enter backup number to restore (0 to cancel)"
            if ($backupNum -ne "0") {
                $backups = Get-ChildItem $BackupDir -Filter "*.reg" | Sort-Object LastWriteTime -Descending
                $selected = $backups[[int]$backupNum - 1]
                if ($selected) {
                    Restore-RegistryBackup -BackupPath $selected.FullName
                }
            }
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "5" {
            Show-Backups
            Write-Host ""
            Read-Host "Press Enter to continue"
        }
        "6" {
            Write-Log "Exiting..."
            exit 0
        }
        default {
            Write-Host "Invalid choice" -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
    }
} while ($true)