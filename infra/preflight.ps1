param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Region = "asia-southeast2",
    [string]$Service = "shoots",
    [string]$ServiceAccount = "",
    [string]$Bucket = "",
    [string]$EnvFile = "backend/.env",
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$script:Failures = 0

function Fail([string]$Message) {
    Write-Host "FAIL: $Message" -ForegroundColor Red
    $script:Failures += 1
}

function Pass([string]$Message) {
    Write-Host "pass: $Message" -ForegroundColor Green
}

function Invoke-GcloudCli([string[]]$Arguments) {
    $output = & $script:GcloudExecutable @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) { throw "gcloud failed: $($Arguments[0..1] -join ' ')" }
    return $output
}

function EnvValues([string]$Path) {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2].Trim().Trim('"')
        }
    }
    return $values
}

$gitCommand = Get-Command git -ErrorAction SilentlyContinue
$gcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
if (-not $gcloudCommand) { $gcloudCommand = Get-Command gcloud -ErrorAction SilentlyContinue }
if (-not $gitCommand) { Fail "git is unavailable" }
if (-not $gcloudCommand) { Fail "gcloud is unavailable" }
if ($script:Failures) { exit 1 }
$script:GcloudExecutable = $gcloudCommand.Source

$head = (& git rev-parse --short HEAD 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $head) {
    Fail "current directory is not a readable git checkout"
} else {
    $status = (& git status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0) {
        Fail "git status could not read the checkout"
    } elseif ($status -and -not $AllowDirty) {
        Fail "git checkout is dirty"
    } elseif ($status) {
        Pass "git checkout at $head; dirty state explicitly allowed for read-only audit"
    } else {
        Pass "clean git checkout at $head"
    }
}

$resolvedEnv = Resolve-Path -LiteralPath $EnvFile -ErrorAction SilentlyContinue
if (-not $resolvedEnv) {
    Fail "$EnvFile does not exist"
    $envValues = @{}
} else {
    Pass "$EnvFile exists"
    $envValues = EnvValues $resolvedEnv.Path
}

$requiredPublic = @(
    "GOOGLE_CLIENT_ID",
    "VAPID_PUBLIC_KEY",
    "VAPID_SUBJECT",
    "ANDROID_APP_LINK_SHA256"
)
foreach ($key in $requiredPublic) {
    if (-not $envValues[$key]) { Fail "$key is empty in $EnvFile" }
}
if ($envValues["GOOGLE_CLIENT_ID"] -and
    -not $envValues["GOOGLE_CLIENT_ID"].EndsWith(".apps.googleusercontent.com")) {
    Fail "GOOGLE_CLIENT_ID is not a Google web client id"
}
if ($envValues["VAPID_SUBJECT"] -and
    $envValues["VAPID_SUBJECT"] -notmatch '^(mailto:|https://)') {
    Fail "VAPID_SUBJECT must start with mailto: or https://"
}
if ($envValues["VAPID_SUBJECT"] -like '*your-contact@example.com*') {
    Fail "VAPID_SUBJECT still contains the example contact"
}
$fingerprintPattern = '^([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}(,([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2})*$'
if ($envValues["ANDROID_APP_LINK_SHA256"] -and
    $envValues["ANDROID_APP_LINK_SHA256"] -notmatch $fingerprintPattern) {
    Fail "ANDROID_APP_LINK_SHA256 is not a comma-separated SHA-256 fingerprint list"
}

try {
    $activeAccount = (Invoke-GcloudCli @(
        "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"
    )) | Select-Object -First 1
} catch {
    $activeAccount = ""
}
if (-not $activeAccount) {
    Fail "gcloud has no active account"
} else {
    Pass "gcloud has an active account"
}

try {
    $projectNumber = (Invoke-GcloudCli @("projects", "describe", $Project, "--format=value(projectNumber)")) | Select-Object -First 1
    Pass "project $Project is readable"
    Write-Host "candidate service URL: https://$Service-$projectNumber.$Region.run.app"
} catch {
    Fail "project $Project is not readable"
    $projectNumber = ""
}

$requiredApis = @(
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "fcm.googleapis.com",
    "drive.googleapis.com"
)
$enabledApis = @()
try {
    $enabledApis = @(Invoke-GcloudCli @("services", "list", "--enabled", "--project", $Project, "--format=value(config.name)"))
} catch {
    Fail "enabled API list is unreadable"
}
foreach ($api in $requiredApis) {
    if ($enabledApis -contains $api) { Pass "API $api" } else { Fail "API $api is not enabled" }
}

if (-not $ServiceAccount) { $ServiceAccount = "shoots-ingest@$Project.iam.gserviceaccount.com" }
if (-not $Bucket) { $Bucket = "$Project-shoots" }

try {
    Invoke-GcloudCli @("iam", "service-accounts", "describe", $ServiceAccount, "--project", $Project) | Out-Null
    Pass "service account $ServiceAccount"
} catch { Fail "service account $ServiceAccount is missing" }

try {
    Invoke-GcloudCli @("firestore", "databases", "describe", "--database=(default)", "--project", $Project) | Out-Null
    Pass "Firestore default database"
} catch { Fail "Firestore default database is missing" }

try {
    Invoke-GcloudCli @("storage", "buckets", "describe", "gs://$Bucket") | Out-Null
    Pass "bucket gs://$Bucket"
} catch { Fail "bucket gs://$Bucket is missing" }

foreach ($secret in @(
    "shoots-google-client-secret",
    "shoots-session-secret",
    "shoots-tasks-token",
    "shoots-vapid-private-key"
)) {
    try {
        $version = (Invoke-GcloudCli @(
            "secrets", "versions", "list", $secret,
            "--project", $Project,
            "--filter=state:ENABLED", "--limit=1", "--format=value(name)"
        )) | Select-Object -First 1
        if ($version) { Pass "secret $secret has an enabled version" } else { Fail "secret $secret has no enabled version" }
    } catch { Fail "secret $secret has no enabled version" }
}

if ($script:Failures) {
    Write-Host "$script:Failures deployment preflight failure(s)" -ForegroundColor Red
    exit 1
}

Write-Host "deployment preflight passed" -ForegroundColor Green
