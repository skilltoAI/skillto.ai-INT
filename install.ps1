param(
  [string]$Destination = $(if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $HOME '.codex\skills' }),
  [ValidateSet('all', 'douyin-xhs-crawler', 'skillto-table')][string]$Skill = 'all'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$names = if ($Skill -eq 'all') { @('douyin-xhs-crawler', 'skillto-table') } else { @($Skill) }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
foreach ($name in $names) {
  $source = Join-Path $repoRoot "skills\$name"
  $target = Join-Path $Destination $name
  if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) { throw "Invalid skill source: $source" }
  if (Test-Path -LiteralPath $target) { throw "Destination already exists: $target" }
  Copy-Item -LiteralPath $source -Destination $target -Recurse
  Write-Host "Installed $name -> $target"
}
