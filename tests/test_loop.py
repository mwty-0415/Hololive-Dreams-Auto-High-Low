"""Headless integration tests: real policy/ledger with synthetic UI states."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import auto_bot
from strategy_runtime import atomic_json
from datetime import datetime


class LoopTests(unittest.TestCase):
    def run_states(self, states, coins=19600, failed_click=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            config=Path(auto_bot.__file__).with_name('strategy_config.json').read_text()
            (root/'strategy_config.json').write_text(config)
            atomic_json(root/'daily_coins.json', {'date':datetime.now().strftime('%Y-%m-%d'),'coins':coins,'fails':0})
            fake_card=SimpleNamespace(card_id=0,rank='2',rank_score=1,suit_score=1,rank_margin=1)
            recognizer=SimpleNamespace(recognize=lambda img: ([fake_card]*5,[(0,0,1,1)]*5))
            calls=[]
            def click(*args,**kwargs):
                calls.append(args[1]); return not failed_click
            iterator=iter(states)
            def detect(img):
                return next(iterator,'FULL')
            with patch.multiple(auto_bot, APP_DIR=root, RESOURCE_DIR=root, bot_running=True), \
                 patch.object(auto_bot,'CardRecognizer',return_value=recognizer), \
                 patch.object(auto_bot,'capture_game_window',return_value=(np.zeros((1,1,3),dtype=np.uint8),0,0)), \
                 patch.object(auto_bot,'detect_game_state',side_effect=detect), \
                 patch.object(auto_bot,'read_screen_number',return_value=400), \
                 patch.object(auto_bot,'read_result_number',return_value=200), \
                 patch.object(auto_bot,'calculate_best',return_value=(SimpleNamespace(held_indices=()),[])), \
                 patch.object(auto_bot,'find_and_click_icon',side_effect=click), \
                 patch.object(auto_bot.time,'sleep'), patch('builtins.print'):
                auto_bot.auto_play_loop('time_target')
            ledger=json.loads((root/'daily_coins.json').read_text())
            events=[json.loads(line) for line in (root/'strategy_events.jsonl').read_text().splitlines()]
            return ledger,events,calls

    def test_result_flicker_does_not_duplicate_income(self):
        ledger,events,_=self.run_states(['HOLD_CARDS','ASK_CHALLENGE','ASK_CHALLENGE','RESULT','RESULT','UNKNOWN','RESULT','RESULT','FULL'])
        self.assertEqual(ledger['coins'],19800)
        self.assertEqual(sum(e['event']=='settlement' for e in events),1)
        self.assertEqual(sum(e['event']=='target_reached' for e in events),1)

    def test_takeover_at_existing_result_does_not_recredit(self):
        ledger,events,_=self.run_states(['RESULT','RESULT','FULL'])
        self.assertEqual(ledger['coins'],19600)
        self.assertTrue(any(e['event']=='existing_settlement_skipped' for e in events))

    def test_fail_flicker_does_not_duplicate_loss(self):
        ledger,_,_=self.run_states(['HOLD_CARDS','FAIL','UNKNOWN','FAIL','FULL'])
        self.assertEqual(ledger['fails'],1)

    def test_failed_click_does_not_book_unsettled_reward(self):
        ledger,events,_=self.run_states(['HOLD_CARDS','ASK_CHALLENGE','ASK_CHALLENGE','FULL'],failed_click=True)
        self.assertEqual(ledger['coins'],19600)
        self.assertFalse(any(e['event']=='settlement' for e in events))

    def test_takeover_at_existing_failure_does_not_charge(self):
        ledger,_,_=self.run_states(['FAIL','FAIL','FULL'])
        self.assertEqual(ledger['fails'],0)


if __name__=='__main__':
    unittest.main()
