import json,pathlib,struct,tempfile,unittest
from unittest.mock import patch
from deck_library.models import Entry,Store
from deck_library.steam import active_account,read_kv,get,update_shortcuts
from deck_library.service import queue_entries,sync

class ServiceTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data');self.cfg=self.root/'steam/config';self.cfg.mkdir(parents=True)
    def tearDown(self):self.tmp.cleanup()
    def test_queue_survives_steam_running_and_merges_selection(self):
        a=Entry('A',['/bin/true']);b=Entry('B',['/bin/false'])
        with patch('deck_library.service.steam_running',return_value=True):
            result=queue_entries([a],self.cfg,self.store,start_worker=False)
            queue_entries([b],self.cfg,self.store,start_worker=False)
        self.assertEqual(result['state'],'pending');self.assertFalse((self.cfg/'shortcuts.vdf').exists());self.assertEqual(len(json.loads((self.store.root/'pending.json').read_text())['ids']),2)
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False):
            result=sync(self.store,wait=False)
        self.assertEqual(result['count'],2);self.assertFalse((self.store.root/'pending.json').exists());self.assertTrue((self.cfg/'shortcuts.vdf').exists())
    def test_a_second_steam_account_is_not_silently_mixed(self):
        e=Entry('A',['/bin/true'])
        with patch('deck_library.service.steam_running',return_value=True):
            queue_entries([e],self.cfg,self.store,start_worker=False)
            with self.assertRaises(ValueError):queue_entries([e],self.root/'another',self.store,start_worker=False)
        self.assertEqual(json.loads((self.store.root/'pending.json').read_text())['account'],str(self.cfg))
    def test_selection_arriving_during_sync_is_saved_too(self):
        a=Entry('A',['/bin/true']);b=Entry('B',['/bin/false']);calls=[]
        with patch('deck_library.service.steam_running',return_value=True):queue_entries([a],self.cfg,self.store,start_worker=False)
        def write(account,entries,launcher):
            calls.append([e.name for e in entries])
            if len(calls)==1:
                with patch('deck_library.service.steam_running',return_value=True):queue_entries([b],self.cfg,self.store,start_worker=False)
            return [{'name':e.name} for e in entries],None
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.service.update_shortcuts',side_effect=write):sync(self.store,wait=False)
        self.assertEqual(calls,[['A'],['A','B']]);self.assertFalse((self.store.root/'pending.json').exists())
    def test_rescan_does_not_reset_user_edits(self):
        e=Entry('Original',['/bin/true']);self.store.save([e]);e.name='Edited';e.mods=False;self.store.save([e])
        found=Entry('Original',['/bin/true'],id=e.id);self.store.merge([found],overwrite=False)
        saved=self.store.load()[0];self.assertEqual(saved.name,'Edited');self.assertFalse(saved.mods)
    def test_same_name_on_different_systems_creates_two_shortcuts(self):
        a=Entry('Same',['/bin/true'],platform='Switch');b=Entry('Same',['/bin/false'],platform='PS2')
        update_shortcuts(self.cfg,[a,b],lambda e:self.root/(e.id+'.sh'),lambda:False)
        root=read_kv((self.cfg/'shortcuts.vdf').read_bytes())['shortcuts'][1]
        self.assertEqual(len(root),2);self.assertEqual({get(v[1],'appname') for v in root.values()},{'Same · Switch','Same · PS2'})
    def test_account_detection_uses_login_state_not_arbitrary_folder(self):
        root=self.root/'home/.local/share/Steam';(root/'config').mkdir(parents=True)
        for number in (123,456):(root/'userdata'/str(number)/'config').mkdir(parents=True)
        (root/'config/loginusers.vdf').write_text('"users"\n{\n "76561197960265851"\n {\n "Timestamp" "100"\n }\n "76561197960266184"\n {\n "Timestamp" "200"\n }\n}\n')
        self.assertEqual(active_account(self.root/'home'),(root/'userdata/456/config').resolve())
    def test_unsafe_entry_identifier_is_rejected(self):
        with self.assertRaises(ValueError):Entry('Bad',['/bin/true'],id='../unsafe')
