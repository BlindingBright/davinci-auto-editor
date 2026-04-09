$ErrorActionPreference = 'Stop'
Write-Host '--- DaVinci Auto-Editor Release Builder ---'
Write-Host '[i] Checking Node.js version...'
$nodeVer = node -v
Write-Host "Node.js version: $nodeVer"
Write-Host '[i] Installing dependencies...'
& npm.cmd install
Write-Host '[!] BUILDING PRODUCTION MSI... (2-5 minutes)'
& npm.cmd run tauri build
Write-Host '--- ALL DONE! Check the src-tauri/target/release/bundle/msi folder. ---'
