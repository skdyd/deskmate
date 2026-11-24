param([string]$Dir, [int]$Runs = 3)
$files = Get-ChildItem $Dir -Filter *.jpg | Sort-Object Name
$res = @()
for ($r = 1; $r -le $Runs; $r++) {
  foreach ($f in $files) {
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.FullName))
    $body = @{ model = 'qwen3-vl:4b-instruct'; stream = $false; keep_alive = '5m'
      options = @{ num_ctx = 8192; num_predict = 60; temperature = 0 }
      messages = @(@{ role = 'user'; content = 'Describe what is on this screen in one short sentence, naming any app or game you can read.'; images = @($b64) }) } | ConvertTo-Json -Depth 6
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $o = Invoke-RestMethod http://127.0.0.1:11434/api/chat -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 120
    $sw.Stop()
    $res += [pscustomobject]@{ run = $r; file = $f.BaseName; prompt_tokens = $o.prompt_eval_count
      prefill_ms = [int]($o.prompt_eval_duration / 1e6); gen_ms = [int]($o.eval_duration / 1e6); wall_ms = $sw.ElapsedMilliseconds
      answer = $o.message.content.Substring(0, [math]::Min(110, $o.message.content.Length)) }
  }
}
$res | Export-Csv -NoTypeInformation (Join-Path $Dir 'bench.csv')
$res | Group-Object file | % { [pscustomobject]@{ file = $_.Name; tokens = $_.Group[0].prompt_tokens
  prefill_ms_avg = [int](($_.Group | ? run -gt 1 | Measure prefill_ms -Average).Average); wall_ms_avg = [int](($_.Group | ? run -gt 1 | Measure wall_ms -Average).Average) } } | ft -AutoSize | Out-String
$res | ? run -eq $Runs | Select file, answer | ft -Wrap | Out-String -Width 200
