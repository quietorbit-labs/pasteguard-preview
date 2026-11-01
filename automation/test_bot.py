import unittest,datetime as dt
from unittest.mock import patch
import bot
class GuardTests(unittest.TestCase):
 def test_missing_metrics_never_selects_winner(self):
  with patch.dict('os.environ',{},clear=True):self.assertEqual(bot.assessment()['decision'],'explore_no_winner')
 def test_plan_always_uses_fake_data_and_limits(self):
  for i in range(18):
   p=bot.plan({'decision':'explore_no_winner'},dt.date(2026,11,1)+dt.timedelta(days=i))
   self.assertIn('Can miss secrets',p['caption']);self.assertIn(p['example']['secret'],p['example']['text'])
 def test_wrong_account_blocks(self):
  with patch.dict('os.environ',{'IG_ACCESS_TOKEN':'test','IG_USER_ID':'123'},clear=True),patch('bot.ig',return_value={'username':'someone_else'}):
   with self.assertRaises(bot.SetupRequired):bot.assessment()
 def test_missing_auth_blocks_publish(self):
  with self.assertRaises(bot.SetupRequired):bot.publish({'date':'2026-11-01'},{'instagram_connected':False})
 def test_pending_publish_never_retries_post(self):
  with patch.dict('os.environ',{'IG_PUBLISH_ENABLED':'true','GITHUB_REF_NAME':'main','IG_USER_ID':'123'},clear=True),patch('bot.load_ledger',return_value=({'days':{'2026-11-01':{'phase':'publishing'}}},'sha')),patch('bot.ig') as api:
   with self.assertRaises(bot.SetupRequired):bot.publish({'date':'2026-11-01'},{'instagram_connected':True})
   api.assert_not_called()
 def test_existing_same_day_manual_post_skips(self):
  with patch.dict('os.environ',{'IG_PUBLISH_ENABLED':'true','GITHUB_REF_NAME':'main','IG_USER_ID':'123'},clear=True),patch('bot.load_ledger',return_value=({'days':{}},None)),patch('bot.save_ledger'),patch('bot.ig') as api:
   data={'instagram_connected':True,'_recent':[{'media':{'id':'m','timestamp':'2026-11-01T20:00:00Z'}}]}
   self.assertEqual(bot.publish({'date':'2026-11-01'},data),'already_posted_today');api.assert_not_called()
if __name__=='__main__':unittest.main()
