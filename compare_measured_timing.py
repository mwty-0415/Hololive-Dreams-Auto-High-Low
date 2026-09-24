"""Compare stopping policies with measured cycle timings; simulation only."""
import json
import statistics
from pathlib import Path
from benchmark_strategy import simulate
from high_low_strategy import TimePolicy

def main():
    config = json.loads(Path('strategy_config.json').read_text())
    config.update(round_seconds=7.920, flip_seconds=4.245,
                  fail_seconds=2.0, cashout_seconds=2.0)
    report = {'kind': 'simulation calibrated with sparse live timing samples',
              'days': 200, 'seed': 531987, 'config': config, 'results': {}}
    for threshold in (0, 400, 800, 1600):
        policy = TimePolicy(config['payout_probabilities'], **{
            k: config[k] for k in ('round_seconds', 'flip_seconds', 'cashout_seconds', 'fail_seconds')},
            min_cashout=threshold)
        modes = ('legacy', 'time_target') if threshold == 0 else ('time_target',)
        for mode in modes:
            rows = [simulate(policy, mode, config, 531987+i) for i in range(200)]
            result = {'mean_seconds': statistics.mean(r['seconds'] for r in rows),
                      'mean_rounds': statistics.mean(r['rounds'] for r in rows),
                      'mean_guesses': statistics.mean(r['guesses'] for r in rows),
                      'final_round_available_days': sum(r['final_round_available'] for r in rows)}
            key = 'legacy' if mode == 'legacy' else str(threshold)
            report['results'][key] = result
            print(key, result, flush=True)
    Path('benchmark_measured_timing.json').write_text(json.dumps(report, indent=2)+'\n')

if __name__ == '__main__':
    main()
