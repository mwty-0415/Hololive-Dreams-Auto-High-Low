import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from high_low_strategy import TimePolicy, legacy_decision, choice_and_rate
from strategy_runtime import DailyLedger, StableNumber, atomic_json


class StrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = json.loads(Path(__file__).resolve().parents[1].joinpath('strategy_config.json').read_text())
        cls.policy = TimePolicy(config['payout_probabilities'], **{k: config[k] for k in ('round_seconds', 'flip_seconds', 'cashout_seconds', 'fail_seconds', 'min_cashout')})

    def test_legacy_matches_original_branch_order(self):
        def original(coins,cash,rate):
            rate = 1 if rate is None else rate
            if coins >= 19800:
                return 'cashout' if cash >= 10000 else 'challenge'
            if coins + cash <= 19800 and coins + cash*2 > 19800:
                return 'cashout'
            if coins + cash > 19800:
                return 'cashout' if cash >= 10000 else 'challenge'
            return 'cashout' if rate < .60 else 'challenge'
        for coins in (0, 15000, 19400, 19700, 19800, 19900):
            for cash in (100, 200, 700, 1600, 10000, 20000):
                for rate in (None, .50, .59, .60, 1):
                    self.assertEqual(legacy_decision(coins,cash,rate).action, original(coins,cash,rate))

    def test_target_is_banked_even_with_certain_win(self):
        self.assertEqual(self.policy.decide(19600,200,{14:4},2).action,'cashout')
        self.assertEqual(self.policy.decide(19760,200,{14:4},2).action,'cashout')

    def test_small_payouts_continue_with_favorable_cards(self):
        for cash in (200,800):
            self.assertEqual(self.policy.decide(0,cash,{r:4-(r==2) for r in range(2,15)},2).action,'challenge')

    def test_sprint_has_no_ten_thousand_cashout(self):
        for cash in (200, 10000, 102400, 104857600):
            self.assertEqual(self.policy.decide(19800,cash,{2:1,14:1},8).action,'challenge')

    def test_preserve_final_round(self):
        self.assertEqual(self.policy.decide(19000,700,{14:4},2).action,'cashout')

    def test_unknown_reward_never_defaults_to_200(self):
        self.assertEqual(self.policy.decide(0,0,{14:4}).action,'wait')

    def test_known_certain_loss_cashout(self):
        # Equal-only exhausted deck cannot promise a win.
        self.assertEqual(self.policy.decide(0,1000,{8:1},8).action,'cashout')

    def test_depleted_deck_can_reverse_direction(self):
        self.assertEqual(choice_and_rate({2:4, 14:1},8),('low',.8))

    def test_unseen_card_not_guaranteed(self):
        d=self.policy.decide(0,1000,{r:4 for r in range(2,15)})
        self.assertGreater(d.challenge_seconds, 0)

    def test_two_identical_positive_ocr_samples_required(self):
        reader=StableNumber()
        self.assertFalse(reader.accept(200))
        self.assertFalse(reader.accept(2000))
        self.assertFalse(reader.accept(0))
        self.assertFalse(reader.accept(200))
        self.assertTrue(reader.accept(200))

    def test_rollover_and_old_ledger_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'daily.json'
            atomic_json(path, {'date':datetime.now().strftime('%Y-%m-%d'),'coins':2560,'fails':13})
            ledger=DailyLedger(path)
            self.assertEqual(ledger.data['coins'],2560)
            self.assertFalse(ledger.rollover())
            ledger.rollover(datetime(2099,1,1,12))
            self.assertEqual(ledger.data['coins'],0)
            self.assertFalse(ledger.data['target_reached'])

    def test_configured_reset_hour(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=DailyLedger(Path(folder)/'daily.json',4)
            self.assertEqual(ledger.day_key(datetime(2026,9,18,3)), '2026-09-17')

    def test_corrupt_progress_is_not_silently_zeroed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'daily.json'; path.write_text('broken')
            with self.assertRaises(json.JSONDecodeError):
                DailyLedger(path)


if __name__ == '__main__':
    unittest.main()
