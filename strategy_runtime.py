"""Configuration, durable daily accounting and decision comparison logs."""
from datetime import datetime, timedelta
import json
import os
import time
from pathlib import Path
from dataclasses import asdict
from high_low_strategy import TimePolicy, TARGET, legacy_decision, choice_and_rate


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def load_config(app_dir, resource_dir):
    path = Path(app_dir) / 'strategy_config.json'
    if not path.exists():
        path = Path(resource_dir) / 'strategy_config.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    if config.get('mode') not in ('legacy', 'time_target'):
        raise ValueError('Unknown strategy mode')
    if config.get('target') != 19800 or config.get('daily_cap') != 20000:
        raise ValueError('This model requires target=19800 and daily_cap=20000')
    if not 0 <= config.get('day_reset_hour', 0) <= 23:
        raise ValueError('Invalid daily reset hour')
    return config


class DailyLedger:
    def __init__(self, path, reset_hour=0):
        self.path = Path(path)
        self.reset_hour = reset_hour
        self.data = {}
        if self.path.exists():
            # Never silently reset corrupted accounting and spend a whole day
            # acting on a false zero. Repair the file before resuming.
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
        self.rollover()

    def day_key(self, now=None):
        return ((now or datetime.now()) - timedelta(hours=self.reset_hour)).strftime('%Y-%m-%d')

    def rollover(self, now=None):
        key = self.day_key(now)
        if self.data.get('date') != key:
            self.data = {'date': key, 'coins': 0, 'fails': 0, 'rounds': 0,
                         'best_doubles': 0, 'target_reached': False}
            self.save()
            return True
        for name in ('coins', 'fails', 'rounds', 'best_doubles'):
            value = self.data.setdefault(name, 0)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f'Invalid daily field: {name}')
        self.data['target_reached'] = self.data['coins'] >= TARGET
        return False

    def save(self):
        atomic_json(self.path, self.data)


class StrategySession:
    def __init__(self, app_dir, resource_dir, mode=None):
        self.config = load_config(app_dir, resource_dir)
        self.mode = mode or self.config['mode']
        if self.mode not in ('legacy', 'time_target'):
            raise ValueError('Unknown strategy')
        self.ledger = DailyLedger(Path(app_dir) / 'daily_coins.json', self.config['day_reset_hour'])
        self.log_path = Path(app_dir) / 'strategy_events.jsonl'
        self.started = time.monotonic()
        self.session_id = datetime.now().isoformat(timespec='microseconds')
        self.policy = TimePolicy(self.config['payout_probabilities'], **{
            k: self.config[k] for k in ('round_seconds', 'flip_seconds', 'cashout_seconds', 'fail_seconds')},
            min_cashout=self.config.get('min_cashout', 0))
        self.event('session_start', config=self.config, coins=self.ledger.data['coins'])

    def event(self, kind, **fields):
        row = {'timestamp': datetime.now().isoformat(timespec='milliseconds'),
               'session_id': self.session_id, 'elapsed_seconds': round(time.monotonic()-self.started, 3),
               'mode': self.mode, 'event': kind, **fields}
        with self.log_path.open('a', encoding='utf-8') as out:
            out.write(json.dumps(row, ensure_ascii=False) + '\n')

    def decide(self, coins, cash, deck, rank):
        rate = choice_and_rate(deck, rank)[1] if rank is not None else None
        old = legacy_decision(coins, cash, rate)
        new = self.policy.decide(coins, cash, deck, rank)
        selected = old if self.mode == 'legacy' else new
        self.event('decision', coins=coins, cash=cash, rank=rank, deck=deck, rate=rate,
                   legacy=asdict(old), time_target=asdict(new), selected=selected.action)
        return selected


class StableNumber:
    def __init__(self):
        self.reset()

    def reset(self):
        self.previous = None
        self.count = 0

    def accept(self, value):
        if value <= 0:
            self.reset()
            return False
        self.count = self.count + 1 if value == self.previous else 1
        self.previous = value
        return self.count >= 2
