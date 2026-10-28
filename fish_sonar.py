# -*- coding: utf-8 -*-
"""
鱼群声呐：给一条 B站视频的评论区测「鱼浓度」（只读，不发任何东西）。

用法：
    python fish_sonar.py BV1xxxxxxxxx [--pages 3]

建议：环境变量 BILI_COOKIE 放你自己的 cookie（匿名请求经常被风控，返回 -352）。
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
FISHY_NAME = re.compile(r"鱼|鲸")
AT_HEAD = re.compile(r"^@\S+")


def get(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
    if os.environ.get("BILI_COOKIE"):
        headers["Cookie"] = os.environ["BILI_COOKIE"]
    with urllib.request.urlopen(urllib.request.Request(full, headers=headers), timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def fishy(reply):
    """粗筛：昵称带鱼/鲸，或评论以 @某人 开头。只是启发式，会误伤也会漏。"""
    name = (reply.get("member") or {}).get("uname", "")
    msg = (reply.get("content") or {}).get("message", "")
    return bool(FISHY_NAME.search(name) or AT_HEAD.match(msg))


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="B站评论区鱼浓度（只读）")
    ap.add_argument("bvid")
    ap.add_argument("--pages", type=int, default=3)
    a = ap.parse_args()

    view = get("https://api.bilibili.com/x/web-interface/view", {"bvid": a.bvid})
    aid = view["data"]["aid"]
    total = fish = 0
    cursor = 0
    for _ in range(a.pages):
        d = get("https://api.bilibili.com/x/v2/reply/main", {"type": 1, "oid": aid, "mode": 2, "next": cursor, "ps": 20})
        if d.get("code") != 0:
            print("B站返回 code=%s（%s）。匿名请求常被风控，请把你自己的 cookie 放进环境变量 BILI_COOKIE 再试；不要反复重试。"
                  % (d.get("code"), d.get("message")))
            return
        data = d.get("data") or {}
        replies = data.get("replies") or []
        total += len(replies)
        fish += sum(fishy(r) for r in replies)
        cur = data.get("cursor") or {}
        if cur.get("is_end") or not replies:
            break
        cursor = cur.get("next")
        time.sleep(1.2)
    rate = fish / total * 100 if total else 0
    print("%s  最新 %d 条评论里疑似鱼 %d 条，鱼浓度 %.0f%%" % (a.bvid, total, fish, rate))


if __name__ == "__main__":
    main()
