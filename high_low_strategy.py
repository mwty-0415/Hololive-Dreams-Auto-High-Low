"""Two selectable policies; no screen/input dependencies.

The time policy minimizes expected completion time in a coarse renewal model.
Its live two-step lookahead uses the observed, depleted deck.  This is a model,
not a proof of optimality for the game's undocumented high/low rules.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import numpy as np

TARGET = 19800
DAILY_CAP = 20000
PRIZES = (0, 200, 400, 700, 800, 1500, 3000, 7000, 10000)


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    cashout_seconds: float | None = None
    challenge_seconds: float | None = None


def legacy_decision(coins, cash, rate):
    """Exact old stopping rules, including the blind-card 100% assumption."""
    rate = 1.0 if rate is None else rate
    if coins >= TARGET:
        return Decision('cashout' if cash >= 10000 else 'challenge', 'legacy_sprint_10000')
    if coins + cash <= TARGET and coins + cash * 2 > TARGET:
        return Decision('cashout', 'legacy_before_target')
    if coins + cash > TARGET:
        return Decision('cashout' if cash >= 10000 else 'challenge', 'legacy_overshoot')
    return Decision('cashout' if rate < .60 else 'challenge', 'legacy_60_percent')


def choice_and_rate(deck, rank):
    high = sum(n for r, n in deck.items() if r > rank)
    low = sum(n for r, n in deck.items() if r < rank)
    return ('high', high / (high + low)) if high >= low and high + low else (
        ('low', low / (high + low)) if high + low else ('high', .5))


class TimePolicy:
    """Renewal Bellman model + two observed-deck steps.

    Unknown first rank is averaged, not treated as a guaranteed win. Equal
    ranks are assumed to consume a card and replay without doubling. No joker
    is assumed in high/low (same as upstream); live jokers pause the bot.
    """
    def __init__(self, payout_probabilities, round_seconds=7.920,
                 flip_seconds=4.245, cashout_seconds=2.0, fail_seconds=2.0,
                 min_cashout=0):
        probs = np.asarray(payout_probabilities, dtype=float)
        if len(probs) != len(PRIZES) or not np.isfinite(probs).all() or (probs < 0).any() or probs.sum() <= 0:
            raise ValueError('Invalid payout probabilities')
        if any(not math.isfinite(v) or v <= 0 for v in (round_seconds, flip_seconds, cashout_seconds, fail_seconds)):
            raise ValueError('Timings must be positive')
        self.probs = probs / probs.sum()
        self.round_seconds = round_seconds
        self.flip_seconds = flip_seconds
        self.cashout_seconds = cashout_seconds
        self.fail_seconds = fail_seconds
        self.min_cashout = max(0, int(min_cashout))
        # Coarse model: fresh ordinary deck, current rank already removed.
        self.transitions = []
        for direction in ('high', 'low'):
            w = np.array([[4 / 51 if (j > i if direction == 'high' else j < i) else 0
                           for j in range(13)] for i in range(13)])
            self.transitions.append(w)
        self.values = np.zeros(TARGET // 100 + 1)
        self._build()

    def remaining_time(self, remaining):
        if remaining <= 0:
            return 0.0
        return float(self.values[min(len(self.values) - 1, math.ceil(remaining / 100))])

    def _build(self):
        # A fixed policy has value A + B*T(g); exact evaluation A/(1-B)
        # removes the failure self-loop. Policy iteration then chooses the
        # smaller cashout/continue line until the policy stabilizes.
        for units in range(1, len(self.values)):
            gap = units * 100
            limit = gap + 100  # bank in [19,800, 19,900], below 20,000
            amounts = set()
            for prize in PRIZES[1:]:
                while prize <= limit:
                    amounts.add(prize)
                    prize *= 2
            guess = max(1.0, self.values[units - 1] + self.round_seconds * 10)
            for _ in range(80):
                lines = {}
                forced_lines = {}
                for cash in sorted(amounts, reverse=True):
                    stop = self.cashout_seconds + self.remaining_time(gap - cash)
                    if cash < self.min_cashout and cash < gap and cash * 2 <= limit:
                        stop = float('inf')
                    a = np.full(13, stop)
                    b = np.zeros(13)
                    if cash * 2 <= limit:
                        na, nb = lines[cash * 2]
                        for direction, w in enumerate(self.transitions):
                            lose = 1 - 3 / 51 - w.sum(axis=1)
                            ca = (self.flip_seconds + w @ na + lose * self.fail_seconds) / (1 - 3 / 51)
                            cb = (w @ nb + lose) / (1 - 3 / 51)
                            # Match the live maximum-survival high/low choice.
                            preferred = (np.arange(13) <= 6) if direction == 0 else (np.arange(13) > 6)
                            better = preferred & (ca + cb * guess < a + b * guess)
                            a = np.where(better, ca, a)
                            b = np.where(better, cb, b)
                            if direction == 0:
                                forced_a, forced_b = ca, cb
                            else:
                                forced_a = np.where(preferred, ca, forced_a)
                                forced_b = np.where(preferred, cb, forced_b)
                        forced_lines[cash] = float(forced_a.mean()), float(forced_b.mean())
                    lines[cash] = a, b
                aa = self.round_seconds + self.probs[0] * self.fail_seconds
                bb = self.probs[0]
                for prize, prob in zip(PRIZES[1:], self.probs[1:]):
                    if prize in lines:
                        # First rank is hidden at the challenge prompt. Do
                        # not grant an oracle's free stop after seeing it.
                        a = self.cashout_seconds + self.remaining_time(gap-prize)
                        b = 0.0
                        if prize in forced_lines:
                            ca, cb = forced_lines[prize]
                            forced_small = prize < self.min_cashout and prize < gap
                            if forced_small or ca + cb * guess < a:
                                a, b = ca, cb
                        aa += prob * a
                        bb += prob * b
                    else:
                        # Oversized poker payouts cannot be safely banked.
                        # Approximate that rare round as a failed restart.
                        aa += prob * self.fail_seconds
                        bb += prob
                if bb >= 1 - 1e-12:
                    raise ValueError('Payout model cannot reach the target')
                updated = aa / (1 - bb)
                if abs(updated - guess) < 1e-6:
                    break
                guess = updated
            self.values[units] = updated

    def decide(self, coins, cash, deck, rank=None):
        if cash <= 0:
            return Decision('wait', 'unreadable_reward')
        if coins >= TARGET:
            return Decision('challenge', 'sprint_to_game_limit')
        if TARGET <= coins + cash < DAILY_CAP:
            return Decision('cashout', 'bank_target_then_sprint')
        if coins + cash >= DAILY_CAP:
            return Decision('challenge', 'oversized_hand_early_sprint')
        stop = self.cashout_seconds + self.remaining_time(TARGET - coins - cash)
        if coins + 2 * cash >= DAILY_CAP:
            return Decision('cashout', 'preserve_final_round', stop)
        if cash < self.min_cashout:
            return Decision('challenge', 'build_small_reward_before_cashout')
        counts = tuple(deck.get(r, 0) for r in range(2, 15))
        restart = self.fail_seconds + self.remaining_time(TARGET - coins)

        @lru_cache(maxsize=None)
        def value(amount, current, counts, depth):
            bank = self.cashout_seconds + self.remaining_time(TARGET - coins - amount)
            if coins + amount >= TARGET or depth <= 0 or coins + 2 * amount >= DAILY_CAP:
                return bank
            if amount < self.min_cashout:
                return challenge(amount, current, counts, depth)
            return min(bank, challenge(amount, current, counts, depth))

        def challenge(amount, current, counts, depth):
            total = sum(counts)
            if not total:
                return float('inf')
            if current is None:
                # First visible rank has not been removed yet.
                avg = 0.0
                for i, n in enumerate(counts):
                    if n:
                        after = list(counts); after[i] -= 1
                        avg += n / total * challenge(amount, i, tuple(after), depth)
                return avg
            options = []
            high_count = sum(n for i, n in enumerate(counts) if i > current)
            low_count = sum(n for i, n in enumerate(counts) if i < current)
            for high in (high_count >= low_count,):
                result = self.flip_seconds
                for i, n in enumerate(counts):
                    if not n:
                        continue
                    after = list(counts); after[i] -= 1
                    if i == current:
                        # Forced replay: approximate beyond lookahead with
                        # a fresh choice, never turn a tie into a win.
                        if depth > 1:
                            future = challenge(amount, current, tuple(after), depth - 1)
                        else:
                            win = sum(m for j, m in enumerate(after) if (j > i if high else j < i))
                            valid = sum(after) - after[i]
                            p = win / valid if valid else 0.0
                            future = self.flip_seconds + p * value(amount * 2, current, tuple(after), 0) + (1-p) * restart
                    elif (i > current) == high:
                        future = value(amount * 2, i, tuple(after), depth - 1)
                    else:
                        future = restart
                    result += n / total * future
                options.append(result)
            return min(options)

        play = challenge(cash, None if rank is None else rank - 2, counts, 2)
        return Decision('challenge' if play < stop else 'cashout', 'estimated_time', stop, play)
