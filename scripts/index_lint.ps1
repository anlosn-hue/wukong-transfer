# index_lint.ps1 -- 知识库索引与记忆结构机械体检（纯体检、零代写）
# 设计依据: docs/superpowers/specs/2026-07-24-自维护机制-design.md D6/D7
# 四项检查:
#   1. INDEX 双向核对: cases/活动方案库/六维规则库 登记 vs 目录实际(死链+隐身); knowledge 总览只查死链
#   2. 活动库: 状态 vs 时间窗 vs 今日矛盾 + INDEX 行与卡片字段一致性 + 状态枚举 + 畸形行(列数!=12)
#   3. 活动卡 assessment_path <-> work/ 实际目录双向核对(work/ 缺失时黄牌跳过)
#   4. 海马体/backlog 结构体检: 出口列必填/无完结残留/类型五枚举/条目年龄>30天/到期日过期与45天预警
# 用法: powershell -File scripts\index_lint.ps1 [-Root <仓根>] [-Today yyyy-MM-dd]
#   -Today 供测试钉死日期; 不传取当天
# 输出: [红]=错误(exit 1, 当次会话内订正或报安之裁定, 报告不许只看不办) / [黄]=提醒(exit 0) / [绿]=通过
# 判断信息(scene/关键词/日期取值/状态翻转)永远人工写, 本脚本只报不改。
# 测试: powershell -File scripts\tests\index_lint.tests.ps1
# 注意: 本文件必须保持 UTF-8 BOM(PS 5.1 无 BOM 中文标记乱码->匹配静默失败, skills_lint 同款约定)

param(
    [string]$Root  = (Split-Path -Parent $PSScriptRoot),
    [string]$Today = ""
)

$ErrorActionPreference = "Stop"

if ($Today) { $script:TodayDate = [datetime]::ParseExact($Today, "yyyy-MM-dd", $null) }
else        { $script:TodayDate = (Get-Date).Date }

$script:Reds    = New-Object System.Collections.ArrayList
$script:Yellows = New-Object System.Collections.ArrayList

function Add-Red    { param([string]$Msg) [void]$script:Reds.Add($Msg) }
function Add-Yellow { param([string]$Msg) [void]$script:Yellows.Add($Msg) }

function Read-Utf8 { param([string]$Path) [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) }

# 从任意文本提取全部 yyyy-MM-dd, 返回 datetime 数组(可空)
function Get-Dates { param([string]$Text)
    $out = @()
    foreach ($m in [regex]::Matches([string]$Text, '\d{4}-\d{2}-\d{2}')) {
        try { $out += [datetime]::ParseExact($m.Value, "yyyy-MM-dd", $null) } catch {}
    }
    return ,$out
}

# markdown 表行拆单元格; 尊重 \| 转义(海马体条目含 wiki 链接); 非表行/分隔行返回 $null
function Split-TableRow { param([string]$Line)
    $t = ([string]$Line).Trim()
    if (-not $t.StartsWith("|")) { return $null }
    if ($t -match '^\|[\s:\-\|]+\|$') { return $null }
    $inner = $t.Trim('|')
    $cells = [regex]::Split($inner, '(?<!\\)\|')
    return ,($cells | ForEach-Object { $_.Trim() })
}

# 提取 $Heading 起到下一个 "## " 标题前的文本; 未找到返回 $null
# 锚定行首整行匹配, 防止正文里出现同名字样(引用/说明)时截错节
function Get-Section { param([string]$Text, [string]$Heading)
    $m = [regex]::Match($Text, "(?m)^" + [regex]::Escape($Heading) + "\s*$")
    if (-not $m.Success) { return $null }
    $rest = $Text.Substring($m.Index + $m.Length)
    $next = [regex]::Match($rest, "(?m)^## ")
    if ($next.Success) { return $rest.Substring(0, $next.Index) }
    return $rest
}

# ==================== 检查函数(Task 2-5 追加) ====================

function Invoke-Check1 {
    # 1a. 逐文件登记型 INDEX: 双向核对(死链+隐身)
    $perFile = @(
        @{ Label = "cases";      Index = "knowledge\cases\INDEX.md";            Dir = "knowledge\cases";            Mode = "link" },
        @{ Label = "六维规则库"; Index = "knowledge\tools\六维规则库\INDEX.md"; Dir = "knowledge\tools\六维规则库"; Mode = "link" },
        @{ Label = "活动方案库"; Index = "knowledge\活动方案库\INDEX.md";       Dir = "knowledge\活动方案库";       Mode = "id"   }
    )
    foreach ($cfg in $perFile) {
        $idxPath = Join-Path $Root $cfg.Index
        $dirPath = Join-Path $Root $cfg.Dir
        if (-not (Test-Path $idxPath)) { Add-Red "检查1[$($cfg.Label)]: INDEX 不存在: $($cfg.Index)"; continue }
        if (-not (Test-Path $dirPath)) { Add-Red "检查1[$($cfg.Label)]: 目录不存在: $($cfg.Dir)"; continue }
        $text = Read-Utf8 $idxPath
        $listed = @()
        if ($cfg.Mode -eq "link") {
            # 同目录相对链接(不含路径分隔符)
            foreach ($m in [regex]::Matches($text, '\]\(([^)/\\]+\.md)\)')) { $listed += $m.Groups[1].Value }
        } else {
            # 活动方案库: 表格首列活动ID -> <ID>.md
            foreach ($line in ($text -split "`n")) {
                $cells = Split-TableRow $line
                if ($null -eq $cells -or $cells.Count -lt 2) { continue }
                if ($cells[0] -match '^\d{8}-') { $listed += "$($cells[0]).md" }
            }
        }
        # @() 必须: 空集流经管道变 $null, 而 $null -notcontains X 恒真 -> 反向全量误报
        $listed = @($listed | Sort-Object -Unique)
        $actual = @(Get-ChildItem $dirPath -Filter *.md -File |
            Where-Object { $_.Name -ne "INDEX.md" } | ForEach-Object { $_.Name } | Sort-Object)
        foreach ($f in @($listed | Where-Object { $actual -notcontains $_ })) {
            Add-Red "检查1[$($cfg.Label)]: 死链——登记了不存在的文件 $f"
        }
        foreach ($f in @($actual | Where-Object { $listed -notcontains $_ })) {
            Add-Red "检查1[$($cfg.Label)]: 隐身——文件未登记进 INDEX: $f (未登记=对按 INDEX 加载的技能不存在且无报错)"
        }
    }

    # 1b. knowledge 总览: 只查死链(目录级总览, 不做隐身核对)
    $ovPath = Join-Path $Root "knowledge\INDEX.md"
    if (-not (Test-Path $ovPath)) { Add-Red "检查1[总览]: knowledge\INDEX.md 不存在"; return }
    $ovText  = Read-Utf8 $ovPath
    $ovDir   = Join-Path $Root "knowledge"
    # ../<顶层>/ 链接: 顶层目录整个缺失(junction 未接/移交仓克隆环境)时黄牌跳过, 不误报死链
    $skippedTops = @{}
    foreach ($m in [regex]::Matches($ovText, '\]\(([^)]+)\)')) {
        $target = ($m.Groups[1].Value -split '#')[0]
        if (-not $target -or $target -match '^(https?:|mailto:)') { continue }
        if ($target -match '^\.\./([^/]+)/') {
            $top = $Matches[1]
            if (-not (Test-Path (Join-Path $Root $top))) { $skippedTops[$top] = $true; continue }
        }
        $resolved = Join-Path $ovDir ($target -replace '/', '\')
        if (-not (Test-Path $resolved)) { Add-Red "检查1[总览]: 死链 $target" }
    }
    foreach ($top in ($skippedTops.Keys | Sort-Object)) {
        Add-Yellow "检查1[总览]: $top\ 不存在(junction 未接或移交仓环境), 指向 ../$top/ 的链接未核"
    }
}

function Invoke-Check2 {
    $idxPath = Join-Path $Root "knowledge\活动方案库\INDEX.md"
    $dirPath = Join-Path $Root "knowledge\活动方案库"
    if (-not (Test-Path $idxPath)) { return }   # 检查1已报
    $statusEnum = @("进行中", "待上线", "已结束", "已下线", "已取消")
    $lineNo = 0
    foreach ($line in ((Read-Utf8 $idxPath) -split "`n")) {
        $lineNo++
        $cells = Split-TableRow $line
        if ($null -eq $cells -or $cells.Count -lt 1) { continue }
        if ($cells[0] -notmatch '^\d{8}-') { continue }
        $id = $cells[0]
        if ($cells.Count -ne 12) {
            Add-Red "检查2[畸形行]: 第${lineNo}行「$id」列数 $($cells.Count) != 12——该行会被盯盘解析器整行跳过等于从盯盘消失"
            continue
        }
        # INDEX 时间窗: 按 ~ 劈两半再各取日期(存在 待填~2026-07-31 之类, 全串抓会把终点当起点)
        $parts = [regex]::Split($cells[5], '[~～]')
        $idxStart = $null; $idxEnd = $null
        $d = Get-Dates $parts[0]; if ($d.Count) { $idxStart = $d[0] }
        if ($parts.Count -ge 2) { $d = Get-Dates $parts[1]; if ($d.Count) { $idxEnd = $d[0] } }
        $idxStatus = $cells[7]

        # 卡片字段(卡片优先)
        $cardPath = Join-Path $dirPath "$id.md"
        if (-not (Test-Path $cardPath)) { continue }   # 检查1已报死链
        $card = Read-Utf8 $cardPath
        $cardStatus = ""; $cardStart = $null; $cardEnd = $null
        if ($card -match '(?m)^status:\s*(\S+)')     { $cardStatus = $Matches[1].Trim() }
        if ($card -match '(?m)^start_date:\s*(.+)$') { $d = Get-Dates $Matches[1]; if ($d.Count) { $cardStart = $d[0] } }
        if ($card -match '(?m)^end_date:\s*(.+)$')   { $d = Get-Dates $Matches[1]; if ($d.Count) { $cardEnd = $d[0] } }

        # 状态枚举(格式约定自检③: 模板枚举 vs 实际取值; 卡片与 INDEX 状态列都查)
        if ($cardStatus -and $statusEnum -notcontains $cardStatus) {
            Add-Red "检查2[枚举]: 卡「$id」status=「$cardStatus」不在枚举(进行中/待上线/已结束/已下线/已取消)——补枚举还是订数据, 报安之定"
        }
        if ($idxStatus -and $idxStatus -ne "-" -and $statusEnum -notcontains $idxStatus) {
            Add-Red "检查2[枚举]: 「$id」INDEX 状态列「$idxStatus」不在枚举(进行中/待上线/已结束/已下线/已取消)"
        }
        # INDEX 行与卡片一致性(P0 五条订正即此类漂移)
        if ($cardStatus -and $idxStatus -and $idxStatus -ne $cardStatus) {
            Add-Red "检查2[不同步]: 「$id」INDEX 状态「$idxStatus」!= 卡片 status「$cardStatus」(卡片优先, INDEX 未同步)"
        }
        if ($cardStart -and $idxStart -and $idxStart -ne $cardStart) {
            Add-Red "检查2[不同步]: 「$id」INDEX 时间窗起点 $($idxStart.ToString('yyyy-MM-dd')) != 卡片 start_date $($cardStart.ToString('yyyy-MM-dd'))"
        }
        if ($cardEnd -and $idxEnd -and $idxEnd -ne $cardEnd) {
            Add-Red "检查2[不同步]: 「$id」INDEX 时间窗终点 $($idxEnd.ToString('yyyy-MM-dd')) != 卡片 end_date $($cardEnd.ToString('yyyy-MM-dd'))"
        }

        # 状态 vs 时间窗 vs 今日(D7; 卡片值优先, 缺则回落 INDEX; 日期解析不出的规则跳过)
        $st = $cardStatus; if (-not $st) { $st = $idxStatus }
        $start = $cardStart; if (-not $start) { $start = $idxStart }
        $end = $cardEnd; if (-not $end) { $end = $idxEnd }
        if ($end -and $end -lt $script:TodayDate -and @("进行中", "待上线") -contains $st) {
            Add-Red "检查2[矛盾]: 「$id」end_date $($end.ToString('yyyy-MM-dd')) 已过但状态仍「$st」(只报不代翻, 状态翻转是业务动作)"
        }
        if ($start -and $start -gt $script:TodayDate -and @("进行中", "已结束") -contains $st) {
            Add-Red "检查2[矛盾]: 「$id」start_date $($start.ToString('yyyy-MM-dd')) 未到但状态已「$st」(只报不代翻)"
        }
        if ($end -and $end -gt $script:TodayDate -and $st -eq "已结束") {
            Add-Yellow "检查2: 「$id」状态已结束但 end_date 在未来——若提前终止请确认应否为已下线或更新 end_date"
        }
        if ($start -and $start -lt $script:TodayDate -and $st -eq "待上线") {
            Add-Yellow "检查2: 「$id」start_date $($start.ToString('yyyy-MM-dd')) 已过仍待上线——上线延期或漏翻状态, 待人工确认"
        }
    }
}

function Invoke-Check3 {
    $workRoot = Join-Path $Root "work"
    if (-not (Test-Path $workRoot)) {
        Add-Yellow "检查3: work\ 不存在(junction 未接, 移交仓克隆环境属正常), 本项跳过"
        return
    }
    # work\ 存在但两个业务子目录都不在 = 占位空目录(移交仓数据 zip 未落位), 全量死链红没有意义
    $subA = Join-Path $workRoot "声誉风险评估"; $subB = Join-Path $workRoot "活动评审"
    if (-not (Test-Path $subA) -and -not (Test-Path $subB)) {
        Add-Yellow "检查3: work\ 下无 声誉风险评估\活动评审 子目录(数据未落位的占位状态), 本项跳过"
        return
    }
    $dirPath = Join-Path $Root "knowledge\活动方案库"
    if (-not (Test-Path $dirPath)) { return }
    $referenced = @{}
    foreach ($cardFile in (Get-ChildItem $dirPath -Filter *.md -File | Where-Object { $_.Name -ne "INDEX.md" })) {
        $card = Read-Utf8 $cardFile.FullName
        if ($card -notmatch '(?m)^assessment_path:\s*(.+)$') { continue }
        # 排除类不含括号: 真库目录名实证含全角括号(20260701-财富新客礼遇（限时加码）), 排除会截断路径误报死链;
        # 「（推断）」类括注若未来真出现在 assessment_path 会报死链红(fail loud), 届时订数据即可——实证目录名优先于假想括注
        foreach ($m in [regex]::Matches($Matches[1], 'work/[^\s"，,、；;]+')) {
            $rel = $m.Value.TrimEnd('/')
            $referenced[$rel] = $true
            if (-not (Test-Path (Join-Path $Root ($rel -replace '/', '\')))) {
                Add-Red "检查3[死链]: 卡「$($cardFile.BaseName)」assessment_path 指向不存在目录: $rel"
            }
        }
    }
    foreach ($sub in @("声誉风险评估", "活动评审")) {
        $base = Join-Path $workRoot $sub
        if (-not (Test-Path $base)) { continue }
        foreach ($d in (Get-ChildItem $base -Directory)) {
            $rel = "work/$sub/$($d.Name)"
            if (-not $referenced.ContainsKey($rel)) {
                Add-Yellow "检查3[孤儿]: $rel 无任何活动卡指向——可能未上线待人工判断(照妖镜先评审后建卡属正常时序, 不算错误)"
            }
        }
    }
}

function Invoke-Check4 {
    $typeEnum = @("任务跨会话", "专业判断", "新排查要点", "安之的纠正", "监管新动向")

    # 海马体: 五类+出口结构(设计: spec D4)
    $hipPath = Join-Path $Root "memory\海马体.md"
    if (-not (Test-Path $hipPath)) { Add-Red "检查4: memory\海马体.md 不存在" }
    else {
        $sec = Get-Section (Read-Utf8 $hipPath) "## 待处理条目"
        if ($null -eq $sec) { Add-Red "检查4[海马体]: 「## 待处理条目」节未找到(标题被改动? 改标题须同步本脚本)" }
        else {
            foreach ($line in ($sec -split "`n")) {
                $cells = Split-TableRow $line
                if ($null -eq $cells -or $cells.Count -lt 2) { continue }
                if ($cells[0] -eq "条目") { continue }
                $label = $cells[0] -replace '\*', ''
                if ($label.Length -gt 18) { $label = $label.Substring(0, 18) + "…" }
                if ($cells.Count -ne 4) { Add-Red "检查4[海马体]: 「$label」列数 $($cells.Count) != 4(条目/类型/出口/来源)"; continue }
                if ($cells[0] -match '✅') { Add-Red "检查4[海马体]: 「$label」含 ✅ 完结标记残留——完结当场删不过夜, 按三分流提炼归档后删条" }
                $typeOk = $false
                foreach ($t in $typeEnum) { if ($cells[1] -match [regex]::Escape($t)) { $typeOk = $true } }
                if (-not $typeOk) { Add-Red "检查4[海马体]: 「$label」类型「$($cells[1])」不在五类之内——当场分诊, 不许自由堆放" }
                if (-not $cells[2] -or $cells[2] -eq "-") { Add-Red "检查4[海马体]: 「$label」出口列为空——每条必填出口, 没有出口的进 backlog 或删" }
                $dates = Get-Dates $cells[3]
                if ($dates.Count -eq 0) { Add-Yellow "检查4[海马体]: 「$label」来源列无日期, 无法判龄" }
                else {
                    $age = ($script:TodayDate - ($dates | Sort-Object | Select-Object -Last 1)).Days
                    if ($age -gt 30) { Add-Yellow "检查4[海马体]: 「$label」已滞留 $age 天(>30)——确认出口是否仍成立, 或分诊 backlog" }
                }
            }
        }
    }

    # backlog: 到期日扫描(健检之外的第二层触发, 设计: spec D5)
    $bkPath = Join-Path $Root "memory\backlog.md"
    if (-not (Test-Path $bkPath)) { Add-Red "检查4: memory\backlog.md 不存在" }
    else {
        $sec = Get-Section (Read-Utf8 $bkPath) "## 挂账清单"
        if ($null -eq $sec) { Add-Red "检查4[backlog]: 「## 挂账清单」节未找到(标题被改动? 改标题须同步本脚本)" }
        else {
            foreach ($line in ($sec -split "`n")) {
                $cells = Split-TableRow $line
                if ($null -eq $cells -or $cells.Count -lt 4) { continue }
                if ($cells[0] -eq "#") { continue }
                if ($cells.Count -ne 5) { Add-Red "检查4[backlog]: 「$($cells[1])」列数 $($cells.Count) != 5(#/事项/背景/到期日/来源)"; continue }
                $due = $cells[3]
                if ($due -eq "-" -or -not $due) { continue }
                $dates = Get-Dates $due
                if ($dates.Count -eq 0) { Add-Yellow "检查4[backlog]: 「$($cells[1])」到期日列有内容但无法解析日期: $due"; continue }
                $days = ($dates[0] - $script:TodayDate).Days
                if ($days -lt 0) { Add-Red "检查4[backlog]: 「$($cells[1])」到期日 $($dates[0].ToString('yyyy-MM-dd')) 已过期 $(-$days) 天——处置后更新或移除标记" }
                elseif ($days -le 45) { Add-Yellow "检查4[backlog]: 「$($cells[1])」$days 天后到期($($dates[0].ToString('yyyy-MM-dd')))" }
            }
        }
    }
}

# ==================== 主流程(Task 2-5 追加调用) ====================

Invoke-Check1
Invoke-Check2
Invoke-Check3
Invoke-Check4

# ==================== 汇总 ====================

if ($script:Reds.Count -gt 0) {
    Write-Host "[红] $($script:Reds.Count) 项错误(当次会话内订正, 订正不了的报安之裁定):" -ForegroundColor Red
    $script:Reds | ForEach-Object { Write-Host "     - $_" -ForegroundColor Red }
}
if ($script:Yellows.Count -gt 0) {
    Write-Host "[黄] $($script:Yellows.Count) 项提醒(不影响退出码):" -ForegroundColor Yellow
    $script:Yellows | ForEach-Object { Write-Host "     - $_" -ForegroundColor Yellow }
}
if ($script:Reds.Count -gt 0) { exit 1 }
Write-Host "[绿] index_lint 体检通过" -ForegroundColor Green
exit 0
