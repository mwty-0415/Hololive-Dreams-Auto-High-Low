"""Seeded synthetic A/B comparison. Never operates the game.

Shares poker payouts and deck permutations by day and round, independent of
policy. Timing/payout/deck assumptions are written to the report. Reaching
the target while retaining a final round is measured separately from an
early daily-cap crossing. A synthetic 10-win game limit is not a known rule.
"""
import argparse
import json
import random
import statistics
from pathlib import Path
from high_low_strategy import TimePolicy, PRIZES, TARGET, DAILY_CAP, legacy_decision, choice_and_rate


def simulate(policy, mode, config, seed, max_rounds=2000):
    coins = 0
    seconds = 0.0
    guesses = 0
    for round_no in range(max_rounds):
        rng = random.Random(seed * 100003 + round_no)
        cash = rng.choices(PRIZES, config['payout_probabilities'])[0]
        seconds += config['round_seconds']
        if cash == 0:
            seconds += config['fail_seconds']
            continue
        cards = [r for r in range(2, 15) for _ in range(4)]
        rng.shuffle(cards)
        deck = {r: 4 for r in range(2, 15)}
        rank = None
        won = 0
        while cash:
            rate = choice_and_rate(deck, rank)[1] if rank is not None else None
            decision = legacy_decision(coins, cash, rate) if mode == 'legacy' else policy.decide(coins, cash, deck, rank)
            if decision.action == 'cashout' or won >= 10 or len(cards) < 2:
                seconds += config['cashout_seconds']
                coins += cash
                break
            if rank is None:
                rank = cards.pop(); deck[rank] -= 1
            choice, _ = choice_and_rate(deck, rank)
            seconds += config['flip_seconds']
            guesses += 1
            next_rank = cards.pop(); deck[next_rank] -= 1
            while next_rank == rank and cards:
                # A push forces replay, not a cashout opportunity.
                choice, _ = choice_and_rate(deck, rank)
                seconds += config['flip_seconds']
                guesses += 1
                next_rank = cards.pop(); deck[next_rank] -= 1
            win = next_rank > rank if choice == 'high' else next_rank < rank
            if win:
                cash *= 2
                won += 1
                rank = next_rank
            else:
                cash = 0
                seconds += config['fail_seconds']
        if coins >= TARGET:
            return {'seconds': seconds, 'rounds': round_no + 1, 'guesses': guesses,
                    'coins': coins, 'final_round_available': coins < DAILY_CAP, 'completed': True}
    return {'seconds': seconds, 'rounds': max_rounds, 'guesses': guesses,
            'coins': coins, 'final_round_available': False, 'completed': False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days', type=int, default=500)
    p.add_argument('--seed', type=int, default=20260918)
    p.add_argument('--round-seconds', type=float)
    p.add_argument('--output', default='benchmark_results.json')
    args = p.parse_args()
    config = json.loads(Path(__file__).with_name('strategy_config.json').read_text())
    if args.round_seconds:
        config['round_seconds'] = args.round_seconds
    policy = TimePolicy(config['payout_probabilities'], **{
        k: config[k] for k in ('round_seconds', 'flip_seconds', 'cashout_seconds', 'fail_seconds')},
        min_cashout=config.get('min_cashout',0))
    report = {'kind': 'synthetic simulation, NOT live measurements', 'days': args.days,
              'seed': args.seed, 'config': config,
              'assumptions': ['Payout prior from 128 sampled optimal poker hands, not live history',
                              'Independent fresh 52-card high/low deck, equal rank consumes card and replays',
                              'First rank hidden until challenge; subsequent rank known',
                              '10 successful doublings forces settlement (hypothetical game limit)',
                              'No OCR errors, no UI latency variation; fixed configured seconds',
                              'Both policies share poker payouts and decks per day/round'], 'results': {}}
    raw = {}
    for mode in ('legacy', 'time_target'):
        rows = [simulate(policy, mode, config, args.seed+i) for i in range(args.days)]
        raw[mode] = rows
        values = sorted(r['seconds'] for r in rows)
        eligible = [r['seconds'] for r in rows if r['final_round_available']]
        result = {'mean_seconds': statistics.mean(values), 'median_seconds': statistics.median(values),
                  'p90_seconds': values[min(len(values)-1, int(.90*len(values)))],
                  'mean_rounds': statistics.mean(r['rounds'] for r in rows),
                  'final_round_available_days': sum(r['final_round_available'] for r in rows),
                  'unfinished_days': sum(not r['completed'] for r in rows),
                  'mean_seconds_final_round_available': statistics.mean(eligible) if eligible else None}
        report['results'][mode] = result
        print(mode, json.dumps(result), flush=True)
    diffs = [a['seconds']-b['seconds'] for a,b in zip(raw['legacy'],raw['time_target'])]
    delta = statistics.mean(diffs)
    error = 1.96 * statistics.stdev(diffs) / len(diffs)**.5 if len(diffs) > 1 else 0
    report['paired_time_saving_seconds'] = {'mean': delta, 'approx_95_percent_interval': [delta-error,delta+error]}
    report['raw_days'] = raw
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('paired saving', report['paired_time_saving_seconds'])


if __name__ == '__main__':
    main()
