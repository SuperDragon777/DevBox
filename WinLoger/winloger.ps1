$outFile = "$env:USERPROFILE\Desktop\WinLog_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$info = @()

$info += "`n===== SYSTEM =====`n"
$os = Get-CimInstance Win32_OperatingSystem
$info += "Hostname     : $env:COMPUTERNAME"
$info += "User         : $env:USERNAME"
$info += "OS           : $($os.Caption) (Build $($os.BuildNumber))"
$info += "Arch         : $env:PROCESSOR_ARCHITECTURE"
$info += "Boot time    : $($os.LastBootUpTime)"
$info += "Uptime       : $((Get-Date) - $os.LastBootUpTime)"
$info += "Domain       : $env:USERDOMAIN"
$info += "Time zone    : $(Get-TimeZone | % DisplayName)"

$info += "`n===== HARDWARE =====`n"
$cpu = Get-CimInstance Win32_Processor
$info += "CPU          : $($cpu.Name.Trim()) ($($cpu.NumberOfCores) cores)"
$ram = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
$info += "RAM          : $([math]::Round($ram,2)) GB"
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
$info += "GPU          : $($gpu.Name)"
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3"
$disk | ForEach-Object { $info += "Drive $_($_.DeviceID) : $([math]::Round($_.Size/1GB,2)) GB total, $([math]::Round($_.FreeSpace/1GB,2)) GB free" }
$bios = Get-CimInstance Win32_BIOS
$info += "BIOS         : $($bios.Manufacturer) $($bios.Name) ($($bios.Version))"
$mb = Get-CimInstance Win32_BaseBoard
$info += "Motherboard  : $($mb.Manufacturer) $($mb.Product)"

$info += "`n===== NETWORK =====`n"
$adapters = Get-NetAdapter | Where-Object Status -eq 'Up'
$adapters | ForEach-Object {
    $ip = Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
    $gw = Get-NetRoute -InterfaceIndex $_.InterfaceIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue
    $dns = (Get-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex).ServerAddresses -join ', '
    $info += "Adapter      : $($_.Name)"
    $info += "  MAC        : $($_.MacAddress)"
    $info += "  IP         : $($ip.IPAddress -join ', ')"
    $info += "  Gateway    : $($gw.NextHop -join ', ')"
    $info += "  DNS        : $dns`n"
}
$ports = Get-NetTCPConnection | Group-Object State | Sort-Object Count -Descending
$info += "Open TCP ports (listening):"
Get-NetTCPConnection -State Listen | Select-Object LocalPort, OwningProcess | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== PROCESSES (Top 20 by RAM) =====`n"
Get-Process | Sort-Object WorkingSet -Descending | Select-Object -First 20 | 
    Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== NON‑STANDARD SERVICES =====`n"
Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.State -ne 'Running' } | 
    Select-Object Name, DisplayName, State, StartMode | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== INSTALLED SOFTWARE =====`n"
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*,
                    HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*,
                    HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue |
    Where-Object DisplayName | Select-Object DisplayName, DisplayVersion, Publisher |
    Sort-Object DisplayName | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== STARTUP PROGRAMS =====`n"
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== ENVIRONMENT VARIABLES =====`n"
Get-ChildItem Env: | Sort-Object Name | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== LOCAL USERS =====`n"
Get-LocalUser | Select-Object Name, Enabled, LastLogon | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== RECENT DOCUMENTS =====`n"
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Recent" -ErrorAction SilentlyContinue | 
    Select-Object Name, LastWriteTime, Length | Format-Table -AutoSize | Out-String -Width 4096 | % { $info += $_ }

$info += "`n===== SECURITY STATUS =====`n"
$defender = Get-MpComputerStatus -ErrorAction SilentlyContinue
if ($defender) {
    $info += "Defender     : $($defender.AntivirusEnabled)"
    $info += "Real‑time    : $($defender.RealTimeProtectionEnabled)"
    $info += "Last scan    : $($defender.QuickScanEndTime)"
} else { $info += "Defender     : Not available" }
$fw = Get-NetFirewallProfile | Select-Object Name, Enabled
$info += "Firewall profiles:"
$fw | ForEach-Object { $info += "  $($_.Name) : $($_.Enabled)" }

$info | Out-File -FilePath $outFile -Encoding utf8
Write-Host "[+] Full log saved to: $outFile"