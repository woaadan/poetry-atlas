# 詩海圖譜 · 一键发布到 GitHub Pages
# 用法：在 poetry_atlas 目录下运行
#   .\deploy_github.ps1 -Repo poetry-atlas
# 需要：已安装 git，并已在 GitHub 建好同名空仓库，且已配置好凭据（PAT 或 SSH）。
param(
  [string]$Repo = "poetry-atlas",
  [string]$User = "",
  [string]$Message = "poetry atlas: 历代诗人诗作文本挖掘可视化"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "docs\index.html")) {
  throw "请在 poetry_atlas 目录下运行本脚本（找不到 docs\index.html）。"
}
if (-not $User) {
  $User = Read-Host "请输入你的 GitHub 用户名"
}

if (-not (Test-Path ".git")) {
  git init | Out-Null
  git branch -M main
}
git add -A
git commit -m $Message 2>$null
if (git remote 2>$null | Select-String -Quiet "origin") {
  git remote set-url origin "https://github.com/$User/$Repo.git"
} else {
  git remote add origin "https://github.com/$User/$Repo.git"
}
git branch -M main
git push -u origin main

Write-Host ""
Write-Host "推送完成。" -ForegroundColor Green
Write-Host "接下来在仓库 Settings → Pages 中选择：Source = Deploy from a branch，Branch = main，Folder = / (root)。"
Write-Host "几分钟后访问： https://$User.github.io/$Repo/" -ForegroundColor Cyan
