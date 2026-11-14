# V2 统一来源目录（docs/SOURCE_REGISTRY.md）

本文件由 `python -m etl.source_inventory` 自动生成，对应 `data/source_catalog.json`。

| `source_id` | 名称 | 来源类型 | 格式 | 页数 | 文本层状态 | 相对路径 | SHA-256（前12位） |
|---|---|---|---|---:|---|---|---|
| `ni-bencao-pdf` | 倪海厦注神农本草经 | `collated_transcript` | `pdf` | 154 | `mixed` | `books/ni-haixia-medicine/【倪海厦注解版】倪海厦注神农本草经(清晰版).pdf` | `8159131c89a1` |
| `ni-jinkui-pdf` | 倪海厦人纪系列之金匮要略 | `collated_transcript` | `pdf` | 419 | `clean_digital` | `books/ni-haixia-medicine/【倪海厦注释 】倪海厦人纪系列之金匮要略.pdf` | `9ece46d46c90` |
| `ni-hantang-clinic-notes-pdf` | 倪海厦传统中医跟诊过程（心得） | `lecture_transcript` | `pdf` | 35 | `mixed` | `books/ni-haixia-medicine/【汉唐中医内容】倪海厦传统中医跟诊过程.pdf` | `2bb30b7a29f9` |
| `ni-hantang-articles-cases-pdf` | 倪海厦汉唐中医经典文章医案集 | `collated_transcript` | `pdf` | 383 | `clean_digital` | `books/ni-haixia-medicine/【汉唐中医内容】倪海厦汉唐中医经典文章医案集.pdf` | `d940d48e4513` |
| `ni-jinkui-video-pdf` | 《金匮要略》——倪海厦人纪教程简体整理稿（视频同步文稿） | `video_sync_transcript` | `pdf` | 377 | `clean_digital` | `books/ni-haixia-medicine/【视频同步文稿】《金匮要略》——倪海厦人纪教程简体整理稿.pdf` | `d304834877d6` |
| `ni-neijing-vol1-pdf` | 倪海厦人纪系列《黄帝内经》上册（视频同步文稿） | `video_sync_transcript` | `pdf` | 152 | `mixed` | `books/ni-haixia-medicine/【视频同步文稿】倪海厦人纪系列书籍之《皇帝内经上册》 .pdf` | `a2708f2828b9` |
| `ni-neijing-vol2-pdf` | 倪海厦人纪系列《黄帝内经》下册（视频同步文稿） | `video_sync_transcript` | `pdf` | 154 | `mixed` | `books/ni-haixia-medicine/【视频同步文稿】倪海厦人纪系列书籍之《黄帝内经下册》.pdf` | `30297c7a0ecc` |
| `shanghan-juyi-book-txt` | 伤寒论辑义（本地原始文本） | `classical_edition` | `txt` | — | `plain_text` | `books/ni-haixia-medicine/伤寒论辑义--.txt` | `13fb57424558` |
| `ni-shanghan-pdf` | 倪海厦人纪系列之伤寒论 | `collated_transcript` | `pdf` | 209 | `clean_digital` | `books/ni-haixia-medicine/倪海厦人纪系列之伤寒论.pdf` | `14f74c79021f` |
| `ni-acupuncture-v2-20100703` | 倪海厦人纪系列之针灸教程（校勘转录版） | `collated_transcript` | `pdf` | 216 | `clean_digital` | `books/ni-haixia-medicine/倪海厦人纪系列之针灸教程.pdf` | `9ee42f24f983` |
| `ni-hantang-formulas-pdf` | 汉唐中医方剂讲解 | `lecture_transcript` | `pdf` | 235 | `clean_digital` | `books/ni-haixia-medicine/倪海夏-汉唐中医方剂讲解.pdf` | `52af76b122ad` |
| `otsuka-shanghan-docx` | 大冢敬节《伤寒论解说》摘录 | `collated_transcript` | `docx` | — | `uninspected` | `books/ni-haixia-medicine/大冢敬节伤寒论解说(1).docx` | `dcb898e87b31` |
| `xu-lingtai-collection-pdf` | 明清名医全书大成·徐灵胎医学全书 | `classical_edition` | `pdf` | 434 | `image_only` | `books/ni-haixia-medicine/明清名医全书大成(徐灵胎医学全书 ).pdf` | `031a8d91a0ac` |
| `chen-shiduo-shishimilu-txt` | 石室秘录 | `classical_edition` | `txt` | — | `plain_text` | `books/ni-haixia-medicine/石室秘录-清-陈士铎.txt` | `a71413ddccf4` |
| `tang-rongchuan-xuezhenglun-pdf` | 血证论 | `classical_edition` | `pdf` | 170 | `mixed` | `books/ni-haixia-medicine/血证论-唐容川.pdf` | `2781a89e0283` |
| `wang-rulin-zhengyinfanglun-doc` | 证因方论集要 | `classical_edition` | `doc` | — | `uninspected` | `books/ni-haixia-medicine/证因方论集要-汪汝麟.doc` | `9fb06638c40a` |
| `huangdi-waijing-pdf` | 黄帝外经 | `classical_edition` | `pdf` | 85 | `image_only` | `books/ni-haixia-medicine/黄帝外经.pdf` | `b8b6647b0d24` |
| `jinkui-recipes-snapshot` | 金匮要略 186 条方剂抽取快照 | `structured_snapshot` | `json` | — | `structured_data` | `sources/jinkui_recipes_source.json` | `5b427ad8350b` |
| `ni-jinkui-pages-jsonl` | 倪海厦注金匮要略 PDF 页级文本快照 | `structured_snapshot` | `jsonl` | — | `structured_data` | `sources/ni_jinkui_pages.jsonl` | `4dfc166292d6` |
| `ni-jinkui-video-jsonl` | 《金匮要略》视频同步文稿页级文本快照 | `structured_snapshot` | `jsonl` | — | `structured_data` | `sources/ni_jinkui_transcript.jsonl` | `eacc1170e54f` |
| `ni-shanghan-pages-jsonl` | 倪海厦人纪系列之伤寒论 PDF 页级文本快照 | `structured_snapshot` | `jsonl` | — | `structured_data` | `sources/ni_shanghan_pages.jsonl` | `1cab66bf87b4` |
| `shanghan-juyi-snapshot` | 伤寒论辑义（仓库抽取底本） | `classical_edition` | `txt` | — | `plain_text` | `sources/shanghan_juyi.txt` | `13fb57424558` |
| `ni-bencao-351-snapshot` | 倪海厦注神农本草经 351 味药结构化快照 | `structured_snapshot` | `json` | — | `structured_data` | `data/herbs.json` | `d83f278f603e` |
