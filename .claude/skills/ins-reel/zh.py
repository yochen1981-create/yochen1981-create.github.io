#!/usr/bin/env python3
"""
zh.py - Chinese support shared by hookscore.py and beats.py.

Chinese has no spaces, so it cannot be counted in words. It is counted in
characters instead: one character is one syllable, and scripted Mandarin on a
Reel runs at about 4.5 of them a second (270 a minute). An English word at
165 wpm takes 0.36s and a character takes 0.22s, so one character is worth
about 0.6 of a word wherever the scripts reason in words. A hook of 5 to 12
English words is therefore a hook of roughly 8 to 20 characters.

The marker lists below are the Chinese counterparts of the English ones in
hookscore.py: numbers that are actually spoken as quantities, money words,
words that put something at stake, openers that say nothing, and the
greetings and preambles that are dealbreakers in either language. They are
written for Traditional Chinese; the common Simplified forms are included
where they differ.
"""

import re

HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

CPS = 4.5                    # characters per second, scripted Mandarin
EN_WPS = 165 / 60            # the English default in both scripts
HAN_WEIGHT = EN_WPS / CPS    # one character, measured in English words


def han_count(text):
    return len(HAN_RE.findall(text))


def latin(text):
    """Blank out the Chinese so the English regexes see word boundaries.

    Python treats a Han character as a word character, so in "虧了18萬" there
    is no \\b before the 1 and the English number pattern never fires.
    """
    return HAN_RE.sub(" ", text)


# Numbers. "一" on its own is left out for the same reason "one" is left out
# of the English list: 一個, 一定, 一起 are filler far more often than they
# are a quantity. A numeral counts when a unit follows it, or when it is a
# compound like 三十 or 兩百 that can only be a quantity.
NUMERALS = "零〇一二兩两三四五六七八九十百千萬万億亿半幾几"
CN_NUM_RE = re.compile(f"[{NUMERALS}]+")
UNITS = (
    "個月", "个月", "小時", "小时", "分鐘", "分钟", "公斤", "塊錢", "块钱",
    "元", "塊", "块", "萬", "万", "千", "倍", "成", "年", "月", "週", "周",
    "天", "秒", "歲", "岁", "次", "張", "张", "個", "个", "位", "筆", "笔",
    "件", "堂", "斤", "趟", "間", "间", "家", "台", "支", "集", "組", "组",
    "%", "％", "趴",
)
# Numeral runs that are words, not quantities.
NOT_NUMBERS = {"萬一", "万一", "十分", "百分", "一一"}
# Runs that are a quantity only with a unit after them: 千萬元 is money,
# 千萬不要 is "whatever you do, don't".
UNIT_ONLY = {"千萬", "千万", "一", "二"}

# Spoken money, the counterpart of MONEY_WORDS.
MONEY = (
    "薪水", "月薪", "年薪", "時薪", "房租", "營收", "利潤", "獲利", "利息",
    "存款", "保費", "理賠金", "解約金", "退休金", "收入", "報酬率", "本金",
    "新台幣", "台幣", "美金", "工资", "利润", "保费",
)

CN_PRICE_RE = re.compile(
    rf"(?:\d[\d,.]*|[{NUMERALS}]+)\s?(?:萬|万|千)?\s?(?:元|塊|块|美金|台幣)"
    r"|\d[\d,.]*\s?(?:萬|万)")

# Words that put something on the line, the counterpart of STAKES. Matched
# longest first, so 千萬不要 is one marker and not three.
STAKES = (
    "千萬不要", "千萬別", "千万不要", "千万别", "不應該", "不应该", "沒有人",
    "没有人", "沒想到", "没想到", "第一次", "被開除", "被开除",
    "不要", "不該", "不该", "別再", "别再", "沒人", "没人", "從來", "从来",
    "永遠", "永远", "絕對", "绝对", "停止", "錯誤", "错误", "錯過", "错过",
    "損失", "损失", "浪費", "浪费", "白繳", "白缴", "白花", "多花", "後悔",
    "后悔", "陷阱", "真相", "秘密", "祕密", "內幕", "内幕", "其實", "其实",
    "竟然", "居然", "只有", "只要", "唯一", "但是", "可是", "不過", "不过",
    "除非", "直到", "之前", "風險", "风险", "危險", "危险", "警告", "解約",
    "解约", "退保", "拒賠", "拒赔", "失去", "失敗", "失败", "破產", "破产",
    "搞砸", "差點", "差点", "辭職", "辞职", "免費", "免费", "省下", "刪掉", "删掉", "取代",
    "討厭", "讨厌", "問題", "问题", "代價", "代价", "少領", "少领",
    "不", "沒", "没", "別", "别", "錯", "错", "虧", "亏", "賠", "赔", "騙",
    "骗", "坑", "卻", "却",
)
# Common words that contain a stakes character but put nothing at stake.
# They are matched first and thrown away, so 不錯 ("not bad") is not read as
# a negation plus a mistake.
NOT_STAKES = (
    "不錯", "不错", "差不多", "不好意思", "對不起", "对不起", "了不起",
    "沒關係", "没关系", "沒問題", "没问题", "不客氣", "不客气", "不用謝",
)
_STAKES_RE = re.compile("|".join(
    re.escape(w) for w in sorted(NOT_STAKES + STAKES, key=len, reverse=True)))

# Openers that spend the first second saying nothing.
WEAK_OPENERS = (
    "大家好", "各位好", "哈囉", "哈喽", "嗨", "嘿", "欸", "那個", "那个",
    "就是", "所以", "好啦", "好的", "今天", "歡迎", "欢迎", "我想", "我要",
    "跟大家", "你知道嗎", "你知道吗", "你們知道", "有沒有人", "我們來",
    "这是", "這是", "這個", "这个", "說真的", "说真的", "老實說", "老实说",
    "基本上",
)

# Imperatives that earn the front position.
IMPERATIVES = (
    "不要", "千萬", "千万", "別", "别", "停止", "快", "馬上", "马上", "立刻",
    "記得", "记得", "試試", "试试", "趕快", "赶快", "收藏", "檢查", "检查",
    "先別", "先别",
)

DEALBREAKERS = [
    (re.compile(r"^\s*(?:先別滑|先别滑|別滑走|别滑走|不要滑走|先不要滑)"),
     "Opens with \"don't scroll\" (別滑走). Asking for attention proves you have not earned it."),
    (re.compile(r"這支影片|这支视频|這部影片|這集|这集|今天(?:要|來|来|就來|就来)?(?:跟|和)大家"
                r"|我(?:要|來|来)教你|帶你(?:看|了解)|带你(?:看|了解)"),
     "Video preamble (這支影片 / 今天跟大家). Delete it and open on the payoff."),
    (re.compile(r"^\s*(?:大家好|各位好|哈囉|哈喽|嗨|嘿)"),
     "Greeting (大家好 / 哈囉). Nobody came to the feed to be greeted."),
]


def numbers(text):
    """Spoken Chinese quantities, as (text, char position)."""
    found = []
    for m in CN_NUM_RE.finditer(text):
        run, after = m.group(), text[m.end():]
        if run in NOT_NUMBERS:
            continue
        unit = next((u for u in UNITS if after.startswith(u)), None)
        # 十幾次 and 幾百塊 are quantities; 幾個 on its own is "a few".
        if unit and run not in ("一", "二", "幾", "几"):
            found.append((run + unit, m.start()))
        elif run not in UNIT_ONLY and len(run) >= 2 and re.search("[十百千萬万億亿半]", run):
            found.append((run, m.start()))
    return found


def money(text):
    return [(w, text.find(w)) for w in dict.fromkeys(MONEY) if w in text]


def stakes(text):
    """Distinct stakes markers, as (marker, char position of first use)."""
    seen = {}
    ignore = set(NOT_STAKES)
    for m in _STAKES_RE.finditer(text):
        if m.group() not in ignore:
            seen.setdefault(m.group(), m.start())
    return sorted(seen.items(), key=lambda kv: kv[1])


def has_price(text):
    return bool(CN_PRICE_RE.search(text))


def weak_opener(text):
    head = text.lstrip(" \t「『\"'“")
    return next((w for w in WEAK_OPENERS if head.startswith(w)), None)


def imperative_opener(text):
    head = text.lstrip(" \t「『\"'“")
    return next((w for w in IMPERATIVES if head.startswith(w)), None)


def addresses_viewer(text):
    return bool(re.search("[你妳您]", text))


def first_person(text):
    return "我" in text


STOP_HAN = set("的了是我你妳您他她它在就都也和跟與与這这那個个一不有要會会啊嗎吗呢吧嗯喔哦")


def bigrams(text):
    """Two-character chunks with no particle or pronoun in them, for loop matching."""
    han = [c if HAN_RE.match(c) else " " for c in text]
    out = set()
    for a, b in zip(han, han[1:]):
        if a != " " and b != " " and a not in STOP_HAN and b not in STOP_HAN:
            out.add(a + b)
    return out
