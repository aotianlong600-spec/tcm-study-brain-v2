# 中医学习大脑 · 本地方剂模块

这是重新建立的干净仓库，当前只交付方剂模块。数据来自本地倪海厦资料，不接第三方方剂库作为正式内容。

## 当前数据

- 伤寒论辑义：110 首方，全部通过“上X味/右X味”味数校验。
- 倪海厦注神农本草经：351 味药，保留 PDF 页码与分段原文。
- 每首方保留原文行号、组成、剂量、煎服法、校注和版本差异。

金匮方、针灸、辨证论治和病症模块尚未接入。页面会明确显示待接入，不拿第三方数据填充。

## 启动

```powershell
python -m pip install -r requirements.txt
.\run.ps1 -NoBrowser
```

默认地址：`http://127.0.0.1:8768`

## 重建与校验

```powershell
python -m etl.extract_shanghan
python scripts\audit_formula.py
python -m unittest discover -s tests -v
```

## API

- `GET /api/overview`
- `GET /api/formulas?q=&type=&meridian=`
- `GET /api/formulas/{id}`
- `GET /api/herbs?q=&category=`
- `GET /api/herbs/{id}`

方剂详情中的 `source_ingredients` 是原文正文，`ingredients` 是当前整理组成；两者不一致时页面会显示同页校注，不静默覆盖。
