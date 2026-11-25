# Copies every character's model\exp folder from Claude's virtualized AppData to the real %APPDATA%\deskmate (run via copy_exp.lnk)
$src = Join-Path $env:LOCALAPPDATA 'Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\deskmate\character'
$dst = Join-Path $env:APPDATA 'deskmate\character'
$log = 'C:\Users\jywhy\Desktop\deskmate AI\logs\copy_exp.log'
"$(Get-Date) start" | Out-File $log -Encoding utf8
Get-ChildItem $src -Directory | % { $e = Join-Path $_.FullName 'model\exp'; if (Test-Path $e) { robocopy $e (Join-Path $dst "$($_.Name)\model\exp") *.json /NJH /NJS /NP | Out-File $log -Append -Encoding utf8 } }
"done" | Out-File $log -Append -Encoding utf8
