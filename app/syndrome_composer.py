"""Deterministic clinical syndrome decomposition, pulse-weighted Jingfang compound composition,
and meridian-acupoint reasoning engine (Stage 5 Clinical Differentiation + AI Hook).
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

from ai.grounded_study import _detect_safety_boundary
from app import acupuncture_diagnose, formula_diagnose
from retrieval.index import norm_simp, search_library_pages, tokenize_query


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


PULSE_OPTIONS: list[dict[str, Any]] = [
    {"id": "沉", "label": "脉沉", "axis": "interior", "note": "病位在里（太阴、少阴、厥阴或里水瘀结）"},
    {"id": "微细", "label": "脉微细", "axis": "yin_def_yang_weak", "note": "少阴气血阴阳俱虚、阳气衰微之核心脉象"},
    {"id": "迟", "label": "脉迟", "axis": "cold", "note": "里寒阳虚、营卫气血运行迟滞（亦须分阳明实热腑阻偶见沉迟）"},
    {"id": "弦", "label": "脉弦", "axis": "shaoyang_water", "note": "主少阳枢机不利、肝胆郁滞、或饮停心下胸胁"},
    {"id": "紧", "label": "脉紧", "axis": "cold_excess", "note": "主表寒束表、寒饮痛剧或寒凝经脉"},
    {"id": "浮", "label": "脉浮", "axis": "exterior", "note": "病邪在表（太阳中风浮缓 / 伤寒浮紧 / 或虚阳外越浮大无根）"},
    {"id": "缓", "label": "脉缓", "axis": "wind_def", "note": "太阳中风营卫失调（发热汗出恶风）"},
    {"id": "滑", "label": "脉滑", "axis": "phlegm_heat", "note": "痰饮停蓄、胃肠宿食或阳明里热充盛"},
    {"id": "数", "label": "脉数", "axis": "heat", "note": "热邪偏旺、阴虚内热或热毒逼血"},
    {"id": "洪大", "label": "脉洪大", "axis": "yangming_heat", "note": "阳明经分热盛（大热大汗大烦渴）"},
    {"id": "涩", "label": "脉细涩", "axis": "blood_stasis_def", "note": "血虚津少、冲任寒凝或下焦瘀血阻滞"},
    {"id": "结代", "label": "脉结代", "axis": "heart_def", "note": "心动悸（脉律不齐），需先辨心阳心血不足或高危心律急症"},
]

QUICK_SYMPTOM_PILLS: list[dict[str, str]] = [
    {"label": "身冷", "token": "身冷"},
    {"label": "脚冷", "token": "脚冷"},
    {"label": "眩晕", "token": "眩晕"},
    {"label": "但头汗出", "token": "但头汗出"},
    {"label": "小便不利", "token": "小便不利"},
    {"label": "往来寒热", "token": "往来寒热"},
    {"label": "腹痛", "token": "腹痛"},
    {"label": "痛经", "token": "痛经"},
    {"label": "习惯性便秘", "token": "习惯性便秘"},
    {"label": "大便干", "token": "大便干"},
    {"label": "胸痹短气", "token": "胸痹 短气"},
    {"label": "心下痞呕", "token": "心下痞 呕吐"},
    {"label": "自汗恶风", "token": "发热 汗出 恶风"},
    {"label": "无汗恶寒", "token": "无汗 恶寒"},
    {"label": "口苦咽干", "token": "口苦 咽干"},
    {"label": "下利清谷", "token": "下利清谷"},
    {"label": "失眠心烦", "token": "失眠 心烦"},
    {"label": "咳嗽白痰", "token": "咳嗽 白痰"},
    {"label": "夜尿频多", "token": "夜尿多"},
    {"label": "关节痛", "token": "关节痛"},
]

PRESET_CASES: list[dict[str, Any]] = [
    {
        "id": "case:zhenwu-danggui",
        "title": "示范A：身冷脚冷眩晕 + 腹痛痛经大便干（合方示范）",
        "symptoms": "身冷，脚冷，眩晕，习惯性便秘，腹痛，大便干，痛经",
        "pulse": "沉 微细 涩",
        "note": "对比示范组1：少阴阳虚水寒（真武汤轴）兼肝脾血虚湿滞胞宫冲任（当归芍药散轴），脉沉微细则拒寒凉泻下而辨津血冷秘。",
    },
    {
        "id": "case:zhenwu-chaihu-guizhi-ganjiang",
        "title": "示范B：改见但头汗出+小便不利+往来寒热（动态变方示范）",
        "symptoms": "身冷，脚冷，眩晕，但头汗出，小便不利，往来寒热",
        "pulse": "沉 弦 微细",
        "note": "对比示范组2：保留少阴水寒轴，改兼《伤寒》147条但头汗出、小便不利、往来寒热少阳太阴枢机证，自动转合【真武汤 合 柴胡桂枝干姜汤】。",
    },
    {
        "id": "case:xiongbi-xintong",
        "title": "示范C：胸痹心痛彻背短气 + 心悸不得卧",
        "symptoms": "胸痛，短气，心痛彻背，不得卧，心悸",
        "pulse": "沉 迟 弦",
        "note": "阳微阴弦胸痹痰瘀痹阻，合方与内关/膻中/巨阙配穴并出。",
    },
    {
        "id": "case:taiyang-yangming-shaoyang",
        "title": "示范D：发热无汗项背强 + 口苦心烦呕吐",
        "symptoms": "发热，无汗，恶寒，项背强，口苦，心烦，呕吐",
        "pulse": "浮 紧 弦",
        "note": "太阳伤寒兼少阳（太少合病 / 葛根与柴胡桂枝系统鉴别）。",
    },
]

# Synonym normalizer -> canonical symptom tags
SYMPTOM_CANONICAL_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("身冷", ("身冷", "怕冷", "畏寒", "恶寒", "背恶寒", "身体冷", "全身发冷")),
    ("脚冷", ("脚冷", "手脚冰冷", "四肢厥冷", "厥逆", "足冷", "膝盖冷", "手足寒", "脚凉")),
    ("眩晕", ("眩晕", "头晕", "头眩", "站立不稳", "欲仆地", "眼花", "美尼尔")),
    ("但头汗出", ("但头汗出", "头汗", "只有头出汗", "头汗出")),
    ("小便不利", ("小便不利", "尿少", "小便少", "小便不畅", "浮肿", "水肿", "蓄水")),
    ("往来寒热", ("往来寒热", "寒热往来", "忽冷忽热", "时冷时热")),
    ("痛经", ("痛经", "经痛", "行经腹痛", "月经痛", "经水不调", "经闭", "血块")),
    ("腹痛", ("腹痛", "肚子痛", "小腹痛", "少腹痛", "腹中㽲痛", "绕脐痛", "少腹急结")),
    ("习惯性便秘", ("习惯性便秘", "长期便秘", "便秘", "排便困难")),
    ("大便干", ("大便干", "大便硬", "大便干结", "大便难", "燥屎", "羊屎", "不大便")),
    ("下利清谷", ("下利清谷", "腹泻", "泄泻", "拉肚子", "稀水便", "五更泻")),
    ("发热", ("发热", "发烧", "身热", "壮热", "潮热")),
    ("有汗", ("有汗", "自汗", "汗出", "恶风", "盗汗")),
    ("无汗", ("无汗", "不出汗", "表实")),
    ("项背强", ("项背强", "项强", "脖子僵", "颈项强")),
    ("口苦", ("口苦", "胸胁苦满", "胁痛", "两胁胀")),
    ("咽干", ("咽干", "口燥咽干", "咽痛")),
    ("口渴", ("口渴", "大渴", "烦渴", "欲饮水", "渴而不呕", "消渴")),
    ("呕吐", ("呕吐", "干呕", "恶心", "喜呕", "反胃", "吐涎沫")),
    ("心悸", ("心悸", "心动悸", "心跳快", "心跳不齐", "脐下悸")),
    ("胸痹", ("胸痹", "胸痛", "胸闷", "心痛彻背", "背痛彻心", "短气")),
    ("心下痞", ("心下痞", "胃胀", "心下闷", "痞满", "胃痛")),
    ("心烦失眠", ("心烦", "失眠", "不得卧", "睡不着", "懊憹", "多梦")),
    ("咳喘痰多", ("咳嗽", "咳喘", "哮喘", "白痰", "黄痰", "痰多", "不得平卧")),
    ("头痛", ("头痛", "偏头痛", "巅顶痛", "前额痛", "头疼")),
    ("失血", ("吐血", "鼻衄", "便血", "先便后血", "崩漏", "下血")),
    ("关节痹痛", ("风湿", "历节", "关节痛", "膝痛", "腿肿")),
    ("夜尿多", ("夜尿多", "夜尿频数", "夜尿", "小便频数", "小便反多")),
    ("口不渴", ("口不渴", "不欲饮", "不渴")),
    ("耳鸣", ("耳鸣", "耳聋")),
    ("黄疸", ("黄疸", "发黄", "身目黄", "胆结石", "胆囊痛")),
    ("鼻症", ("鼻炎", "过敏性鼻炎", "鼻息肉", "鼻塞", "流涕", "鼻窦炎", "打喷嚏")),
    ("面瘫", ("面瘫", "面部中风", "口眼歪斜", "嘴角歪")),
    ("水肿", ("水肿", "浮肿", "腹水", "肺积水", "胸腔积液")),
    ("咽喉肿痛", ("喉咙痛", "咽痛", "扁桃腺", "咽喉痛", "梅核气")),
    ("带下崩漏", ("白带", "赤白带", "赤带", "崩漏", "经血不止")),
]

CLINICAL_ENTRY_CARDS: list[dict[str, Any]] = [
    {
        "id": "entry:exterior-cold",
        "title": "外感发热 / 太阳表证",
        "subtitle": "伤寒太阳 · 桂枝/麻黄/葛根汤轴",
        "tokens": ["恶寒", "发热", "无汗", "有汗", "项背强"],
        "default_query": "发热 无汗 恶寒 项背强",
        "formulas_hint": "桂枝汤 / 麻黄汤 / 葛根汤",
    },
    {
        "id": "entry:shaoyang",
        "title": "少阳寒热 / 胸胁口苦",
        "subtitle": "少阳枢机 · 小柴胡/柴桂干姜轴",
        "tokens": ["往来寒热", "口苦", "咽干", "但头汗出", "小便不利"],
        "default_query": "往来寒热 口苦 咽干",
        "formulas_hint": "小柴胡汤 / 柴胡桂枝干姜汤",
    },
    {
        "id": "entry:headache",
        "title": "头痛 / 偏头痛 / 眩晕",
        "subtitle": "《针灸》头部治症 · 厥阴/少阳",
        "tokens": ["头痛", "偏头痛", "前额痛", "眩晕", "呕吐"],
        "default_query": "头痛 眩晕 呕吐",
        "formulas_hint": "吴茱萸汤 / 苓桂术甘汤 / 五苓散",
    },
    {
        "id": "entry:chest-heart",
        "title": "胸痹心痛 / 心悸心律",
        "subtitle": "《金匮》胸痹 · 《针灸》心脏治症",
        "tokens": ["胸痹", "胸痛", "心痛彻背", "短气", "心悸"],
        "default_query": "胸痛 短气 心痛彻背 心悸",
        "formulas_hint": "栝蒌薤白半夏汤 / 炙甘草汤",
    },
    {
        "id": "entry:lung-cough",
        "title": "咳嗽哮喘 / 痰饮积水",
        "subtitle": "肺症虚实 · 《针灸》肺积水",
        "tokens": ["咳嗽", "白痰", "黄痰", "咳喘痰多", "水肿"],
        "default_query": "咳嗽 白痰 咳喘痰多",
        "formulas_hint": "小青龙汤 / 麻杏石甘汤 / 十枣汤",
    },
    {
        "id": "entry:stomach",
        "title": "胃痛痞满 / 呕吐反胃",
        "subtitle": "脾肿大与胃病 · 朝食暮吐",
        "tokens": ["心下痞", "胃痛", "呕吐", "反胃", "口不渴"],
        "default_query": "心下痞 呕吐 胃痛",
        "formulas_hint": "半夏泻心汤 / 理中丸 / 旋覆代赭汤",
    },
    {
        "id": "entry:abdomen",
        "title": "腹痛肠痈 / 奔豚气冲",
        "subtitle": "《针灸》盲肠奔豚 · 太阴寒滞",
        "tokens": ["腹痛", "少腹痛", "右下腹痛", "身冷"],
        "default_query": "腹痛 少腹痛",
        "formulas_hint": "小建中汤 / 大黄牡丹汤 / 桂枝加桂汤",
    },
    {
        "id": "entry:constipation",
        "title": "便秘便干 / 寒实与阳明",
        "subtitle": "《针灸》大肠虚实 · 冷秘 vs 燥屎",
        "tokens": ["习惯性便秘", "大便干", "身冷", "脚冷"],
        "default_query": "习惯性便秘 大便干",
        "formulas_hint": "大承气汤 / 麻子仁丸 / 真武汤",
    },
    {
        "id": "entry:diarrhea",
        "title": "下利泄泻 / 霍乱吐利",
        "subtitle": "少阴太阴虚寒 · 协热下利",
        "tokens": ["下利清谷", "腹泻", "口不渴", "身冷"],
        "default_query": "下利清谷 腹泻",
        "formulas_hint": "四逆汤 / 理中丸 / 葛根芩连汤",
    },
    {
        "id": "entry:shaoyin-urinary",
        "title": "身冷脚冷 / 夜尿水不利",
        "subtitle": "少阴肾阳气化 · 五苓与真武",
        "tokens": ["身冷", "脚冷", "眩晕", "小便不利", "夜尿多"],
        "default_query": "身冷 脚冷 眩晕 小便不利",
        "formulas_hint": "真武汤 / 肾气丸 / 五苓散",
    },
    {
        "id": "entry:insomnia",
        "title": "心烦失眠 / 癫狂神志",
        "subtitle": "十三鬼穴 · 心肾不交",
        "tokens": ["失眠", "心烦", "不得卧", "心悸"],
        "default_query": "失眠 心烦 不得卧",
        "formulas_hint": "酸枣仁汤 / 黄连阿胶汤 / 栀子豉汤",
    },
    {
        "id": "entry:gynecology",
        "title": "痛经崩漏 / 赤白带下",
        "subtitle": "《针灸》妇科经带 · 金匮妇人",
        "tokens": ["痛经", "腹痛", "脚冷", "赤白带", "崩漏"],
        "default_query": "痛经 腹痛 脚冷",
        "formulas_hint": "当归芍药散 / 温经汤 / 桂枝茯苓丸",
    },
    {
        "id": "entry:bleeding",
        "title": "吐血衄血 / 痔疮便血",
        "subtitle": "《针灸》血症肠风 · 先血先便",
        "tokens": ["吐血", "鼻衄", "便血", "痔疮", "失血"],
        "default_query": "便血 吐血 鼻衄",
        "formulas_hint": "黄土汤 / 柏叶汤 / 泻心汤",
    },
    {
        "id": "entry:metabolic-liver",
        "title": "消渴引饮 / 黄疸胆结石",
        "subtitle": "《针灸》消渴与肝胆治症",
        "tokens": ["消渴", "口渴", "黄疸", "胆结石", "口苦"],
        "default_query": "消渴 口渴 黄疸",
        "formulas_hint": "白虎加人参汤 / 肾气丸 / 茵陈蒿汤",
    },
    {
        "id": "entry:ent",
        "title": "耳鸣鼻炎 / 喉症面瘫",
        "subtitle": "《针灸》五官头面专病",
        "tokens": ["耳鸣", "过敏性鼻炎", "鼻塞", "咽喉痛", "面瘫"],
        "default_query": "耳鸣 过敏性鼻炎 鼻塞",
        "formulas_hint": "麻黄附子细辛汤 / 葛根汤 / 半夏散",
    },
    {
        "id": "entry:arthritis",
        "title": "风湿历节 / 关节痹痛",
        "subtitle": "桂枝附子 / 历节痛风",
        "tokens": ["关节痛", "风湿", "腿肿", "身冷"],
        "default_query": "关节痛 风湿",
        "formulas_hint": "桂枝芍药知母汤 / 乌头汤 / 麻杏苡甘汤",
    },
]

# Classic Pattern Atoms (with strict verifiable formula IDs and classic clinical logic)
PATTERN_ATOMS: list[dict[str, Any]] = [
    {
        "atom_id": "atom:zhenwu",
        "formula_id": "shanghan:真武汤",
        "name": "真武汤",
        "six_meridian": "少阴病 · 阳虚水泛轴",
        "pathogenesis": "少阴肾阳衰微，不能温煦四肢百骸（身冷脚冷），水邪停蓄上泛（头眩、心下悸、小便不利或腹痛自利）。",
        "symptom_weights": {"身冷": 16, "脚冷": 18, "眩晕": 16, "小便不利": 12, "腹痛": 8, "心悸": 10, "下利清谷": 12},
        "boost_pulses": {"沉": 10, "微细": 14, "迟": 8},
        "conflict_pulses": {"洪大": -22, "数": -12},
        "conflict_symptoms": {"发热": -6},
        "acupoints": [
            {"id": "acupoint:ren04:关元", "name": "关元", "role": "主穴（宜灸）", "reason": "培元固本、温壮少阴下焦元阳，治身冷脚冷水寒上泛"},
            {"id": "acupoint:ki03:太溪", "name": "太溪", "role": "主穴（补法/灸）", "reason": "足少阴肾经原穴，交通水火、温肾利水定眩"},
            {"id": "acupoint:sp09:阴陵泉", "name": "阴陵泉", "role": "配穴", "reason": "健脾渗湿利小便，佐真武分消停蓄之水邪"},
            {"id": "acupoint:ki07:复溜", "name": "复溜", "role": "配穴", "reason": "补肾阳、通利下焦水道、调节汗水代谢"},
        ],
    },
    {
        "atom_id": "atom:danggui-shaoyao",
        "formula_id": "jinkui:当归芍药散",
        "name": "当归芍药散",
        "six_meridian": "太阴厥阴妇科 · 血虚肝郁夹湿胞宫痛经轴",
        "pathogenesis": "《金匮·妇人》主方：脾土虚寒水湿内停，兼肝血不足冲任涩滞，见妇人腹中㽲痛、痛经、眩晕手足不温，兼津血不濡肠窍而现虚性大便干。",
        "symptom_weights": {"痛经": 26, "腹痛": 14, "眩晕": 10, "脚冷": 8, "大便干": 10, "习惯性便秘": 8, "身冷": 6, "小便不利": 6},
        "boost_pulses": {"沉": 6, "微细": 10, "涩": 14, "弦": 8},
        "conflict_pulses": {"洪大": -18},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "主穴", "reason": "肝脾肾三阴交会，调冲任止痛经兼健脾除湿、养血润肠"},
            {"id": "acupoint:sp10:血海", "name": "血海", "role": "配穴", "reason": "理血活血，统调经水与胞宫血室瘀滞腹痛"},
            {"id": "acupoint:sp08:地机", "name": "地机", "role": "配穴", "reason": "足太阴脾经郄穴，急性与周期性痛经要穴"},
            {"id": "acupoint:st36:足三里", "name": "足三里", "role": "配穴", "reason": "健运中土气血生化之源，配合三阴交化湿定眩"},
        ],
    },
    {
        "atom_id": "atom:chaihu-guizhi-ganjiang",
        "formula_id": "shanghan:柴胡桂枝干姜汤",
        "name": "柴胡桂枝干姜汤",
        "six_meridian": "少阳枢机兼太阴津郁 · 《伤寒》147条专轴",
        "pathogenesis": "《伤寒》明文：“胸胁满微结，小便不利，渴而不呕，但头汗出，往来寒热，心烦者，此为未解也，柴胡桂枝干姜汤主之。”枢机郁热不得下达而单上蒸作头汗，同时中焦脾虚阴寒不运（干姜配栝蒌根、牡蛎）。",
        "symptom_weights": {"但头汗出": 28, "往来寒热": 24, "小便不利": 16, "口苦": 10, "口渴": 8, "身冷": 6, "心烦失眠": 6},
        "pair_bonus": [("但头汗出", "往来寒热", 18), ("但头汗出", "小便不利", 14), ("往来寒热", "小便不利", 10)],
        "boost_pulses": {"弦": 14, "沉": 8, "微细": 8},
        "conflict_pulses": {"洪大": -12},
        "conflict_symptoms": {"无汗": -8},
        "acupoints": [
            {"id": "acupoint:lv14:期门", "name": "期门", "role": "主穴", "reason": "肝募兼入少阳厥阴交关，解胸胁满微结与寒热往来"},
            {"id": "acupoint:gb34:阳陵泉", "name": "阳陵泉", "role": "主穴", "reason": "胆经合穴，疏泄少阳胆腑枢机不利"},
            {"id": "acupoint:sj05:外关", "name": "外关", "role": "配穴", "reason": "手少阳三焦经络穴，宣通三焦水道、解往来寒热但头汗"},
            {"id": "acupoint:sp09:阴陵泉", "name": "阴陵泉", "role": "配穴", "reason": "复三焦脾运化水湿，助小便不利通调"},
        ],
    },
    {
        "atom_id": "atom:wenjing",
        "formula_id": "jinkui:温经汤",
        "name": "温经汤",
        "six_meridian": "妇人虚寒瘀滞 · 下寒兼上虚热",
        "pathogenesis": "冲任虚寒（身冷脚冷、痛经瘀块）兼瘀久微化虚热（手心烦热、口唇干）。",
        "symptom_weights": {"痛经": 20, "脚冷": 10, "身冷": 8, "腹痛": 8, "咽干": 8},
        "boost_pulses": {"涩": 10, "沉": 6, "迟": 6},
        "conflict_pulses": {"洪大": -16},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren04:关元", "name": "关元", "role": "主穴（宜灸）", "reason": "温煦冲任下元"},
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "主穴", "reason": "理肝脾肾经血"},
        ],
    },
    {
        "atom_id": "atom:maziren",
        "formula_id": "shanghan:麻子仁丸",
        "name": "麻子仁丸",
        "six_meridian": "阳明脾约 · 津亏大便硬便秘",
        "pathogenesis": "胃热津耗、脾不为胃行津液，致习惯性大便硬如羊屎；若全身兼明显身冷脚冷脉沉微，须防苦寒泻下伤阳！",
        "symptom_weights": {"习惯性便秘": 16, "大便干": 16},
        "pair_bonus": [("习惯性便秘", "大便干", 10)],
        "boost_pulses": {"数": 8, "滑": 6},
        "conflict_pulses": {"微细": -12, "迟": -10},
        "conflict_symptoms": {"身冷": -10, "脚冷": -10, "下利清谷": -20},
        "acupoints": [
            {"id": "acupoint:st25:天枢", "name": "天枢", "role": "主穴", "reason": "大肠募穴，调理大肠传导之腑气"},
            {"id": "acupoint:sj06:支沟", "name": "支沟", "role": "配穴", "reason": "三焦经经穴，古传专治习惯性便秘与大便干难"},
            {"id": "acupoint:ki06:照海", "name": "照海", "role": "配穴", "reason": "配支沟“支沟照海通大便”（尤其虚燥津亏便干）"},
        ],
    },
    {
        "atom_id": "atom:xiaochaihu",
        "formula_id": "shanghan:小柴胡汤",
        "name": "小柴胡汤",
        "six_meridian": "少阳经病 · 半表半里枢机主方",
        "pathogenesis": "正邪分争少阳胆与三焦，但见往来寒热、胸胁苦满、口苦咽干目眩、心烦喜呕一证便是。",
        "symptom_weights": {"往来寒热": 18, "口苦": 16, "呕吐": 12, "咽干": 8, "心烦失眠": 8, "头痛": 6},
        "boost_pulses": {"弦": 14},
        "conflict_pulses": {},
        "conflict_symptoms": {"但头汗出": -4},
        "acupoints": [
            {"id": "acupoint:sj05:外关", "name": "外关", "role": "主穴", "reason": "和解少阳三焦气机"},
            {"id": "acupoint:gb34:阳陵泉", "name": "阳陵泉", "role": "主穴", "reason": "清泄胆热、利胸胁苦满"},
            {"id": "acupoint:lv14:期门", "name": "期门", "role": "配穴", "reason": "兼热入血室或胸胁胀满加刺期门"},
        ],
    },
    {
        "atom_id": "atom:guizhi",
        "formula_id": "shanghan:桂枝汤",
        "name": "桂枝汤",
        "six_meridian": "太阳表虚中风 · 调和营卫",
        "pathogenesis": "卫阳外浮、营阴外泄，见发热、汗出、恶风、脉浮缓。",
        "symptom_weights": {"发热": 12, "有汗": 20, "头痛": 6},
        "pair_bonus": [("发热", "有汗", 14)],
        "boost_pulses": {"浮": 12, "缓": 14},
        "conflict_pulses": {"紧": -10, "洪大": -10},
        "conflict_symptoms": {"无汗": -18, "但头汗出": -10},
        "acupoints": [
            {"id": "acupoint:gb20:风池", "name": "风池", "role": "主穴", "reason": "祛太阳风邪、止头项疼痛"},
            {"id": "acupoint:lu07:列缺", "name": "列缺", "role": "配穴", "reason": "宣肺解肌、疏泄后项头部风邪"},
            {"id": "acupoint:li04:合谷", "name": "合谷", "role": "配穴", "reason": "调和营卫气血，固表解肌"},
        ],
    },
    {
        "atom_id": "atom:gegengtang",
        "formula_id": "shanghan:葛根汤",
        "name": "葛根汤",
        "six_meridian": "太阳表实兼项背强 · 无汗恶寒",
        "pathogenesis": "太阳寒实束表无汗而津液不能上输阳明太阳经脉，故项背强几几。",
        "symptom_weights": {"项背强": 24, "无汗": 16, "身冷": 8, "发热": 8},
        "pair_bonus": [("项背强", "无汗", 14)],
        "boost_pulses": {"浮": 10, "紧": 14},
        "conflict_pulses": {"缓": -10},
        "conflict_symptoms": {"有汗": -16},
        "acupoints": [
            {"id": "acupoint:du14:大椎", "name": "大椎", "role": "主穴", "reason": "手足三阳与督脉交会，退表热解项强"},
            {"id": "acupoint:gb20:风池", "name": "风池", "role": "主穴", "reason": "松解项背肌肉痉挛"},
            {"id": "acupoint:si03:后溪", "name": "后溪", "role": "配穴", "reason": "通督脉，专治颈项强痛不能回顾"},
        ],
    },
    {
        "atom_id": "atom:wuling",
        "formula_id": "shanghan:五苓散",
        "name": "五苓散",
        "six_meridian": "太阳蓄水 · 膀胱气化不利",
        "pathogenesis": "膀胱气化不行致小便不利，津不上承则口渴欲饮水或水入即吐。",
        "symptom_weights": {"小便不利": 18, "口渴": 14, "眩晕": 8, "心悸": 6},
        "pair_bonus": [("小便不利", "口渴", 16)],
        "boost_pulses": {"浮": 6},
        "conflict_pulses": {},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren09:水分", "name": "水分", "role": "主穴（宜灸）", "reason": "分利水谷、治一切水肿水逆小便不利"},
            {"id": "acupoint:sp09:阴陵泉", "name": "阴陵泉", "role": "主穴", "reason": "健脾化气利小便"},
        ],
    },
    {
        "atom_id": "atom:xiongbi",
        "formula_id": "jinkui:栝蒌薤白白酒汤",
        "name": "栝蒌薤白白酒汤",
        "six_meridian": "金匮胸痹心痛 · 阳微阴弦",
        "pathogenesis": "胸阳不振而痰浊阴邪上乘胸膈，见胸痛彻背、短气喘息。",
        "symptom_weights": {"胸痹": 28, "咳喘痰多": 8, "心悸": 8},
        "boost_pulses": {"沉": 8, "迟": 8, "弦": 6},
        "conflict_pulses": {"洪大": -12},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:pc06:内关", "name": "内关", "role": "主穴", "reason": "宣通心脉、宽胸定痛（配公孙主胸腹诸疾）"},
            {"id": "acupoint:ren17:膻中", "name": "膻中", "role": "主穴", "reason": "气会膻中，宽胸散结、通心阳短气"},
            {"id": "acupoint:ren14:巨阙", "name": "巨阙", "role": "主穴", "reason": "心之募穴，治心痛彻背胸痹急证"},
        ],
    },
    {
        "atom_id": "atom:sini",
        "formula_id": "shanghan:四逆汤",
        "name": "四逆汤",
        "six_meridian": "少阴回阳救逆 · 亡阳厥逆",
        "pathogenesis": "少阴肾阳衰极、下利清谷、四肢厥冷、脉微欲绝。",
        "symptom_weights": {"下利清谷": 20, "脚冷": 16, "身冷": 14},
        "pair_bonus": [("下利清谷", "脚冷", 14)],
        "boost_pulses": {"微细": 16, "迟": 10},
        "conflict_pulses": {"洪大": -25, "数": -15},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren04:关元", "name": "关元", "role": "急救灸穴", "reason": "隔盐隔姜重灸关元回阳固脱"},
            {"id": "acupoint:ren06:气海", "name": "气海", "role": "配穴（宜灸）", "reason": "益原气、温脾肾"},
        ],
    },
    {
        "atom_id": "atom:lizhong",
        "formula_id": "shanghan:理中丸",
        "name": "理中丸",
        "six_meridian": "太阴中焦虚寒 · 寒多吐利腹痛",
        "pathogenesis": "脾胃虚寒不运，腹痛喜温、食不下、呕吐泄泻、口不渴。",
        "symptom_weights": {"腹痛": 10, "下利清谷": 14, "呕吐": 10, "身冷": 8},
        "boost_pulses": {"沉": 8, "迟": 8, "缓": 6},
        "conflict_pulses": {"洪大": -20, "数": -10},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren12:中脘", "name": "中脘", "role": "主穴", "reason": "胃募腑会，温运中焦脾胃"},
            {"id": "acupoint:st36:足三里", "name": "足三里", "role": "主穴", "reason": "升清降浊、固护胃气"},
            {"id": "acupoint:bl20:脾俞", "name": "脾俞", "role": "配穴", "reason": "温补脾阳"},
        ],
    },
    {
        "atom_id": "atom:xiaoqinglong",
        "formula_id": "shanghan:小青龙汤",
        "name": "小青龙汤",
        "six_meridian": "外寒内饮射肺 · 喘咳白沫痰",
        "pathogenesis": "太阳伤寒不解而心下有水气上冲犯肺，咳嗽喘急白沫痰。",
        "symptom_weights": {"咳喘痰多": 22, "无汗": 10, "身冷": 8},
        "boost_pulses": {"浮": 8, "紧": 10, "弦": 8},
        "conflict_pulses": {},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:lu05:尺泽", "name": "尺泽", "role": "主穴", "reason": "肺经合穴泻肺实平喘降逆"},
            {"id": "acupoint:bl13:肺俞", "name": "肺俞", "role": "主穴", "reason": "宣通肺气、化背寒伏饮"},
            {"id": "acupoint:st40:丰隆", "name": "丰隆", "role": "配穴", "reason": "化痰要穴，蠲化心下胸膈顽痰"},
        ],
    },
    {
        "atom_id": "atom:dachengqi",
        "formula_id": "shanghan:大承气汤",
        "name": "大承气汤",
        "six_meridian": "阳明腑实燥热 · 痞满燥实",
        "pathogenesis": "阳明胃家实热与燥屎搏结（日晡潮热、腹满硬痛、大便硬结、脉沉实洪滑）。切忌用于身冷脉微细虚寒便干！",
        "symptom_weights": {"大便干": 14, "习惯性便秘": 10, "腹痛": 8, "发热": 10},
        "boost_pulses": {"滑": 14, "数": 12, "洪大": 12},
        "conflict_pulses": {"微细": -28, "迟": -18},
        "conflict_symptoms": {"身冷": -22, "脚冷": -22, "下利清谷": -30},
        "acupoints": [
            {"id": "acupoint:st25:天枢", "name": "天枢", "role": "主穴", "reason": "泻阳明大肠实滞"},
            {"id": "acupoint:li04:合谷", "name": "合谷", "role": "主穴", "reason": "阳明原穴清泻腑热"},
        ],
    },
    {
        "atom_id": "atom:suanzaoren",
        "formula_id": "jinkui:酸枣仁汤",
        "name": "酸枣仁汤",
        "six_meridian": "肝血虚热 · 虚烦失眠不得眠",
        "pathogenesis": "肝阴血虚内生虚烦，夜不能寐、心悸多梦。",
        "symptom_weights": {"心烦失眠": 22, "眩晕": 6, "心悸": 8},
        "boost_pulses": {"弦": 8, "数": 6, "涩": 6},
        "conflict_pulses": {},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ht07:神门", "name": "神门", "role": "主穴", "reason": "心经原穴，宁心安神定失眠"},
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "配穴", "reason": "养血滋阴以敛肝魂"},
        ],
    },
    {
        "atom_id": "atom:wuzhuyu",
        "formula_id": "shanghan:吴茱萸汤",
        "name": "吴茱萸汤",
        "six_meridian": "厥阴寒痰浊阴上逆 · 巅顶痛吐涎沫",
        "pathogenesis": "胃寒肝虚浊阴上冲巅顶，头痛、干呕、吐涎沫。",
        "symptom_weights": {"头痛": 18, "呕吐": 14, "脚冷": 8, "身冷": 6},
        "pair_bonus": [("头痛", "呕吐", 16)],
        "boost_pulses": {"沉": 8, "迟": 10},
        "conflict_pulses": {"洪大": -16},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:du20:百会", "name": "百会", "role": "主穴", "reason": "巅顶厥阴督脉汇处"},
            {"id": "acupoint:lv03:太冲", "name": "太冲", "role": "主穴", "reason": "疏降肝胃上冲逆气"},
        ],
    },
    {
        "atom_id": "atom:xiexin-huangtu",
        "formula_id": "jinkui:黄土汤",
        "name": "黄土汤",
        "six_meridian": "脾阳虚寒不摄 · 下血远血",
        "pathogenesis": "脾阳虚弱不能统摄血脉，先便后血、四肢不温。",
        "symptom_weights": {"失血": 24, "身冷": 6, "脚冷": 6},
        "boost_pulses": {"沉": 8, "微细": 10},
        "conflict_pulses": {"洪大": -14},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:sp10:血海", "name": "血海", "role": "主穴", "reason": "养血止血要穴"},
            {"id": "acupoint:bl20:脾俞", "name": "脾俞", "role": "配穴（宜灸）", "reason": "温脾以统血"},
        ],
    },
    {
        "atom_id": "atom:linggui-zhugan",
        "formula_id": "jinkui:苓桂术甘汤",
        "name": "苓桂术甘汤",
        "six_meridian": "太阴痰饮气冲 · 脾虚水饮上凌心肺",
        "pathogenesis": "《伤寒》《金匮》名方：中阳不足而痰饮停聚中焦，上冲作心下逆满、起则头眩、心悸胸胁支满。",
        "symptom_weights": {"眩晕": 14, "心悸": 16, "胸痹": 10, "咳喘痰多": 8, "小便不利": 6},
        "pair_bonus": [("眩晕", "心悸", 14)],
        "boost_pulses": {"沉": 6, "弦": 8, "紧": 8},
        "conflict_pulses": {"洪大": -14},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren12:中脘", "name": "中脘", "role": "主穴", "reason": "健运中土化饮降浊"},
            {"id": "acupoint:pc06:内关", "name": "内关", "role": "主穴", "reason": "定心悸、宽胸理气降冲逆"},
            {"id": "acupoint:st40:丰隆", "name": "丰隆", "role": "配穴", "reason": "化中焦痰饮水浊"},
            {"id": "acupoint:sp09:阴陵泉", "name": "阴陵泉", "role": "配穴", "reason": "渗湿利水通调水道"},
        ],
    },
    {
        "atom_id": "atom:banxia-xiexin",
        "formula_id": "shanghan:半夏泻心汤",
        "name": "半夏泻心汤",
        "six_meridian": "寒热错杂痞证 · 升降失司心下痞呕利",
        "pathogenesis": "中焦脾胃升降失调、寒热互结心下，见心下痞满而不痛、呕吐干呕、肠鸣下利。",
        "symptom_weights": {"心下痞": 26, "呕吐": 14, "下利清谷": 10, "口苦": 6},
        "pair_bonus": [("心下痞", "呕吐", 14)],
        "boost_pulses": {"弦": 6, "滑": 8},
        "conflict_pulses": {},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:ren12:中脘", "name": "中脘", "role": "主穴", "reason": "消痞散结、和胃降逆"},
            {"id": "acupoint:pc06:内关", "name": "内关", "role": "主穴", "reason": "止呕宽胃痞（配公孙主胃心胸）"},
            {"id": "acupoint:st36:足三里", "name": "足三里", "role": "配穴", "reason": "调中州升降、止肠鸣下利"},
            {"id": "acupoint:sp04:公孙", "name": "公孙", "role": "配穴", "reason": "八脉交会通冲脉，配内关治心下痞呕吐"},
        ],
    },
    {
        "atom_id": "atom:sini-san",
        "formula_id": "shanghan:四逆散",
        "name": "四逆散",
        "six_meridian": "少阴阳郁气滞 · 肝脾失调四肢不温",
        "pathogenesis": "阳气内郁不达四末（手足不温而脉弦非微细），常兼胸胁苦满、腹痛、或泄利下重。",
        "symptom_weights": {"口苦": 14, "腹痛": 14, "脚冷": 10, "痛经": 8, "心下痞": 8, "心烦失眠": 6},
        "pair_bonus": [("口苦", "腹痛", 12)],
        "boost_pulses": {"弦": 14},
        "conflict_pulses": {"微细": -14, "迟": -8},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:lv03:太冲", "name": "太冲", "role": "主穴", "reason": "疏肝解郁、达阳气于四末"},
            {"id": "acupoint:gb34:阳陵泉", "name": "阳陵泉", "role": "主穴", "reason": "利少阳肝胆气机、舒筋止胁痛腹痛"},
            {"id": "acupoint:lv14:期门", "name": "期门", "role": "配穴", "reason": "解胸胁苦满肝郁气滞"},
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "配穴", "reason": "柔肝缓急调脾止腹痛"},
        ],
    },
    {
        "atom_id": "atom:shenqi-wan",
        "formula_id": "jinkui:肾气丸",
        "name": "肾气丸",
        "six_meridian": "下焦肾气虚弱 · 腰痛脚弱小便不利或反多",
        "pathogenesis": "《金匮》肾气不足核心方：腰冷脚弱、少腹拘急、小便不利或夜尿反多、耳鸣消渴。",
        "symptom_weights": {"夜尿多": 24, "小便不利": 16, "耳鸣": 14, "脚冷": 10, "身冷": 10, "口渴": 8},
        "pair_bonus": [("夜尿多", "身冷", 12)],
        "boost_pulses": {"沉": 10, "微细": 10, "迟": 6},
        "conflict_pulses": {"洪大": -18},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:bl23:肾俞", "name": "肾俞", "role": "主穴", "reason": "补益肾气、强腰膝定耳鸣"},
            {"id": "acupoint:ren04:关元", "name": "关元", "role": "主穴（宜灸）", "reason": "培补下焦真元、统摄夜尿小便开阖"},
            {"id": "acupoint:ki03:太溪", "name": "太溪", "role": "主穴", "reason": "肾经原穴滋水涵阳"},
            {"id": "acupoint:du04:命门", "name": "命门", "role": "配穴（宜灸）", "reason": "温煦下元肾阳命火"},
        ],
    },
    {
        "atom_id": "atom:guizhi-fuling",
        "formula_id": "jinkui:桂枝茯苓丸",
        "name": "桂枝茯苓丸",
        "six_meridian": "妇人癥瘕瘀血 · 胞宫血瘀腹痛痛经",
        "pathogenesis": "瘀血阻滞胞宫少腹（痛经血块、少腹硬痛、经行不畅、或下血不止）。",
        "symptom_weights": {"痛经": 18, "腹痛": 14, "失血": 8, "小便不利": 6},
        "boost_pulses": {"涩": 12, "弦": 6, "滑": 6},
        "conflict_pulses": {"微细": -10},
        "conflict_symptoms": {},
        "acupoints": [
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "主穴", "reason": "调理冲任胞宫血室瘀滞"},
            {"id": "acupoint:sp10:血海", "name": "血海", "role": "主穴", "reason": "活血化瘀止少腹胞宫痛经"},
            {"id": "acupoint:st29:归来", "name": "归来", "role": "配穴", "reason": "下腹归来直入胞宫散结止痛"},
            {"id": "acupoint:bl32:次髎", "name": "次髎", "role": "配穴", "reason": "八髎调经活血止胞宫瘀痛要穴"},
        ],
    },
    {
        "atom_id": "atom:danggui-sini",
        "formula_id": "shanghan:当归四逆汤",
        "name": "当归四逆汤",
        "six_meridian": "厥阴血虚寒凝 · 手足厥寒关节冷痛",
        "pathogenesis": "《伤寒》厥阴篇：营血不足复感寒邪客于经脉（手足厥寒、脉细欲绝、寒凝痛经或关节冷痛）。",
        "symptom_weights": {"脚冷": 16, "关节痹痛": 16, "痛经": 10, "腹痛": 6, "身冷": 6},
        "pair_bonus": [("脚冷", "关节痹痛", 14)],
        "boost_pulses": {"微细": 12, "涩": 8},
        "conflict_pulses": {"洪大": -20, "数": -12},
        "conflict_symptoms": {"发热": -6},
        "acupoints": [
            {"id": "acupoint:sp06:三阴交", "name": "三阴交", "role": "主穴", "reason": "养阴血、温经散厥阴寒凝"},
            {"id": "acupoint:ren04:关元", "name": "关元", "role": "主穴（宜灸）", "reason": "温经通阳散下焦冲任寒滞"},
            {"id": "acupoint:lv03:太冲", "name": "太冲", "role": "配穴", "reason": "厥阴肝经原穴，养肝血通经脉止厥冷"},
            {"id": "acupoint:st36:足三里", "name": "足三里", "role": "配穴", "reason": "益气养血温运四肢经脉"},
        ],
    },
]


# Curated Clinical Symptom -> Formula/Acupoint Differential Notes (like Constipation in Cold-Yang-Deficiency)
CLINICAL_DIFFERENTIAL_NOTES: list[dict[str, Any]] = [
    {
        "trigger_all": ("习惯性便秘", "身冷"),
        "alt_trigger_all": ("大便干", "脚冷"),
        "title": "【关键鉴别】寒虚（阳虚/血虚）大便干 vs 阳明实热燥屎",
        "explanation": "见「习惯性便秘 / 大便干」却同时伴见「身冷、脚冷、脉沉微细」时，切忌见到便干就误投大承气汤等纯苦寒攻下剂！张仲景与汉唐思路指出：大肠传导全赖脾肾阳气蒸腾与津血濡润。阳虚水停则用真武汤温肾气化；血虚水湿挟胞宫痛经则配当归芍药散养血柔肝兼调肠道津微（白术健脾、当归芍药泽泻同调水湿与血燥）。临床需随大便干甚或虚冷偏重灵活参考温脾/润肠加减法，同时配针灸天枢、支沟、照海通腑气。",
    },
    {
        "trigger_all": ("但头汗出", "往来寒热"),
        "alt_trigger_all": ("但头汗出", "小便不利"),
        "title": "【核心枢纽】《伤寒》147条「但头汗出 + 小便不利 + 往来寒热」合方推演",
        "explanation": "但头汗出（余处无汗）配小便不利、往来寒热，乃少阳三焦枢机瘀郁（热郁上熏于头）同时下焦/中焦阳虚寒滞（水湿不行），正合《伤寒论》第147条「柴胡桂枝干姜汤」专证；若同时兼身冷、脚冷、眩晕少阴肾阳水寒之底色，即自然构成「真武汤 合 柴胡桂枝干姜汤」双轴并发格局。",
    },
    {
        "trigger_all": ("痛经", "腹痛"),
        "alt_trigger_all": ("痛经", "脚冷"),
        "title": "【妇人调经取穴理法】冲任虚寒血滞 vs 肝脾血虚湿郁",
        "explanation": "痛经兼身冷脚冷、眩晕腹痛，经方层以真武汤温少阴肾水之寒、当归芍药散（或兼温经汤）调肝脾血室与水湿；针灸层以「关元、三阴交、血海、地机」为核心轴：下腹寒凝宜灸关元归来，痛甚泻地机与三阴交以迅速通冲任经气。",
    },
]


@lru_cache(maxsize=1)
def _formulas_by_id() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fn in ("formulas.json", "jinkui_formulas.json"):
        for f in json.loads((DATA_DIR / fn).read_text(encoding="utf-8")):
            out[f["id"]] = f
    return out


@lru_cache(maxsize=1)
def _curated_batches_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    cb_dir = DATA_DIR / "curated_batches"
    if cb_dir.exists():
        for p in sorted(cb_dir.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out.update(data)
    return out


@lru_cache(maxsize=1)
def _modifications_index() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    path = DATA_DIR / "formula_modifications.json"
    items = json.loads(path.read_text(encoding="utf-8")).get("items", []) if path.exists() else []
    by_fid: dict[str, list[dict[str, Any]]] = {}
    for m in items:
        bfid = m.get("base_formula_id")
        if bfid:
            by_fid.setdefault(bfid, []).append(m)
    return items, by_fid


@lru_cache(maxsize=1)
def _fa_links_by_formula() -> dict[str, list[dict[str, Any]]]:
    path = DATA_DIR / "formula_acupuncture_links.json"
    items = json.loads(path.read_text(encoding="utf-8")).get("items", []) if path.exists() else []
    by_fid: dict[str, list[dict[str, Any]]] = {}
    for lk in items:
        fid = lk.get("formula_id")
        if fid:
            by_fid.setdefault(fid, []).append(lk)
    return by_fid


@lru_cache(maxsize=1)
def _acupoints_by_id() -> dict[str, dict[str, Any]]:
    path = DATA_DIR / "acupuncture" / "acupoints.json"
    items = json.loads(path.read_text(encoding="utf-8")).get("items", []) if path.exists() else []
    return {pt["id"]: pt for pt in items}


def _extract_query_terms(q: str, canonical_symptoms: list[str]) -> list[str]:
    """Combine normalized symptom tokens, space/comma clauses, and authentic TCM synonyms without noisy bigrams."""
    nq = norm_simp(q)
    nq_syn = nq.replace("但头汗出", " ").replace("头汗出", " ").replace("往来寒热", " ")
    raw = [t.strip() for t in re.split(r"[\s,，、；;：:。！？!?\-\/]+", nq) if len(t.strip()) >= 2]
    terms: list[str] = list(dict.fromkeys(canonical_symptoms + raw))
    seen = set(terms)
    for grp in formula_diagnose.SYNONYM_GROUPS:
        norm_grp = [norm_simp(g) for g in grp]
        if any(g in nq_syn or any(g == t for t in terms) for g in norm_grp):
            for g in norm_grp:
                if g and g not in seen:
                    seen.add(g)
                    terms.append(g)
    # Remove overly broad 1-char or non-clinical tokens if any crept in
    return [t for t in terms if len(t) >= 2][:28]


def _is_clean_symptom_cue(cue: str, formula_name: str = "") -> bool:
    """Reject classical clause fragments, formula titles, and overly long phrases from clickable cue pills."""
    c = re.sub(r"[（）()\s]", "", cue or "").strip()
    if not (2 <= len(c) <= 6):
        return False
    if formula_name and (c in formula_name or norm_simp(formula_name) in norm_simp(c)):
        return False
    bad_markers = ("，", "。", "、", "：", "；", "而", "之", "者", "得之", "假令", "此远", "二三日", "以上", "不瘥", "服后", "汤", "散", "丸", "方")
    return not any(m in c for m in bad_markers)


def _search_all_jingfang_clues(
    cleaned_q: str,
    canonical_symptoms: list[str],
    top_atom_fids: list[str],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Score ALL 299 formulas using curated symptoms, Ni why rationale, overview, and 108 modifications."""
    fmap = _formulas_by_id()
    cbmap = _curated_batches_map()
    _, mods_by_fid = _modifications_index()
    fa_by_fid = _fa_links_by_formula()
    pt_map = _acupoints_by_id()
    terms = _extract_query_terms(cleaned_q, canonical_symptoms)
    nq = norm_simp(cleaned_q)

    scored: list[tuple[int, dict[str, Any]]] = []
    for fid, fobj in fmap.items():
        fname = fobj.get("name", "")
        cb = cbmap.get(fid, {})
        cb_syms = cb.get("symptoms") if isinstance(cb.get("symptoms"), list) else []
        why_txt = norm_simp(cb.get("why") or "")
        ind_txt = norm_simp(fobj.get("indication") or "")
        ov_paras = ""
        if isinstance(cb.get("overview"), dict):
            ov_paras = " ".join(cb["overview"].get("paragraphs", []))
        ov_txt = norm_simp(ov_paras)
        six_m = fobj.get("six_meridian") or fobj.get("chapter") or cb.get("six_channel") or ""

        sc = 0
        matched_terms: list[str] = []
        supporting_symptoms: list[str] = []
        unselected_cues: list[str] = []

        fname_n = norm_simp(fname)
        if fname_n and fname_n in nq:
            sc += 55
            matched_terms.append(fname)

        for sym_entry in cb_syms:
            if not isinstance(sym_entry, dict):
                continue
            sname = (sym_entry.get("name") or "").strip()
            sname_n = norm_simp(sname)
            sexp_n = norm_simp(sym_entry.get("explanation") or "")
            hit_sym = False
            for t in terms:
                if len(t) < 2:
                    continue
                if t in sname_n or sname_n in t:
                    sc += 22
                    hit_sym = True
                    if t not in matched_terms:
                        matched_terms.append(t)
                elif t in sexp_n:
                    sc += 8
                    hit_sym = True
                    if t not in matched_terms:
                        matched_terms.append(t)
            if hit_sym and sname and sname not in supporting_symptoms:
                supporting_symptoms.append(sname)
            elif sname and sname not in unselected_cues and _is_clean_symptom_cue(sname, fname):
                unselected_cues.append(sname)

        for t in terms:
            if len(t) < 2:
                continue
            in_ind = t in ind_txt
            in_why = t in why_txt
            in_ov = t in ov_txt
            if in_ind:
                sc += 14
            if in_why:
                sc += 10
            if in_ov and not in_why:
                sc += 5
            if (in_ind or in_why or in_ov) and t not in matched_terms:
                matched_terms.append(t)

        # Match 108 modifications connected to this base formula
        f_mods = mods_by_fid.get(fid, [])
        relevant_mods: list[dict[str, Any]] = []
        for m in f_mods:
            cond_n = norm_simp(m.get("condition", ""))
            rat_n = norm_simp(m.get("rationale", ""))
            mod_hit = any(t in cond_n or t in rat_n for t in terms if len(t) >= 2)
            if mod_hit:
                sc += 10
            if mod_hit or fid in top_atom_fids:
                relevant_mods.append(
                    {
                        "id": m["id"],
                        "condition": m.get("condition", ""),
                        "changes_summary": (m.get("changes") or {}).get("summary", ""),
                        "target_formula_id": m.get("target_formula_id", ""),
                        "target_formula_name": m.get("target_formula_name", ""),
                        "rationale": m.get("rationale", ""),
                        "boundary": m.get("boundary", ""),
                        "matched": mod_hit,
                    }
                )
        relevant_mods.sort(key=lambda x: (not x["matched"], x["id"]))

        if fid in top_atom_fids:
            idx_boost = 150 - top_atom_fids.index(fid) * 20
            sc += idx_boost

        if sc < 10:
            continue

        links = []
        for lk in fa_by_fid.get(fid, [])[:4]:
            tid = lk.get("target_id", "")
            pt_obj = pt_map.get(tid, {})
            links.append(
                {
                    "id": tid,
                    "name": lk.get("target_name") or pt_obj.get("canonical_name", tid),
                    "relation_kind": lk.get("relation_kind", ""),
                    "quote": lk.get("quote", ""),
                    "note": lk.get("note", ""),
                }
            )

        herbs = _herb_names_of(fobj)
        scored.append(
            (
                sc,
                {
                    "formula_id": fid,
                    "name": fname,
                    "book": fobj.get("book", ""),
                    "six_meridian": six_m,
                    "score": sc,
                    "in_compound": fid in top_atom_fids,
                    "matched_terms": matched_terms[:6],
                    "supporting_symptoms": supporting_symptoms[:6],
                    "unselected_cues": unselected_cues[:4],
                    "why_summary": (cb.get("why") or fobj.get("indication") or "")[:180],
                    "ingredients_summary": "、".join(herbs[:8]),
                    "decoction": (cb.get("usage_plain") or fobj.get("decoction_method") or fobj.get("decoction") or "")[:140],
                    "modifications": relevant_mods[:3],
                    "linked_acupoints": links,
                },
            )
        )

    scored.sort(key=lambda x: (-x[0], not x[1]["in_compound"], x[1]["formula_id"]))
    return [item for _, item in scored[:limit]]


def _build_followup_questions(
    symptoms: list[str],
    pulses: list[str],
    top_clues: list[dict[str, Any]],
    cond_patterns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Suggest high-discrimination clinical follow-up symptoms & pulses (学习问诊 · 鉴别追问)."""
    probes: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    sym_set = set(symptoms)
    pulse_set = set(pulses)

    def add_probe(label: str, token: str = "", pulse_id: str = "", why: str = "", kind: str = "symptom") -> None:
        if not label or label in sym_set or token in sym_set or (pulse_id and pulse_id in pulse_set):
            return
        if label in seen_labels:
            return
        seen_labels.add(label)
        probes.append({"label": label, "token": token, "pulse_id": pulse_id, "why": why, "kind": kind})

    # Structured differential probes based on present symptoms
    if sym_set & {"发热", "恶寒", "身冷"}:
        if "无汗" not in sym_set:
            add_probe("是否无汗", token="无汗", why="太阳伤寒表实（麻黄/葛根）vs 中风自汗（桂枝）")
        if "有汗" not in sym_set and "但头汗出" not in sym_set:
            add_probe("是否但头汗出", token="但头汗出", why="少阳三焦水热互结（柴胡桂枝干姜汤专症）")
        if "往来寒热" not in sym_set:
            add_probe("是否往来寒热", token="往来寒热", why="区分邪仍在太阳 vs 己入少阳半表半里")

    if sym_set & {"身冷", "脚冷", "习惯性便秘", "大便干", "腹痛", "痛经"}:
        add_probe("是否脉沉", pulse_id="沉", why="判断病在表或在里阴虚寒水停", kind="pulse")
        add_probe("是否脉微细", pulse_id="微细", why="少阴虚寒核心脉象，忌苦寒泻下", kind="pulse")
        add_probe("是否小便不利", token="小便不利", why="辨水气停蓄（真武 / 五苓 / 柴胡桂枝干姜）")
        add_probe("是否但头汗出", token="但头汗出", why="若寒热兼但头汗出则转合柴胡桂枝干姜汤")
        add_probe("是否脉洪大", pulse_id="洪大", why="若便干兼洪大数实则属阳明热实而非寒秘", kind="pulse")

    if sym_set & {"头痛", "偏头痛", "前额痛", "眩晕"}:
        add_probe("是否项背强痛", token="项背强", why="辨太阳/督脉葛根汤及后溪申脉证")
        add_probe("是否干呕吐涎", token="呕吐", why="辨厥阴吴茱萸汤巅顶痛 vs 少阳呕")
        add_probe("是否口渴小便少", token="口渴 小便不利", why="辨蓄水证头晕口渴（五苓散）")

    if sym_set & {"胸痹", "胸痛", "心悸", "咳喘痰多", "心下痞"}:
        add_probe("是否心痛彻背", token="心痛彻背", why="辨胸阳痹阻痰饮偏重（栝蒌薤白半夏/乌头赤石脂）")
        add_probe("是否口苦咽干", token="口苦 咽干", why="辨少阳柴胡或半夏泻心寒热错杂")
        add_probe("是否脉弦", pulse_id="弦", why="阳微阴弦或少阳水饮之核心脉象", kind="pulse")

    if "鼻症" in sym_set:
        add_probe("是否恶寒无汗", token="恶寒 无汗", why="鼻症兼恶寒无汗常由肺表受寒闭郁（可参葛根汤/麻黄/小青龙）")
        add_probe("是否稀清涕喷嚏", token="咳喘痰多", why="肺寒水饮停蓄致鼻流清涕、喷嚏不止（小青龙汤证）")
        add_probe("是否口渴黄涕", token="口渴", why="辨肺寒水饮 vs 鼻窦郁热")

    # Add top unselected symptom cues from top 299-formula matches & acupuncture patterns
    for clue in top_clues[:3]:
        for cue in clue.get("unselected_cues", [])[:2]:
            clean_cue = re.sub(r"[（）()\s]", "", cue).strip()
            if _is_clean_symptom_cue(clean_cue, clue.get("name", "")):
                add_probe(f"兼见{clean_cue}?", token=clean_cue, why=f"核对「{clue['name']}」核心主症")
    for cp in cond_patterns[:2]:
        for s in cp.get("symptoms", [])[:3]:
            cs = re.sub(r"[（）()\s]", "", s).strip()
            if _is_clean_symptom_cue(cs):
                add_probe(f"兼见{cs}?", token=cs, why=f"核对《针灸》「{cp['pattern_name'][:14]}」分型")

    return probes[:10]


def _extract_symptoms(q: str) -> list[str]:
    nq = norm_simp(q)
    # Remove localized "但头汗出 / 头汗出" before matching generalized sweating ("汗出")
    nq_no_head_sweat = nq.replace("但头汗出", " ").replace("只有头出汗", " ").replace("头汗出", " ")
    found: list[str] = []
    for canon, aliases in SYMPTOM_CANONICAL_RULES:
        haystack = nq_no_head_sweat if canon == "有汗" else nq
        if any(a in haystack for a in aliases):
            found.append(canon)
    return found


def _extract_pulses(pulse_str: str, q: str) -> list[str]:
    combined = norm_simp(f"{pulse_str} {q}")
    selected: list[str] = []
    for p in PULSE_OPTIONS:
        pid = p["id"]
        if pid in combined or (pid == "微细" and ("微" in combined or "细" in combined)):
            selected.append(pid)
    return list(dict.fromkeys(selected))


def _herb_names_of(formula: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for ing in formula.get("ingredients", []):
        if isinstance(ing, dict):
            nm = ing.get("herb") or ing.get("name") or ""
        else:
            nm = str(ing)
        nm = re.sub(r"（.*?）", "", nm).strip()
        if nm:
            names.append(nm)
    return names


def compose_differentiation(q: str = "", pulse: str = "") -> dict[str, Any]:
    """Perform clinical symptom + pulse breakdown -> dynamic single/compound Jingfang + Acupoints."""
    cleaned_q = (q or "").strip()
    cleaned_pulse = (pulse or "").strip()
    safety = _detect_safety_boundary(f"{cleaned_q} {cleaned_pulse}")
    symptoms = _extract_symptoms(cleaned_q)
    pulses = _extract_pulses(cleaned_pulse, cleaned_q)
    fmap = _formulas_by_id()

    if not cleaned_q and not cleaned_pulse:
        return {
            "query": "",
            "pulse": "",
            "safety_boundary": safety,
            "pulse_options": PULSE_OPTIONS,
            "quick_symptom_pills": QUICK_SYMPTOM_PILLS,
            "clinical_entry_cards": CLINICAL_ENTRY_CARDS,
            "preset_cases": PRESET_CASES,
            "recognized_symptoms": [],
            "recognized_pulses": [],
            "followup_questions": [],
            "compound_regimens": [],
            "candidate_formulas": [],
            "matched_jingfang_clues": [],
            "matched_condition_patterns": [],
            "acupoint_protocol": {"primary": [], "adjuncts": [], "technique_note": ""},
            "differential_notes": [],
            "excluded_pitfalls": [],
            "library_evidence": [],
            "ai_ready_case_packet": {},
        }

    # Score every pattern atom dynamically
    scored_atoms: list[dict[str, Any]] = []
    for atom in PATTERN_ATOMS:
        score = 0
        matched_syms: list[str] = []
        matched_pulses: list[str] = []
        conflict_reasons: list[str] = []

        for sym, w in atom.get("symptom_weights", {}).items():
            if sym in symptoms:
                score += w
                matched_syms.append(sym)
        for s1, s2, bonus in atom.get("pair_bonus", []):
            if s1 in symptoms and s2 in symptoms:
                score += bonus
        for p, w in atom.get("boost_pulses", {}).items():
            if p in pulses:
                score += w
                matched_pulses.append(f"+脉{p}")
        for sym, pen in atom.get("conflict_symptoms", {}).items():
            if sym in symptoms:
                score += pen
                conflict_reasons.append(f"症状「{sym}」偏离本方寒热表里边界（{pen}）")
        for p, pen in atom.get("conflict_pulses", {}).items():
            if p in pulses:
                score += pen
                conflict_reasons.append(f"脉象「{p}」与本方病机相反（{pen}）")

        if score <= 8 or not matched_syms:
            if conflict_reasons and matched_syms:
                # Keep suppressed candidates transparently for "excluded pitfalls" UI!
                scored_atoms.append(
                    {
                        **atom,
                        "score": score,
                        "suppressed": True,
                        "matched_symptoms": matched_syms,
                        "matched_pulses": matched_pulses,
                        "conflict_reasons": conflict_reasons,
                    }
                )
            continue

        fobj = fmap.get(atom["formula_id"], {})
        scored_atoms.append(
            {
                **atom,
                "score": score,
                "suppressed": False,
                "matched_symptoms": matched_syms,
                "matched_pulses": matched_pulses,
                "conflict_reasons": conflict_reasons,
                "formula_summary": fobj.get("indication", ""),
                "decoction": fobj.get("decoction_method", ""),
                "herbs": _herb_names_of(fobj),
            }
        )

    active = [a for a in scored_atoms if not a["suppressed"]]
    active.sort(key=lambda x: (-x["score"], -len(x["matched_symptoms"]), x["atom_id"]))
    suppressed = [a for a in scored_atoms if a["suppressed"]]

    # Build Dynamic Compound Regimen(s): identify distinct complementary top formulas covering different symptom subsets
    compound_regimens: list[dict[str, Any]] = []
    if len(active) >= 2:
        f1 = active[0]
        # Prefer second formula that contributes uncovered symptoms OR distinctly complements axis 1
        uncovered = set(symptoms) - set(f1["matched_symptoms"])
        ranked_partners = sorted(
            active[1:6],
            key=lambda cand: (
                -(len(set(cand["matched_symptoms"]) & uncovered) * 20 + cand["score"]),
                cand["atom_id"],
            ),
        )
        f2 = ranked_partners[0]
        covered = set(f1["matched_symptoms"]) | set(f2["matched_symptoms"])
        herbs1 = set(f1.get("herbs", []))
        herbs2 = set(f2.get("herbs", []))
        overlap_herbs = sorted(herbs1 & herbs2)
        compound_regimens.append(
            {
                "title": f"主推合方：{f1['name']} 合 {f2['name']}",
                "formula_ids": [f1["formula_id"], f2["formula_id"]],
                "formula_names": [f1["name"], f2["name"]],
                "axis_roles": [
                    f"【主轴一】{f1['name']}（{f1['six_meridian']}）：主司「{'、'.join(f1['matched_symptoms'])}」",
                    f"【主轴二】{f2['name']}（{f2['six_meridian']}）：兼顾「{'、'.join(f2['matched_symptoms'])}」",
                ],
                "covered_symptoms": [s for s in symptoms if s in covered],
                "uncovered_symptoms": [s for s in symptoms if s not in covered],
                "overlap_herbs": overlap_herbs,
                "overlap_note": (
                    f"两方共有重叠药味：{'、'.join(overlap_herbs)}（传统合方需依轻重统调克数并分明姜/干姜及制附先后煎法，不可机械叠加双倍剂量）。"
                    if overlap_herbs
                    else "两方药味分工各专，可据证候主次斟酌主从合参。"
                ),
            }
        )
    elif len(active) == 1:
        f1 = active[0]
        compound_regimens.append(
            {
                "title": f"单方统摄：{f1['name']}",
                "formula_ids": [f1["formula_id"]],
                "formula_names": [f1["name"]],
                "axis_roles": [f"【专方主轴】{f1['name']}（{f1['six_meridian']}）：统括「{'、'.join(f1['matched_symptoms'])}」"],
                "covered_symptoms": f1["matched_symptoms"],
                "uncovered_symptoms": [s for s in symptoms if s not in set(f1["matched_symptoms"])],
                "overlap_herbs": [],
                "overlap_note": "目前症状高度集中于单一主经病机，优先考虑专方纯正取效。",
            }
        )

    # Build Dynamic Acupoint Protocol from top active atoms + uncovered symptoms
    primary_pts: list[dict[str, str]] = []
    adjunct_pts: list[dict[str, str]] = []
    seen_pts: set[str] = set()
    for idx, atom in enumerate(active[:3]):
        for pt in atom.get("acupoints", []):
            if pt["id"] in seen_pts:
                continue
            seen_pts.add(pt["id"])
            entry = {**pt, "from_axis": atom["name"]}
            if idx < 2 and pt["role"].startswith(("主", "急")):
                primary_pts.append(entry)
            else:
                adjunct_pts.append(entry)

    # Full-corpus Jingfang clues (299 formulas + 258 curated symptoms + 108 modifications)
    top_atom_fids = [a["formula_id"] for a in active[:4]]
    jingfang_clues = _search_all_jingfang_clues(cleaned_q, symptoms, top_atom_fids, limit=8)

    # Full-corpus Acupuncture Condition Sub-patterns (34倪师《针灸》临床治症)
    acup_diag = acupuncture_diagnose.diagnose_symptoms(cleaned_q or " ".join(symptoms), limit_patterns=6, limit_points=8)
    cond_patterns_raw = acup_diag.get("matched_patterns", [])
    matched_condition_patterns: list[dict[str, Any]] = []
    for cp in cond_patterns_raw[:6]:
        matched_condition_patterns.append(
            {
                "condition_id": cp.get("condition_id", ""),
                "condition_name": cp.get("condition_name", ""),
                "pattern_name": cp.get("pattern_name", ""),
                "symptoms": cp.get("symptoms", []),
                "syndrome_differentiation": cp.get("syndrome_differentiation", ""),
                "why_selected": cp.get("why_selected", ""),
                "differentiation_notes": cp.get("differentiation_notes", ""),
                "score": cp.get("score", 0),
                "points": [
                    {"id": p.get("id", ""), "name": p.get("canonical_name", ""), "meridian_name": p.get("meridian_name", "")}
                    for p in cp.get("resolved_points", [])[:6]
                ],
            }
        )

    # Fallback hero recommendation if no compound atom matched directly (e.g. disease search like 胆结石/鼻炎/消渴)
    if not compound_regimens and jingfang_clues:
        jc1 = jingfang_clues[0]
        jc2 = jingfang_clues[1] if len(jingfang_clues) > 1 else None
        compound_regimens.append(
            {
                "title": f"全库经方线索：{jc1['name']}" + (f" / 互参 {jc2['name']}" if jc2 else ""),
                "formula_ids": [x["formula_id"] for x in ([jc1, jc2] if jc2 else [jc1])],
                "formula_names": [x["name"] for x in ([jc1, jc2] if jc2 else [jc1])],
                "axis_roles": [
                    f"【经方首选线索】{jc1['name']}（{jc1['book']} · {jc1['six_meridian']}）：{jc1['why_summary'] or '命中主症 ' + '、'.join(jc1['matched_terms'])}"
                ] + (
                    [f"【对照互参方】{jc2['name']}（{jc2['book']} · {jc2['six_meridian']}）：{jc2['why_summary'] or '命中 ' + '、'.join(jc2['matched_terms'])}"]
                    if jc2
                    else []
                ),
                "covered_symptoms": jc1["matched_terms"],
                "uncovered_symptoms": [],
                "overlap_herbs": [],
                "overlap_note": "由全库 299 首经方与 258 套课程症候资料自动关联命中；请点击右侧「支持/待核症状」与加减条文进一步收敛。",
            }
        )
    elif not compound_regimens and not jingfang_clues and matched_condition_patterns:
        cp0 = matched_condition_patterns[0]
        pts0 = [p["name"] for p in cp0.get("points", [])[:6]]
        compound_regimens.append(
            {
                "title": f"《针灸》专症主治：{cp0['condition_name']}",
                "formula_ids": [],
                "formula_names": [],
                "axis_roles": [
                    f"【《针灸》分型主症】{cp0['pattern_name']}：{cp0.get('syndrome_differentiation') or ''}",
                    f"【选穴思路】{cp0.get('why_selected') or '按局部/邻近/远端经络配穴：' + '、'.join(pts0)}",
                ],
                "covered_symptoms": [s for s in cp0.get("symptoms", [])[:4]],
                "uncovered_symptoms": [],
                "overlap_herbs": [],
                "overlap_note": "当前输入侧重局部或专科病症，《针灸》原书已有明确专症分型与选穴；如欲同步匹配经方内服，请点击下方「临床症状追问」补充全身寒热、出汗、二便或脉象线索。",
            }
        )

    # Merge formula_acupuncture_links & matched_condition_patterns acupoints when needed so every disease gets points!
    fa_by_fid = _fa_links_by_formula()
    pt_by_id = _acupoints_by_id()
    for fid in ([a["formula_id"] for a in active[:2]] or [c["formula_id"] for c in jingfang_clues[:2]]):
        fname_lbl = fmap.get(fid, {}).get("name", fid)
        for lk in fa_by_fid.get(fid, [])[:3]:
            tid = lk.get("target_id", "")
            if not tid or tid in seen_pts:
                continue
            seen_pts.add(tid)
            target_pt = pt_by_id.get(tid, {})
            entry = {
                "id": tid,
                "name": lk.get("target_name") or target_pt.get("canonical_name", tid),
                "role": lk.get("relation_kind") or "针药并行",
                "reason": lk.get("note") or lk.get("quote", ""),
                "from_axis": f"《伤寒/金匮》{fname_lbl}原文针药直连",
            }
            if len(primary_pts) < 3:
                primary_pts.append(entry)
            else:
                adjunct_pts.append(entry)

    for cp in matched_condition_patterns[:2]:
        for p in cp.get("points", [])[:4]:
            pid = p.get("id", "")
            if not pid or pid in seen_pts:
                continue
            seen_pts.add(pid)
            entry = {
                "id": pid,
                "name": p["name"],
                "role": "针灸治症取穴" if len(primary_pts) < 4 else "分型随症配穴",
                "reason": (cp.get("why_selected") or cp.get("syndrome_differentiation") or "")[:96],
                "from_axis": f"《针灸》{cp['condition_name']}",
            }
            if len(primary_pts) < 3:
                primary_pts.append(entry)
            else:
                adjunct_pts.append(entry)

    if len(primary_pts) < 3:
        for mp in acup_diag.get("matched_points", [])[:4]:
            pid = mp.get("id", "")
            if not pid or pid in seen_pts:
                continue
            seen_pts.add(pid)
            primary_pts.append(
                {
                    "id": pid,
                    "name": mp.get("canonical_name", pid),
                    "role": "《针灸》主治专穴",
                    "reason": "；".join(mp.get("indications", [])[:2]) or mp.get("technique_notes", "")[:80],
                    "from_axis": f"《针灸》{mp.get('meridian_name', '十四经')}主治匹配",
                }
            )
            if len(primary_pts) >= 4:
                break

    # Extra targeted symptom-to-acupoint rules (preserved cleanly)
    if ("习惯性便秘" in symptoms or "大便干" in symptoms) and "acupoint:st25:天枢" not in seen_pts:
        adjunct_pts.append({"id": "acupoint:st25:天枢", "name": "天枢", "role": "便干随症配穴", "reason": "大肠募穴，调肠通腑（兼寒可用温灸/配照海润燥）", "from_axis": "大便干/便秘轴"})
        seen_pts.add("acupoint:st25:天枢")
    if ("习惯性便秘" in symptoms or "大便干" in symptoms) and "acupoint:sj06:支沟" not in seen_pts:
        adjunct_pts.append({"id": "acupoint:sj06:支沟", "name": "支沟", "role": "便干随症配穴", "reason": "支沟配照海为通调大便经典对穴", "from_axis": "大便干/便秘轴"})
        seen_pts.add("acupoint:sj06:支沟")
    if ("身冷" in symptoms or "脚冷" in symptoms) and "acupoint:du04:命门" not in seen_pts:
        adjunct_pts.append({"id": "acupoint:du04:命门", "name": "命门", "role": "虚寒温灸配穴", "reason": "温命门肾火，引火归元散寒", "from_axis": "身冷/脚冷轴"})
        seen_pts.add("acupoint:du04:命门")

    moxa_advice = []
    if any(s in symptoms for s in ("身冷", "脚冷", "下利清谷", "痛经")):
        moxa_advice.append("【刺灸寒热区分】含身冷脚冷/下利/虚寒痛经，下焦关元、命门、太溪宜重用隔姜灸或温针以助阳气化水；若兼但头汗出或少阳口苦，阳陵泉、外关、期门宜针刺平泻而不重灸。")
    if acup_diag.get("safety_alerts"):
        moxa_advice.append("【针灸安全提醒】" + "；".join(acup_diag["safety_alerts"][:2]))
    if pulses:
        pulse_notes = [f"{p['label']}：{p['note']}" for p in PULSE_OPTIONS if p["id"] in pulses]
        moxa_advice.append("【脉象参与辨证权重】" + "；".join(pulse_notes))

    # Dynamic differential follow-up questions (学习问诊)
    followup_questions = _build_followup_questions(symptoms, pulses, jingfang_clues, matched_condition_patterns)

    # Match differential notes & excluded pitfalls
    diffs = []
    for d in CLINICAL_DIFFERENTIAL_NOTES:
        t1 = d.get("trigger_all", ())
        t2 = d.get("alt_trigger_all", ())
        if (t1 and all(x in symptoms for x in t1)) or (t2 and all(x in symptoms for x in t2)):
            diffs.append({"title": d["title"], "explanation": d["explanation"]})

    excluded = []
    for sp in suppressed:
        excluded.append(
            {
                "name": sp["name"],
                "formula_id": sp["formula_id"],
                "why_excluded": "；".join(sp["conflict_reasons"]),
            }
        )

    lib_query = " ".join((symptoms[:4] or _extract_query_terms(cleaned_q, [])[:3])) or cleaned_q
    lib_res = search_library_pages(lib_query, limit=6)
    lib_refs = [
        {
            "book_id": r["book_id"],
            "book_title": r["book_title"],
            "page_no": r["page_no"],
            "unit_label": r["unit_label"],
            "snippet": r["snippet"],
            "text_sha256": r["text_sha256"],
        }
        for r in lib_res.get("items", [])
    ]

    # Pre-formatted packet ready for Stage 6 LLM clinical co-pilot integration
    ai_packet = {
        "schema": "tcm_brain.ai_clinical_case_packet.v1",
        "ready_for_llm": True,
        "safety_gate": safety,
        "recognized_symptoms": symptoms,
        "recognized_pulses": pulses,
        "decomposed_axes": [{"formula": a["name"], "axis": a["six_meridian"], "matched": a["matched_symptoms"], "score": a["score"]} for a in active[:4]],
        "matched_jingfang_ids": [c["formula_id"] for c in jingfang_clues[:6]],
        "matched_condition_ids": [cp["condition_id"] for cp in matched_condition_patterns[:4]],
        "proposed_compound": compound_regimens[0]["formula_names"] if compound_regimens else [],
        "proposed_acupoints": [p["name"] for p in (primary_pts + adjunct_pts)[:8]],
        "excluded_pitfalls": excluded,
        "grounded_citations": [{"book": c["book_title"], "unit": c["unit_label"], "sha256": c["text_sha256"], "snippet": c["snippet"]} for c in lib_refs[:4]],
        "system_constraint": "Future AI plugin MUST cite only grounded_citations SHA hashes, respect safety_gate non-prescribing rules, and never drop contradictory pulse constraints.",
    }

    return {
        "query": cleaned_q,
        "pulse": cleaned_pulse,
        "safety_boundary": safety,
        "pulse_options": PULSE_OPTIONS,
        "quick_symptom_pills": QUICK_SYMPTOM_PILLS,
        "clinical_entry_cards": CLINICAL_ENTRY_CARDS,
        "preset_cases": PRESET_CASES,
        "recognized_symptoms": symptoms,
        "recognized_pulses": pulses,
        "followup_questions": followup_questions,
        "compound_regimens": compound_regimens,
        "candidate_formulas": active[:6],
        "matched_jingfang_clues": jingfang_clues,
        "matched_condition_patterns": matched_condition_patterns,
        "acupoint_protocol": {
            "primary": primary_pts[:6],
            "adjuncts": adjunct_pts[:6],
            "technique_note": " ".join(moxa_advice),
        },
        "differential_notes": diffs,
        "excluded_pitfalls": excluded,
        "library_evidence": lib_refs,
        "ai_ready_case_packet": ai_packet,
    }
