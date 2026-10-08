[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Prompt,
    [string[]]$ImagePath,
    [switch]$Json,
    [string]$Model = $(if ($env:QWEN38_MODEL) { $env:QWEN38_MODEL } else { 'qwen3.8-35b-a3b-q6' }),
    [string]$BaseUrl = $(if ($env:QWEN38_BASE_URL) { $env:QWEN38_BASE_URL } else { 'http://192.168.3.188:8080/v1' }),
    [string]$ApiKey,
    [int]$MaxOutputTokens = 2048,
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = [Environment]::GetEnvironmentVariable('QWEN38_API_KEY', 'User')
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) { $ApiKey = $env:QWEN38_API_KEY }
if ([string]::IsNullOrWhiteSpace($ApiKey)) { $ApiKey = 'sk-local' }

$content = [System.Collections.Generic.List[object]]::new()
$content.Add(@{ type = 'input_text'; text = $Prompt })
foreach ($path in @($ImagePath)) {
    if ([string]::IsNullOrWhiteSpace($path)) { continue }
    $resolved = (Resolve-Path -LiteralPath $path).Path
    $extension = [IO.Path]::GetExtension($resolved).ToLowerInvariant()
    $mime = switch ($extension) {
        '.png'  { 'image/png' }
        '.webp' { 'image/webp' }
        '.gif'  { 'image/gif' }
        default { 'image/jpeg' }
    }
    $base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($resolved))
    $content.Add(@{ type = 'input_image'; image_url = "data:$mime;base64,$base64" })
}

$body = @{
    model = $Model
    input = @(@{ role = 'user'; content = @($content) })
    max_output_tokens = $MaxOutputTokens
}
if ($Json) { $body.text = @{ format = @{ type = 'json_object' } } }

$headers = @{ Authorization = "Bearer $ApiKey"; 'Content-Type' = 'application/json' }
$uri = $BaseUrl.TrimEnd('/') + '/responses'
$response = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
    -Body ($body | ConvertTo-Json -Depth 20 -Compress) -TimeoutSec 600

$texts = @()
if ($response.output_text) { $texts += [string]$response.output_text }
foreach ($item in @($response.output)) {
    foreach ($part in @($item.content)) {
        if ($part.text) { $texts += [string]$part.text }
    }
}
$result = ($texts -join "`n").Trim()
if ([string]::IsNullOrWhiteSpace($result)) { $result = $response | ConvertTo-Json -Depth 20 }

if ($OutputPath) {
    $parent = Split-Path -Parent $OutputPath
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [IO.File]::WriteAllText($OutputPath, $result, [Text.UTF8Encoding]::new($false))
}
$result
