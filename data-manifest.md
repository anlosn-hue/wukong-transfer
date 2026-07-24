# data-manifest — 离线数据包批次清单与落位说明

本仓走「文本资产在 git 仓、重资产走离线包」双通道交付。离线包 `wukong-data-YYYYMMDD.zip` 由移交人通过 U盘/网盘递送，本文件记录批次台账与解压落位方式。

---

## 一、批次台账

> 每次打包后由导出流程在此追加一行（新批次在上）。收包方核对：手上 zip 的文件名/体积/文件数须与某一行完全一致。

| 批次日期 | 对应仓 commit | zip 文件名 | 体积 | 文件数 |
|----------|--------------|-----------|------|--------|
| 2026-07-23 | ca85337 | wukong-data-20260723.zip | 713.65MB | 2491 |

---

## 二、落位对照表

zip 解压后的顶层目录 → 本仓路径：

| zip 内顶层目录 | 落位到仓内路径 | 内容 |
|----------------|---------------|------|
| `work/` | `work/` | 工作档案：声誉风险评估/活动评审/客户投诉分析/事后质检 等历史卷宗 |
| `internal-comms/` | `internal-comms/` | 内部宣传材料、经验提炼 |
| `knowledge-raw/` | `knowledge-raw/` | 原始资料 |
| `private/` | `knowledge/tools/assessment-manual/private/` | 处室清单（内部使用） |
| `templates/` | `templates/originals/` | 模板原件（docx/xlsx 等二进制） |
| `种子文件/` | 仓根（参考存放） | 两个 office 参考件：`办公室职能相关部分工作事项.xlsx`、`负面舆情风险隐患排查要点表.docx` |

另：`_raw/`（新材料收纳桶）**不在离线包内**，属可选自建目录——按 `BOOTSTRAP.md` 3.4 节在仓根建立空目录即可（`.gitignore` 已排除各数据落位目录；`_raw/` 内容同样不应提交）。

---

## 三、解压步骤与核对

1. 把 zip 放到仓根之外的临时目录，解压：

   ```
   powershell -Command "Expand-Archive -Path wukong-data-YYYYMMDD.zip -DestinationPath wukong-data-unpacked"
   ```

2. 按第二节对照表，把各顶层目录**合并复制**进仓内对应路径（目标目录已存在时合并，不要先删除——仓内可能已有你自己的运行时积累）：

   ```
   powershell -Command "Copy-Item wukong-data-unpacked/work/* work/ -Recurse -Force"
   ```

   （其余各行同理，逐目录执行；`private/` 与 `templates/` 注意目标路径不同名，见对照表）

3. 核对——五个落位目录均非空：

   ```
   powershell -Command "'work','internal-comms','knowledge-raw','templates/originals','knowledge/tools/assessment-manual/private' | ForEach-Object { '{0}: {1} 个文件' -f $_, (Get-ChildItem $_ -Recurse -File | Measure-Object).Count }"
   ```

   预期五行、每行文件数 > 0；文件总数应与第一节批次台账的「文件数」列对得上（种子文件另计 2 个）。

4. 抽查关键文件存在：

   ```
   powershell -Command "Test-Path 'knowledge/tools/assessment-manual/private/处室清单.md'"
   ```

   预期 `True`。

5. 核对完成后删除临时解压目录，zip 原件由用户自行留存备份。

---

## 四、版本对应声明（错位风险）

git 仓与离线包是**两条独立通道**：仓随时可 pull 到最新，离线包只在打包日的状态。两者错位时的典型症状——技能引用的 `work/` 历史卷宗路径不存在、活动方案库 INDEX 与卡片对不上。

约定：

- 每个离线包批次在第一节台账登记**打包时对应的仓 commit**；
- 收包落位时核对：当前 `git log` 首条 = 台账 commit，或晚于它——**仓可以比包新，包不能比仓新**（包比仓新说明你 clone 的不是最新仓，先 `git pull`）；
- 若仓明显新于包（隔了多个批次），以仓内文本为准，`work/` 等数据以最近一次落位的包为准，发现引用断裂时向移交人索取新批次数据包；
- 发现 zip 文件名日期在台账中查无此行 → 停止落位，向移交人核实包的来源与完整性。
