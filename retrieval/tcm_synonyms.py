"""Shared classical TCM clinical synonyms and edition/orthographic variant mappings.

Used by:
- app.formula_diagnose (Stage 4 formula & symptom diagnosis)
- app.syndrome_composer (Stage 5 syndrome clue extraction)
- retrieval.index (Full-corpus 17-book search & multi-module knowledge lookup)
"""
from __future__ import annotations

from typing import Callable


FORMULA_SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("项背强", "项强", "项背强几几", "颈项强", "脖子僵", "身体强几几然", "刚痉", "柔痉"),
    ("往来寒热", "寒热往来", "忽冷忽热", "时冷时热", "发寒发热"),
    ("心烦喜呕", "心烦", "喜呕", "呕吐", "干呕", "恶心", "反胃"),
    ("胸胁苦满", "胸胁满", "胁下痞硬", "胁痛", "两胁胀痛", "往来寒热"),
    ("恶寒", "怕冷", "畏寒", "背恶寒", "恶风", "怕风"),
    ("发热", "发烧", "身热", "壮热", "骨蒸", "潮热", "日晡所发潮热", "日晡所剧"),
    ("无汗", "不出汗", "汗闭", "表实"),
    ("有汗", "汗出", "自汗", "汗出恶风", "微汗", "大汗", "汗多"),
    ("口渴", "大渴", "烦渴", "欲饮水", "渴欲饮水", "引饮", "消渴", "糖尿病"),
    ("不渴", "不欲饮", "不用水", "寒多不用水", "口不渴"),
    ("小便不利", "小便少", "小便反少", "尿少", "癃闭", "水肿", "浮肿", "水气", "蓄水"),
    ("小便自利", "小便利", "小便清长", "小便数", "尿频"),
    ("大便硬", "大便干", "大便难", "不大便", "便秘", "燥屎", "宿食", "不转矢气"),
    ("下利", "泄泻", "腹泻", "拉肚子", "下利清谷", "热利", "痢疾", "脓血便"),
    ("远血", "先便后血", "黑便", "胃出血", "柏油便"),
    ("近血", "先血后便", "便血", "痔疮出血", "肠风下血"),
    ("心下痞", "胃痞", "心下闷", "胃胀", "心下满", "痞满", "心中痞气"),
    ("胸痹", "胸痛", "心痛彻背", "背痛彻心", "心痛", "心绞痛", "短气", "喘息"),
    ("少腹肿痞", "少腹肿", "按之即痛如淋", "大黄牡丹汤", "肠痈", "右下腹痛", "盲肠炎"),
    ("肌肤甲错", "皮肤甲错", "两目黯黑", "干血", "癥瘕", "血痹", "麻木不仁"),
    ("热入血室", "经水适断", "经水适来", "寒热如疟", "如疟状", "期门"),
    ("喘", "咳逆", "上气", "哮喘", "咳嗽", "水鸡声", "但坐不得眠", "肺胀", "肺痈", "肺痿"),
    ("咽痛", "喉咙痛", "咽中伤", "失音", "梅核气", "咽中如有炙脔"),
    ("黄疸", "发黄", "谷疸", "酒疸", "女劳疸", "身目黄"),
    ("奔豚", "气上冲胸", "脐下悸"),
    ("虚劳", "悸", "心悸", "心动悸", "失眠", "虚烦不得眠", "梦遗", "酸枣仁"),
    ("风湿", "历节", "关节痛", "身烦疼", "身重", "不能自转侧", "骨节疼痛"),
    ("厥逆", "四肢厥冷", "手脚冰冷", "手足寒", "脉微欲绝", "亡阳", "附子"),
    ("吐蛔", "蚘虫", "蛔虫", "蚘厥", "脏寒"),
    ("转筋", "脚挛急", "拘急", "抽筋", "小腿抽筋"),
    ("郁冒", "眩晕", "头晕", "冒家", "水饮眩悸"),
    ("妊娠", "怀孕", "胎动", "漏下", "产后", "恶露"),
)

# Classical text / recension / abbreviation variants grounded in the corpus & tcm-classic-supplements
CLASSIC_ORTHO_VARIANTS: tuple[tuple[str, ...], ...] = (
    ("四逆汤", "回逆汤"),
    ("真武汤", "玄武汤"),
    ("乌梅丸", "乌梅圆"),
    ("理中丸", "理中汤", "理中圆", "人参汤"),
    ("厚朴", "浓朴"),
    ("黄芩", "黄苓"),
    ("炙甘草汤", "灸甘草汤", "复脉汤"),
    ("肾气丸", "八味肾气丸", "金匮肾气丸", "桂附八味丸", "崔氏八味丸"),
    ("栝蒌", "栝篓", "瓜蒌"),
    ("栝篓桂枝汤", "栝蒌桂枝汤", "瓜蒌桂枝汤"),
    ("栝蒌瞿麦丸", "瓜蒌瞿麦丸", "栝篓瞿麦丸"),
    ("栝蒌薤白半夏汤", "瓜蒌薤白半夏汤"),
    ("栝蒌薤白白酒汤", "瓜蒌薤白白酒汤"),
    ("黄芪", "黄耆"),
    ("桂枝加黄芪汤", "桂枝加黄耆汤"),
    ("防己黄芪汤", "防己黄耆汤"),
    ("黄芪建中汤", "黄耆建中汤"),
    ("黄芪桂枝五物汤", "黄耆桂枝五物汤"),
    ("黄芪芍药桂枝苦酒汤", "黄耆芍药桂枝苦酒汤"),
    ("蟅虫", "䗪虫", "蛰虫"),
    ("大黄蟅虫丸", "大黄䗪虫丸", "大黄蛰虫丸"),
    ("蚘虫", "蛔虫"),
    ("栀子柏皮汤", "栀子蘗皮汤", "栀子檗皮汤"),
    ("栀子大黄汤", "桅子大黄汤"),
    ("猪膏发煎", "猪膏髪煎", "膏发煎", "膏髪煎"),
    ("旋覆代赭石汤", "旋覆代赭汤"),
    ("麻黄杏仁甘草石膏汤", "麻杏石甘汤", "麻杏甘石汤"),
    ("麻黄杏仁薏苡甘草汤", "麻杏苡甘汤"),
    ("橘枳生姜汤", "橘皮枳实生姜汤", "橘枳姜汤"),
    ("桂枝加芍药生姜人参新加汤", "桂枝新加汤", "新加汤"),
    ("桂枝去桂加茯苓白术汤", "桂枝去桂加苓术汤"),
    ("桂枝去芍药加蜀漆牡蛎龙骨救逆汤", "桂枝救逆汤"),
    ("柴胡去半夏加栝蒌汤", "柴胡去半夏加瓜蒌汤"),
    ("柴胡桂枝干姜汤", "柴胡桂姜汤"),
    ("赤小豆当归散", "赤豆当归散"),
    ("梅核气", "咽中如有炙脔"),
    ("黄疸", "黄瘅"),
    ("心悸", "心动悸"),
    ("虚劳", "虚痨"),
)

RETRIEVAL_EXTRA_SYNONYMS: tuple[tuple[str, ...], ...] = (
    ("不寐", "失眠", "不得眠", "不得卧", "彻夜难眠"),
    ("胃痛", "胃脘痛", "心下痛", "心下痞痛"),
    ("头痛", "头疼", "偏头痛", "巅顶痛", "前额痛", "头风"),
    ("喘", "气喘", "呼吸困难", "喘不上气", "喘息", "咳喘"),
    ("湿疹", "皮肤湿疹", "皮肤干燥", "流黄水", "瘙痒"),
    ("淋痛", "尿痛", "小便刺痛", "尿血", "血淋", "砂淋", "石淋"),
    ("痛风", "历节", "脚肿如脱", "关节痛", "风湿"),
)


def expand_ortho_variants(term: str, norm_fn: Callable[[str], str] | None = None) -> list[str]:
    """Return exact-equivalent classical spelling/abbreviation forms, keeping primary first."""
    fn = norm_fn or (lambda s: (s or "").strip().lower())
    base = fn(term)
    if not base:
        return []
    alts: list[str] = [base]
    seen: set[str] = {base}
    for grp in CLASSIC_ORTHO_VARIANTS:
        norm_grp = [fn(item) for item in grp if fn(item)]
        # Exact group hit first
        if base in norm_grp:
            for g in norm_grp:
                if g not in seen:
                    seen.add(g)
                    alts.append(g)
        else:
            # Substring herb/character variant replacement inside multi-char queries (e.g. 黄耆 -> 黄芪)
            for item in norm_grp:
                if len(item) >= 2 and item in base:
                    for repl in norm_grp:
                        if repl != item:
                            cand = base.replace(item, repl)
                            if cand and cand not in seen:
                                seen.add(cand)
                                alts.append(cand)
    return alts[:8]


def expand_clinical_synonyms(tokens: list[str], norm_fn: Callable[[str], str] | None = None) -> list[list[str]]:
    """Expand each token into [literal + ortho forms..., clinical synonyms...]."""
    fn = norm_fn or (lambda s: (s or "").strip().lower())
    all_groups = FORMULA_SYNONYM_GROUPS + RETRIEVAL_EXTRA_SYNONYMS
    out: list[list[str]] = []
    for raw in tokens:
        base = fn(raw)
        if not base:
            continue
        grp_list = expand_ortho_variants(raw, norm_fn=fn)
        seen = set(grp_list)
        for sgrp in all_groups:
            ns = [fn(s) for s in sgrp if fn(s)]
            if any(base == s or (len(base) >= 2 and len(s) >= 2 and (base in s or s in base)) for s in ns):
                for s in ns:
                    if s not in seen:
                        seen.add(s)
                        grp_list.append(s)
        out.append(grp_list[:12])
    return out
