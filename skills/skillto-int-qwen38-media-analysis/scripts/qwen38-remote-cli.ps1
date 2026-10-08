[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory)][ValidateSet('status','chat','json-chat','vision','ocr','native')]
    [string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = 'Stop'
$invokeScript = Join-Path $PSScriptRoot 'invoke-qwen38.ps1'
$baseUrl = 'http://192.168.3.188:8080/v1'
$model = 'qwen3.8-35b-a3b-q6'

switch ($Command) {
    'status' {
        $healthUrl = ([Uri]$baseUrl).GetLeftPart([System.UriPartial]::Authority) + '/'
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 10
        [pscustomobject]@{ status = $response.StatusCode; api = $baseUrl; model = $model } |
            ConvertTo-Json -Compress
    }
    'chat' {
        if (-not $Arguments) { throw 'usage: qwen38-remote-cli.ps1 chat <prompt>' }
        & $invokeScript -Prompt ($Arguments -join ' ')
    }
    'json-chat' {
        if (-not $Arguments) { throw 'usage: qwen38-remote-cli.ps1 json-chat <prompt>' }
        & $invokeScript -Prompt ($Arguments -join ' ') -Json
    }
    'vision' {
        if ($Arguments.Count -lt 2) { throw 'usage: qwen38-remote-cli.ps1 vision <local-image> <prompt>' }
        & $invokeScript -ImagePath $Arguments[0] -Prompt ($Arguments[1..($Arguments.Count - 1)] -join ' ')
    }
    'ocr' {
        if ($Arguments.Count -ne 1) { throw 'usage: qwen38-remote-cli.ps1 ocr <local-image>' }
        & $invokeScript -ImagePath $Arguments[0] -Prompt 'Extract all visible text. Preserve reading order and line breaks. Mark uncertain characters.'
    }
    'native' {
        $legacyWrapper = $env:QWEN38_NATIVE_WRAPPER
        if ([string]::IsNullOrWhiteSpace($legacyWrapper) -or -not (Test-Path -LiteralPath $legacyWrapper)) {
            throw 'Native SSH mode requires QWEN38_NATIVE_WRAPPER to reference an authorized local wrapper script.'
        }
        if (-not (Get-Command sshpass -ErrorAction SilentlyContinue)) {
            throw 'Native SSH mode requires sshpass in PATH. Use status/chat/json-chat/vision/ocr for the HTTP CLI.'
        }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $legacyWrapper @Arguments
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
