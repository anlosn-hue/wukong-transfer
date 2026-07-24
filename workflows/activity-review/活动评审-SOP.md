# 活动评审 — 操作规程（SOP）

> 适用：处室正式发起申请前的可选前置评审
> 当前版本：照妖镜技能（anzhi-huodongpingshen）自动化版

---

## 触发

处室提交活动材料（任意组合，可以是全部，也可以是部分）：
- 活动方案
- 宣传物料
- 触客话术

## 操作步骤

1. 接收材料，存入 `work/活动评审/YYYYMMDD-[活动名]/input/`
2. 调用照妖镜技能（对悟空说"帮我做活动评审"或直接提供材料）
3. 悟空自动跑完七阶段评审，输出两份结论：
   - 活动评审意见（给处室，含改进建议）
   - 声誉风险等级（给审批链参考）
4. 评审结论保存至 `work/活动评审/YYYYMMDD-[活动名]/output/评审结论.md`

## 参考文档

- 技能设计：`docs/superpowers/specs/2026-06-02-活动评审技能-design.md`
- 技能文件：`C:\Users\Lenovo\.claude\skills\anzhi-huodongpingshen\SKILL.md`
- 知识库：`knowledge/tools/六维规则库/`、`knowledge/tools/声誉风险事件库/`

---

## 历史版本（手动流程，已停用）

原六步手动 SOP 已被照妖镜技能取代。核心检查逻辑已内化至技能 Phase 1–2：
- 原第二步（广告宣传规范审核）→ Phase 1 宣传物料检查
- 原第三步（消保审查）→ Phase 1 触客话术 + Phase 2 事项合理性
- 原第四步（舆情隐患排查）→ Phase 2 政治敏感性 + Phase 3 三源情报
