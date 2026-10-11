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

PNG=b'\x89PNG\r\n\x1a\n'+b'x'*40

class SteamArtTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data');self.cfg=self.root/'steam/userdata/1/config';self.cfg.mkdir(parents=True)
    def tearDown(self):self.tmp.cleanup()
    def test_existing_slots_are_detected_and_an_icon_may_be_an_ico(self):
        from deck_library import steamart
        grid=self.cfg/'grid';grid.mkdir();(grid/'123p.png').write_bytes(PNG);(grid/'123_icon.ico').write_bytes(b'ico');found=steamart.existing(self.cfg,123)
        self.assertEqual((found['portrait'].name,found['icon'].name,found['hero'],found['logo']),('123p.png','123_icon.ico',None,None))
    def test_a_new_file_is_written_with_the_logo_position_and_a_replacement_keeps_a_backup(self):
        from deck_library import steamart
        source=self.root/'a.png';source.write_bytes(PNG)
        self.assertTrue(steamart.write(self.cfg,3000000000,'logo',source,lambda:False));grid=self.cfg/'grid'
        self.assertEqual((grid/'3000000000_logo.png').read_bytes(),PNG);self.assertIn('BottomLeft',(grid/'3000000000.json').read_text())
        self.assertFalse(steamart.write(self.cfg,3000000000,'logo',source,lambda:False))
        other=self.root/'b.jpg';other.write_bytes(b'\xff\xd8\xff'+b'y'*30);self.assertTrue(steamart.write(self.cfg,3000000000,'logo',other,lambda:False))
        self.assertTrue((grid/'3000000000_logo.jpg').is_file());self.assertFalse((grid/'3000000000_logo.png').exists());self.assertEqual(len(list((grid/'.deck-library-backups').glob('3000000000_logo.png.*'))),1)
    def test_nothing_is_written_while_steam_runs_and_non_images_are_refused(self):
        from deck_library import steamart
        from deck_library.steam import SteamRunningError
        source=self.root/'a.png';source.write_bytes(PNG)
        with self.assertRaises(SteamRunningError):steamart.write(self.cfg,5,'hero',source,lambda:True)
        self.assertFalse((self.cfg/'grid/5_hero.png').exists())
        bad=self.root/'x.png';bad.write_bytes(b'<html>');
        with self.assertRaises(ValueError):steamart.write(self.cfg,5,'hero',bad,lambda:False)
    def test_candidates_skip_adult_humor_and_insecure_items(self):
        from deck_library import steamart
        data=json.dumps({'data':[{'id':1,'url':'https://x/a.png','thumb':'https://x/t.png','width':600,'height':900,'author':{'name':'n'}},{'id':2,'url':'https://x/b.png','nsfw':True},{'id':3,'url':'http://x/c.png'},{'id':4,'url':'https://x/d.png','humor':True}]}).encode()
        urls=[];rows=steamart.candidates('key',77,'portrait',request=lambda u,k,limit=0:(urls.append(u),data)[1])
        self.assertEqual([r['id'] for r in rows],[1]);self.assertIn('dimensions=600x900',urls[0]);self.assertIn('nsfw=false',urls[0])
    def test_queued_art_waits_for_steam_then_is_written_by_the_sync(self):
        from deck_library import steamart
        from deck_library.service import queue_art
        staged=steamart.stage(self.store,3000000001,'hero',PNG,'.png')
        with patch('deck_library.service.steam_running',return_value=True):
            self.assertEqual(queue_art([{'appid':3000000001,'slot':'hero','file':staged}],self.cfg,self.store,start_worker=False)['state'],'pending')
            queue_art([{'appid':3000000001,'slot':'hero','file':staged},{'appid':3000000001,'slot':'nonsense','file':staged}],self.cfg,self.store,start_worker=False)
        self.assertEqual(len(json.loads((self.store.root/'pending.json').read_text())['art']),1);self.assertFalse((self.cfg/'grid').exists())
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False):result=sync(self.store,wait=False)
        self.assertEqual((result['state'],result.get('art')),('saved',1));self.assertEqual((self.cfg/'grid/3000000001_hero.png').read_bytes(),PNG);self.assertFalse((self.store.root/'pending.json').exists())

class CompleteArtTests(SteamArtTests):
    def entry(self,name,appid,**meta):
        from deck_library.models import Entry
        return Entry(name,['/bin/true'],metadata={'steam_appid':appid,'steam_account':str(self.cfg),**meta})
    def test_only_empty_slots_are_filled_and_one_failing_game_does_not_stop_the_rest(self):
        from deck_library import steamart
        grid=self.cfg/'grid';grid.mkdir();(grid/'3000000010p.png').write_bytes(PNG)
        def request(url,key='',limit=0,timeout=0):
            if 'search/autocomplete/Broken' in url:raise OSError('boom')
            if 'search/autocomplete' in url:return json.dumps({'data':[{'id':9,'name':'Game'}]}).encode()
            if '/game/' in url:return json.dumps({'data':[{'id':1,'url':'https://x/i.png','thumb':'https://x/t.png'}]}).encode()
            return PNG
        entries=[self.entry('Complete',3000000011),self.entry('Broken',3000000012),self.entry('Game',3000000010),self.entry('Store',3000000013,steam_store=True)]
        for slot,suffix in (('hero','_hero'),('logo','_logo'),('icon','_icon'),('banner','')):(grid/('3000000011'+suffix+'.png')).write_bytes(PNG)
        (grid/'3000000011p.png').write_bytes(PNG)
        items,report=steamart.complete_missing('k',entries,self.store,request=request,pause=0);names=dict(report)
        self.assertEqual(names['Complete'],'completo');self.assertTrue(names['Broken'].startswith('error'));self.assertTrue(names['Game'].startswith('se agregó'));self.assertNotIn('Store',names)
        self.assertEqual(sorted(i['slot'] for i in items),['banner','hero','icon','logo']);self.assertTrue(all(i['appid']==3000000010 for i in items))
