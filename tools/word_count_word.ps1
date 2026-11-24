# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), tools/word_count_word.ps1 (itself adapted from hssling/india-tb-acf-campaign and hssling/india-state-tb-score); modified: Primary Care Diabetes sections (Introduction, Methods, Results, Discussion as level-2 headings, with level-3 subsection headings inside them) and the structured abstract
# Count the abstract and the main text of the manuscript in Microsoft Word.
# Usage: powershell -NoProfile -File word_count_word.ps1 <docx> <out.json>
# Opens its own Word instance (read-only, hidden) and quits only that instance.
# Abstract: the paragraphs between the "Abstract" heading and the Keywords line (Keywords excluded;
# the run-in labels Aims, Methods, Results and Conclusions included).
# IJTLD (manuscript/v2): the Introduction has no heading; the abstract ends, and the Introduction
# begins, at the first paragraph after the Abstract heading that starts a new page.
# DMSCRR (manuscript/v3): also 'Subjects, Materials and Methods'; table_cells (the words in the tables),
# table_text (the Table Title and Table Note paragraphs) and legends (the paragraphs under 'Figure legends').
# Main text: the text under the level-2 headings Introduction, Methods, Results and Discussion,
# headings excluded; level-3 subsection headings stay inside the section and are counted only in
# main_with_headings. It ends at any other level-2 heading (Acknowledgements). Tables are excluded.
param([string]$Docx, [string]$Out)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $d = $word.Documents.Open($Docx, $false, $true)
  $state = ""; $abs = 0; $main = 0; $heads = 0; $sec = [ordered]@{}; $cur = ""; $ttext = 0; $legends = 0
  foreach ($p in $d.Paragraphs) {
    $t = $p.Range.Text.Trim()
    if ($p.Range.Information(12)) { continue }          # inside a table
    $n = $p.Range.ComputeStatistics(0)
    $lvl = $p.OutlineLevel
    if ($lvl -lt 10) {
      if ($lvl -le 2) {
        if ($t -eq "Abstract") { $state = "abs" }
        elseif ($t -match '^(Introduction|Methods|Subjects, Materials and Methods|Results|Discussion)$') { $state = "main"; $cur = $Matches[1]; $sec[$cur] = 0 }
        elseif ($t -eq "Figure legends") { $state = "legends" }
        else { $state = "" }
      } elseif ($state -eq "main") { $heads += $n }
      continue
    }
    if ($t -like "Keywords:*") { $state = ""; continue }
    $style = $p.Style.NameLocal
    if ($style -eq "Table Title" -or $style -eq "Table Note") { $ttext += $n; continue }
    if ($state -eq "legends") { $legends += $n; continue }
    if ($state -eq "abs" -and $p.Format.PageBreakBefore) { $state = "main"; $cur = "Introduction"; $sec[$cur] = 0 }
    if ($state -eq "abs") { $abs += $n }
    if ($state -eq "main") { $main += $n; $sec[$cur] += $n }
  }
  $cells = 0
  foreach ($tb in $d.Tables) { $cells += $tb.Range.ComputeStatistics(0) }
  $pages = $d.ComputeStatistics(2)
  $d.Close(0)
  $parts = @()
  foreach ($k in $sec.Keys) { $parts += ('"' + $k + '": ' + $sec[$k]) }
  $json = '{"abstract": ' + $abs + ', "main_text": ' + $main + ', "main_with_headings": ' + ($main + $heads) + ', "sections": {' + ($parts -join ', ') + '}, "pages": ' + $pages + ', "table_cells": ' + $cells + ', "table_text": ' + $ttext + ', "legends": ' + $legends + '}'
  Set-Content -Path $Out -Value $json -Encoding ascii
} finally { $word.Quit() }
