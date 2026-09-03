$ErrorActionPreference='Stop'
$file = Join-Path $PSScriptRoot '..\data\submissions.json'
$outSql = Join-Path $PSScriptRoot '..\data\import_statements.sql'
if (-not (Test-Path $file)) {
  Write-Output "No submissions.json found at $file — nothing to import."
  exit 0
}
$json = Get-Content $file -Raw | ConvertFrom-Json
if ($json.Count -eq 0) {
  Write-Output "No entries in submissions.json"
  exit 0
}
@()
Remove-Item -Path $outSql -ErrorAction SilentlyContinue
foreach ($entry in $json) {
  $email = ($entry.email -replace "'","''")
  $phone = ($entry.phone -replace "'","''")
  $message = ($entry.message -replace "'","''")
  $contentObj = @{ email = $email; phone = $phone; message = $message }
  $content = ($contentObj | ConvertTo-Json -Compress) -replace "'","''"
  $stmt = "INSERT INTO inbox_entries (id, recipient_session_id, sender_id, sender_name, sender_type, interaction_id, sequence, summary, content, unread, sent_at) VALUES (lower(hex(randomblob(16))), 'local-session', 'web-form', 'Guest', 'user', lower(hex(randomblob(16))), 0, 'Contact form submission', '$content', 1, strftime('%s','now'));"
  Add-Content -Path $outSql -Value $stmt
}
Write-Output "Wrote import SQL to: $outSql"
Write-Output "To import, open the file and run its statements with the session SQL tool."