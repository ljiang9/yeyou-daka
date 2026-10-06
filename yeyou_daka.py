#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""夜游打卡模拟器 yeyou-daka。

致敬 2026 国庆夜游经济热点：沉浸式演出、烟花秀、夜游标签景区搜索量同比增长超五成，
多地景区夜游延时开放。本游戏所有地点、事件均为虚构，如有雷同纯属巧合。

玩法：玩家只有一晚（18:00-23:00，共 5 小时），在虚构的"夜游小城"里规划打卡路线。
体力归零会被强制送回酒店。纯 Python 标准库，无第三方依赖。
"""

from __future__ import annotations

import argparse
import random
import sys

TOTAL_HOURS = 5.0      # 一晚：18:00-23:00
START_STAMINA = 100    # 初始体力
WALLET = 300           # 一晚预算（元）
EVENT_CHANCE = 0.35    # 每次打卡触发随机事件的概率
EPS = 1e-9

# 8 个虚构夜游点：耗时(h) / 花费(元) / 快乐值 / 体力消耗
SPOTS = [
    {
        "name": "花鼓戏沉浸式街区",
        "hours": 1.5, "cost": 68, "fun": 85, "stamina": 18,
        "desc": "戏台搭进老街，观众席就是街道，锣鼓一响全街入戏。",
        "events": ["npc_shangtai"],
    },
    {
        "name": "望舒湖畔光影秀",
        "hours": 1.0, "cost": 40, "fun": 80, "stamina": 10,
        "desc": "湖面当幕布，光影讲了一整座城的前世今生。",
        "events": ["yanhua"],
    },
    {
        "name": "临江古城墙灯会",
        "hours": 1.0, "cost": 30, "fun": 70, "stamina": 12,
        "desc": "城墙挂满花灯，登高望江，朋友圈素材管够。",
        "events": ["yanhua"],
    },
    {
        "name": "拾味夜市小吃街",
        "hours": 1.0, "cost": 50, "fun": 78, "stamina": 8,
        "desc": "从街头吃到街尾，快乐是按串计费的。",
        "events": ["paidui"],
    },
    {
        "name": "江心游船夜游",
        "hours": 1.5, "cost": 88, "fun": 90, "stamina": 12,
        "desc": "船行江心，两岸灯火流淌，晚风把疲惫都吹散。",
        "events": ["yanhua"],
    },
    {
        "name": "长夜剧本杀街区",
        "hours": 2.0, "cost": 98, "fun": 95, "stamina": 22,
        "desc": "整条街都是剧本，路人可能是隐藏凶手。",
        "events": ["npc_shangtai"],
    },
    {
        "name": "星野天文台观星",
        "hours": 1.0, "cost": 25, "fun": 65, "stamina": 8,
        "desc": "远离灯火，银河低垂，适合发呆和许愿。",
        "events": [],
    },
    {
        "name": "不打烊24小时书店",
        "hours": 0.5, "cost": 0, "fun": 40, "stamina": 5,
        "desc": "深夜书店，咖啡配书香，夜猫子的精神角落。",
        "events": [],
    },
]

# 随机事件池：快乐倍率 / 额外耗时 / 是否社死 / 快乐加成
EVENTS = {
    "yanhua": {
        "name": "烟花秀临时加场",
        "text": "湖对岸突然升起烟花——临时加场！快乐暴击，本次快乐值 x1.5！",
        "fun_mul": 1.5, "time": 0.0, "shedie": False, "fun_bonus": 0,
    },
    "paidui": {
        "name": "夜市排队一小时",
        "text": "人气摊位前排起长龙，排队花掉 1 小时，但吃到就是赚到。",
        "fun_mul": 1.0, "time": 1.0, "shedie": False, "fun_bonus": 0,
    },
    "npc_shangtai": {
        "name": "被NPC拉上台",
        "text": "沉浸式 NPC 一把把你拉上台演路人甲，全场鼓掌——社死值 +1，快乐 +40！",
        "fun_mul": 1.0, "time": 0.5, "shedie": True, "fun_bonus": 40,
    },
}


class Night:
    """一晚的夜游状态机。"""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.time_left = TOTAL_HOURS
        self.stamina = START_STAMINA
        self.money = WALLET
        self.visited: list[str] = []
        self.fun_total = 0.0
        self.shedie = 0
        self.log: list[str] = []
        self.ended_reason = ""

    def spot_by_name(self, name: str) -> dict:
        for s in SPOTS:
            if s["name"] == name:
                return s
        raise ValueError(f"没有这个夜游点：{name}")

    def can_visit(self, spot: dict) -> tuple[bool, str]:
        if spot["name"] in self.visited:
            return False, "已经打卡过了"
        if spot["hours"] > self.time_left + EPS:
            return False, "时间不够"
        if spot["cost"] > self.money:
            return False, "预算不够"
        if spot["stamina"] > self.stamina:
            return False, "体力不够，去了会直接累瘫回酒店"
        return True, ""

    def candidates(self) -> list[dict]:
        return [s for s in SPOTS if self.can_visit(s)[0]]

    def visit(self, name: str) -> dict:
        """打卡一个夜游点。非法输入抛 ValueError。返回本轮结算。"""
        spot = self.spot_by_name(name)
        ok, reason = self.can_visit(spot)
        if not ok:
            raise ValueError(reason)

        event_id = None
        if spot["events"] and self.rng.random() < EVENT_CHANCE:
            event_id = self.rng.choice(spot["events"])
        event = EVENTS[event_id] if event_id else None

        fun = float(spot["fun"])
        if event:
            fun = fun * event["fun_mul"] + event["fun_bonus"]

        cost_time = spot["hours"] + (event["time"] if event else 0.0)
        self.time_left = max(0.0, self.time_left - cost_time)
        self.stamina -= spot["stamina"]
        self.money -= spot["cost"]
        self.fun_total += fun
        self.visited.append(spot["name"])

        entry = (f"打卡「{spot['name']}」（{spot['hours']}h，"
                 f"-{spot['stamina']}体力，快乐 +{fun:.0f}）")
        if event:
            entry += f" → 事件：{event['name']}"
            if event["shedie"]:
                self.shedie += 1
        self.log.append(entry)

        if self.stamina <= 0:
            self.ended_reason = "体力耗尽，被迫回酒店躺平"
        elif self.time_left <= EPS:
            self.ended_reason = "23:00 到了，夜游结束"
        return {"spot": spot["name"], "fun": fun, "event_id": event_id}

    @property
    def finished(self) -> bool:
        return bool(self.ended_reason) or not self.candidates()

    def finish(self) -> None:
        if not self.ended_reason:
            self.ended_reason = "没有合适的下一个打卡点了，今晚就到这"


def score(night: Night) -> float:
    """评分 = 打卡数 x 总快乐值。"""
    return len(night.visited) * night.fun_total


def title_for(score_value: float) -> str:
    if score_value >= 1800:
        return "夜游之王"
    if score_value >= 1200:
        return "特种兵夜猫"
    return "早睡早起养生派"


COMMENTS = {
    "夜游之王": [
        "五小时逛穿整座城，朋友圈九宫格根本放不下！",
        "建议申遗：人类高质量夜游行为。",
    ],
    "特种兵夜猫": [
        "行程拉满但没猝死，夜猫中的特种兵。",
        "快乐和黑眼圈一起收获，值！",
    ],
    "早睡早起养生派": [
        "十点就回酒店？保温杯里泡枸杞说的就是你。",
        "夜游虽好，可不要贪杯——你倒是真听劝。",
    ],
}


def report(night: Night) -> str:
    sc = score(night)
    title = title_for(sc)
    comment = night.rng.choice(COMMENTS[title])
    spots = "、".join(night.visited) if night.visited else "（一个都没去，纯纯的云夜游）"
    lines = [
        "今晚战报",
        f"打卡 {len(night.visited)} 个点：{spots}",
        f"总快乐值 {night.fun_total:.0f} ｜ 评分 {sc:.0f}（打卡数 x 快乐值）",
        f"剩余体力 {night.stamina} ｜ 剩余预算 ￥{night.money} ｜ 社死 {night.shedie} 次",
        f"结束：{night.ended_reason}",
        f"称号：{title}",
        f"评语：{comment}",
    ]
    return "\n".join(lines)


def greedy_ai(rng: random.Random, verbose: bool = False) -> Night:
    """AI 贪心规划：每一步选单位时间快乐值最高的、去得起的点。"""
    night = Night(rng)
    while not night.finished:
        cands = night.candidates()
        if not cands:
            night.finish()
            break
        cands.sort(key=lambda s: (s["fun"] / s["hours"], s["fun"]), reverse=True)
        res = night.visit(cands[0]["name"])
        if verbose:
            print("  " + night.log[-1])
            if res["event_id"]:
                print("    " + EVENTS[res["event_id"]]["text"])
    night.finish()
    return night


def interactive() -> int:
    if not sys.stdin.isatty():
        print("需要交互式终端运行；非交互环境请使用 --auto 自动演示。", file=sys.stderr)
        return 2
    rng = random.Random()
    night = Night(rng)
    print("夜游打卡模拟器：今晚 18:00-23:00，5 小时任你规划！")
    print("规则：体力归零会被强制送回酒店；预算 ￥300。")
    while not night.finished:
        print(f"\n剩余 {night.time_left:.1f}h ｜ 体力 {night.stamina} "
              f"｜ 预算 ￥{night.money} ｜ 已打卡 {len(night.visited)}")
        cands = night.candidates()
        for i, s in enumerate(cands, 1):
            print(f"  {i}. {s['name']}（{s['hours']}h / ￥{s['cost']} / "
                  f"快乐{s['fun']} / 体力-{s['stamina']}）— {s['desc']}")
        print("   q. 提前回酒店")
        choice = input("去哪？输入编号：").strip()
        if choice.lower() == "q":
            night.ended_reason = "你选择提前回酒店休息"
            break
        try:
            spot = cands[int(choice) - 1]
        except (ValueError, IndexError):
            print("无效输入，请输入列表中的编号。")
            continue
        res = night.visit(spot["name"])
        print("✅ " + night.log[-1])
        if res["event_id"]:
            print("🎉 " + EVENTS[res["event_id"]]["text"])
    night.finish()
    print("\n" + report(night))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="夜游打卡模拟器：一晚 5 小时的夜游路线规划")
    ap.add_argument("--auto", action="store_true", help="AI 自动规划演示")
    ap.add_argument("--games", type=int, default=1, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--verbose", action="store_true", help="打印整晚战报")
    args = ap.parse_args(argv)

    if args.games < 1:
        print("--games 必须 >= 1", file=sys.stderr)
        return 2

    if args.auto:
        seed = args.seed if args.seed is not None else random.randrange(2 ** 32)
        tally: dict[str, int] = {}
        for g in range(args.games):
            rng = random.Random(seed + g)
            night = greedy_ai(rng, verbose=args.verbose)
            title = title_for(score(night))
            tally[title] = tally.get(title, 0) + 1
            if args.verbose:
                print(f"\n—— 第 {g + 1} 局（seed={seed + g}）——")
                print(report(night))
        print(f"\n共 {args.games} 局（seed 基准 {seed}），称号分布：")
        for t in ("夜游之王", "特种兵夜猫", "早睡早起养生派"):
            print(f"  {t}：{tally.get(t, 0)} 局")
        return 0

    return interactive()


if __name__ == "__main__":
    raise SystemExit(main())
