# 中医大脑 V2 项目治理规范（AGENTS.md）

本文件定义仓库中所有模块（针灸、神农本草经、黄帝内经、伤寒金匮经方、辨证知识网络与后续检索）共同遵守的数据口径、证据要求与安全边界。

## 一、不可违反的边界

1. **来源可追溯**：每条正式入库知识必须绑定 `source_id`、`page_id`（或明确行号）、`pdf_page` / `printed_page` 与原文摘录（`quote`），且 `quote` 必须能在对应页级来源中找到。严禁伪造页码、书名或空泛的“某书说”。
2. **五层内容严格分离**：不得将不同来源角色混写为一段文字后失去归属：
   - `source_quote`：原典正文或讲义转录原文
   - `ni_teaching`：倪海厦先生讲授与临床说明
   - `other_annotations`：校勘版脚注中引用的古籍或外部注解（如《针灸大成》《难经》《灵枢》《素问》）
   - `collation_notes`：民间校勘者说明、版本差异、校对注与待考说明
   - `organizer_summary`：整理者结构化摘要或系统整理说明（严禁冒充原文）
3. **未说明不补结论**：凡原书/讲稿未交代深浅、留针时间、机制或步骤之处，必须显式写入 `open_questions`（尚待考证），不得由 AI 自行补出结论。
4. **四个正交状态分离记录与展示**：不得用单一“已完成”掩盖状态差异：
   - `generation_status`：`auto` | `assisted` | `manual`
   - `evidence_status`：`unlinked` | `anchored` | `verified` | `conflicted`
   - `review_status`：`pending` | `needs_changes` | `approved` | `rejected`
   - `risk_level`：`standard` | `high_risk` | `emergency`
5. **不覆盖既有成果**：`data/formulas.json`、`data/jinkui_formulas.json`、`data/herbs.json`、`data/formula_evidence.json`、`data/formula_modules.json`、`data/six_channels.json` 及 `data/curated_batch_manifest.json` 已签收批次不得被覆盖式重建；现有 140 项回归测试必须持续保持通过。
6. **批次签收闸门**：候选批次须通过结构与原文一致性校验，并写入对应 `batch_manifest.json` 的 `accepted` 列表，才可计入正式已审统计数字。

## 二、高风险与安全红线

- 针刺操作、深浅与角度、放血、烧针（火针）、艾灸烫伤风险、妊娠期禁忌、婴幼儿操作、急症昏迷抢救、脑瘤/癌症等重病内容，以及有毒药材或矿物药粉，一律标为 `high_risk` 或 `emergency`，并附显式教学风险警示。
- 所有治疗与技法内容均以“专业教学与原书文献学习条目”呈现，**不得包装为普通用户可自行执行的个人操作指南、诊断或处方**。

## 三、版本与来源口径

- 本地《倪海厦人纪系列之针灸教程.pdf》（V2-20100703 第四次修改，共 216 页）经校勘序核实为**基于网络流传授课扫描件由民间中医爱好者校勘整理的转录版本**，其 `source_type` 必须标注为 `collated_transcript`（校勘转录版），不可标为原始出版“原书”。
- 原始 PDF 只读不改；页图与页级文本双轨留存，校字与结构化抽取不覆盖原始抽取文本。
