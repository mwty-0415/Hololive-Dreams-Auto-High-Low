"""Estimate the poker payout prior from seeded optimal-hold enumeration."""
import argparse
import json
import random
from pathlib import Path
from poker_core import calculate_best, PRIZES
from high_low_strategy import PRIZES as REWARDS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hands', type=int, default=128)
    parser.add_argument('--seed', type=int, default=19800)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    probs = dict.fromkeys(REWARDS, 0.0)
    for _ in range(args.hands):
        best, _ = calculate_best(rng.sample(range(53), 5), 'standard')
        for prize, n in zip(PRIZES, best.category_counts):
            probs[int(prize)] += n / best.total_outcomes / args.hands
    config = {'mode': 'time_target', 'target': 19800, 'daily_cap': 20000,
              'payout_probabilities': [probs[p] for p in REWARDS],
              'prior_hands': args.hands, 'prior_seed': args.seed,
              'round_seconds': 12.0, 'flip_seconds': 2.5, 'min_cashout': 800,
              'cashout_seconds': 2.0, 'fail_seconds': 2.0,
              'day_reset_hour': 0,
              'high_low_rules': 'ordinary deck; equal ranks replay; joker pauses'}
    Path(__file__).with_name('strategy_config.json').write_text(
        json.dumps(config, indent=2), encoding='utf-8')
    print(json.dumps(config, indent=2))


if __name__ == '__main__':
    main()
