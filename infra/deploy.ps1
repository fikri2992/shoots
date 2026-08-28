param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Region = "asia-southeast2",
    [string]$Service = "shoots",
    [string]$ServiceAccount = "",
    [string]$Bucket = "",
    [string]$EnvFile = "backend/.env",
    [string]$ServiceUrl = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Read-EnvValues([string]$Path) {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2].Trim().Trim('"')
        }
    }
    return $values
}

function Invoke-Gcloud([string[]]$Arguments, [switch]$Capture) {
    if ($Capture) {
        $output = & $script:Gcloud @Arguments 2>$null
        if ($LASTEXITCODE -ne 0) { throw "gcloud failed: $($Arguments[0..1] -join ' ')" }
        return $output
    }
    & $script:Gcloud @Arguments
    if ($LASTEXITCODE -ne 0) { throw "gcloud failed: $($Arguments[0..1] -join ' ')" }
}

$gcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
if (-not $gcloudCommand) { $gcloudCommand = Get-Command gcloud -ErrorAction Stop }
$script:Gcloud = $gcloudCommand.Source

$resolvedEnv = Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop
$values = Read-EnvValues $resolvedEnv.Path
$sourceSha = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $sourceSha) { throw "git commit is unavailable" }
if (& git status --porcelain) { throw "deploy from a clean checkout" }

if (-not $ServiceAccount) { $ServiceAccount = "shoots-ingest@$Project.iam.gserviceaccount.com" }
if (-not $Bucket) { $Bucket = "$Project-shoots" }

& "$PSScriptRoot/preflight.ps1" `
    -Project $Project `
    -Region $Region `
    -Service $Service `
    -ServiceAccount $ServiceAccount `
    -Bucket $Bucket `
    -EnvFile $resolvedEnv.Path
if ($LASTEXITCODE -ne 0) { throw "deployment preflight failed" }

$repository = "shoots"
$image = "$Region-docker.pkg.dev/$Project/$repository/app:$($sourceSha.Substring(0, 7))"
try {
    Invoke-Gcloud @(
        "artifacts", "repositories", "describe", $repository,
        "--location", $Region,
        "--project", $Project
    ) -Capture | Out-Null
} catch {
    Invoke-Gcloud @(
        "artifacts", "repositories", "create", $repository,
        "--repository-format", "docker",
        "--location", $Region,
        "--project", $Project,
        "--description", "Shoots images"
    )
}

if (-not $SkipBuild) {
    Invoke-Gcloud @(
        "builds", "submit", ".",
        "--tag", $image,
        "--project", $Project,
        "--region", $Region
    )
}

if (-not $ServiceUrl) {
    $projectNumber = (Invoke-Gcloud @(
        "projects", "describe", $Project, "--format=value(projectNumber)"
    ) -Capture | Select-Object -First 1).Trim()
    $ServiceUrl = "https://$Service-$projectNumber.$Region.run.app"
}

$publicEnvironment = @(
    "USE_VERTEX_AI=true",
    "GCP_PROJECT=$Project",
    "GCP_LOCATION=$Region",
    "CLOUD_STATE=true",
    "GCS_BUCKET=$Bucket",
    "PUBSUB_PUSH_BASE_URL=$ServiceUrl",
    "PUBSUB_PUSH_AUDIENCE=$ServiceUrl",
    "DRIVE_WEBHOOK_URL=$ServiceUrl/drive/notify",
    "OAUTH_REDIRECT_URI=$ServiceUrl/auth/callback",
    "FRONTEND_ORIGIN=$ServiceUrl",
    "GOOGLE_CLIENT_ID=$($values['GOOGLE_CLIENT_ID'])",
    "VAPID_PUBLIC_KEY=$($values['VAPID_PUBLIC_KEY'])",
    "VAPID_SUBJECT=$($values['VAPID_SUBJECT'])",
    "ANDROID_APP_LINK_SHA256=$($values['ANDROID_APP_LINK_SHA256'])",
    "DRIVE_PICKER_API_KEY=$($values['DRIVE_PICKER_API_KEY'])",
    "DRIVE_PICKER_APP_ID=$($values['DRIVE_PICKER_APP_ID'])",
    "DRIVE_SERVICE_ACCOUNT=$ServiceAccount",
    "SOURCE_SHA=$sourceSha"
) -join "|"

Invoke-Gcloud @(
    "run", "deploy", $Service,
    "--project", $Project,
    "--region", $Region,
    "--image", $image,
    "--service-account", $ServiceAccount,
    "--allow-unauthenticated",
    "--min-instances", "0",
    "--max-instances", "3",
    "--concurrency", "40",
    "--cpu", "2",
    "--memory", "2Gi",
    "--timeout", "600",
    "--set-env-vars", "^|^$publicEnvironment",
    "--set-secrets",
    "GOOGLE_CLIENT_SECRET=shoots-google-client-secret:latest,SESSION_SECRET=shoots-session-secret:latest,TASKS_TOKEN=shoots-tasks-token:latest,VAPID_PRIVATE_KEY=shoots-vapid-private-key:latest"
)

Invoke-Gcloud @(
    "run", "services", "add-iam-policy-binding", $Service,
    "--project", $Project,
    "--region", $Region,
    "--member", "serviceAccount:$ServiceAccount",
    "--role", "roles/run.invoker",
    "--quiet"
)

$actualUrl = (Invoke-Gcloud @(
    "run", "services", "describe", $Service,
    "--project", $Project,
    "--region", $Region,
    "--format=value(status.url)"
) -Capture | Select-Object -First 1).Trim()
for ($attempt = 1; $attempt -le 12; $attempt += 1) {
    try {
        $health = Invoke-RestMethod -Uri "$ServiceUrl/api/health" -TimeoutSec 15
        if ($health.status -eq "ok") { break }
    } catch {
        if ($attempt -eq 12) { throw "canonical URL did not reach the deployment" }
        Start-Sleep -Seconds 5
    }
}

Write-Host "deployed SHA: $sourceSha"
Write-Host "Cloud Run service URL: $actualUrl"
Write-Host "Configured canonical URL: $ServiceUrl"
