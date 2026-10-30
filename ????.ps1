# 本地预览：启动一个静态服务器并打开页面
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8811

Write-Host "詩海圖譜 · 本地预览" -ForegroundColor DarkRed
Write-Host "服务目录：$root\docs"
Write-Host "地址：    http://127.0.0.1:$port/"
Write-Host "按 Ctrl+C 结束。`n"

Start-Process "http://127.0.0.1:$port/"
python -m http.server $port --directory (Join-Path $root "docs")
