# skills_lint.ps1 -- 技能清单防漂移校验 + SKILL.md BOM 校验
# 用法: powershell -File scripts\skills_lint.ps1
# 校验 WORKSPACE.md「技能清单（项目级）」与 .claude\skills\ 目录一一对应：
#   目录有、清单没登记 -> 该技能对非 Claude agent 不可见（违反发现契约）
#   清单登记、目录没有 -> 清单指向不存在的技能（删除/改名未同步）
# 另校验每个 SKILL.md 开头是否带 UTF-8 BOM：带 BOM 会让 frontmatter 静默解析失败
#   （description 显示为 "---"、触发词匹配完全失效，且不报错，2026-07-12 白泽实测踩坑）。
# 月度知识库健检时顺带跑一次；新增/改名/删除技能后立即跑。

param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$workspace = Join-Path $Root "WORKSPACE.md"
$skillsDir = Join-Path $Root ".claude\skills"

if (-not (Test-Path $workspace)) { Write-Error "WORKSPACE.md not found: $workspace"; exit 1 }
if (-not (Test-Path $skillsDir)) { Write-Error "skills dir not found: $skillsDir"; exit 1 }

$text = [System.IO.File]::ReadAllText($workspace, [System.Text.Encoding]::UTF8)

$startMark = "### 技能清单（项目级"
$endMark   = "### 常用全局技能"
$start = $text.IndexOf($startMark)
$end   = $text.IndexOf($endMark, [Math]::Max($start, 0))
if ($start -lt 0 -or $end -lt 0) { Write-Error "WORKSPACE.md 技能清单章节标记未找到（章节标题被改动？）"; exit 1 }
$section = $text.Substring($start, $end - $start)

# 反引号包裹、形如目录名的 token（小写字母数字连字符，不含路径字符）
$listed = @()
foreach ($m in [regex]::Matches($section, '`([a-z0-9][a-z0-9-]*)`')) { $listed += $m.Groups[1].Value }
$listed = $listed | Sort-Object -Unique

$actual = Get-ChildItem $skillsDir -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
    ForEach-Object { $_.Name } | Sort-Object

$missing = $actual  | Where-Object { $listed -notcontains $_ }   # 目录有清单无
$phantom = $listed  | Where-Object { $actual -notcontains $_ }   # 清单有目录无

$fail = $false
if ($missing) {
    Write-Host "[红] 未登记进 WORKSPACE.md 技能清单（对非 Claude agent 不可见）:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "     - $_" -ForegroundColor Red }
    $fail = $true
}
if ($phantom) {
    Write-Host "[红] 清单登记了不存在的技能（已删除或改名未同步）:" -ForegroundColor Red
    $phantom | ForEach-Object { Write-Host "     - $_" -ForegroundColor Red }
    $fail = $true
}

$bomHit = @()
foreach ($name in $actual) {
    $skillFile = Join-Path $skillsDir "$name\SKILL.md"
    $fs = [System.IO.File]::OpenRead($skillFile)
    try {
        $head = New-Object byte[] 3
        [void]$fs.Read($head, 0, 3)
    } finally { $fs.Close() }
    if ($head[0] -eq 0xEF -and $head[1] -eq 0xBB -and $head[2] -eq 0xBF) { $bomHit += $name }
}
if ($bomHit) {
    Write-Host "[红] SKILL.md 带 UTF-8 BOM（frontmatter 会静默解析失败，触发词失效）:" -ForegroundColor Red
    $bomHit | ForEach-Object { Write-Host "     - $_" -ForegroundColor Red }
    Write-Host "     修复：用 Write 工具重写该文件（不要用 PowerShell Out-File/Set-Content）" -ForegroundColor Red
    $fail = $true
}

if ($fail) { exit 1 }
Write-Host ("[绿] 技能清单与 .claude\skills\ 一致（{0} 个技能），SKILL.md 均无 BOM" -f $actual.Count) -ForegroundColor Green
exit 0
