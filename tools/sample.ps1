param([int]$Seconds = 30, [string]$Label = 'x', [string]$Out)
# Per-second samples: total CPU, GPU 3D/compute, VRAM per process group, CPU%/RAM per process group.
$groups = @{ deskmate = '^Deskmate$'; ollama = '^(ollama|ollama app|llama-server|ollama_llama_server)$'; voice = '^python$' }
$ncpu = [Environment]::ProcessorCount
$prev = @{}; Get-Process | % { $prev[$_.Id] = $_.CPU }
$rows = @()
for ($t = 0; $t -lt $Seconds; $t++) {
  $c = Get-Counter '\Processor(_Total)\% Processor Time', '\GPU Engine(*)\Utilization Percentage', '\GPU Process Memory(*)\Dedicated Usage' -ErrorAction SilentlyContinue
  $s = $c.CounterSamples
  $cpuTot = ($s | ? Path -like '*processor(_total)*').CookedValue
  $eng = $s | ? Path -like '*gpu engine*'
  $g3d = ($eng | ? InstanceName -like '*engtype_3d' | Measure CookedValue -Sum).Sum
  $gcomp = ($eng | ? InstanceName -match 'engtype_compute' | Measure CookedValue -Sum).Sum
  $mem = $s | ? Path -like '*gpu process memory*'
  $procs = Get-Process
  $row = [ordered]@{ label = $Label; t = $t; cpu_total = [math]::Round($cpuTot, 1); gpu_3d = [math]::Round($g3d, 1); gpu_compute = [math]::Round($gcomp, 1)
    vram_total_gb = [math]::Round((($mem | Measure CookedValue -Sum).Sum) / 1GB, 2) }
  foreach ($g in $groups.Keys) {
    $ps = $procs | ? ProcessName -match $groups[$g]
    $ids = $ps.Id
    $cpuDelta = 0; foreach ($p in $ps) { if ($prev.ContainsKey($p.Id)) { $cpuDelta += ($p.CPU - $prev[$p.Id]) } }
    $row["${g}_cpu"] = [math]::Round($cpuDelta * 100 / $ncpu, 1)
    $row["${g}_ram_mb"] = [math]::Round((($ps | Measure WorkingSet64 -Sum).Sum) / 1MB)
    $vr = ($mem | ? { $id = [int](($_.InstanceName -split '_')[1]); $ids -contains $id } | Measure CookedValue -Sum).Sum
    $row["${g}_vram_mb"] = [math]::Round($vr / 1MB)
  }
  $prev = @{}; $procs | % { $prev[$_.Id] = $_.CPU }
  $rows += [pscustomobject]$row
  Start-Sleep -Milliseconds 700
}
$rows | Export-Csv -Append -NoTypeInformation -Path $Out
$rows | Measure-Object -Property ($rows[0].psobject.Properties.Name | ? { $_ -notin 'label','t' }) -Average -Maximum |
  Select Property, @{n='avg';e={[math]::Round($_.Average,1)}}, @{n='max';e={[math]::Round($_.Maximum,1)}} | ft -AutoSize | Out-String
