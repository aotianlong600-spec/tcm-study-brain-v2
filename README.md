# 中医学习大脑 · 本地方剂模块

这是重新建立的干净仓库，当前只交付方剂模块。数据来自本地倪海厦资料，不接第三方方剂库作为正式内容。

## 当前数据

- 伤寒论辑义：113 条记录。110 首严格通过味数校验，2 首按同段原文补入，`土瓜根方` 原文缺并保留占位。
- 倪海厦注金匮要略：186 条记录全部进入目录；当前 168 条味数校验完整、17 条有组成但未找到“上X味”锚点、1 条加味方。186 条均已有剂量字段。
- 倪海厦注神农本草经：351 味药，保留 PDF 页码与分段原文。
- 每首方保留原文出处、组成、剂量、煎服法、校注和版本差异。
- `formula_evidence.json` 为每一方保存用法、为什么用、书本候选页、视频候选页和校对状态；目前正式验收 114 条，其余 185 条明确标为待校。候选批次只有在 `curated_batch_manifest.json` 中签收后才计入。
- `formula_modules.json` 为全部 299 方建立独立可导航模块：每方含详细初页、原方、古文煎药、现代资料整理、逐页原文、六经/篇章关联和校对依据。自动编页模块标为“原文页索引”，不冒充人工定稿。
- 桂枝汤已有完整二级考证页：太阳病提纲、太阳中风原文、倪注、桂枝汤原方、古文用法、现代煎服步骤和方义证据分开陈列。
- 新增「六经辨证」板块，六经条目全部建立；太阳病已完成理解总结、原文和原文注解，其余五经保留原文并标为待整理。

针灸、辨证论治和病症模块尚未接入。页面会明确显示待接入，不拿第三方数据填充。

## 启动

```powershell
python -m pip install -r requirements.txt
.\run.ps1 -NoBrowser
```

默认地址：`http://127.0.0.1:8768`

## 重建与校验

```powershell
python -m etl.extract_shanghan
python -m etl.import_jinkui
python -m etl.enrich_evidence
python -m etl.build_formula_modules
python scripts\audit_formula.py
python -m unittest discover -s tests -v
```

## API

- `GET /api/overview`
- `GET /api/formulas?q=&type=&meridian=&book=&status=&review=`
- `GET /api/formulas/{id}`
- `GET /api/herbs?q=&category=`
- `GET /api/herbs/{id}`
- `GET /api/six-channels`
- `GET /api/six-channels/{id}`

方剂详情中的 `source_ingredients` 是原文正文，`ingredients` 是当前整理组成；两者不一致时页面会显示同页校注，不静默覆盖。`evidence.review_status=pending` 表示尚未完成逐方核对。
