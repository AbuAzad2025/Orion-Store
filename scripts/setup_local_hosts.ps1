#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Map Azadexa beta tenant subdomains to 127.0.0.1 for local testing.
.DESCRIPTION
  Adds entries like "127.0.0.1 beta-ramallah.local.azadexa" to the Windows
  hosts file so each tenant can be tested with its own subdomain on localhost.
  Run in an elevated PowerShell prompt.
#>

$hostsFile = "$env:SystemRoot\System32\drivers\etc\hosts"
$tenants = @(
    "beta-ramallah",
    "beta-nablus",
    "beta-hebron",
    "beta-jenin",
    "beta-bethlehem",
    "beta-tulkarm",
    "beta-amman",
    "beta-irbid",
    "beta-zarqa",
    "beta-aqaba"
)

$marker = "# Azadexa local beta tenants"

$lines = Get-Content -Path $hostsFile -ErrorAction SilentlyContinue

if ($lines -contains $marker) {
    Write-Host "Azadexa tenant entries already present." -ForegroundColor Green
    exit 0
}

$entries = @($marker)
foreach ($tenant in $tenants) {
    $entries += "127.0.0.1 $tenant.local.azadexa"
}
$entries += "# End Azadexa local beta tenants"

Add-Content -Path $hostsFile -Value ("`r`n" + ($entries -join "`r`n")) -Encoding ASCII

# Flush DNS
ipconfig /flushdns | Out-Null

Write-Host "Done. Added these local domains:" -ForegroundColor Green
foreach ($tenant in $tenants) {
    Write-Host "  http://$tenant.local.azadexa:5000/"
}
Write-Host "`nRestart your browser if it still resolves to the old IP."
