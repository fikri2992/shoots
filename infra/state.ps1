param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Region = "asia-southeast2",
    [string]$ServiceAccount = "",
    [string]$Bucket = "",
    [Parameter(Mandatory = $true)][string]$EnvFile
)

# gcloud writes successful long-running-operation progress to stderr on Windows.
# Inspect its process exit code instead of promoting that stream to a script failure.
$ErrorActionPreference = "Continue"
if (-not $ServiceAccount) { $ServiceAccount = "shoots-ingest@$Project.iam.gserviceaccount.com" }
if (-not $Bucket) { $Bucket = "$Project-shoots" }
$gcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
if (-not $gcloudCommand) { $gcloudCommand = Get-Command gcloud -ErrorAction Stop }
$script:GcloudExecutable = $gcloudCommand.Source

function Invoke-GcloudCli([string[]]$Arguments, [switch]$Quiet) {
    $output = & $script:GcloudExecutable @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) { throw "gcloud failed: $($Arguments[0..1] -join ' ')" }
    if (-not $Quiet) { return $output }
}

function Read-EnvValues([string]$Path) {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2].Trim().Trim('"')
        }
    }
    return $values
}

function Require-Value([hashtable]$Values, [string]$Key, [int]$Minimum) {
    $value = [string]$Values[$Key]
    if ([string]::IsNullOrWhiteSpace($value) -or $value.Length -lt $Minimum) {
        throw "$Key is absent or shorter than $Minimum characters"
    }
    if ($value.StartsWith("change-me") -or $value.Contains("example.com")) {
        throw "$Key still contains an example value"
    }
    return $value
}

function Add-SecretVersion([string]$Name, [string]$Value) {
    & $script:GcloudExecutable secrets describe $Name --project $Project 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Invoke-GcloudCli @(
            "secrets", "create", $Name, "--project", $Project,
            "--replication-policy", "automatic"
        ) -Quiet
    }

    $temporary = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllText($temporary, $Value, [Text.UTF8Encoding]::new($false))
        Invoke-GcloudCli @(
            "secrets", "versions", "add", $Name,
            "--project", $Project, "--data-file", $temporary
        ) -Quiet
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }

    Invoke-GcloudCli @(
        "secrets", "add-iam-policy-binding", $Name,
        "--project", $Project,
        "--member", "serviceAccount:$ServiceAccount",
        "--role", "roles/secretmanager.secretAccessor", "--quiet"
    ) -Quiet
    Write-Host "secret $Name ready"
}

$resolvedEnv = Resolve-Path -LiteralPath $EnvFile -ErrorAction Stop
$values = Read-EnvValues $resolvedEnv.Path
$secretValues = @{
    "shoots-google-client-secret" = Require-Value $values "GOOGLE_CLIENT_SECRET" 10
    "shoots-session-secret" = Require-Value $values "SESSION_SECRET" 32
    "shoots-tasks-token" = Require-Value $values "TASKS_TOKEN" 32
    "shoots-vapid-private-key" = Require-Value $values "VAPID_PRIVATE_KEY" 20
}

Invoke-GcloudCli @(
    "services", "enable",
    "fcm.googleapis.com", "gmail.googleapis.com", "cloudtrace.googleapis.com",
    "--project", $Project, "--quiet"
) -Quiet

& $script:GcloudExecutable storage buckets describe "gs://$Bucket" --project $Project 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Invoke-GcloudCli @(
        "storage", "buckets", "create", "gs://$Bucket",
        "--project", $Project, "--location", $Region,
        "--uniform-bucket-level-access", "--public-access-prevention"
    ) -Quiet
}

foreach ($role in @(
    "roles/datastore.user",
    "roles/secretmanager.admin",
    "roles/pubsub.publisher",
    "roles/aiplatform.user",
    "roles/firebasecloudmessaging.admin",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent"
)) {
    Invoke-GcloudCli @(
        "projects", "add-iam-policy-binding", $Project,
        "--member", "serviceAccount:$ServiceAccount",
        "--role", $role, "--condition=None", "--quiet"
    ) -Quiet
}

Invoke-GcloudCli @(
    "storage", "buckets", "add-iam-policy-binding", "gs://$Bucket",
    "--member", "serviceAccount:$ServiceAccount",
    "--role", "roles/storage.objectAdmin", "--quiet"
) -Quiet

$projectNumber = (Invoke-GcloudCli @(
    "projects", "describe", $Project, "--format=value(projectNumber)"
)) | Select-Object -First 1
Invoke-GcloudCli @(
    "projects", "add-iam-policy-binding", $Project,
    "--member", "serviceAccount:service-$projectNumber@gcp-sa-pubsub.iam.gserviceaccount.com",
    "--role", "roles/iam.serviceAccountTokenCreator", "--condition=None", "--quiet"
) -Quiet

foreach ($secret in $secretValues.GetEnumerator()) {
    Add-SecretVersion $secret.Key $secret.Value
}

Write-Host "state ready: Firestore (default), gs://$Bucket, $ServiceAccount"
