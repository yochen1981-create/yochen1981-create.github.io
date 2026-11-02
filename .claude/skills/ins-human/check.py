#!/usr/bin/env python3
"""
check.py - 保險業務員社群文字檢查：合規字詞、AI 味、文案格式。

在本機跑，不連網，不上傳任何東西。只看文字本身。

它會抓三類問題：
  合規  保險業務員常見的違規字詞（存錢、保本、報酬、比較、贈品、職稱……）
  AI 味  中文生成文字常見的痕跡（破折號、隱形字元、套話、「不是……而是……」）
  文案  用 --caption 時，另外檢查第一行長度、hashtag 數量、呼籲次數、連結

重要：這是字詞比對，不是法遵審核。
  - 沒抓到東西，只代表「沒有出現常見的危險字」，不代表合規。
  - 合規看的是整體印象：比喻、諧音、圖片暗示也算，這些工具抓不到。
  - 發布前一定要送公司法遵或主管審核。

用法
  python3 check.py 草稿.txt
  python3 check.py 草稿.txt --caption          # 文案模式，多檢查格式
  python3 check.py 草稿.txt --fix -o 乾淨.txt  # 自動清掉隱形字元、把破折號改成逗號
  pbpaste | python3 check.py -
  python3 check.py 草稿.txt --json
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------- 合規
# (類別, 嚴重度, 正規表示式, 說明)。嚴重度：高＝幾乎一定要改；中＝看上下文，多半要改。
COMPLIANCE = [
    ("職稱", "高", r"理財(顧問|專員|規劃師|夥伴|達人)|財務(規劃|顧問)|財富管理|投資顧問|資產配置|財稅顧問",
     "職稱不得含理財、財務規劃、投資顧問等字，改用公司核定的正式職稱"),
    ("存錢理財訴求", "高", r"存錢|存款|存下|儲蓄|理財|節稅|避稅|基金|資產傳承|錢滾錢",
     "不得以存錢、理財、節稅、基金當訴求，hashtag 和比喻也算"),
    ("比較", "高", r"定存|銀行(利息|利率)|比銀行|通膨|0050|ETF|股票|比.{0,6}(划算|好賺|安全)",
     "不得和定存、基金、股票或其他保單比較"),
    ("保證", "高", r"保證|保本|穩賺|不會虧|零風險|穩定收益|一定(會)?(漲|賺)|翻倍|本金不會少",
     "不得保證獲利或保本，先否認再暗示也算"),
    ("報酬", "高", r"報酬率?|配息|現金流|被動收入|年化|IRR|領回|回本|利率\s*\d",
     "保險以保障為目的，不談報酬、配息、現金流"),
    ("借錢解約", "高", r"借錢|貸款|舉債|解約|保單借款|舊保單.{0,4}換|換新保單|停繳轉",
     "不得鼓勵借錢、貸款或解約換新來投保"),
    ("贈品折扣", "高", r"投保送|簽約送|送禮券|贈品|打折|折扣|退佣|回饋金|幫你出.{0,4}保費|保費.{0,2}優惠",
     "不得以贈品、折扣、退佣招攬"),
    ("推薦商品", "中", r"推薦.{0,6}(保單|商品|險)|哪張(保單)?最好|最(划算|便宜)的保單|必買|CP\s*值",
     "不推薦特定商品、不比較商品優劣；對外商品資訊要用公司核可資料"),
    ("急迫話術", "中", r"停售|即將(調漲|漲價)|最後(機會|一波)|趕快(買|保)|錯過(就|再)",
     "停售、漲價的急迫話術容易被認定不當招攬"),
    ("恐嚇", "中", r"不買(就|會)|你就完了|後悔(都)?來不及|家人.{0,6}喝西北風|拖累家人",
     "避免恐嚇式說法，改講家庭責任和具體情境"),
    ("個資", "中", r"身分證|保單號碼|病歷|診斷書|要保書|理賠(明細|資料)|截圖",
     "客戶故事要去識別化，不放姓名、照片、保單、病歷或對話截圖"),
    ("未核准商品", "高", r"境外保單|海外保單|香港保單|投資平台|虛擬(貨幣|幣)",
     "不得推介未經核准的保險或金融商品"),
    ("保單健檢", "中", r"保單健檢|哪裡不足|保障缺口|還缺(什麼|哪些)",
     "「保單健檢」曾出現在違規貼文；避免引導加保或換約的說法，可改「保單整理」"),
]

# ---------------------------------------------------------------- AI 味
INVISIBLE = re.compile("[​‌‍⁠﻿­᠎⁡-⁤\U000e0000-\U000e007f]")
DASH = re.compile("——|—|–")
SLOP = [
    "賦能", "助力", "打造", "全方位", "一站式", "無縫", "深耕", "聚焦", "抓手", "閉環", "底層邏輯",
    "綜上所述", "總而言之", "總的來說", "值得一提的是", "不可否認", "毋庸置疑", "在這個.{0,8}的時代",
    "讓我們一起", "一起來看看", "你是否曾經", "你有沒有想過", "相信大家都", "大家好", "今天要跟大家",
    "在這支影片", "記得按讚", "分享給需要的人", "標記你的朋友", "停止滑動", "先別滑走", "乾貨",
    "建議收藏", "收藏起來慢慢看", "滿滿的", "超級重要", "不藏私", "懶人包",
]
SLOP_RE = re.compile("|".join(SLOP))
NOT_BUT = re.compile(r"不是[^。！？\n]{1,20}?(而是|是)")
NOT_ONLY = re.compile(r"不僅[^。！？\n]{1,20}?(更|還)")
TRIAD = re.compile(r"[^，、。\n]{1,6}、[^，、。\n]{1,6}、[^，、。\n]{1,6}[，。]")
RHET = re.compile(r"^.{1,6}[？?]$", re.M)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅]")

# ---------------------------------------------------------------- 文案
FIRST_LINE_ZH = 55          # 動態牆大約顯示到這裡就出現「…更多」（手機、中文，約兩行）
HASHTAG_LIMIT = 5           # Instagram 2025-12 起每則貼文最多 5 個 hashtag
FILLER_TAGS = {"#viral", "#fyp", "#explorepage", "#foryou", "#instagood", "#推薦", "#熱門", "#保險", "#保險業務"}
ASK_RE = re.compile(r"留言|私訊|收藏|分享給|追蹤|按讚|點連結|加.{0,4}LINE|傳給")
URL_RE = re.compile(r"https?://|www\.|\.com\b|\.tw\b|\.dev\b")
HASHTAG_RE = re.compile(r"#[^\s#]+")


def scan(text, caption=False):
    findings = []
    lines = text.splitlines()

    def where(m):
        n = text.count("\n", 0, m.start()) + 1
        return n, lines[n - 1].strip()[:40] if n - 1 < len(lines) else ""

    for cat, level, pat, why in COMPLIANCE:
        for m in re.finditer(pat, text, re.I):
            n, ln = where(m)
            findings.append({"group": "合規", "level": level, "cat": cat, "hit": m.group(0),
                             "line": n, "context": ln, "why": why})

    inv = INVISIBLE.findall(text)
    if inv:
        findings.append({"group": "AI味", "level": "中", "cat": "隱形字元", "hit": f"{len(inv)} 個",
                         "line": 0, "context": "", "why": "鍵盤打不出來的字元，用 --fix 自動刪掉"})
    for m in DASH.finditer(text):
        n, ln = where(m)
        findings.append({"group": "AI味", "level": "低", "cat": "破折號", "hit": m.group(0), "line": n,
                         "context": ln, "why": "台灣日常文字很少用破折號，改逗號或句號（--fix 會處理）"})
    for m in SLOP_RE.finditer(text):
        n, ln = where(m)
        findings.append({"group": "AI味", "level": "低", "cat": "套話", "hit": m.group(0), "line": n,
                         "context": ln, "why": "罐頭說法，改成你平常會講的話，或直接刪掉"})
    for rx, cat, why in [(NOT_BUT, "不是…而是…", "一篇最多一次，多了就像模板"),
                         (NOT_ONLY, "不僅…更…", "書面語，口播講不出來"),
                         (TRIAD, "三連詞", "「A、B、C」排比太工整，留一個最具體的")]:
        hits = list(rx.finditer(text))
        limit = 1 if cat == "不是…而是…" else 0
        for m in hits[limit:]:
            n, ln = where(m)
            findings.append({"group": "AI味", "level": "低", "cat": cat, "hit": m.group(0)[:16],
                             "line": n, "context": ln, "why": why})
    for m in RHET.finditer(text):
        n, ln = where(m)
        findings.append({"group": "AI味", "level": "低", "cat": "自問自答", "hit": m.group(0), "line": n,
                         "context": ln, "why": "「結果呢？」這種單獨一行的設問很像模板"})

    han = len(re.findall(r"[一-鿿]", text))
    emo = EMOJI.findall(text)
    if han and len(emo) / max(han, 1) * 100 > 4:
        findings.append({"group": "AI味", "level": "低", "cat": "emoji 太多",
                         "hit": f"{len(emo)} 個", "line": 0, "context": "",
                         "why": "每 100 字超過 4 個 emoji，讀起來像廣告"})

    if caption:
        first = next((l.strip() for l in lines if l.strip()), "")
        if len(first) > FIRST_LINE_ZH:
            findings.append({"group": "文案", "level": "中", "cat": "第一行太長", "hit": f"{len(first)} 字",
                             "line": 1, "context": first[:40],
                             "why": f"動態牆大約只顯示前 {FIRST_LINE_ZH} 字，重點要在這之前講完"})
        if first.startswith("#") or (first and EMOJI.match(first)):
            findings.append({"group": "文案", "level": "中", "cat": "開頭", "hit": first[:6], "line": 1,
                             "context": first[:40], "why": "第一個字不要是 hashtag 或 emoji"})
        tags = HASHTAG_RE.findall(text)
        if len(tags) > HASHTAG_LIMIT:
            findings.append({"group": "文案", "level": "高", "cat": "hashtag", "hit": f"{len(tags)} 個",
                             "line": 0, "context": "", "why": f"超過 Instagram 上限 {HASHTAG_LIMIT} 個"})
        filler = [t for t in tags if t.lower() in FILLER_TAGS]
        if filler:
            findings.append({"group": "文案", "level": "低", "cat": "空泛 hashtag", "hit": " ".join(filler),
                             "line": 0, "context": "", "why": "描述不了任何東西，換成具體主題"})
        asks = ASK_RE.findall(text)
        if len(asks) > 1:
            findings.append({"group": "文案", "level": "中", "cat": "呼籲太多", "hit": "、".join(asks),
                             "line": 0, "context": "", "why": "一篇只要一個呼籲，兩個等於沒有"})
        if URL_RE.search(text):
            findings.append({"group": "文案", "level": "中", "cat": "放連結", "hit": URL_RE.search(text).group(0),
                             "line": 0, "context": "", "why": "IG 文案的連結點不了，放個人檔案或私訊"})
    return findings


def fix(text):
    text = INVISIBLE.sub("", text)
    text = re.sub(r"\s*(——|—)\s*", "，", text)
    text = text.replace("–", "-")
    text = re.sub(r"，([，。！？])", r"\1", text)
    return text


def report(findings, out=sys.stdout):
    order = {"高": 0, "中": 1, "低": 2}
    findings = sorted(findings, key=lambda f: (f["group"] != "合規", order[f["level"]], f["line"]))
    comp = [f for f in findings if f["group"] == "合規"]
    print("合規字詞檢查", file=out)
    print("=" * 60, file=out)
    if not comp:
        print("  沒有出現常見的危險字詞。", file=out)
    for f in comp:
        loc = f"第 {f['line']} 行" if f["line"] else ""
        print(f"  [{f['level']}] {f['cat']}：「{f['hit']}」 {loc}", file=out)
        if f["context"]:
            print(f"       {f['context']}", file=out)
        print(f"       → {f['why']}", file=out)
    rest = [f for f in findings if f["group"] != "合規"]
    print("\nAI 味與格式", file=out)
    print("=" * 60, file=out)
    if not rest:
        print("  沒有發現。", file=out)
    for f in rest:
        loc = f"第 {f['line']} 行" if f["line"] else ""
        print(f"  [{f['group']}・{f['level']}] {f['cat']}：「{f['hit']}」 {loc}  → {f['why']}", file=out)
    high = sum(1 for f in comp if f["level"] == "高")
    print("\n" + "-" * 60, file=out)
    if high:
        verdict = f"有 {high} 處高風險字詞，改完再送審。"
    elif comp:
        verdict = "有需要確認的字詞，看上下文決定，拿不準就從嚴。"
    else:
        verdict = "未發現明顯問題（這不代表合規）。"
    print(f"結論：{verdict}", file=out)
    print("提醒：比喻、諧音、圖片暗示這個工具抓不到。發布前請送公司法遵或主管審核，並保留審核紀錄。", file=out)
    return high


def main():
    ap = argparse.ArgumentParser(description="保險業務員社群文字檢查")
    ap.add_argument("input", nargs="?", default="-", help="草稿檔，或 - 從標準輸入讀")
    ap.add_argument("--caption", action="store_true", help="文案模式：多檢查第一行、hashtag、呼籲、連結")
    ap.add_argument("--fix", action="store_true", help="刪掉隱形字元、破折號改逗號")
    ap.add_argument("-o", "--out", help="--fix 的輸出檔")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    if a.fix:
        text = fix(text)
        if a.out:
            open(a.out, "w", encoding="utf-8").write(text)
            print(f"已清理，存到 {a.out}\n")
        else:
            print(text + "\n" + "=" * 60)
    f = scan(text, caption=a.caption)
    if a.json:
        print(json.dumps(f, ensure_ascii=False, indent=1))
        return
    high = report(f)
    sys.exit(1 if high else 0)


if __name__ == "__main__":
    main()
