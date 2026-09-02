param(
  [string]$BaseUrl = "http://localhost:8791",
  [string]$Output = "trueforge-local-export.json"
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd('/')

function Get-Tf($Path) {
  Invoke-RestMethod -Uri "$BaseUrl$Path" -Method GET -TimeoutSec 30
}

$export = [ordered]@{
  exported_at = (Get-Date).ToString("o")
  source = $BaseUrl
  agents = $null
  model_providers = $null
  mcp_servers = $null
  skills = $null
  sandbox_providers = $null
  sessions = $null
}

$export.agents = Get-Tf "/api/v1/agents"
$export.model_providers = Get-Tf "/api/v1/settings/model-providers"
$export.mcp_servers = Get-Tf "/api/v1/settings/mcp-servers"
$export.skills = Get-Tf "/api/v1/settings/skills"
$export.sandbox_providers = Get-Tf "/api/v1/settings/sandbox-providers"
$export.sessions = Get-Tf "/api/v1/sessions"

# TrueForge redacts stored provider secrets in GET responses. Keep the export that way.
$export | ConvertTo-Json -Depth 100 | Set-Content -Encoding UTF8 $Output
Write-Host "Saved non-secret TrueForge snapshot to $Output"
Write-Host "This captures reusable configuration plus session metadata. It does not expose model API keys or OAuth/PAT secrets."
