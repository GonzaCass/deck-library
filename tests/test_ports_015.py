import io,json,pathlib,tempfile,threading,unittest,hashlib,zipfile,shutil
from unittest.mock import patch
from deck_library import ports,originals,catalog_sources,project2099_update,project2099,updates,presets
from deck_library.models import Entry,Store

class PortImprovements(unittest.TestCase):
    def test_live_metadata_survives_old_lists_and_cache_normalization(self):
        def get(url):
            if '/release-status?' in url:return {'items':[{'slug':'native','provider':'github','repository':'author/native'}],'isDone':True}
            if '/apps?' in url:return {'items':[{'slug':'native','projectName':'Native Port','games':[{'title':'Original Game'}],'description':'A native version.','libraryArt':{'capsule':'https://cdn.example/cover.jpg'},'artwork':'https://cdn.example/icon.png'}],'isDone':True}
            return {'apps':[{'repository':'author/native','name':'Old project name'}]}
        rows=ports.fetch_catalog(get);item=rows[0]
        self.assertEqual(item['name'],'Native Port');self.assertEqual(item['game_title'],'Original Game');self.assertEqual(item['description'],'A native version.')
        normalized=ports.clean(item)
        self.assertEqual(normalized['icon'],'https://cdn.example/cover.jpg');self.assertEqual(normalized['icon_fallback'],'https://cdn.example/icon.png')
        self.assertEqual(normalized['description'],'A native version.')

    def test_failed_capsule_uses_the_project_icon_and_caches_it(self):
        from deck_library import cover_provider
        with tempfile.TemporaryDirectory() as tmp:
            item={'name':'Native','icon':'https://cdn.example/cover','icon_fallback':'https://cdn.example/icon','list':''};png=b'\x89PNG'+b'x'*(2*1024*1024+1)
            def request(url,**kwargs):
                if url.endswith('/cover'):raise OSError('temporarily unavailable')
                self.assertGreater(kwargs['limit'],len(png));return png
            with patch.object(cover_provider,'request',side_effect=request) as download:
                store=Store(tmp);path=ports.icon_path(store,item);self.assertEqual(pathlib.Path(path).read_bytes(),png)
                self.assertEqual(ports.icon_path(store,item),path);self.assertEqual(download.call_count,2)

    def test_failed_images_are_retried_after_the_backoff(self):
        from deck_library import cover_provider
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);item={'name':'Native','icon':'https://cdn.example/cover','list':''}
            with patch.object(cover_provider,'request',side_effect=OSError('offline')) as download:
                self.assertEqual(ports.icon_path(store,item),'');self.assertEqual(ports.icon_path(store,item),'');self.assertEqual(download.call_count,1)
            marker=next((store.root/'catalog-icons').glob('*.none'))
            import os,time
            expired=time.time()-ports.ICON_RETRY_SECONDS-1;os.utime(marker,(expired,expired))
            with patch.object(cover_provider,'request',return_value=b'\x89PNGimage') as download:
                path=ports.icon_path(store,item);self.assertTrue(path);self.assertEqual(download.call_count,1)
            self.assertFalse(marker.exists())
            pathlib.Path(path).unlink();marker.write_bytes(b'')
            with patch.object(cover_provider,'request',return_value=b'\x89PNGimage') as download:
                self.assertTrue(ports.icon_path(store,item));self.assertEqual(download.call_count,1)

    def test_missing_artwork_search_uses_the_original_game_title(self):
        from deck_library import cover_provider
        with tempfile.TemporaryDirectory() as tmp,patch.object(cover_provider,'search',return_value=[{'title':'Original Game','url':'https://cdn.example/cover'}]) as search,patch.object(cover_provider,'request',return_value=b'\x89PNGimage'):
            self.assertTrue(ports.icon_path(Store(tmp),{'name':'Obscure Project','game_title':'Original Game','list':'Nintendo 64'}))
            self.assertEqual(search.call_args.args[0],'Original Game')

    def test_current_catalog_uses_pagination_dates_and_release_repository(self):
        def get(url):
            if '/release-status?' in url:return {'items':[{'slug':'one','provider':'github','repository':'author/game'}],'isDone':True}
            return {'items':[{'slug':'one','name':'Game','projectName':'Native','addedAt':100000,'lastReleaseAt':200000,'games':[{'title':'Game'}],'supportedOS':['linux']}],'isDone':True}
        rows=catalog_sources.quiver(get,ports.clean);self.assertEqual(rows[0]['repository'],'author/game');self.assertEqual(rows[0]['added_at'],100);self.assertEqual(rows[0]['release_at'],200);self.assertEqual(rows[0]['game_title'],'Game')
    def test_repeated_cursor_stops_instead_of_hanging(self):
        calls=[]
        def get(url):calls.append(url);return {'items':[],'nextCursor':'same','isDone':False}
        catalog_sources.pages('/apps?',get);self.assertEqual(len(calls),2)
    def test_independent_catalog_is_metadata_only(self):
        rows=catalog_sources.independent('## Nintendo\n### ⭐ [Game](https://github.com/author/game)\n### [Other](https://malicious.example/owner/repo)',ports.clean)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['repository'],'author/game')
    def test_original_port_alias_and_shared_disc_protection(self):
        port=Entry('Crash Team Racing: Turbocharged',['/bin/true']);original=Entry('CTR - Crash Team Racing',['/bin/true'],kind='emulated')
        self.assertEqual(originals.pairs([port,original]),[(original,[port])])
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);cue=root/'game.cue';track=root/'game.bin';cue.write_text('FILE "game.bin" BINARY\n');track.touch();original.source=str(cue)
            self.assertEqual(originals.files_for(original,[original]),[cue,track])
            shared=Entry('Shared',['/bin/false'],source=str(track))
            with self.assertRaises(ValueError):originals.files_for(original,[original,shared])
            other_cue=root/'other.cue';other_cue.write_text('FILE "game.bin" BINARY\n');shared.source=str(other_cue)
            with self.assertRaises(ValueError):originals.files_for(original,[original,shared])
            cue.write_text('FILE "../outside.bin" BINARY\n')
            with self.assertRaises(ValueError):originals.files_for(original,[original])
    def test_trash_requires_validated_files_and_never_hard_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp)/'own.iso';p.write_bytes(b'disc');e=Entry('Game',['/bin/true'],kind='emulated',source=str(p));seen=[]
            self.assertEqual(originals.trash(e,[e],lambda file:seen.append(file)),1);self.assertEqual(seen,[p]);self.assertTrue(p.exists())
    def test_cancelled_install_leaves_original_port_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);existing=root/'Game';existing.mkdir();(existing/'game').write_bytes(b'original');cancel=threading.Event();cancel.set()
            with self.assertRaises(ports.Cancelled):ports.install({'repository':'a/game','folderName':'Game'},Store(root/'private'),root,cancel=cancel,replace=True)
            self.assertEqual((existing/'game').read_bytes(),b'original')
    def test_update_checker_reads_installed_project_build(self):
        entry=project2099.entry_for('/tmp/fake','2.0.0-beta.5')
        self.assertIsNone(updates.check_project2099([entry],lambda url:{'tag_name':'v2.0.0-beta.5'}))
    def test_custom_switch_profiles_follow_the_three_primary_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);e=Entry('Title',['/bin/true'],platform='Switch',game_id='0100abcdef120000');custom=presets.recommended(e,s)[0];custom['id']='custom-choice';p=pathlib.Path(tmp)/'input.json';p.write_text(json.dumps(custom));presets.import_preset(p,s)
            rows=presets.recommended(e,s);self.assertNotIn('custom-choice',[r['id'] for r in rows[:3]]);self.assertIn('custom-choice',[r['id'] for r in rows[3:]])

class ProjectUpdateTests(unittest.TestCase):
    def fixture(self,root):
        store=Store(root/'private');folder=root/'game';folder.mkdir();(folder/'SpiderManEOT.exe').write_bytes(b'old');(folder/'rexruntime.dll').write_bytes(b'old');(folder/'UserData').mkdir();(folder/'UserData/save.bin').write_bytes(b'save')
        entry=project2099.entry_for(folder,project2099.VERSION);store.save([entry]);source=root/'game.iso';data=bytearray(65536+100);data[65536:65554]=b'MICROSOFT*XBOX*MEDIA';source.write_bytes(data)
        tag='2.0.0-beta.5';cache=store.root/'downloads/project2099'/tag;cache.mkdir(parents=True);setup=cache/'Project2099-Beta5-Setup.exe';setup.write_bytes(b'PE'+ '--install-test'.encode('utf-16le'));payload=cache/'Project2099-Beta5-Payload.zip'
        with zipfile.ZipFile(payload,'w') as z:z.writestr('payload/payload-manifest.json','{}')
        assets=[{'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest(),'browser_download_url':'https://github.com/GenryTheFox0/Project-2099/releases/download/v'+tag+'/'+p.name} for p in (setup,payload)]
        return store,folder,entry,source,{'tag_name':'v'+tag,'assets':assets}
    def test_staged_update_preserves_save_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store,folder,e,source,release=self.fixture(pathlib.Path(tmp))
            def runner(command,*_):
                stage=pathlib.Path(command[5][2:].replace('\\','/'));stage.mkdir();(stage/'SpiderManEOT.exe').write_bytes(b'new');(stage/'rexruntime.dll').write_bytes(b'new')
            with patch.object(presets,'busy',return_value=False),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')),patch.object(project2099,'proton_env',return_value={}),patch('shutil.disk_usage',return_value=shutil._ntuple_diskusage(100<<30,0,100<<30)):
                result=project2099_update.update(e,source,release,store,runner=runner)
            self.assertEqual((folder/'SpiderManEOT.exe').read_bytes(),b'new');self.assertEqual((folder/'UserData/save.bin').read_bytes(),b'save');self.assertEqual((pathlib.Path(result['backup'])/'SpiderManEOT.exe').read_bytes(),b'old');self.assertEqual(store.load()[0].metadata['build'],'2.0.0-beta.5')
    def test_failure_keeps_old_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store,folder,e,source,release=self.fixture(pathlib.Path(tmp))
            with patch.object(presets,'busy',return_value=False),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')),patch.object(project2099,'proton_env',return_value={}),patch('shutil.disk_usage',return_value=shutil._ntuple_diskusage(100<<30,0,100<<30)),self.assertRaises(RuntimeError):
                project2099_update.update(e,source,release,store,runner=lambda *_:(_ for _ in ()).throw(RuntimeError('Installer failed')))
            self.assertEqual((folder/'SpiderManEOT.exe').read_bytes(),b'old')

    def test_retained_xbox_data_is_detected_without_the_old_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            store,folder,e,source,release=self.fixture(pathlib.Path(tmp));data=folder/'Data/Original'
            for name in ('Default.xex','Data/Main.pkz','Data/BaseGameplay.pkz'):
                file=data/name;file.parent.mkdir(parents=True,exist_ok=True);file.touch()
            self.assertEqual(project2099_update.source_for(e,[e]),str(data))
