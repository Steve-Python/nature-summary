[CmdletBinding()]
param(
  [ValidateSet("prompt", "minimal", "full", "none")]
  [string]$DependencyMode = "prompt",

  [string]$SkillRoot = $(if ($env:CODEX_SKILLS_DIR) { $env:CODEX_SKILLS_DIR } else { Join-Path $HOME ".codex\skills" }),

  [string]$NatureSkillsRepo = "Yuan1z0825/nature-skills",

  [string]$NatureSkillsRef = "main",

  [switch]$Check,

  [switch]$KeepTemp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RequiredNatureSkills = @(
  "nature-academic-search",
  "nature-downloader",
  "nature-reader",
  "nature-writing"
)

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message"
}

function Get-FullPath {
  param([string]$Path)
  return [System.IO.Path]::GetFullPath($Path)
}

function Assert-ChildPath {
  param(
    [string]$Parent,
    [string]$Child
  )
  $parentFull = (Get-FullPath $Parent).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
  $childFull = Get-FullPath $Child
  $prefix = $parentFull + [System.IO.Path]::DirectorySeparatorChar
  if (-not $childFull.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to write outside skill root: $childFull"
  }
}

function Copy-DirectoryFresh {
  param(
    [string]$Source,
    [string]$Destination,
    [string]$Root
  )
  if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Source directory not found: $Source"
  }
  Assert-ChildPath -Parent $Root -Child $Destination
  if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Copy-SkillSelf {
  param(
    [string]$RepoRoot,
    [string]$DestinationRoot
  )
  $destination = Join-Path $DestinationRoot "nature-summary"
  Assert-ChildPath -Parent $DestinationRoot -Child $destination
  if (Test-Path -LiteralPath $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $destination | Out-Null
  Get-ChildItem -LiteralPath $RepoRoot -Force |
    Where-Object { $_.Name -notin @(".git", ".github") } |
    ForEach-Object {
      Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $destination $_.Name) -Recurse -Force
    }
}

function New-InstallTempDir {
  $base = Join-Path ([System.IO.Path]::GetTempPath()) ("nature-summary-install-" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $base | Out-Null
  return $base
}

function Download-GitHubRepoZip {
  param(
    [string]$Repo,
    [string]$Ref,
    [string]$TempDir
  )
  $zip = Join-Path $TempDir "repo.zip"
  $extract = Join-Path $TempDir "repo"
  $url = "https://codeload.github.com/$Repo/zip/$Ref"
  Write-Step "Downloading $Repo@$Ref"
  Invoke-WebRequest -Uri $url -OutFile $zip
  Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
  $root = Get-ChildItem -LiteralPath $extract -Directory | Select-Object -First 1
  if (-not $root) {
    throw "Downloaded archive was empty: $Repo@$Ref"
  }
  return $root.FullName
}

function Resolve-DependencyMode {
  param([string]$Mode)
  if ($Mode -ne "prompt") {
    return $Mode
  }

  Write-Host ""
  Write-Host "Choose nature-skills dependency install mode:"
  Write-Host "  1. minimal - install _shared plus four required companion skills"
  Write-Host "  2. full    - install the complete Yuan1z0825/nature-skills skills/ directory"
  Write-Host "  3. none    - skip dependency installation"
  $choice = Read-Host "Select 1, 2, or 3 [1]"
  switch ($choice.Trim()) {
    "" { return "minimal" }
    "1" { return "minimal" }
    "minimal" { return "minimal" }
    "2" { return "full" }
    "full" { return "full" }
    "3" { return "none" }
    "none" { return "none" }
    default { throw "Unknown dependency mode selection: $choice" }
  }
}

function Install-NatureSkills {
  param(
    [string]$Mode,
    [string]$DestinationRoot,
    [string]$TempDir
  )
  if ($Mode -eq "none") {
    Write-Step "Skipping nature-skills dependency installation"
    return
  }

  $repoRoot = Download-GitHubRepoZip -Repo $NatureSkillsRepo -Ref $NatureSkillsRef -TempDir $TempDir
  $src = Join-Path $repoRoot "skills"
  if (-not (Test-Path -LiteralPath $src -PathType Container)) {
    throw "skills directory not found in downloaded nature-skills repo: $src"
  }

  if ($Mode -eq "minimal") {
    $names = @("_shared") + $RequiredNatureSkills
  } elseif ($Mode -eq "full") {
    $names = Get-ChildItem -LiteralPath $src -Directory | Sort-Object Name | ForEach-Object { $_.Name }
  } else {
    throw "Unsupported dependency mode: $Mode"
  }

  foreach ($name in $names) {
    $source = Join-Path $src $name
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
      throw "Expected dependency directory not found: $source"
    }
    if ($name -ne "_shared" -and -not (Test-Path -LiteralPath (Join-Path $source "SKILL.md"))) {
      throw "Dependency directory is missing SKILL.md: $source"
    }
    Copy-DirectoryFresh -Source $source -Destination (Join-Path $DestinationRoot $name) -Root $DestinationRoot
    Write-Host "    installed $name"
  }
}

function Test-InstalledSkill {
  param(
    [string]$DestinationRoot,
    [string]$Name
  )
  $path = Join-Path $DestinationRoot $Name
  $skillFile = Join-Path $path "SKILL.md"
  if (Test-Path -LiteralPath $skillFile) {
    Write-Host "MATCH    $Name"
    return $true
  }
  Write-Host "MISSING  $Name"
  return $false
}

function Invoke-InstallCheck {
  param([string]$DestinationRoot)
  $ok = $true
  foreach ($name in @("nature-summary") + $RequiredNatureSkills) {
    if (-not (Test-InstalledSkill -DestinationRoot $DestinationRoot -Name $name)) {
      $ok = $false
    }
  }
  $shared = Join-Path $DestinationRoot "_shared"
  if (Test-Path -LiteralPath $shared -PathType Container) {
    Write-Host "MATCH    _shared"
  } else {
    Write-Host "MISSING  _shared"
    $ok = $false
  }
  $reader = Join-Path $DestinationRoot "nature-summary\scripts\build_reader.py"
  if (Test-Path -LiteralPath $reader) {
    Write-Host "MATCH    nature-summary/scripts/build_reader.py"
  } else {
    Write-Host "MISSING  nature-summary/scripts/build_reader.py"
    $ok = $false
  }
  if (-not $ok) {
    throw "Install check failed"
  }
}

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
$skillRootFull = Get-FullPath $SkillRoot
New-Item -ItemType Directory -Force -Path $skillRootFull | Out-Null

if ($Check) {
  Write-Step "Checking Codex skills in $skillRootFull"
  Invoke-InstallCheck -DestinationRoot $skillRootFull
  exit 0
}

$tempDir = New-InstallTempDir
try {
  $mode = Resolve-DependencyMode -Mode $DependencyMode
  Install-NatureSkills -Mode $mode -DestinationRoot $skillRootFull -TempDir $tempDir

  Write-Step "Installing nature-summary from $repoRoot"
  Copy-SkillSelf -RepoRoot $repoRoot -DestinationRoot $skillRootFull
  Write-Host "    installed nature-summary"

  Write-Step "Verifying install"
  Invoke-InstallCheck -DestinationRoot $skillRootFull

  Write-Step "Done. Restart Codex to pick up new or updated skills."
} finally {
  if (-not $KeepTemp -and (Test-Path -LiteralPath $tempDir)) {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
  }
}
