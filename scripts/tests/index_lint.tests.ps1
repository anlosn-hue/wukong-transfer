# index_lint.tests.ps1 -- fixture 驱动测试; 用法: powershell -File scripts\tests\index_lint.tests.ps1
# 每个用例: New-GreenFixture 搭全绿最小仓 -> 扰动单点 -> 断言退出码与输出
# 注意: 本文件必须保持 UTF-8 BOM(同 index_lint.ps1)

$ErrorActionPreference = "Stop"
$script:FixtureRoot = Join-Path $env:TEMP "index_lint_fixture"
$script:LintPath    = Join-Path $PSScriptRoot "..\index_lint.ps1"
$script:Fails = 0

function Write-Fx { param([string]$Rel, [string]$Content)
    $p = Join-Path $script:FixtureRoot $Rel
    $d = Split-Path -Parent $p
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force $d | Out-Null }
    [System.IO.File]::WriteAllText($p, $Content, (New-Object System.Text.UTF8Encoding($true)))
}

function New-GreenFixture {
    if (Test-Path $script:FixtureRoot) { Remove-Item $script:FixtureRoot -Recurse -Force }
    foreach ($d in @("knowledge\cases", "knowledge\活动方案库", "knowledge\tools\六维规则库",
                     "work\声誉风险评估\20260701-测试活动", "work\活动评审")) {
        New-Item -ItemType Directory -Force (Join-Path $script:FixtureRoot $d) | Out-Null
    }
    Write-Fx "knowledge\log.md" "# log"
    Write-Fx "knowledge\INDEX.md" "# 总览`n`n[log.md](log.md)`n"
    Write-Fx "knowledge\cases\c1.md" "# c1"
    Write-Fx "knowledge\cases\INDEX.md" @"
| 文件 | scene |
|------|-------|
| [c1.md](c1.md) | 内部·测试 |
"@
    Write-Fx "knowledge\tools\六维规则库\01-测试.md" "# 01"
    Write-Fx "knowledge\tools\六维规则库\INDEX.md" @"
| 文件 | 维度 |
|------|------|
| [01-测试.md](01-测试.md) | ① |
"@
    Write-Fx "knowledge\活动方案库\INDEX.md" @"
| 活动ID | 活动名 | 来源 | 类型 | 客群 | 时间窗 | 渠道 | 状态 | 风险等级 | 舆情关键词 | 下次盯盘节点 | 评估校正 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260701-测试处-测试活动 | 测试活动 | internal | 活动 | 测试客群 | 2026-07-01~2026-07-30 | APP | 进行中 | 四级 | 测试 | - | - |
"@
    Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" @"
---
activity_id: 20260701-测试处-测试活动
category: 活动
start_date: 2026-07-01
end_date: 2026-07-30
assessment_path: work/声誉风险评估/20260701-测试活动/
status: 进行中
---
"@
    # memory\海马体.md 与 memory\backlog.md 的 fixture 随检查4 于 2026-08-13 退役后移除
    # (本脚本已不再读 memory\, 结构体检归点卯 hippo-lib)
}

function Invoke-Lint {
    # -Width 4096 必须: PS 5.1 重定向输出默认 80 列折行, 长消息被劈开会让 -match 断言假性失败
    $out = & powershell -NoProfile -File $script:LintPath -Root $script:FixtureRoot -Today "2026-07-24" 2>&1 | Out-String -Width 4096
    return @{ Exit = $LASTEXITCODE; Out = $out }
}

function Assert { param([bool]$Cond, [string]$Msg)
    if ($Cond) { Write-Host "  PASS: $Msg" -ForegroundColor Green }
    else       { Write-Host "  FAIL: $Msg" -ForegroundColor Red; $script:Fails++ }
}

# ---- T-0: 两个 .ps1 必须带 UTF-8 BOM(机械自检, 不靠执行者记得) ----
Write-Host "T-0: BOM 自检"
foreach ($p in @($script:LintPath, $PSCommandPath)) {
    $b = [System.IO.File]::ReadAllBytes($p)[0..2]
    Assert ($b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) "带 BOM: $(Split-Path -Leaf $p)"
}

# ---- T0: 基线全绿 ----
Write-Host "T0: 基线 fixture 全绿"
New-GreenFixture
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "基线退出码 0 (实际 $($r.Exit))"
Assert ($r.Out -match '\[绿\]') "输出含 [绿]"

# ==================== 各检查项用例(Task 2-5 追加) ====================

# ---- T1: 检查1 死链(登记了不存在的文件) ----
Write-Host "T1: cases INDEX 死链"
New-GreenFixture
Write-Fx "knowledge\cases\INDEX.md" @"
| 文件 | scene |
|------|-------|
| [c1.md](c1.md) | 内部·测试 |
| [missing.md](missing.md) | 内部·测试 |
"@
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "死链退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '死链' -and $r.Out -match 'missing\.md') "输出报 missing.md 死链"

# ---- T2: 检查1 隐身(文件未登记) ----
Write-Host "T2: cases 目录文件隐身"
New-GreenFixture
Write-Fx "knowledge\cases\20260720-未登记案例.md" "# 未登记"
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "隐身退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '隐身' -and $r.Out -match '20260720-未登记案例\.md') "输出报隐身文件"

# ---- T2b: 活动方案库按活动ID核对(无链接形态) ----
Write-Host "T2b: 活动方案库 INDEX 登记了无卡片的 ID"
New-GreenFixture
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
# 注意前置 `n: here-string 内容末尾无换行, 直接 += 会拼进上一行变超长畸形行
$idx += "`n| 20260702-测试处-幽灵活动 | 幽灵 | internal | 活动 | 客群 | 2026-07-02~2026-07-31 | APP | 进行中 | 四级 | 测试 | - | - |`n"
Write-Fx "knowledge\活动方案库\INDEX.md" $idx
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "幽灵ID退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '20260702-测试处-幽灵活动') "输出报幽灵活动ID"

# ---- T3: 检查1 knowledge 总览死链 ----
Write-Host "T3: knowledge 总览死链"
New-GreenFixture
Write-Fx "knowledge\INDEX.md" "# 总览`n`n[log.md](log.md)`n[坏链](tools/不存在目录/)`n"
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "总览死链退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '总览' -and $r.Out -match '不存在目录') "输出报总览死链"

# ---- T4: 畸形行(列数!=12) ----
Write-Host "T4: 活动库畸形行"
New-GreenFixture
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
# 注意前置 `n: 同 T2b, 防止拼进上一行
$idx += "`n| 20260703-测试处-缺列活动 | 缺列 | internal | 活动 | 客群 | 2026-07-03~2026-07-31 | APP | 进行中 | 四级 | 测试 | - |`n"
Write-Fx "knowledge\活动方案库\INDEX.md" $idx
Write-Fx "knowledge\活动方案库\20260703-测试处-缺列活动.md" "---`nstatus: 进行中`n---`n"
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "畸形行退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '畸形行' -and $r.Out -match '20260703-测试处-缺列活动') "输出报畸形行"

# ---- T5: 状态 vs 时间窗矛盾(end 已过仍进行中) ----
Write-Host "T5: end_date 已过仍进行中"
New-GreenFixture
Write-Fx "knowledge\活动方案库\INDEX.md" @"
| 活动ID | 活动名 | 来源 | 类型 | 客群 | 时间窗 | 渠道 | 状态 | 风险等级 | 舆情关键词 | 下次盯盘节点 | 评估校正 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260701-测试处-测试活动 | 测试活动 | internal | 活动 | 测试客群 | 2026-07-01~2026-07-10 | APP | 进行中 | 四级 | 测试 | - | - |
"@
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" @"
---
activity_id: 20260701-测试处-测试活动
category: 活动
start_date: 2026-07-01
end_date: 2026-07-10
assessment_path: work/声誉风险评估/20260701-测试活动/
status: 进行中
---
"@
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "矛盾退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '矛盾' -and $r.Out -match '只报不代翻') "输出报矛盾且声明不代翻"

# ---- T6: INDEX 与卡片状态不同步 ----
Write-Host "T6: INDEX 状态 != 卡片 status"
New-GreenFixture
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '\| 进行中 \|', '| 已结束 |')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "不同步退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '不同步' -and $r.Out -match '卡片优先') "输出报不同步(卡片优先)"

# ---- T7: 卡片 status 枚举外 ----
Write-Host "T7: status 枚举外值"
New-GreenFixture
$card = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\20260701-测试处-测试活动.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" ($card -replace 'status: 进行中', 'status: 快结束了')
# INDEX 状态列同改, 免得同时触发 T6 的不同步红
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '\| 进行中 \|', '| 快结束了 |')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "枚举外退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '枚举' -and $r.Out -match '快结束了') "输出报枚举外值"

# ---- T7b: 待上线但 start 已过 -> 黄不红 ----
Write-Host "T7b: start 已过仍待上线(黄)"
New-GreenFixture
$card = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\20260701-测试处-测试活动.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" ($card -replace 'status: 进行中', 'status: 待上线')
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '\| 进行中 \|', '| 待上线 |')
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "黄牌不影响退出码 (实际 $($r.Exit))"
Assert ($r.Out -match '待上线' -and $r.Out -match '\[黄\]') "输出黄牌提醒上线延期"

# ---- T5b: start 未到却已进行中 ----
Write-Host "T5b: start_date 未到却进行中"
New-GreenFixture
Write-Fx "knowledge\活动方案库\INDEX.md" @"
| 活动ID | 活动名 | 来源 | 类型 | 客群 | 时间窗 | 渠道 | 状态 | 风险等级 | 舆情关键词 | 下次盯盘节点 | 评估校正 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20260701-测试处-测试活动 | 测试活动 | internal | 活动 | 测试客群 | 2026-08-01~2026-08-30 | APP | 进行中 | 四级 | 测试 | - | - |
"@
$card = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\20260701-测试处-测试活动.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" (($card -replace 'start_date: 2026-07-01', 'start_date: 2026-08-01') -replace 'end_date: 2026-07-30', 'end_date: 2026-08-30')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "start未到红 (实际 $($r.Exit))"
Assert ($r.Out -match '未到但状态已') "输出报 start 未到矛盾"

# ---- T6b: INDEX 时间窗与卡片日期不同步 ----
Write-Host "T6b: INDEX 时间窗起点 != 卡片 start_date"
New-GreenFixture
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '2026-07-01~2026-07-30', '2026-07-02~2026-07-30')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "日期不同步红 (实际 $($r.Exit))"
Assert ($r.Out -match '不同步' -and $r.Out -match 'start_date') "输出报时间窗起点不同步"

# ---- T7c: 已结束但 end 在未来 -> 黄不红 ----
Write-Host "T7c: 已结束但 end_date 在未来(黄)"
New-GreenFixture
$card = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\20260701-测试处-测试活动.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" ($card -replace 'status: 进行中', 'status: 已结束')
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '\| 进行中 \|', '| 已结束 |')
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "提前结束不红 (实际 $($r.Exit))"
Assert ($r.Out -match '已结束但 end_date 在未来') "输出黄牌提示确认已下线或更新end_date"

# ---- T7d: INDEX 状态列枚举外值 ----
Write-Host "T7d: INDEX 状态列枚举外"
New-GreenFixture
$idx = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\INDEX.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\INDEX.md" ($idx -replace '\| 进行中 \|', '| 暂停 |')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "INDEX枚举外红 (实际 $($r.Exit))"
Assert ($r.Out -match 'INDEX 状态列「暂停」不在枚举') "输出报 INDEX 状态列枚举外"

# ---- T8: assessment_path 死链 ----
Write-Host "T8: assessment_path 指向不存在目录"
New-GreenFixture
$card = [System.IO.File]::ReadAllText((Join-Path $script:FixtureRoot "knowledge\活动方案库\20260701-测试处-测试活动.md"), [System.Text.Encoding]::UTF8)
Write-Fx "knowledge\活动方案库\20260701-测试处-测试活动.md" ($card -replace 'work/声誉风险评估/20260701-测试活动/', 'work/声誉风险评估/20260701-不存在目录/ 及 work/活动评审/20260701-也不存在/')
$r = Invoke-Lint
Assert ($r.Exit -eq 1) "路径死链退出码 1 (实际 $($r.Exit))"
Assert ($r.Out -match '检查3' -and $r.Out -match '20260701-不存在目录' -and $r.Out -match '20260701-也不存在') "多路径逐一报死链"

# ---- T9: work 目录无卡指向 -> 黄不红 ----
Write-Host "T9: work 孤儿目录(黄)"
New-GreenFixture
New-Item -ItemType Directory -Force (Join-Path $script:FixtureRoot "work\活动评审\20260702-孤儿评审") | Out-Null
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "孤儿目录不红 (实际 $($r.Exit))"
Assert ($r.Out -match '孤儿|无任何活动卡指向' -and $r.Out -match '20260702-孤儿评审') "输出黄牌列出孤儿目录"
Assert ($r.Out -match '先评审后建卡属正常时序') "标注属正常时序待人工判断"

# ---- T9b: work junction 缺失 -> 黄牌跳过整项 ----
Write-Host "T9b: work 缺失跳过检查3"
New-GreenFixture
Remove-Item (Join-Path $script:FixtureRoot "work") -Recurse -Force
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "work 缺失不红 (实际 $($r.Exit))"
Assert ($r.Out -match '检查3' -and $r.Out -match '跳过') "输出黄牌声明跳过"

# ---- T9c: work 存在但业务子目录全缺(占位状态) -> 黄牌跳过 ----
Write-Host "T9c: work 占位空目录跳过检查3"
New-GreenFixture
Remove-Item (Join-Path $script:FixtureRoot "work\声誉风险评估") -Recurse -Force
Remove-Item (Join-Path $script:FixtureRoot "work\活动评审") -Recurse -Force
$r = Invoke-Lint
Assert ($r.Exit -eq 0) "占位状态不红 (实际 $($r.Exit))"
Assert ($r.Out -match '数据未落位' -and $r.Out -match '跳过') "输出黄牌声明占位跳过"

# 注: 原 T10/T11/T11b(海马体结构体检、backlog 到期日扫描、章节标记丢失)随检查4
# 于 2026-08-13 一并退役——该职责移交点卯 hippo-lib(anzhi-dianmao/scripts/hippo-lib.ps1),
# 对应用例在 anzhi-dianmao/scripts/test-hippo.ps1。此处不再保留, 防两套解析器漂移。

# ---- 汇总 ----
Write-Host ""
if ($script:Fails -gt 0) { Write-Host "共 $script:Fails 个断言失败" -ForegroundColor Red; exit 1 }
Write-Host "全部断言通过" -ForegroundColor Green
exit 0
