# Daruma site pre-publish checker
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Errors = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

function Add-Error($Message) { $Errors.Add($Message) | Out-Null }
function Add-Warning($Message) { $Warnings.Add($Message) | Out-Null }

$RequiredFiles = @(
  "index.html",
  "robots.txt",
  "sitemap.xml",
  "ja\index.html",
  "ja\purchase\index.html",
  "en\index.html",
  "en\access\index.html",
  "assets\css\style.css",
  "assets\js\lang.js",
  "assets\js\opening-status.js",
  "assets\js\analytics-events.js",
  "assets\js\homage-motion.js",
  "assets\data\site-data.json",
  "assets\img\daruma-logo.jpg",
  "assets\img\access-map.jpg",
  "assets\img\access-map-en.png",
  "assets\img\access-map-en.png",
  "assets\img\shop-banner.png",
  "assets\img\card-yugioh.png",
  "assets\img\card-onepiece.png",
  "assets\img\card-pokemon.png"
)

foreach ($File in $RequiredFiles) {
  if (!(Test-Path (Join-Path $Root $File))) { Add-Error "必須ファイルがありません: $File" }
}

$HtmlFiles = Get-ChildItem -Path $Root -Filter "*.html" -Recurse
foreach ($File in $HtmlFiles) {
  $Rel = $File.FullName.Replace($Root + "\", "")
  $Text = Get-Content $File.FullName -Raw -Encoding UTF8

  if ($Text -notmatch "<title>.+?</title>") { Add-Error "$Rel : title がありません" }
  if ($Text -notmatch '<meta name="description" content="[^"]+') { Add-Error "$Rel : meta description がありません" }
  if ($Text -notmatch 'rel="canonical"') { Add-Warning "$Rel : canonical がありません" }
  if ($Text -notmatch 'hreflang=') { Add-Warning "$Rel : hreflang がありません" }

  $Imgs = [regex]::Matches($Text, '<img\b[^>]*>')
  foreach ($Img in $Imgs) {
    $Tag = $Img.Value
    if ($Tag -notmatch 'alt="[^"]*"') { Add-Error "$Rel : alt属性がない画像があります: $Tag" }
  }

  foreach ($Word in @("未設定", "正確な住所を入力", "TODO", "後で差し替え")) {
    if ($Text.Contains($Word)) { Add-Warning "$Rel : 仮置き文言の可能性があります: $Word" }
  }
}

$SitemapPath = Join-Path $Root "sitemap.xml"
if (Test-Path $SitemapPath) {
  $Sitemap = Get-Content $SitemapPath -Raw -Encoding UTF8
  @("/ja/", "/ja/purchase/", "/en/", "/en/access/") | ForEach-Object {
    if ($Sitemap -notmatch [regex]::Escape($_)) { Add-Error "sitemap.xml に $_ がありません" }
  }
}

Write-Host ""
Write-Host "=== Daruma site check result ===" -ForegroundColor Cyan

if ($Errors.Count -eq 0 -and $Warnings.Count -eq 0) {
  Write-Host "OK: エラー・警告はありません。" -ForegroundColor Green
  exit 0
}

if ($Errors.Count -gt 0) {
  Write-Host ""
  Write-Host "Errors:" -ForegroundColor Red
  $Errors | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
}

if ($Warnings.Count -gt 0) {
  Write-Host ""
  Write-Host "Warnings:" -ForegroundColor Yellow
  $Warnings | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
}

if ($Errors.Count -gt 0) { exit 1 } else { exit 0 }
