import shutil,hashlib,io,json,os,pathlib,struct,tarfile,tempfile,unittest
from unittest.mock import patch
from deck_library import controllers,updates
from deck_library.models import Entry,Store
from deck_library.steam import read_kv,write_kv,get,remove_shortcuts,move_artwork_aside,SteamRunningError,update_shortcuts
from deck_library.service import queue_entries,queue_removals,queue_controllers,sync
from deck_library.steam_inventory import prune

def fake_steam(root):
    """Minimal Steam tree: account config, templates and an existing Deck configset."""
    config=root/'steam/userdata/42/config';config.mkdir(parents=True)
    templates=root/'steam/controller_base/templates';templates.mkdir(parents=True)
    for family in controllers.FAMILIES:(templates/f'controller_{family}_gamepad_joystick.vdf').write_text('"controller_mappings"\n{\n}\n')
    sets=root/'steam/steamapps/common/Steam Controller Configs/42/config';sets.mkdir(parents=True)
    (sets/'configset_controller_neptune.vdf').write_text('"controller_config"\n{\n\t"3581851636"\n\t{\n\t\t"template"\t\t"controller_neptune_gamepad_joystick.vdf"\n\t}\n\t"550"\n\t{\n\t\t"workshop"\t\t"123"\n\t}\n}\n')
    return config,sets

class ControllerTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.config,self.sets=fake_steam(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_ids_use_unsigned_and_signed_forms(self):
        self.assertEqual(controllers.keys_for(3581851636),['3581851636','-713115660']);self.assertEqual(controllers.keys_for(1250),['1250'])
    def test_dualsense_gets_gamepad_template_and_deck_choice_is_kept(self):
        before=(self.sets/'configset_controller_neptune.vdf').read_text()
        result=controllers.apply(self.config,[3581851636],is_running=lambda:False)
        ps5=controllers.read_configset(self.sets/'configset_controller_ps5.vdf')
        self.assertEqual({k:dict(v)['template'] for k,v in ps5},{'3581851636':'controller_ps5_gamepad_joystick.vdf','-713115660':'controller_ps5_gamepad_joystick.vdf'})
        self.assertEqual(sorted(result['families']),sorted(controllers.FAMILIES))
        neptune=(self.sets/'configset_controller_neptune.vdf').read_text()
        self.assertIn('"-713115660"',neptune);self.assertIn('"workshop"\t\t"123"',neptune);self.assertTrue(neptune.startswith(before.split('\t"3581851636"')[0]))
    def test_existing_choice_is_only_replaced_when_forced(self):
        (self.sets/'configset_controller_ps5.vdf').write_text('"controller_config"\n{\n\t"3581851636"\n\t{\n\t\t"workshop"\t\t"999"\n\t}\n}\n')
        controllers.apply(self.config,[3581851636],families=['ps5'],is_running=lambda:False)
        self.assertIn('workshop',dict(controllers.read_configset(self.sets/'configset_controller_ps5.vdf')[0][1]))
        result=controllers.apply(self.config,[3581851636],families=['ps5'],force=True,is_running=lambda:False)
        self.assertEqual(dict(controllers.read_configset(self.sets/'configset_controller_ps5.vdf')[0][1])['template'],'controller_ps5_gamepad_joystick.vdf')
        self.assertTrue(result['backups'] and pathlib.Path(result['backups'][0]).is_file())
    def test_nothing_is_written_while_steam_runs(self):
        with self.assertRaises(SteamRunningError):controllers.apply(self.config,[1],is_running=lambda:True)
        self.assertFalse((self.sets/'configset_controller_ps5.vdf').exists())
    def test_second_run_changes_nothing(self):
        controllers.apply(self.config,[7],is_running=lambda:False);self.assertEqual(controllers.apply(self.config,[7],is_running=lambda:False)['changed'],0)
    def test_forget_removes_only_that_shortcut(self):
        controllers.apply(self.config,[3581851636,550],is_running=lambda:False)
        self.assertGreater(controllers.forget(self.config,[3581851636],is_running=lambda:False),0)
        keys=[k for k,_ in controllers.read_configset(self.sets/'configset_controller_ps5.vdf')];self.assertEqual(keys,['550'])
        self.assertIn('"550"',(self.sets/'configset_controller_neptune.vdf').read_text())
    def test_status_reports_missing_family(self):
        state=controllers.status(self.config,3581851636);self.assertEqual(state['neptune'],'controller_neptune_gamepad_joystick.vdf');self.assertIsNone(state['ps5'])

class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data');self.config,self.sets=fake_steam(self.root)
        self.a=Entry('A',['/bin/true']);self.b=Entry('B',['/bin/false'])
        self.unmanaged={'appname':(1,'Otro'),'appid':(2,struct.pack('<I',0xf0000001)),'exe':(1,'"/x"')}
        (self.config/'shortcuts.vdf').write_bytes(write_kv({'shortcuts':(0,{'0':(0,self.unmanaged)})}))
        update_shortcuts(self.config,[self.a,self.b],lambda e:self.root/(e.id+'.sh'),lambda:False)
        root=read_kv((self.config/'shortcuts.vdf').read_bytes())['shortcuts'][1];self.ids={get(v[1],'appname'):get(v[1],'appid') for v in root.values()}
    def tearDown(self):self.tmp.cleanup()
    def test_remove_keeps_others_renumbers_and_backs_up(self):
        old=(self.config/'shortcuts.vdf').read_bytes()
        removed,backup=remove_shortcuts(self.config,[self.ids['A']],lambda:False)
        root=read_kv((self.config/'shortcuts.vdf').read_bytes())['shortcuts'][1]
        self.assertEqual(removed,['A']);self.assertEqual(sorted(root),['0','1']);self.assertEqual({get(v[1],'appname') for v in root.values()},{'Otro','B'})
        self.assertEqual(pathlib.Path(backup).read_bytes(),old)
    def test_unknown_id_changes_nothing(self):
        before=(self.config/'shortcuts.vdf').read_bytes();self.assertEqual(remove_shortcuts(self.config,[12345],lambda:False),([],None));self.assertEqual((self.config/'shortcuts.vdf').read_bytes(),before)
    def test_refused_while_steam_runs(self):
        with self.assertRaises(SteamRunningError):remove_shortcuts(self.config,[self.ids['A']],lambda:True)
    def test_artwork_is_moved_not_deleted(self):
        grid=self.config/'grid';grid.mkdir();n=self.ids['A'];(grid/f'{n}p.png').write_bytes(b'x');(grid/f'{n}_hero.jpg').write_bytes(b'y');(grid/'999p.png').write_bytes(b'z')
        self.assertEqual(move_artwork_aside(self.config,[n]),2);self.assertTrue((grid/'999p.png').exists());self.assertEqual(len(list((grid/'.deck-library-backups').iterdir())),2)
    def test_queued_removal_runs_once_steam_is_closed_and_clears_layouts(self):
        controllers.apply(self.config,[self.ids['A']],is_running=lambda:False)
        with patch('deck_library.service.steam_running',return_value=True):
            result=queue_removals([self.ids['A']],self.config,self.store,start_worker=False)
        self.assertEqual(result['state'],'pending');self.assertEqual(json.loads((self.store.root/'pending.json').read_text())['remove'],[self.ids['A']])
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False),patch('deck_library.controllers.steam_running',return_value=False):
            result=sync(self.store,wait=False)
        self.assertEqual((result['state'],result['removed']),('saved',1));self.assertFalse((self.store.root/'pending.json').exists())
        names={get(v[1],'appname') for v in read_kv((self.config/'shortcuts.vdf').read_bytes())['shortcuts'][1].values()};self.assertNotIn('A',names)
        self.assertNotIn(str(self.ids['A']),[k for k,_ in controllers.read_configset(self.sets/'configset_controller_ps5.vdf')])
    def test_queued_layout_fix_replaces_a_wrong_saved_layout(self):
        (self.sets/'configset_controller_ps5.vdf').write_text('"controller_config"\n{\n\t"%d"\n\t{\n\t\t"template"\t\t"controller_ps5_wasd.vdf"\n\t}\n}\n'%self.ids['B'])
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False),patch('deck_library.controllers.steam_running',return_value=False):
            result=queue_controllers([self.ids['B']],self.config,self.store,start_worker=False)
        self.assertEqual(result['state'],'saved');self.assertEqual(result['layouts'],1)
        ps5=dict(controllers.read_configset(self.sets/'configset_controller_ps5.vdf'));self.assertEqual(dict(ps5[str(self.ids['B'])])['template'],'controller_ps5_gamepad_joystick.vdf')
    def test_adding_assigns_gamepad_layouts_for_all_families(self):
        c=Entry('C',['/bin/true'])
        with patch('deck_library.service.steam_running',return_value=False),patch('deck_library.steam.steam_running',return_value=False),patch('deck_library.controllers.steam_running',return_value=False):
            queue_entries([c],self.config,self.store,start_worker=False)
        appid=next(get(v[1],'appid') for v in read_kv((self.config/'shortcuts.vdf').read_bytes())['shortcuts'][1].values() if get(v[1],'appname')=='C')
        self.assertIn(str(appid),[k for k,_ in controllers.read_configset(self.sets/'configset_controller_ps5.vdf')])
    def test_pruning_forgets_missing_shortcuts_only_for_that_account(self):
        gone=Entry('Gone',['/x'],kind='steam',metadata={'steam_appid':5,'steam_account':'acc'});managed=Entry('M',['/y'],metadata={'steam_appid':6,'steam_account':'acc','steam_name':'M'})
        other=Entry('O',['/z'],kind='steam',metadata={'steam_appid':8,'steam_account':'other'});store=Entry('S',['/s'],kind='steam',metadata={'steam_store':True,'steam_appid':12210,'steam_account':'acc'})
        result=prune([gone,managed,other,store],'acc',{99})
        self.assertEqual([e.name for e in result],['M','O','S']);self.assertNotIn('steam_appid',managed.metadata)

class UpdateTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data')
    def tearDown(self):self.tmp.cleanup()
    def test_version_comparison(self):
        self.assertTrue(updates.is_newer('v0.4.0','0.3.4'));self.assertFalse(updates.is_newer('v0.3.4','0.3.4'));self.assertFalse(updates.is_newer('v0.3.3','0.3.4'));self.assertTrue(updates.is_newer('v0.10.0','0.9.9'));self.assertFalse(updates.is_newer('nightly','0.1'))
    def release(self,tag,assets=()):return {'tag_name':tag,'html_url':'https://github.com/x/y','body':'notas','assets':[{'name':n,'browser_download_url':'https://github.com/'+n} for n in assets]}
    def test_app_update_found_only_when_newer(self):
        get=lambda url:self.release('v0.4.0',['DeckLibrary-0.4.0.tar.gz','DeckLibrary-0.4.0.tar.gz.sha256'])
        info=updates.check_app('0.3.4',get);self.assertEqual((info['version'],info['name']),('0.4.0','DeckLibrary-0.4.0.tar.gz'));self.assertIsNone(updates.check_app('0.4.0',get))
    def test_missing_release_is_not_an_error(self):
        import urllib.error
        def get(url):raise urllib.error.HTTPError(url,404,'x',{},None)
        self.assertIsNone(updates.check_app('0.1',get))
    def test_quiver_ports_compare_installed_version_file(self):
        home=self.root/'home';q=home/'ports/quiver-launcher';(q/'Apps/Game-Port').mkdir(parents=True);(q/'Apps/Game-Port/version.txt').write_text('v1.0.0\n');(q/'Apps/Other').mkdir()
        (q/'apps.json').write_text(json.dumps({'apps':[{'name':'Game','folderName':'Game-Port','repository':'a/game'},{'name':'Uninstalled','folderName':'Nope','repository':'a/none'},{'name':'Other','folderName':'Other','repository':'a/other'}]}))
        found=updates.check_quiver({},lambda url:self.release('v1.2.0'),home);self.assertEqual([(u['name'],u['latest']) for u in found],[('Game','v1.2.0')])
        self.assertEqual(updates.check_quiver({},lambda url:self.release('v1.0.0'),home),[])
    def test_checks_are_cached_and_one_failure_does_not_hide_others(self):
        calls=[]
        def get(url):
            calls.append(url)
            if 'deck-library' in url:raise OSError('sin red')
            return self.release('v1.0.0')
        with patch.object(updates,'refresh_presets',return_value={'count':0,'new':0,'changed':0}):
            state=updates.check_all(self.store,{},[],force=True,get=get);self.assertTrue(state['errors']);self.assertIn('presets',state)
            total=len(calls);updates.check_all(self.store,{},[],get=get);self.assertEqual(len(calls),total)
    def package(self,files):
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w:gz') as tar:
            for name,body in files.items():
                info=tarfile.TarInfo(name);info.size=len(body);tar.addfile(info,io.BytesIO(body))
        return data.getvalue()
    def run_install(self,package,digest=None):
        digest=digest or hashlib.sha256(package).hexdigest();info={'version':'9.9.9','name':'DeckLibrary-9.9.9.tar.gz','archive':'https://github.com/a.tar.gz','checksum':'https://github.com/a.sha256'}
        def fetch(url,limit=0,timeout=0):return (digest+'  DeckLibrary-9.9.9.tar.gz\n').encode() if url.endswith('sha256') else package
        ran=[]
        with patch.object(updates,'fetch',fetch):
            return updates.install_update(info,self.store,lambda _:None,lambda *a,**k:(ran.append(a[0]) or type('R',(),{'returncode':0,'stdout':'','stderr':''})())),ran
    def test_verified_package_is_installed(self):
        version,ran=self.run_install(self.package({'DeckLibrary-9.9.9/install.py':b'print(1)'}));self.assertEqual(version,'9.9.9');self.assertTrue(ran[0][-1].endswith('install.py'))
    def test_wrong_checksum_is_rejected_without_running_anything(self):
        with self.assertRaises(ValueError):self.run_install(self.package({'DeckLibrary-9.9.9/install.py':b'x'}),'0'*64)
    def test_unsafe_paths_are_rejected(self):
        with self.assertRaises(ValueError):self.run_install(self.package({'../evil.py':b'x'}))
    def test_release_without_checksum_is_refused(self):
        with self.assertRaises(ValueError):updates.install_update({'archive':'https://github.com/a','checksum':None},self.store)
    def test_plain_http_is_refused(self):
        with self.assertRaises(ValueError):updates.fetch('http://example.com/x')

if __name__=='__main__':unittest.main()

class DuckStationTests(unittest.TestCase):
    def setUp(self):
        from deck_library import presets
        self.presets=presets;self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.home=self.root/'home'
        self.data=self.home/'.local/share/duckstation';(self.data/'gamesettings').mkdir(parents=True)
        (self.data/'settings.ini').write_text('[GPU]\nResolutionScale = 5\nPGXPEnable = false\nTextureFilter = Nearest\n[Display]\nMaxFPS = 0.000000\nVSync = true\n[Hotkeys]\nTogglePGXP = SDL-0/Back & SDL-0/Y\n')
        self.image=self.root/'game.bin';self.image.write_bytes(b'\0'*40000+b'BOOT = cdrom:\\SLES_012.34;1\r\nTCB = 4\r\n'+b'\0'*100)
        self.entry=Entry('Juego PS1',['/bin/true'],platform='PlayStation',source=str(self.image));self.store=Store(self.root/'data')
    def tearDown(self):self.tmp.cleanup()
    def patches(self):
        from contextlib import ExitStack
        stack=ExitStack();stack.enter_context(patch('pathlib.Path.home',return_value=self.home));stack.enter_context(patch.object(self.presets,'emulator_busy',return_value=False));return stack
    def test_serial_is_read_from_system_cnf_and_cue(self):
        self.assertEqual(self.presets.ps1_serial(self.image),'SLES-01234')
        cue=self.root/'game.cue';cue.write_text('FILE "game.bin" BINARY\n  TRACK 01 MODE2/2352\n');self.assertEqual(self.presets.ps1_serial(cue),'SLES-01234')
        self.assertEqual(self.presets.ps1_serial(self.root/'x.chd'),'')
    def test_chd_needs_a_manual_serial(self):
        entry=Entry('CHD',['/bin/true'],platform='PlayStation',source=str(self.root/'a.chd'))
        with self.patches(),self.assertRaisesRegex(ValueError,'serial'):self.presets.target_for(entry)
        entry.game_id='SLUS-00001'
        with self.patches():self.assertEqual(self.presets.target_for(entry).name,'SLUS-00001.ini')
    def test_editor_starts_from_global_values_and_writes_only_changes(self):
        with self.patches():
            current=self.presets.current_values(self.entry);self.assertEqual(current['GPU']['ResolutionScale'],5);self.assertIs(current['GPU']['PGXPEnable'],False)
            profile=self.presets.manual_profile(self.entry,{'GPU':{'ResolutionScale':3,'PGXPEnable':True},'Display':{'MaxFPS':60.0}})
            result=self.presets.apply(self.entry,profile,self.store)
            written=(self.data/'gamesettings/SLES-01234.ini').read_text();self.assertIn('ResolutionScale = 3',written);self.assertIn('PGXPEnable = true',written);self.assertNotIn('TextureFilter',written)
            self.assertIn('Hotkeys',(self.data/'settings.ini').read_text());self.assertEqual(result['changes'],3)
            self.presets.restore(self.entry,self.store);self.assertFalse((self.data/'gamesettings/SLES-01234.ini').exists())
    def test_unknown_options_and_out_of_range_values_are_rejected(self):
        with self.patches():
            for bad in ({'GPU':{'Renderer':'Software'}},{'GPU':{'ResolutionScale':99}},{'Main':{'EmulationSpeed':9.0}}):
                with self.assertRaises(ValueError):self.presets.manual_profile(self.entry,bad)
    def test_running_emulator_blocks_changes(self):
        with self.patches():
            profile=self.presets.manual_profile(self.entry,{'GPU':{'ResolutionScale':2}})
            with patch.object(self.presets,'emulator_busy',return_value=True),self.assertRaises(RuntimeError):self.presets.apply(self.entry,profile,self.store)

class IniPatchTests(unittest.TestCase):
    def test_repeated_keys_comments_and_other_sections_survive(self):
        from deck_library.presets import patch_ini
        text='; nota\n[Patches]\nEnable = A\nEnable = B\n\n[GPU]\nResolutionScale = 5\nOther = 1\n\n[Hotkeys]\nX = 1\nX = 2\n'
        out=patch_ini(text,{'GPU':{'ResolutionScale':3,'PGXPEnable':True},'Display':{'VSync':False}},spaced=True)
        self.assertIn('Enable = A\nEnable = B',out);self.assertIn('; nota',out);self.assertIn('ResolutionScale = 3',out);self.assertIn('PGXPEnable = true\n\n[Hotkeys]',out);self.assertIn('X = 1\nX = 2',out);self.assertTrue(out.endswith('[Display]\nVSync = false\n'))
    def test_empty_file_gets_sections(self):
        from deck_library.presets import patch_ini
        self.assertEqual(patch_ini('',{'GPU':{'A':1}}),'[GPU]\nA=1\n')

class PortCatalogTests(unittest.TestCase):
    def setUp(self):
        from deck_library import ports
        self.ports=ports;self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data');self.install_root=self.root/'ports'
    def tearDown(self):self.tmp.cleanup()
    def test_catalog_reads_lists_dedupes_and_drops_malformed_entries(self):
        def get(url):
            if url==self.ports.INDEX:return {'lists':[{'remoteLocation':'https://raw.githubusercontent.com/x/a.json'},{'remoteLocation':'https://evil.example/b.json'}]}
            return {'name':'Lista','apps':[{'name':'Uno','repository':'a/uno','folderName':'Uno'},{'name':'Dup','repository':'A/UNO'},{'repository':'no-slash'},{'repository':'a/../x'},'texto',{'name':'Dos','repository':'b/dos','folderName':'../escape'}]}
        apps=self.ports.fetch_catalog(get)
        self.assertEqual([a['repository'] for a in apps],['b/dos','a/uno']);self.assertEqual(apps[0]['folder'],'dos')
    def test_catalog_falls_back_to_the_last_copy_when_offline(self):
        self.ports.catalog(self.store,get=lambda url:{'lists':[{'remoteLocation':'https://raw.githubusercontent.com/x/a.json'}]} if url==self.ports.INDEX else {'apps':[{'repository':'a/uno'}]})
        def offline(url):raise OSError('sin red')
        self.assertEqual(self.ports.catalog(self.store,force=True,get=offline)[0]['repository'],'a/uno')
    def test_asset_choice_prefers_linux_x86_and_skips_other_systems(self):
        names=['Game-windows-x64.zip','Game-macos.dmg','Game-linux-aarch64.tar.gz','Game-linux-x86_64.zip','Game-linux-x86_64.tar.gz','Game.sha256','Source code.zip']
        self.assertEqual(self.ports.pick_asset([{'name':n} for n in names])['name'],'Game-linux-x86_64.tar.gz')
        self.assertEqual(self.ports.pick_asset([{'name':'Game-x86_64.AppImage'},{'name':'Game-linux.zip'}])['name'],'Game-x86_64.AppImage')
        self.assertIsNone(self.ports.pick_asset([{'name':'Game-win64.zip'},{'name':'checksums.txt'}]))
    def zip_bytes(self,files,mode=0o755):
        import zipfile,io
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            for name,body in files.items():
                info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,body)
        return data.getvalue()
    def install(self,files,digest=True,replace=False,assets=None):
        payload=self.zip_bytes(files);sha=hashlib.sha256(payload).hexdigest()
        release={'tag_name':'v1.0','html_url':'https://github.com/a/uno','assets':assets or [{'name':'Uno-linux-x86_64.zip','browser_download_url':'https://github.com/a/uno/x.zip','digest':('sha256:'+sha) if digest is True else digest}]}
        def fake_download(url,target,limit=0,progress=None):pathlib.Path(target).write_bytes(payload)
        with patch.object(self.ports,'download',fake_download):
            return self.ports.install({'name':'Uno','repository':'a/uno','folderName':'Uno'},self.store,self.install_root,lambda _:None,lambda url:release,replace)
    def test_install_flattens_verifies_and_registers_the_port(self):
        record=self.install({'Uno-1.0/Uno':b'\x7fELF....','Uno-1.0/data/a.bin':b'x'})
        folder=self.install_root/'Uno';self.assertEqual(record['executable'],'Uno');self.assertTrue(record['verified']);self.assertTrue((folder/'data/a.bin').is_file());self.assertTrue(os.access(folder/'Uno',os.X_OK))
        entry=self.ports.entry_for(folder);self.assertEqual(entry.command,[str(folder/'Uno')]);self.assertEqual(self.ports.records(self.store)['a/uno']['tag'],'v1.0')
    def test_wrong_digest_installs_nothing(self):
        with self.assertRaises(ValueError):self.install({'Uno':b'\x7fELF'},digest='sha256:'+'0'*64)
        self.assertFalse((self.install_root/'Uno').exists());self.assertEqual(self.ports.records(self.store),{})
    def test_unsafe_archive_paths_and_links_are_rejected(self):
        with self.assertRaises(ValueError):self.install({'../evil':b'x'})
        import zipfile,io
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            info=zipfile.ZipInfo('link');info.external_attr=(0o120777)<<16;z.writestr(info,'/etc/passwd')
        with self.assertRaises(ValueError),patch.object(self.ports,'download',lambda url,target,limit=0,progress=None:pathlib.Path(target).write_bytes(data.getvalue())):
            self.ports.install({'repository':'a/uno'},self.store,self.install_root,lambda _:None,lambda url:{'tag_name':'v1','assets':[{'name':'Uno-linux-x86_64.zip','browser_download_url':'https://github.com/x'}]})
    def test_existing_folder_is_kept_unless_replacing_and_old_copy_is_moved_aside(self):
        self.install({'Uno':b'\x7fELF1'})
        with self.assertRaises(ValueError):self.install({'Uno':b'\x7fELF2'})
        self.install({'Uno':b'\x7fELF2'},replace=True);self.assertEqual((self.install_root/'Uno/Uno').read_bytes(),b'\x7fELF2');self.assertEqual(len(list((self.install_root/'.deck-library-replaced').iterdir())),1)
    def test_release_without_linux_build_gives_a_clear_error(self):
        with self.assertRaisesRegex(ValueError,'Linux'):self.install({'a':b'x'},assets=[{'name':'Uno-win64.zip','browser_download_url':'https://github.com/x'}])
    def test_ambiguous_executable_is_left_unset(self):
        record=self.install({'one':b'\x7fELFa','two':b'\x7fELFb'});self.assertEqual(record['executable'],'');self.assertIsNone(self.ports.entry_for(self.install_root/'Uno'))
    def test_updates_compare_recorded_tag(self):
        self.install({'Uno':b'\x7fELF'})
        newer=lambda url:{'tag_name':'v1.1','html_url':'https://github.com/a','assets':[{'name':'Uno-linux-x86_64.zip'}]}
        self.assertEqual([u['latest'] for u in self.ports.installed_updates(self.store,newer)],['v1.1'])
        same=lambda url:{'tag_name':'v1.0','assets':[{'name':'Uno-linux-x86_64.zip'}]};self.assertEqual(self.ports.installed_updates(self.store,same),[])
    def test_installed_port_appears_in_the_library_scan(self):
        from deck_library.discovery import scan
        home=self.root/'home';self.install_root=home/'ports';self.install({'Uno':b'\x7fELF'})
        found=scan(home,preferences={'rom_roots':[],'port_roots':[],'quiver_roots':[],'emulators':{}})
        self.assertIn('Uno',[e.name for e in found])

class BareBinaryTests(PortCatalogTests):
    def test_bare_linux_binary_is_picked_and_installed_as_executable(self):
        self.assertEqual(self.ports.pick_asset([{'name':'Game.apk'},{'name':'Game-Linux'},{'name':'Game.exe'}])['name'],'Game-Linux')
        payload=b'\x7fELFbinary'
        release={'tag_name':'v2','assets':[{'name':'Game-Linux','browser_download_url':'https://github.com/a/g','digest':'sha256:'+hashlib.sha256(payload).hexdigest()}]}
        with patch.object(self.ports,'download',lambda url,target,limit=0,progress=None:pathlib.Path(target).write_bytes(payload)):
            record=self.ports.install({'repository':'a/game','folderName':'Game'},self.store,self.install_root,lambda _:None,lambda url:release)
        self.assertEqual(record['executable'],'Game-Linux');self.assertTrue(os.access(self.install_root/'Game/Game-Linux',os.X_OK))

class RateLimitTests(unittest.TestCase):
    def test_exhausted_quota_gets_a_clear_error_and_does_not_crash_checks(self):
        import urllib.error
        from email.message import Message
        headers=Message();headers['X-RateLimit-Remaining']='0'
        def blocked(*a,**k):raise urllib.error.HTTPError('https://api.github.com/x',403,'forbidden',headers,None)
        with patch('urllib.request.urlopen',blocked),self.assertRaisesRegex(updates.RateLimited,'limitó'):updates.fetch('https://api.github.com/x')
        tmp=tempfile.TemporaryDirectory();store=Store(tmp.name)
        def get(url):raise updates.RateLimited('límite')
        with patch.object(updates,'refresh_presets',return_value={'count':0,'new':0,'changed':0}):
            state=updates.check_all(store,{},[],force=True,get=get)
        self.assertTrue(state['errors']);tmp.cleanup()

class GithubLauncherTests(PortCatalogTests):
    def test_github_launcher_list_is_parsed_with_categories_and_ai_flag(self):
        document={'N64 Ports':[{'name':'Uno','repository':'a/uno','folderName':'Uno'}],'AI - PlayStation Ports':[{'name':'Dos','repository':'b/dos','folderName':'Dos'},'basura',{'repository':'../x'}],'Vacio':[],'meta':'texto'}
        rows=self.ports.parse_source(document,'GithubLauncher')
        self.assertEqual([(r['repository'],r['list'],r['ai']) for r in rows],[('a/uno','N64 Ports',False),('b/dos','PlayStation Ports',True)])
    def test_sources_merge_by_repository_and_record_every_origin(self):
        quiver={'lists':[{'remoteLocation':'https://raw.githubusercontent.com/q/a.json'}]}
        data={self.ports.INDEX:quiver,'https://raw.githubusercontent.com/q/a.json':{'name':'Nintendo','apps':[{'name':'Uno','repository':'a/uno'}]},self.ports.GHL_LIST:{'N64 Ports':[{'name':'Uno (otra)','repository':'A/Uno'},{'name':'Tres','repository':'c/tres'}]},'https://raw.githubusercontent.com/me/mine.json':{'apps':[{'repository':'d/cuatro'}]}}
        apps=self.ports.fetch_catalog(lambda url:data[url],extra=['https://raw.githubusercontent.com/me/mine.json','http://inseguro.example/x.json'])
        by={a['repository'].lower():a for a in apps};self.assertEqual(sorted(by),['a/uno','c/tres','d/cuatro'])
        self.assertEqual(by['a/uno']['list'],'N64 Ports');self.assertEqual(by['a/uno']['source'],'Quiver, GithubLauncher');self.assertEqual(by['d/cuatro']['source'],'Personalizada')
    def test_one_failing_source_does_not_hide_the_others(self):
        def get(url):
            if url==self.ports.INDEX:raise OSError('caído')
            return {'N64 Ports':[{'repository':'a/uno'}]}
        self.assertEqual([a['repository'] for a in self.ports.fetch_catalog(get)],['a/uno'])
        with self.assertRaises(OSError):self.ports.fetch_catalog(lambda url:(_ for _ in ()).throw(OSError('x')))
    def make_launcher(self,home,name,apps_path=None):
        root=home/'ports'/name;(root/'Apps/Uno').mkdir(parents=True);(root/'Apps/Uno/version.txt').write_text('v1.0');(root/'Apps/Uno/Uno').write_bytes(b'\x7fELF');(root/'Apps/Uno/Uno').chmod(0o755)
        (root/'apps.json').write_text(json.dumps({'apps':[{'name':'Uno','repository':'a/uno','folderName':'Uno'}]}));(root/'settings.json').write_text('{}');return root
    def test_a_renamed_github_launcher_install_is_found_for_updates_and_library(self):
        from deck_library.discovery import scan
        home=self.root/'home';self.make_launcher(home,'MiLanzador')
        prefs={'rom_roots':[],'port_roots':[],'quiver_roots':[],'emulators':{}}
        found=updates.quiver_apps(prefs,home);self.assertEqual([(f['name'],f['installed']) for f in found],[('Uno','v1.0')])
        self.assertEqual(updates.check_quiver(prefs,lambda url:{'tag_name':'v1.1','html_url':'https://github.com/a'},home)[0]['latest'],'v1.1')
        library=scan(home,preferences=prefs);self.assertEqual([e.name for e in library],['Uno']);self.assertFalse(any(e.name=='Milanzador' for e in library))
    def test_custom_apps_path_is_respected(self):
        from deck_library.installations import apps_folder
        home=self.root/'home';root=self.make_launcher(home,'GithubLauncher');elsewhere=self.root/'otro';(root/'Apps').rename(elsewhere);(root/'settings.json').write_text('﻿'+json.dumps({'AppsPath':str(elsewhere)}))
        self.assertEqual(apps_folder(root),elsewhere);self.assertEqual(len(updates.quiver_apps({},home)),1)

class CatalogExtrasTests(PortCatalogTests):
    def test_repository_text_is_parsed_strictly(self):
        for text,expected in (('https://github.com/a/uno','a/uno'),('a/uno','a/uno'),('https://github.com/a/uno.git','a/uno'),('https://github.com/a/uno/releases/tag/v1','a/uno'),('../x','None'),('http://evil.example/a/b','None'),('solo','None'),('a/..','None')):
            self.assertEqual(str(self.ports.parse_repository(text)),expected,text)
        self.assertFalse(self.ports.valid_repository('../x'))
    def test_builtin_spider_man_ports_and_custom_repositories_are_merged(self):
        remote=[self.ports.clean({'name':'Otro','repository':'x/otro'},'N64 Ports','Quiver')]
        entries=self.ports.merged(remote,{'custom_ports':[{'repository':'me/mi-port','name':'Mi port','category':'PlayStation','note':'ojo'},{'repository':'../mal'}]})
        by={e['repository']:e for e in entries}
        self.assertIn('alexbeavs-ps1-ports/spider-man-recomp',by);self.assertIn('alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp',by)
        self.assertEqual(by['alexbeavs-ps1-ports/spider-man-recomp']['source'],'Recomendado');self.assertIn('SLUS-00875',by['alexbeavs-ps1-ports/spider-man-recomp']['note']);self.assertIn('compila',by['alexbeavs-ps1-ports/spider-man-recomp']['note'])
        self.assertEqual((by['me/mi-port']['source'],by['me/mi-port']['list']),('Agregado','PlayStation'));self.assertNotIn('../mal',by)
    def test_custom_entry_overrides_remote_metadata_but_keeps_its_icon(self):
        remote=[self.ports.clean({'name':'Viejo','repository':'a/uno','appIconUrl':'https://cdn.example/i.png'},'N64 Ports','Quiver')]
        merged=self.ports.merged(remote,{'custom_ports':[{'repository':'a/uno','name':'Nuevo'}]})
        mine=next(m for m in merged if m['repository']=='a/uno');self.assertEqual((mine['name'],mine['icon']),('Nuevo','https://cdn.example/i.png'))
    def test_folder_and_category_survive_a_second_cleaning(self):
        once=self.ports.clean({'repository':'a/uno','folderName':'Carpeta','category':'PlayStation'},'','Agregado');twice=self.ports.clean(once)
        self.assertEqual((twice['folder'],twice['list']),('Carpeta','PlayStation'))
    def test_platform_guess_for_cover_lookup(self):
        self.assertEqual(self.ports.platform_for('PlayStation Ports'),'PlayStation');self.assertEqual(self.ports.platform_for('PlayStation 2'),'PlayStation 2');self.assertEqual(self.ports.platform_for('2D Game Ports'),'')
    def test_icons_are_downloaded_once_validated_and_failures_are_remembered(self):
        png=b'\x89PNG\r\n\x1a\n'+b'x'*20;calls=[]
        def request(url,key='',limit=0,timeout=0):
            calls.append(url);return png if 'ok' in url else b'<html>'
        from deck_library import cover_provider
        item={'name':'A','icon':'https://cdn.example/ok.png','list':''};bad={'name':'B','icon':'https://cdn.example/bad.png','list':''}
        with patch.object(cover_provider,'request',request):
            path=self.ports.icon_path(self.store,item);self.assertTrue(path.endswith('.png') and pathlib.Path(path).read_bytes()==png)
            self.ports.icon_path(self.store,item);self.assertEqual(self.ports.icon_path(self.store,bad),'');self.ports.icon_path(self.store,bad)
        self.assertEqual(calls,['https://cdn.example/ok.png','https://cdn.example/bad.png'])
    def test_box_art_is_searched_by_platform_when_there_is_no_icon(self):
        from deck_library import cover_provider
        row={'title':'Spider-Man 2 - Enter - Electro (USA)','url':'https://thumbnails.libretro.com/x.png','provider':'Libretro','page':''}
        png=b'\x89PNG\r\n\x1a\n'+b'y'*8
        with patch.object(cover_provider,'search',return_value=[row]) as search,patch.object(cover_provider,'request',return_value=png):
            path=self.ports.icon_path(self.store,{'name':'Spider-Man 2: Enter Electro (PSX)','icon':'','list':'PlayStation'})
        self.assertTrue(path);self.assertEqual(search.call_args[0][1]['_artwork_platform'],'PlayStation')
        self.assertEqual(self.ports.icon_path(self.store,{'name':'Algo','icon':'','list':'2D Game Ports'}),'')

class BuildEnvironmentTests(PortCatalogTests):
    def test_wrapper_runs_the_program_inside_the_sdk_with_display_audio_input_and_home(self):
        from deck_library import buildenv
        command=buildenv.wrap(['/home/u/ports/Kit/Launcher','--x'])
        self.assertTrue(command[0].endswith('flatpak'));self.assertEqual(command[1],'run');self.assertIn('--devel',command);self.assertIn('--share=network',command);self.assertIn('--device=all',command);self.assertIn('--filesystem=home',command);self.assertIn('--command=/home/u/ports/Kit/Launcher',command)
        self.assertEqual(command[-2:],[buildenv.SDK,'--x']);self.assertTrue(buildenv.is_wrapped(command));self.assertFalse(buildenv.is_wrapped(['/bin/true']))
    def test_sdk_presence_and_installation_progress(self):
        from deck_library import buildenv
        ok=lambda *a,**k:type('R',(),{'returncode':0})();bad=lambda *a,**k:type('R',(),{'returncode':1})()
        self.assertTrue(buildenv.installed(ok));self.assertFalse(buildenv.installed(bad))
        class Proc:
            def __init__(self,code):self.stdout=iter(['Instalando… 10%\n','\n','Listo\n']);self.code=code
            def wait(self):return self.code
        lines=[];buildenv.install(lines.append,lambda *a,**k:Proc(0));self.assertEqual(lines,['Instalando… 10%','Listo'])
        with self.assertRaisesRegex(RuntimeError,'SDK'):buildenv.install(lambda _:None,lambda *a,**k:Proc(1))
    def test_a_setup_kit_is_detected_and_its_entry_is_wrapped(self):
        record=self.install({'Kit/Launcher':b'\x7fELF','Kit/CMakeLists.txt':b'project(x)','Kit/README-SETUP.txt':b'setup'})
        self.assertTrue(record['sandbox']);entry=self.ports.entry_for(self.install_root/'Uno')
        self.assertTrue(entry.command[0].endswith('flatpak'));self.assertEqual(entry.source,str(self.install_root/'Uno/Launcher'));self.assertEqual(entry.metadata['sandbox'],'flatpak-kde-sdk')
        plain=self.install({'Tool':b'\x7fELF'},replace=True);self.assertFalse(plain['sandbox']);self.assertEqual(self.ports.entry_for(self.install_root/'Uno').command,[str(self.install_root/'Uno/Tool')])
    def test_missing_sdk_blocks_launch_with_a_recognised_message(self):
        from deck_library import buildenv
        from deck_library.runtime import diagnostics
        entry=Entry('Kit',['/bin/true'],metadata={'sandbox':'flatpak-kde-sdk'})
        with patch.object(buildenv,'installed',return_value=False):issues,_=diagnostics(entry,self.store)
        self.assertTrue(any(i.startswith('Falta el entorno') for i in issues))
        with patch.object(buildenv,'installed',return_value=True):self.assertFalse(any(i.startswith('Falta el entorno') for i in diagnostics(entry,self.store)[0]))
    def test_builtin_spider_man_kits_are_flagged_for_the_sdk(self):
        kits={b['repository'] for b in self.ports.BUILTIN if b.get('setup')=='kit'};self.assertEqual(len(kits),2)
        flagged={a['repository'] for a in self.ports.merged([],{}) if a['kit']};self.assertEqual(flagged,kits|{'web/openpete','snesrev/zelda3'})

class KitRequirementTests(PortCatalogTests):
    def kit(self,fragment):return next(b for b in self.ports.merged([],{}) if fragment in b['repository'])
    def test_bios_is_found_by_exact_hash_in_the_emudeck_folder_whatever_its_name(self):
        home=self.root/'home';bios=home/'Emulation/bios';bios.mkdir(parents=True);data=b'B'*524288;(bios/'cualquier.bin').write_bytes(data);(bios/'otra.bin').write_bytes(b'C'*524288);(bios/'chica.bin').write_bytes(b'x')
        found=self.ports.find_bios([hashlib.sha256(data).hexdigest().upper()],home);self.assertEqual(found,str(bios/'cualquier.bin'));self.assertEqual(self.ports.find_bios(['0'*64],home),'')
    def test_disc_check_distinguishes_region_from_the_library_names(self):
        one=self.kit('spider-man-recomp');two=self.kit('enter-electro')
        text=lambda lines:' '.join(t for _,t in lines if t.startswith('Disco'))
        spanish=['Spider-Man (Spain)','Spider-Man 2 - Enter - Electro (Europe)','Castlevania - Symphony of the Night (Europe)']
        home=self.root/'sinbios'
        l1=self.ports.requirements(one,spanish,home);l2=self.ports.requirements(two,spanish,home)
        self.assertIn('otra región',text(l1));self.assertIn('Spain',text(l1));self.assertNotIn('Enter',text(l1));self.assertIn('otra región',text(l2));self.assertIn('Europe',text(l2))
        self.assertEqual([ok for ok,t in l1 if t.startswith('Disco')],[False])
        usa=self.ports.requirements(one,['Spider-Man (USA)','Spider-Man 2 - Enter - Electro (USA) (Rev 1)'],home);self.assertEqual([ok for ok,t in usa if t.startswith('Disco')],[None]);self.assertIn('Spider-Man (USA)',text(usa))
        self.assertIn('no hay una copia',text(self.ports.requirements(one,[],home)))
    def test_missing_bios_is_reported_and_kits_without_requirements_report_nothing(self):
        lines=self.ports.requirements(self.kit('spider-man-recomp'),[],self.root/'vacio');self.assertEqual(lines[0][0],False);self.assertIn('hash exacto',lines[0][1])
        self.assertEqual(self.ports.requirements({'name':'x'},['a']),[])

class BuiltKitTests(PortCatalogTests):
    def test_a_built_kit_starts_the_game_directly_and_keeps_a_stable_id(self):
        self.install({'Kit/Launcher':b'\x7fELF','Kit/CMakeLists.txt':b'x','Kit/README-SETUP.txt':b'x'})
        folder=self.install_root/'Uno';before=self.ports.entry_for(folder)
        self.assertNotIn('--no-launcher',before.command);self.assertEqual(before.source,str(folder/'Launcher'))
        (folder/'build').mkdir();(folder/'build/Launcher').write_bytes(b'\x7fELF');(folder/'build/Launcher').chmod(0o755)
        first_run=self.ports.entry_for(folder)
        self.assertNotIn('--no-launcher',first_run.command);self.assertIn('--command='+str(folder/'build/Launcher'),first_run.command)
        (folder/'build/bios.cfg').write_text('/algun/bios.bin\n');after=self.ports.entry_for(folder)
        self.assertEqual(after.command[-1],'--no-launcher');self.assertIn('--command='+str(folder/'build/Launcher'),after.command)
        self.assertEqual((before.id,after.cwd),(after.id,str(folder/'build')));self.assertTrue(after.metadata['built']);self.assertEqual(first_run.id,after.id)
    def test_rescan_updates_the_command_of_a_managed_port_without_duplicating_it(self):
        self.install({'Kit/Launcher':b'\x7fELF','Kit/CMakeLists.txt':b'x','Kit/README-SETUP.txt':b'x'})
        folder=self.install_root/'Uno';store=self.store;store.merge([self.ports.entry_for(folder)])
        (folder/'build').mkdir();(folder/'build/Launcher').write_bytes(b'\x7fELF');(folder/'build/Launcher').chmod(0o755);(folder/'build/bios.cfg').write_text('x')
        store.merge([self.ports.entry_for(folder)],overwrite=False);saved=store.load()
        self.assertEqual(len(saved),1);self.assertIn('--no-launcher',saved[0].command)
    def test_manual_commands_are_not_overwritten_by_a_rescan(self):
        self.install({'Tool':b'\x7fELF'});folder=self.install_root/'Uno';entry=self.ports.entry_for(folder);entry.command=['/mi/comando'];entry.metadata['manual_command']=True;self.store.save([entry])
        self.store.merge([self.ports.entry_for(folder)],overwrite=False);self.assertEqual(self.store.load()[0].command,['/mi/comando'])

class LibraryDuplicateTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.store=Store(self.root/'data')
    def tearDown(self):self.tmp.cleanup()
    def test_entry_types(self):
        from deck_library.library_view import entry_type
        kinds={'port':Entry('a',['/a'],kind='port'),'port2':Entry('b',['/b'],kind='wiicompiled',platform='WiiCompiled'),'emulator':Entry('c',['/c'],kind='emulated',platform='Switch'),'minecraft':Entry('d',['/d'],kind='minecraft',platform='Minecraft'),'steam':Entry('e',['/e'],kind='steam',platform='Steam'),'steam_mc':Entry('f',['/f'],kind='steam',platform='Minecraft'),'custom':Entry('g',['/g'],kind='custom')}
        self.assertEqual({k:entry_type(v) for k,v in kinds.items()},{'port':'port','port2':'port','emulator':'emulator','minecraft':'minecraft','steam':'steam','steam_mc':'steam','custom':'custom'})
    def test_emulator_versions_of_a_game_with_a_port_are_hidden_but_other_games_stay(self):
        from deck_library.library_view import visible_entries
        es=[Entry('Spider-Man (PS1 recompilado)',['/p1'],kind='port'),Entry('Spider-Man (USA)',['/e1'],kind='emulated',platform='PlayStation'),Entry('Spider-Man 2 - Enter - Electro (USA)',['/e2'],kind='emulated',platform='PlayStation'),Entry('Mario Kart Wii',['/w'],kind='wiicompiled',platform='WiiCompiled'),Entry('Mario Kart Wii (PAL)',['/e3'],kind='emulated',platform='Wii'),Entry('Castlevania',['/e4'],kind='emulated',platform='PlayStation')]
        shown,hidden=visible_entries(es);self.assertEqual(hidden,2);self.assertEqual(sorted(e.name for e in shown),['Castlevania','Mario Kart Wii','Spider-Man (PS1 recompilado)','Spider-Man 2 - Enter - Electro (USA)'])
        everything,none=visible_entries(es,prefer_ports=False);self.assertEqual((len(everything),none),(6,0))
    def test_rescan_drops_the_old_entry_of_the_same_catalog_port(self):
        old=Entry('Kit',['/viejo'],kind='port',metadata={'port_repository':'a/kit'});new=Entry('Kit',['/nuevo'],kind='port',id='a'*20,metadata={'port_repository':'a/kit'});other=Entry('Otro',['/otro'],kind='port')
        self.store.save([old,other]);self.store.merge([new],overwrite=False);ids={e.id for e in self.store.load()}
        self.assertEqual(ids,{'a'*20,other.id})
    def test_imported_shortcut_owned_by_a_managed_entry_is_dropped_and_minecraft_names_match_loosely(self):
        from deck_library.steam_inventory import merge_steam,prune
        account='/steam/userdata/1/config'
        mc=Entry('[Alone on a Raft] Ocean Survival',['/mc'],kind='minecraft',platform='Minecraft')
        ghost=Entry('Alone on a Raft - Ocean Survival',['/g'],kind='steam',platform='Minecraft',metadata={'steam_appid':7,'steam_account':account})
        mc.metadata.update(steam_appid=7,steam_account=account)
        self.assertEqual([e.name for e in prune([mc,ghost],account,{7})],['[Alone on a Raft] Ocean Survival'])
        item={'name':'Alone on a Raft - Ocean Survival','appid':7,'exe':'"/x/launch.sh"','options':'','startdir':'','icon':'','account':account}
        with patch('deck_library.steam_inventory.shortcuts',return_value=[item]),patch('deck_library.steam_inventory.discover' if False else 'deck_library.gtaiv.discover',return_value=[]):
            fresh=Entry('[Alone on a Raft] Ocean Survival',['/mc'],kind='minecraft',platform='Minecraft')
            result=merge_steam([fresh],account=account)
        self.assertEqual(len(result),1);self.assertEqual(result[0].metadata['steam_appid'],7)

class WebPortTests(PortCatalogTests):
    OPENPETE='<a href="https://dl.openpete.com/OpenPete-v0.4.2-x86_64.AppImage">Linux</a><p>The Linux AppImage has the SHA-256 hash <code>3b67fcc311193b70a15b12d84fd590886305fb282830dd7cc92b7d8e993c4bea</code>.</p>'
    CTR='<script>window.__BUILDS__={"builds":[{"key":"zip","platform":"windows","name":"x.zip","downloadUrl":"/api/download/1"},{"key":"appimage","platform":"linux","name":"ctr-t-07d0c49-linux-x86.AppImage","size":11652472,"commit":"07d0c49","downloadUrl":"/api/download/11440191688"}],"stale":false};</script>'
    def test_openpete_page_gives_version_url_and_published_hash(self):
        r=self.ports.resolve_web({'kind':'openpete'},self.OPENPETE);self.assertEqual((r['tag'],r['name']),('v0.4.2','OpenPete-v0.4.2-x86_64.AppImage'));self.assertEqual(r['sha256'][:8],'3b67fcc3');self.assertTrue(r['url'].startswith('https://dl.openpete.com/'))
        with self.assertRaises(ValueError):self.ports.resolve_web({'kind':'openpete'},'<html>sin enlace</html>')
    def test_ctr_page_gives_the_linux_appimage_and_its_size(self):
        r=self.ports.resolve_web({'kind':'ctr'},self.CTR);self.assertEqual((r['tag'],r['size'],r['sha256']),('07d0c49',11652472,''));self.assertEqual(r['url'],'https://ctr.cmzi.uk/api/download/11440191688')
        with self.assertRaises(ValueError):self.ports.resolve_web({'kind':'ctr'},'<html></html>')
        with self.assertRaises(ValueError):self.ports.resolve_web({'kind':'otro'})
    def web_install(self,kind,payload,resolved,runner=None,replace=False):
        item=next(b for b in self.ports.BUILTIN if b.get('web',{}).get('kind')==kind)
        def fake_download(url,target,limit=0,progress=None):pathlib.Path(target).write_bytes(payload)
        with patch.object(self.ports,'download',fake_download):
            return self.ports.install(item,self.store,self.install_root,lambda _:None,web=lambda w:resolved,replace=replace,runner=runner)
    def test_openpete_is_verified_unpacked_once_and_flagged_for_the_sdk(self):
        payload=b'APPIMAGE'+b'x'*50;resolved={'tag':'v0.4.2','name':'OpenPete-v0.4.2-x86_64.AppImage','url':'https://dl.openpete.com/a','sha256':hashlib.sha256(payload).hexdigest(),'size':0,'page':'p'}
        def runner(cmd,cwd=None,**k):
            root=pathlib.Path(cwd)/'squashfs-root';(root/'usr').mkdir(parents=True);(root/'AppRun').write_bytes(b'#!/bin/sh');return type('R',(),{'returncode':0})()
        record=self.web_install('openpete',payload,resolved,runner)
        folder=self.install_root/'OpenPete';self.assertEqual((record['executable'],record['sandbox'],record['verified'],record['web'],record['setup']),('squashfs-root/AppRun',True,True,'openpete','openpete'))
        self.assertTrue((folder/'squashfs-root/AppRun').is_file());self.assertFalse(any(p.suffix=='.AppImage' for p in folder.iterdir()));self.assertFalse(record['configured'])
        entry=self.ports.entry_for(folder);self.assertIn('--command='+str(folder/'squashfs-root/AppRun'),entry.command)
    def test_web_downloads_must_match_hash_size_and_host(self):
        payload=b'datos'
        base={'tag':'t','name':'a.AppImage','url':'https://dl.openpete.com/a','sha256':'','size':0,'page':'p'}
        with self.assertRaisesRegex(ValueError,'SHA-256'):self.web_install('ctr',payload,{**base,'url':'https://ctr.cmzi.uk/a','sha256':'0'*64})
        with self.assertRaisesRegex(ValueError,'tamaño'):self.web_install('ctr',payload,{**base,'url':'https://ctr.cmzi.uk/a','size':999})
        with self.assertRaisesRegex(ValueError,'no permitido'):self.web_install('ctr',payload,{**base,'url':'https://evil.example/a'})
        self.assertFalse((self.install_root/'CTRTurbocharged').exists())
    def test_ctr_installs_as_a_plain_appimage_with_size_check_only(self):
        payload=b'\x7fELF'+b'c'*20;record=self.web_install('ctr',payload,{'tag':'07d0c49','name':'ctr-t-linux-x86.AppImage','url':'https://ctr.cmzi.uk/api/download/1','sha256':'','size':len(payload),'page':'p'})
        self.assertEqual((record['executable'],record['sandbox'],record['verified'],record['setup']),('ctr-t-linux-x86.AppImage',False,False,'ctr'))
    def test_web_updates_compare_the_published_tag(self):
        self.web_install('ctr',b'\x7fELF',{'tag':'old','name':'a.AppImage','url':'https://ctr.cmzi.uk/a','sha256':'','size':0,'page':'p'})
        with patch.object(self.ports,'resolve_web',return_value={'tag':'new','page':'https://ctr.cmzi.uk/'}):found=self.ports.installed_updates(self.store)
        self.assertEqual([(u['installed'],u['latest']) for u in found],[('old','new')])
        with patch.object(self.ports,'resolve_web',return_value={'tag':'old','page':'p'}):self.assertEqual(self.ports.installed_updates(self.store),[])

class ConfigureTests(PortCatalogTests):
    def make_disc(self,home,name='Juego',serial='SCUS_942.28',size=2352*4):
        roms=home/'Emulation/roms/psx';roms.mkdir(parents=True,exist_ok=True)
        data=(b'\0'*1000+('BOOT = cdrom:\\'+serial+';1').encode()).ljust(size,b'\0')
        (roms/(name+'.bin')).write_bytes(data);(roms/(name+'.cue')).write_text('FILE "'+name+'.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n');return roms/(name+'.cue'),roms/(name+'.bin')
    def installed(self,home,kind,exe='Bin',sandbox=False,folder='Port',extra=None):
        spec={'openpete':{'serial':'SCUS-94228','match':'spyro','exclude':''},'ctr':{'serial':'SCUS-94426','match':'crash','exclude':''},'kit':{'serial':'SLUS-00875','match':'spiderman','exclude':''}}[kind]
        record={'repository':'web/x','name':'Port','folder':folder,'tag':'1','executable':exe,'sandbox':sandbox,'setup':kind,'web':'','disc':spec,'bios':None,'args':[],'configured':False,**(extra or {})}
        (home/'ports'/folder).mkdir(parents=True,exist_ok=True);(home/'ports'/folder/exe.split('/')[0]).parent.mkdir(exist_ok=True);target=home/'ports'/folder/exe;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'x');self.ports.atomic_json(self.store.root/'ports.json',{'web/x':record});return record
    def games(self,cue):return [('Juego',str(cue))]
    def test_find_disc_matches_by_serial_not_by_name_and_resolves_cue_and_bin(self):
        home=self.root/'home';cue,binary=self.make_disc(home,'Nombre raro');spec={'serial':'SCUS-94228'}
        found=self.ports.find_disc(spec,[('otro',str(home/'nada.bin')),('Nombre raro',str(binary))]);self.assertEqual((found['cue'],found['bin']),(str(cue),str(binary)))
        self.assertEqual(self.ports.find_disc(spec,[('x',str(cue))])['bin'],str(binary));self.assertIsNone(self.ports.find_disc({'serial':'SLUS-00001'},[('x',str(cue))]));self.assertIsNone(self.ports.find_disc(spec,[('x','/a/b.chd')]))
    def test_requirements_report_an_exact_serial_match(self):
        home=self.root/'home';cue,_=self.make_disc(home);lines=self.ports.requirements({'disc':{'serial':'SCUS-94228','match':'spyro'}},self.games(cue),home)
        self.assertEqual(lines[0][0],True);self.assertIn('serial verificado',lines[0][1])
    def test_ctr_copies_the_raw_bin_as_ctr_u_and_refuses_a_cooked_iso(self):
        home=self.root/'home';cue,binary=self.make_disc(home,'CTR',serial='SCUS_944.26');self.installed(home,'ctr')
        record=self.ports.configure('web/x',self.store,self.games(cue),lambda _:None,home)
        target=home/self.ports.DATA_CTR/'assets/ctr-u.bin';self.assertEqual(target.read_bytes(),binary.read_bytes());self.assertTrue(record['configured']);self.assertEqual(record['configured_with'],'Juego')
        cue2,_=self.make_disc(home,'Mala',serial='SCUS_944.26',size=2048*3);target.unlink()
        with self.assertRaisesRegex(ValueError,'MODE2/2352'):self.ports.configure('web/x',self.store,[('Mala',str(cue2))],lambda _:None,home)
    def test_missing_requirements_stop_before_anything_runs(self):
        home=self.root/'home';self.installed(home,'ctr');ran=[]
        with self.assertRaisesRegex(ValueError,'Faltan requisitos'):self.ports.configure('web/x',self.store,[('Otro','/no/existe.cue')],lambda _:None,home,run=lambda *a,**k:ran.append(a))
        self.assertEqual(ran,[])
    def test_openpete_prebuilds_the_module_in_the_sdk_and_remembers_the_disc(self):
        home=self.root/'home';cue,_=self.make_disc(home);self.installed(home,'openpete',exe='squashfs-root/AppRun',sandbox=True,folder='OpenPete');calls=[]
        def run(command,cwd=None,progress=None,until=None):
            calls.append(command);(pathlib.Path(cwd)/'usr').mkdir(exist_ok=True);(pathlib.Path(cwd)/'usr/spyro1-recomp.so').write_bytes(b'so');self.assertTrue(until());return 0
        record=self.ports.configure('web/x',self.store,self.games(cue),lambda _:None,home,run=run)
        self.assertIn('--headless',calls[0]);self.assertEqual(record['args'],['--disc',str(cue),'--fullscreen','1']);calls.clear()
        self.ports.configure('web/x',self.store,self.games(cue),lambda _:None,home,run=run);self.assertEqual(calls,[])
    def test_kit_runs_verify_generate_rebuild_in_order_and_stores_the_bios(self):
        home=self.root/'home';cue,_=self.make_disc(home,'Spider-Man (USA)',serial='SLUS_008.75');bios=home/'Emulation/bios';bios.mkdir(parents=True);data=b'B'*524288;(bios/'x.bin').write_bytes(data)
        extra={'bios':{'name':'b','sha256':[hashlib.sha256(data).hexdigest()]}};self.installed(home,'kit',exe='Spider_Man_Recompiled',sandbox=True,folder='Kit',extra=extra);calls=[]
        (home/'ports/Kit/psxrecomp/bios').mkdir(parents=True);(home/'ports/Kit/psxrecomp/bios/SCPH5552.BIN').write_bytes(data)
        record=self.ports.configure('web/x',self.store,[('Spider-Man (USA)',str(cue))],lambda _:None,home,run=lambda command,cwd=None,progress=None,until=None:calls.append(command) or 0)
        self.assertEqual([c[2] for c in calls],['verify-disc','generate','rebuild']);self.assertIn(str(cue),calls[0]);self.assertIn(str(bios/'x.bin'),calls[1]);self.assertIn('Spider_Man_Recompiled',calls[2])
        self.assertEqual((home/'ports/Kit/build/bios.cfg').read_text().strip(),str(home/'ports/Kit/psxrecomp/bios/SCPH5552.BIN'));self.assertTrue(record['configured'])
    def test_a_failing_step_leaves_the_port_unconfigured(self):
        home=self.root/'home';cue,_=self.make_disc(home,'Spider-Man (USA)',serial='SLUS_008.75');bios=home/'Emulation/bios';bios.mkdir(parents=True);data=b'B'*524288;(bios/'x.bin').write_bytes(data)
        self.installed(home,'kit',exe='K',sandbox=True,folder='Kit',extra={'bios':{'name':'b','sha256':[hashlib.sha256(data).hexdigest()]}})
        def run(command,cwd=None,progress=None,until=None):
            if command[2]=='generate':raise RuntimeError('falló')
            return 0
        with self.assertRaises(RuntimeError):self.ports.configure('web/x',self.store,[('Spider-Man (USA)',str(cue))],lambda _:None,home,run=run)
        self.assertFalse(self.ports.records(self.store)['web/x']['configured'])

class StopTests(unittest.TestCase):
    def test_stopping_a_run_ends_the_whole_process_group(self):
        import subprocess,time,os
        from deck_library import buildenv
        marker=tempfile.NamedTemporaryFile(delete=False);marker.close()
        script='sleep 300 & echo $! > %s; echo listo; wait'%marker.name
        process=subprocess.Popen(['sh','-c',script],stdout=subprocess.PIPE,text=True,start_new_session=True);self.assertEqual(process.stdout.readline().strip(),'listo')
        child=int(pathlib.Path(marker.name).read_text());os.kill(child,0)
        buildenv.stop(process);time.sleep(0.3)
        with self.assertRaises(ProcessLookupError):os.kill(child,0)
        os.unlink(marker.name)
    def test_run_stops_when_the_condition_becomes_true_and_reports_failures(self):
        from deck_library import buildenv
        seen=[];self.assertEqual(buildenv.run(['sh','-c','echo uno; echo dos; sleep 30'],progress=seen.append,until=lambda:len(seen)>=2,sandbox=False),0);self.assertEqual(seen,['uno','dos'])
        with self.assertRaisesRegex(RuntimeError,'fallo'):buildenv.run(['sh','-c','echo fallo; exit 3'],progress=lambda _:None,sandbox=False)

class GameTitleTests(PortCatalogTests):
    def test_a_port_with_a_different_title_still_hides_the_emulator_version(self):
        from deck_library.library_view import visible_entries
        self.install({'Tool':b'\x7fELF'});folder=self.install_root/'Uno'
        record=self.ports.records(self.store)['a/uno'];record['repository']='web/ctr-turbocharged';record['cover_title']='CTR - Crash Team Racing';self.ports.atomic_json(folder/'.deck-library-port.json',record)
        port=self.ports.entry_for(folder);self.assertEqual(port.metadata['game_title'],'CTR - Crash Team Racing')
        shown,hidden=visible_entries([port,Entry('CTR - Crash Team Racing',['/e'],kind='emulated',platform='PlayStation')]);self.assertEqual((len(shown),hidden),(1,1))

class InstallerCacheTests(unittest.TestCase):
    def test_a_same_length_update_with_zero_mtime_is_not_shadowed_by_the_old_compiled_cache(self):
        import os,subprocess,sys
        root=pathlib.Path(tempfile.mkdtemp());home=root/'home';home.mkdir();source=root/'pkg'
        def package(version):
            for d in ('deck_library','assets','docs','presets'):(source/d).mkdir(parents=True,exist_ok=True)
            for f in ('app.py','launch.sh','README.md','LEEME.md','LICENSE'):(source/f).write_text('x')
            (source/'deck_library/__init__.py').write_text("__version__ = '%s'\n"%version);(source/'assets/icon.svg').write_text('<svg/>')
            (source/'install.py').write_text((pathlib.Path(__file__).resolve().parent.parent/'install.py').read_text())
            for path in source.rglob('*'):os.utime(path,(0,0))
        env={**os.environ,'HOME':str(home)};dest=root/'dest'
        def install():subprocess.run([sys.executable,str(source/'install.py'),'--destination',str(dest)],env=env,check=True,capture_output=True)
        def running():return subprocess.run([sys.executable,'-c','import deck_library;print(deck_library.__version__)'],cwd=str(dest),env=env,capture_output=True,text=True).stdout.strip()
        package('0.4.0');install();self.assertEqual(running(),'0.4.0');self.assertTrue(list(dest.rglob('__pycache__')))
        package('0.5.1');install();self.assertEqual(running(),'0.5.1')
        icon=home/'.local/share/icons/hicolor/scalable/apps/deck-library.svg';self.assertTrue(icon.is_file());self.assertGreater(icon.stat().st_mtime,1e9)
        import shutil;shutil.rmtree(root)

class KitControllerTests(PortCatalogTests):
    def kit_folder(self,game_toml,build_toml=None):
        folder=self.install_root/'Kit';(folder/'build').mkdir(parents=True);(folder/'game.toml').write_text(game_toml)
        if build_toml is not None:(folder/'build/game.toml').write_text(build_toml)
        return folder
    def test_player_one_is_set_to_the_first_controller_in_both_copies_without_touching_other_keys(self):
        import tomllib
        toml='[game]\nname = "X"\n\n[controller]\ndefault_mode = "digital"\n\n[video]\nrenderer = "opengl"\n'
        folder=self.kit_folder(toml,toml);changed=self.ports.ensure_controller_default(folder);self.assertEqual(len(changed),2)
        for name in ('game.toml','build/game.toml'):
            data=tomllib.loads((folder/name).read_text());self.assertEqual((data['controller']['p1_device'],data['controller']['default_mode'],data['video']['renderer']),('auto','digital','opengl'))
        self.assertEqual(self.ports.ensure_controller_default(folder),[])
    def test_an_explicit_choice_and_a_missing_table_are_handled(self):
        import tomllib
        folder=self.kit_folder('[controller]\np1_device = "keyboard"\n');self.assertEqual(self.ports.ensure_controller_default(folder),[]);self.assertIn('keyboard',(folder/'game.toml').read_text())
        other=self.root/'Otro';(other).mkdir();(other/'game.toml').write_text('[game]\nname = "Y"\n');self.ports.ensure_controller_default(other);self.assertEqual(tomllib.loads((other/'game.toml').read_text())['controller']['p1_device'],'auto')
        (other/'game.toml').write_text('esto no es toml [[');self.assertEqual(self.ports.ensure_controller_default(other),[])
    def test_maintain_repairs_installed_kits_only(self):
        home=self.root/'home';kit=home/'ports/Kit';kit.mkdir(parents=True);(kit/'game.toml').write_text('[game]\nname = "X"\n');plain=home/'ports/Plain';plain.mkdir();(plain/'game.toml').write_text('[game]\nname = "Y"\n')
        self.ports.atomic_json(self.store.root/'ports.json',{'a/kit':{'folder':'Kit','setup':'kit'},'a/plain':{'folder':'Plain','setup':'ctr'}})
        changed=self.ports.maintain(self.store,home);self.assertEqual(changed,[str(kit/'game.toml')]);self.assertNotIn('p1_device',(plain/'game.toml').read_text())

class KitPerformanceTests(PortCatalogTests):
    SPU="static uint16_t spu_regs[8];\n\nvoid spu_get_global_state(SpuGlobalState* out) {\n    if (!out) return;\n}\n"
    HDR="typedef struct SpuGlobalState { int x; } SpuGlobalState;\nvoid spu_get_global_state(SpuGlobalState* out);\n"
    INT=("uint32_t psx_spu_sample_event_cycles_to_next(void) {\n    SpuGlobalState state;\n    g_spu_sample_deadline_queries++;\n    if (!spu_sample_event_mode()) {\n        return 1;\n    }\n"
         "    spu_get_global_state(&state);\n    if ((state.ctrl & 0x0040u) == 0) {\n        return 2;\n    }\n    return 3;\n}\n\n"
         "void psx_spu_sample_event_service(void) {\n    SpuGlobalState state;\n    spu_get_global_state(&state);\n    if ((state.ctrl & 0x0040u) != 0) {\n        g_a++;\n    }\n"
         "    if ((state.ctrl & 0x0040u) != 0 &&\n        (psx_get_cycle_count() % 768u) == 0) {\n        s_midframe_audio_pump();\n    }\n}\n")
    def kit(self,spu=None,header=None,interrupts=None):
        folder=self.root/'Kit';(folder/'psxrecomp/runtime/src').mkdir(parents=True);(folder/'psxrecomp/runtime/include').mkdir(parents=True)
        (folder/'psxrecomp/runtime/src/spu.c').write_text(spu or self.SPU);(folder/'psxrecomp/runtime/include/spu.h').write_text(header or self.HDR);(folder/'psxrecomp/runtime/src/interrupts.c').write_text(interrupts or self.INT);return folder
    def test_the_spu_patch_applies_once_keeps_backups_and_changes_only_the_register_read(self):
        folder=self.kit();self.assertEqual(self.ports.apply_runtime_patches(folder),'applied')
        interrupts=(folder/'psxrecomp/runtime/src/interrupts.c').read_text()
        self.assertNotIn('state.ctrl',interrupts);self.assertNotIn('spu_get_global_state',interrupts);self.assertEqual(interrupts.count('spu_get_ctrl()'),2);self.assertEqual(interrupts.count('spu_ctrl & 0x0040u'),3)
        self.assertIn('uint16_t spu_get_ctrl(void)',(folder/'psxrecomp/runtime/src/spu.c').read_text());self.assertIn('uint16_t spu_get_ctrl(void);',(folder/'psxrecomp/runtime/include/spu.h').read_text())
        self.assertEqual((folder/'psxrecomp/runtime/src/interrupts.c.orig').read_text(),self.INT)
        self.assertEqual(self.ports.apply_runtime_patches(folder),'present');self.assertEqual((folder/'psxrecomp/runtime/src/interrupts.c').read_text(),interrupts);self.assertEqual((folder/'psxrecomp/runtime/src/interrupts.c.orig').read_text(),self.INT)
    def test_a_different_kit_version_is_left_untouched(self):
        other=self.INT.replace('if ((state.ctrl & 0x0040u) == 0) {','if ((state.ctrl & 0x0080u) == 0) {');folder=self.kit(interrupts=other)
        self.assertEqual(self.ports.apply_runtime_patches(folder),'incompatible')
        self.assertEqual((folder/'psxrecomp/runtime/src/interrupts.c').read_text(),other);self.assertEqual((folder/'psxrecomp/runtime/src/spu.c').read_text(),self.SPU);self.assertFalse((folder/'psxrecomp/runtime/src/spu.c.orig').exists())
        self.assertEqual(self.ports.apply_runtime_patches(self.root/'no-existe'),'incompatible')
    def test_a_newer_runtime_without_the_problem_needs_no_patch(self):
        newer=self.INT.replace('spu_get_global_state(&state);','').replace('SpuGlobalState state;','').replace('state.ctrl','0');folder=self.kit(interrupts=newer)
        self.assertEqual(self.ports.apply_runtime_patches(folder),'not-needed');self.assertFalse((folder/'psxrecomp/runtime/src/spu.c.orig').exists());self.assertEqual((folder/'psxrecomp/runtime/src/interrupts.c').read_text(),newer)
    def test_half_applied_sources_are_not_patched_again(self):
        folder=self.kit(spu=self.SPU+'/* spu_get_ctrl */\n');self.assertEqual(self.ports.apply_runtime_patches(folder),'incompatible')
    def test_overlay_compiler_command_quotes_paths_and_is_set_only_for_games_with_overlays(self):
        import tomllib
        folder=self.root/'con espacio';(folder/'build').mkdir(parents=True)
        for name in ('game.toml','build/game.toml'):(folder/name).write_text('[runtime]\noverlay_cache = true\nname = "x"\n')
        changed=self.ports.ensure_overlay_compiler(folder);self.assertEqual(len(changed),2)
        command=tomllib.loads((folder/'game.toml').read_text())['runtime']['overlay_autocompile_cmd']
        import shlex;parts=shlex.split(command);self.assertEqual(parts[0],'python3');self.assertIn(str(folder/'psxrecomp/tools/compile_overlays.py'),parts);self.assertEqual(parts[parts.index('--compiler')+1],'gcc');self.assertEqual(parts[parts.index('--out-dir')+1],str(folder/'build/cache'))
        self.assertEqual(self.ports.ensure_overlay_compiler(folder),[])
        plain=self.root/'plain';plain.mkdir();(plain/'game.toml').write_text('[runtime]\nname = "x"\n');self.assertEqual(self.ports.ensure_overlay_compiler(plain),[]);self.assertNotIn('autocompile',(plain/'game.toml').read_text())
    def test_a_moved_folder_gets_its_command_refreshed(self):
        import tomllib
        folder=self.root/'a';(folder/'build').mkdir(parents=True);(folder/'game.toml').write_text('[runtime]\noverlay_cache = true\noverlay_autocompile_cmd = "python3 /otro/lugar/compile_overlays.py"\n')
        self.assertEqual(len(self.ports.ensure_overlay_compiler(folder)),1);self.assertIn(str(folder),tomllib.loads((folder/'game.toml').read_text())['runtime']['overlay_autocompile_cmd'])

class ConfigureKitPerformanceTests(ConfigureTests,KitPerformanceTests):
    def test_configure_patches_before_the_build_and_records_the_level(self):
        home=self.root/'home';cue,_=self.make_disc(home,'Spider-Man (USA)',serial='SLUS_008.75');bios=home/'Emulation/bios';bios.mkdir(parents=True);data=b'B'*524288;(bios/'x.bin').write_bytes(data)
        self.installed(home,'kit',exe='K',sandbox=True,folder='Kit',extra={'bios':{'name':'b','sha256':[hashlib.sha256(data).hexdigest()]}})
        kit=home/'ports/Kit';(kit/'psxrecomp/runtime/src').mkdir(parents=True);(kit/'psxrecomp/runtime/include').mkdir(parents=True)
        (kit/'psxrecomp/runtime/src/spu.c').write_text(self.SPU);(kit/'psxrecomp/runtime/include/spu.h').write_text(self.HDR);(kit/'psxrecomp/runtime/src/interrupts.c').write_text(self.INT);(kit/'psxrecomp/bios').mkdir();(kit/'psxrecomp/bios/B.BIN').write_bytes(data)
        (kit/'game.toml').write_text('[runtime]\noverlay_cache = true\n');seen=[]
        def run(command,cwd=None,progress=None,until=None):
            seen.append((command[2],'spu_get_ctrl' in (kit/'psxrecomp/runtime/src/interrupts.c').read_text(),'overlay_autocompile_cmd' in (kit/'game.toml').read_text()));return 0
        record=self.ports.configure('web/x',self.store,[('Spider-Man (USA)',str(cue))],lambda _:None,home,run=run)
        self.assertEqual(seen[0],('verify-disc',True,True));self.assertEqual(record['patch_level'],self.ports.PATCH_LEVEL);self.assertEqual(self.ports.records(self.store)['web/x']['patch_level'],self.ports.PATCH_LEVEL)

class ZeldaPortTests(ConfigureTests):
    def rom_home(self,system='gba',name='cualquier nombre.gba',size=1024,header=False):
        home=self.root/'home';folder=home/'Emulation/roms'/system;folder.mkdir(parents=True);data=bytes(range(256))*(size//256)
        (folder/name).write_bytes((b'H'*512 if header else b'')+data);return home,folder/name,data
    def spec(self,data,**extra):return {'systems':['gba'],'sizes':[len(data),len(data)+512],'sha1':{hashlib.sha1(data).hexdigest():'baserom_eu.gba'},'name':'Prueba',**extra}
    def test_a_rom_is_found_by_sha1_whatever_its_name_and_a_wrong_one_is_not(self):
        home,path,data=self.rom_home();(path.parent/'otra.gba').write_bytes(b'x'*1024)
        found=self.ports.find_rom(self.spec(data),home);self.assertEqual((found['path'],found['target'],found['header']),(str(path),'baserom_eu.gba',False))
        self.assertIsNone(self.ports.find_rom({**self.spec(data),'sha1':{'0'*40:'x'}},home));self.assertIsNone(self.ports.find_rom(self.spec(data),self.root/'vacio'))
    def test_a_copier_header_is_ignored_only_when_the_spec_allows_it(self):
        home,path,data=self.rom_home(header=True)
        self.assertIsNone(self.ports.find_rom(self.spec(data),home))
        found=self.ports.find_rom(self.spec(data,strip_header=True),home);self.assertTrue(found['header'])
    def test_rom_setup_copies_the_rom_under_the_name_the_port_expects(self):
        home,path,data=self.rom_home();record=self.installed(home,'kit',exe='tmc_pc',folder='Picori',extra={'setup':'rom','disc':None,'rom':self.spec(data)})
        self.ports.configure('web/x',self.store,[],lambda _:None,home);self.assertEqual((home/'ports/Picori/baserom_eu.gba').read_bytes(),data)
    def test_zelda3_installs_python_libraries_builds_in_the_sdk_and_sets_audio_and_aspect(self):
        home,path,data=self.rom_home('snes','z.smc',header=True);spec={'systems':['snes'],'sizes':[len(data),len(data)+512],'sha1':{hashlib.sha1(data).hexdigest():'zelda3.sfc'},'strip_header':True,'name':'ALttP'}
        self.installed(home,'kit',exe='zelda3',sandbox=True,folder='Z3',extra={'setup':'zelda3','disc':None,'rom':spec});folder=home/'ports/Z3';(folder/'zelda3.ini').write_text('Fullscreen = 0\nExtendedAspectRatio = 4:3\n');calls=[]
        def run(command,cwd=None,progress=None,until=None):
            calls.append(command)
            if command[0]=='sh':(folder/'zelda3').write_bytes(b'\x7fELF');(folder/'zelda3_assets.dat').write_bytes(b'd')
            return 0
        record=self.ports.configure('web/x',self.store,[],lambda _:None,home,run=run)
        self.assertEqual((folder/'zelda3.sfc').read_bytes(),data);self.assertEqual(calls[0][:4],['python3','-m','pip','install']);self.assertIn('Pillow',calls[0]);self.assertEqual(calls[1][0],'sh');self.assertIn('make',calls[1][2])
        self.assertEqual(record['env'],{'SDL_AUDIODRIVER':'pulseaudio'});ini=(folder/'zelda3.ini').read_text();self.assertIn('ExtendedAspectRatio = 16:10',ini);self.assertIn('Fullscreen = 1',ini)
        entry=self.ports.entry_for(folder);self.assertIn('--env=SDL_AUDIODRIVER=pulseaudio',entry.command)
    def test_zelda3_fails_clearly_when_the_build_produces_nothing(self):
        home,path,data=self.rom_home('snes','z.sfc');spec={'systems':['snes'],'sizes':[len(data)],'sha1':{hashlib.sha1(data).hexdigest():'zelda3.sfc'},'name':'ALttP'}
        self.installed(home,'kit',exe='zelda3',sandbox=True,folder='Z3',extra={'setup':'zelda3','disc':None,'rom':spec})
        with self.assertRaisesRegex(RuntimeError,'zelda3'):self.ports.configure('web/x',self.store,[],lambda _:None,home,run=lambda *a,**k:0)
        self.assertFalse(self.ports.records(self.store)['web/x']['configured'])
    def wiiu_home(self,name='Wind Waker HD (USA, Asia).wux'):
        home=self.root/'home';roms=home/'Emulation/roms/wiiu/roms';roms.mkdir(parents=True,exist_ok=True);image=roms/name;image.write_bytes(b'wux');bios=home/'Emulation/bios/sysdata';bios.mkdir(parents=True,exist_ok=True)
        (bios/'keys.txt').write_text('# cabecera\n'+'a'*32+' # Wii U Common Key\n'+'b'*32+' # The Legend of Zelda: The Wind Waker HD [EUR, WUD]\n'+'c'*32+' # The Legend of Zelda: The Wind Waker HD [USA, WUD]\n'+'d'*32+' # The Legend of Zelda: The Wind Waker HD [USA, NUS]\n');return home,image
    SPEC={'title':'wind waker hd','exts':['.wux','.wud','.wua'],'name':'WWHD'}
    def test_wii_u_keys_are_matched_by_region_and_comment(self):
        home,image=self.wiiu_home();self.assertEqual(self.ports.wiiu_keys('wind waker hd','USA',home),('c'*32,'a'*32));self.assertEqual(self.ports.wiiu_keys('wind waker hd','EUR',home),('b'*32,'a'*32))
        self.assertEqual(self.ports.wiiu_keys('wind waker hd','JPN',home),(None,'a'*32));self.assertEqual(self.ports.wiiu_keys('x','USA',self.root/'nada'),(None,None))
    def test_requirements_report_the_disc_and_the_keys_without_showing_them(self):
        home,image=self.wiiu_home();lines=self.ports.requirements({'wiiu':self.SPEC},[('Wind Waker HD',str(image))],home);text=' '.join(t for _,t in lines)
        self.assertEqual([ok for ok,_ in lines],[True,True]);self.assertNotIn('c'*32,text);self.assertNotIn('a'*32,text)
        self.assertEqual([ok for ok,_ in self.ports.requirements({'wiiu':self.SPEC},[],home)],[False])
        (home/'Emulation/bios/sysdata/keys.txt').write_text('# vacío\n');self.assertEqual([ok for ok,_ in self.ports.requirements({'wiiu':self.SPEC},[('x',str(image))],home)],[True,False])
    def test_wwhd_setup_uses_private_temporary_key_files_and_removes_them(self):
        import stat
        home,image=self.wiiu_home();self.installed(home,'kit',exe='WindWakerHD.AppImage',folder='WWHD',extra={'setup':'wwhd','disc':None,'wiiu':self.SPEC});seen={}
        def run(command,cwd=None,progress=None,until=None,sandbox=True):
            if command[0].endswith('.AppImage'):(pathlib.Path(cwd)/'squashfs-root/tools/installer').mkdir(parents=True);return 0
            keys=[pathlib.Path(command[command.index(flag)+1]) for flag in ('--disc-key','--common-key')]
            seen.update(command=command,sandbox=sandbox,modes=[stat.S_IMODE(k.stat().st_mode) for k in keys],contents=[k.read_text().strip() for k in keys],paths=keys);return 0
        record=self.ports.configure('web/x',self.store,[('Wind Waker HD',str(image))],lambda _:None,home,run=run)
        self.assertEqual(seen['modes'],[0o600,0o600]);self.assertEqual(seen['contents'],['c'*32,'a'*32]);self.assertFalse(seen['sandbox']);self.assertIn(str(image),seen['command']);self.assertIn('--no-launch',seen['command'])
        self.assertFalse(any(k.exists() for k in seen['paths']));self.assertFalse(any('c'*32 in part or 'a'*32 in part for part in seen['command']));self.assertTrue(record['configured'])
    def test_a_cemu_archive_needs_no_keys_and_missing_keys_stop_a_disc_image(self):
        home,image=self.wiiu_home('Wind Waker HD (USA).wua');self.installed(home,'kit',exe='W.AppImage',folder='WWHD',extra={'setup':'wwhd','disc':None,'wiiu':self.SPEC});seen={}
        def run(command,cwd=None,progress=None,until=None,sandbox=True):
            if command[0].endswith('.AppImage'):(pathlib.Path(cwd)/'squashfs-root').mkdir();return 0
            seen['command']=command;return 0
        self.ports.configure('web/x',self.store,[('x',str(image))],lambda _:None,home,run=run);self.assertIn('--archive',seen['command']);self.assertNotIn('--disc-key',seen['command'])
        home2,image2=self.wiiu_home();(home2/'Emulation/bios/sysdata/keys.txt').write_text('# nada\n')
        with self.assertRaisesRegex(ValueError,'Faltan requisitos|claves'):self.ports.configure('web/x',self.store,[('x',str(image2))],lambda _:None,home2,run=run)

class AssetNameTests(PortCatalogTests):
    def test_wind_in_a_game_name_is_not_windows_and_real_windows_builds_are_still_skipped(self):
        names=['WindWakerHD-v0.2.12-windows-x86_64.zip','WindWakerHD-v0.2.12-macos-arm64.zip','WindWakerHD-v0.2.12-android-x86_64.apk','WindWakerHD-v0.2.12-linux-aarch64.AppImage','WindWakerHD-v0.2.12-linux-x86_64.zip','WindWakerHD-v0.2.12-linux-x86_64.AppImage','SHA256SUMS.txt']
        self.assertEqual(self.ports.pick_asset([{'name':n} for n in names])['name'],'WindWakerHD-v0.2.12-linux-x86_64.AppImage')
        for bad in ('game-win64.zip','game-win-x64.zip','game_win32.zip','game-windows.zip','game-mac.zip','game-x64-win.zip'):self.assertIsNone(self.ports.pick_asset([{'name':bad}]),bad)
    def test_the_executable_override_survives_cleaning_twice(self):
        once=self.ports.clean({'repository':'a/uno','executable':'zelda3'},'','x');self.assertEqual(once['exe'],'zelda3');self.assertEqual(self.ports.clean(once)['exe'],'zelda3')

class DeckMaxTests(unittest.TestCase):
    def setUp(self):
        import tempfile;self.home=pathlib.Path(tempfile.mkdtemp());self.addCleanup(shutil.rmtree,self.home,True)
    def write(self,relative,text):
        path=self.home/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);return path
    def test_graphics_keys_change_and_everything_else_is_kept_with_a_backup(self):
        from deck_library import deckmax
        ds=self.write('.local/share/duckstation/settings.ini','[GPU]\nResolutionScale = 2\nRenderer = Vulkan\n[Controller1]\nType = DigitalController\n')
        az=self.write('.config/azahar-emu/qt-config.ini','[Renderer]\nresolution_factor=2\nresolution_factor\\default=true\n[Controls]\nx=1\n')
        result=dict(deckmax.apply(self.home,busy=lambda a:False))
        self.assertEqual((result['DuckStation'],result['Azahar'],result['Dolphin'],result['Eden']),('applied','applied','missing','missing'))
        text=ds.read_text();self.assertIn('ResolutionScale = 5',text);self.assertIn('PGXPEnable = true',text);self.assertIn('Renderer = Vulkan',text);self.assertIn('Type = DigitalController',text)
        text=az.read_text();self.assertIn('resolution_factor=3',text);self.assertIn('resolution_factor\\default=false',text);self.assertIn('x=1',text)
        self.assertEqual(len(list(ds.parent.glob('settings.ini.deck-library-*.bak'))),1)
        self.assertEqual(dict(deckmax.apply(self.home,busy=lambda a:False))['DuckStation'],'present');self.assertEqual(len(list(ds.parent.glob('*.bak'))),1)
    def test_a_running_emulator_is_left_alone(self):
        from deck_library import deckmax
        ds=self.write('.local/share/duckstation/settings.ini','[GPU]\nResolutionScale = 2\n')
        self.assertEqual(dict(deckmax.apply(self.home,busy=lambda a:True))['DuckStation'],'busy');self.assertIn('ResolutionScale = 2',ds.read_text())

class DualScreenTests(unittest.TestCase):
    def setUp(self):
        import tempfile;self.root=pathlib.Path(tempfile.mkdtemp());self.addCleanup(shutil.rmtree,self.root,True)
        self.account=self.root/'userdata/1/config';self.account.mkdir(parents=True);folder=self.root/'controller_base/templates';folder.mkdir(parents=True)
        from deck_library import controllers;self.controllers=controllers
        free='\t"group"\n\t{\n\t\t"id"\t\t"7"\n\t\t"inputs"\n\t\t{\n'+''.join(f'\t\t\t"{b}"\n\t\t\t{{\n\t\t\t\t"activators"\n\t\t\t\t{{\n\t\t\t\t\t"Full_Press"\n\t\t\t\t\t{{\n\t\t\t\t\t\t"bindings"\n\t\t\t\t\t\t{{\n\t\t\t\t\t\t}}\n\t\t\t\t\t}}\n\t\t\t\t}}\n\t\t\t}}\n' for b in ('button_back_left','button_back_right'))+'\t\t}\n\t}\n'
        (folder/'controller_neptune_gamepad_joystick.vdf').write_text('"controller_mappings"\n{\n'+free+'}\n',encoding='utf-8');self.folder=folder
    def test_the_screens_template_binds_the_back_buttons_and_leaves_the_stock_template_alone(self):
        name=self.controllers.screens_template(self.account);text=(self.folder/name).read_text()
        self.assertIn('"key_press F9"',text);self.assertIn('"key_press F10"',text);self.assertNotIn('key_press',(self.folder/'controller_neptune_gamepad_joystick.vdf').read_text())
        self.assertEqual(self.controllers.screens_template(self.account),name)
    def test_only_the_deck_family_of_a_dual_screen_shortcut_gets_it(self):
        result=self.controllers.apply(self.account,[4159837018,2781706728],special=[4159837018],is_running=lambda:False)
        config=self.controllers.config_dir(self.account)/'configset_controller_neptune.vdf';pairs=dict(self.controllers.read_configset(config))
        self.assertEqual(dict(pairs['4159837018'])['template'],self.controllers.SCREENS_TEMPLATE);self.assertEqual(dict(pairs['2781706728'])['template'],'controller_neptune_gamepad_joystick.vdf')
    def test_a_template_without_free_back_buttons_is_refused(self):
        (self.folder/'controller_neptune_gamepad_joystick.vdf').write_text('"controller_mappings"\n{\n}\n')
        with self.assertRaises(ValueError):self.controllers.screens_template(self.account)

class ThreeDsSettingsTests(DeckMaxTests):
    def test_language_block_is_found_by_its_id_and_changed_with_a_backup(self):
        import struct
        from deck_library import deckmax
        folder=self.home/'Emulation/storage/azahar/nand/data/00000000000000000000000000000000/sysdata/00010017/00000000';folder.mkdir(parents=True)
        data=bytearray(64);struct.pack_into('<HH',data,0,3,0)
        for index,(block,value,size) in enumerate(((0x50005,0x5058,32),(0xA0002,1,1),(0xB0000,2,4))):struct.pack_into('<IIHH',data,4+index*12,block,value,size,14)
        (folder/'config').write_bytes(bytes(data))
        self.assertEqual(deckmax.set_3ds_language(self.home,5,busy=lambda a:False),'applied');after=(folder/'config').read_bytes()
        self.assertEqual(struct.unpack_from('<I',after,4+12+4)[0],5);self.assertEqual(after[:4+12]+after[4+24:],bytes(data)[:4+12]+bytes(data)[4+24:])
        self.assertEqual(deckmax.set_3ds_language(self.home,5,busy=lambda a:False),'present');self.assertEqual(len(list(folder.glob('config.deck-library-*.bak'))),1)
        self.assertEqual(deckmax.set_3ds_language(self.home,5,busy=lambda a:True),'busy')
    def test_dual_screen_layout_and_swap_keys_are_written_and_game_files_use_the_global_flag(self):
        from deck_library import deckmax
        az=self.write('.config/azahar-emu/qt-config.ini','[Renderer]\nlayout_option=5\n[UI]\nShortcuts\\Main%20Window\\Swap%20Screens\\KeySeq=Ctrl+Tab\n')
        botw=self.write('.config/eden/custom/01007EF00011E000.ini','[System]\nlanguage_index\\use_global=true\n[Renderer]\nresolution_setup\\use_global=true\n')
        deckmax.apply(self.home,busy=lambda a:False)
        text=az.read_text();self.assertIn('layout_option=1',text);self.assertIn('Swap%20Screens\\KeySeq=F9',text);self.assertIn('Toggle%20Screen%20Layout\\KeySeq=F10',text)
        text=botw.read_text();self.assertIn('language_index=14',text);self.assertIn('language_index\\use_global=false',text);self.assertIn('resolution_setup=2',text);self.assertIn('resolution_setup\\use_global=false',text)

class PortDefaultsTests(ConfigureTests):
    def test_enhance_kit_adds_video_keys_and_mods_without_overriding_the_player(self):
        folder=self.root/'kit';(folder/'build/mods/packages/psx.enhancement.pgxp/1.0.0').mkdir(parents=True)
        for pid in ('psx.enhancement.fast-loading','psx.enhancement.cd-speed'):(folder/'build/mods/packages'/pid/'1.0.0').mkdir(parents=True)
        for pid in ('psx.enhancement.pgxp','psx.enhancement.fast-loading','psx.enhancement.cd-speed'):(folder/'build/mods/packages'/pid/'1.0.0/manifest.toml').write_text('id="x"\n')
        (folder/'game.toml').write_text('[video]\nrenderer = "opengl"\nsupersampling = 2\n');(folder/'build/mods/state.toml').write_text('format_version = 2\n')
        import tomllib
        changed=self.ports.enhance_kit(folder);video=tomllib.loads((folder/'game.toml').read_text())['video']
        self.assertEqual((video['supersampling'],video['geometry_correction'],video['perspective_texturing']),(2,True,True));self.assertNotIn('frame_interpolation',video)
        state=tomllib.loads((folder/'build/mods/state.toml').read_text());self.assertEqual({f['id'] for f in state['feature'] if f['enabled']},{'pgxp','fast-loading','cd-speed'})
        self.assertEqual(self.ports.enhance_kit(folder),[]);self.assertTrue(changed)
    def test_a_state_the_player_already_edited_is_kept(self):
        folder=self.root/'kit';(folder/'build/mods/packages/psx.enhancement.pgxp/1.0.0').mkdir(parents=True);(folder/'build/mods/packages/psx.enhancement.pgxp/1.0.0/manifest.toml').write_text('x')
        text='format_version = 2\n\n[[feature]]\npackage_id = "a"\nid = "b"\nenabled = false\n';(folder/'build/mods/state.toml').write_text(text);self.ports.enhance_kit(folder);self.assertEqual((folder/'build/mods/state.toml').read_text(),text)
    def test_picori_gets_spanish_and_exact_height_scaling_only_with_the_european_rom(self):
        folder=self.root/'p';folder.mkdir();(folder/'config.json').write_text('{"fullscreen": false, "bindings": {"a": 1}}')
        record={'setup':'rom','configured':True};self.assertEqual(self.ports.tune_port(record,folder),[])
        (folder/'baserom_eu.gba').write_bytes(b'x');self.assertEqual(self.ports.tune_port(record,folder),[str(folder/'config.json')])
        config=json.loads((folder/'config.json').read_text());self.assertEqual((config['preferred_language'],config['internal_scale'],config['fullscreen']),(4,5,True));self.assertEqual(config['bindings'],{'a':1});self.assertEqual(self.ports.tune_port(record,folder),[])
    def test_wwhd_env_reaches_the_launch_command_of_a_native_port(self):
        record={'setup':'wwhd'};self.assertEqual(self.ports.tune_port(record,self.root),['env']);self.assertEqual(record['env']['WWHD_LANGUAGE'],'5')
        home=self.root/'home';folder=home/'ports/W';folder.mkdir(parents=True);(folder/'game').write_bytes(b'x');(folder/'game').chmod(0o755)
        (folder/'.deck-library-port.json').write_text(json.dumps({'repository':'a/w','name':'W','executable':'game',**record}));entry=self.ports.entry_for(folder)
        self.assertEqual(entry.command[0],'env');self.assertIn('WWHD_LANGUAGE=5',entry.command);self.assertEqual(entry.command[-1],str(folder/'game'))

def make_ups(source,target):
    import zlib
    def varint(n):
        out=bytearray()
        while True:
            x=n&0x7f;n>>=7
            if n:out.append(x);n-=1
            else:out.append(x|0x80);break
        return bytes(out)
    body=bytearray(b'UPS1'+varint(len(source))+varint(len(target)));last=0;i=0;size=max(len(source),len(target))
    s=source.ljust(size,b'\0');t=target.ljust(size,b'\0')
    while i<size:
        if s[i]==t[i]:i+=1;continue
        j=i
        while j<size and s[j]!=t[j]:j+=1
        body+=varint(i-last)+bytes(a^b for a,b in zip(s[i:j],t[i:j]))+b'\0';last=j+1;i=j+1
    body+=zlib.crc32(source).to_bytes(4,'little')+zlib.crc32(target).to_bytes(4,'little')
    return bytes(body)+zlib.crc32(bytes(body)).to_bytes(4,'little')

class UpsTests(unittest.TestCase):
    def test_a_patch_is_applied_and_a_wrong_rom_or_damaged_patch_is_refused(self):
        from deck_library.patching import apply_ups
        source=bytes(range(256))*8;target=bytearray(source);target[5]^=0xff;target[900:904]=b'abcd';target+=b'xyz'
        patch=make_ups(source,bytes(target));self.assertEqual(apply_ups(source,patch),bytes(target))
        with self.assertRaisesRegex(ValueError,'original'):apply_ups(source[:-1]+b'\1',patch)
        with self.assertRaisesRegex(ValueError,'dañado'):apply_ups(source,patch[:20]+b'\0'+patch[21:])
        with self.assertRaisesRegex(ValueError,'UPS'):apply_ups(source,b'IPS1'+patch[4:])

class SpanishZelda3Tests(ZeldaPortTests):
    def test_a_spanish_rom_adds_the_dialogue_build_and_selects_the_language(self):
        home,path,data=self.rom_home('snes','z.smc',header=False)
        import hashlib
        ours={'systems':['snes'],'sizes':[len(data)],'sha1':{hashlib.sha1(data).hexdigest():'zelda3.sfc'},'name':'ALttP'}
        spanish=(home/'Emulation/roms/snes/es.sfc');spanish.write_bytes(data[::-1]);digest=hashlib.sha1(data[::-1]).hexdigest()
        self.installed(home,'kit',exe='zelda3',sandbox=True,folder='Z3',extra={'setup':'zelda3','disc':None,'rom':ours});folder=home/'ports/Z3';(folder/'zelda3.ini').write_text('# Language = de\nFullscreen = 0\n');calls=[]
        def run(command,cwd=None,progress=None,until=None):
            calls.append(command)
            if command[0]=='sh' and 'make' in command[2]:(folder/'zelda3').write_bytes(b'x');(folder/'zelda3_assets.dat').write_bytes(b'd')
            return 0
        with patch.dict(self.ports.ZELDA3_ES,{'sha1':{digest:'zelda3_es.sfc'},'sizes':[len(data)]}):self.ports.configure('web/x',self.store,[],lambda _:None,home,run=run)
        text=' '.join(' '.join(c) for c in calls);self.assertIn('--extract-dialogue -r zelda3_es.sfc',text);self.assertIn('--languages=es',text);self.assertIn('Language = es',(folder/'zelda3.ini').read_text());self.assertEqual((folder/'zelda3_es.sfc').read_bytes(),data[::-1])

class DisplayModTests(PortDefaultsTests):
    def kit(self):
        folder=self.root/'kit';(folder/'psxrecomp/runtime/src').mkdir(parents=True);(folder/'psxrecomp/runtime/include').mkdir(parents=True)
        (folder/'psxrecomp/runtime/runtime.cmake').write_text('set(S\n    ${PSXRECOMP_ROOT}/runtime/src/mod_builtin_pgxp.c\n    ${PSXRECOMP_ROOT}/runtime/src/mod_builtin_bezel.c\n    ${PSXRECOMP_ROOT}/runtime/src/mod_packages.cpp\n)\n')
        (folder/'psxrecomp/runtime/include/mod_plugins.h').write_text('int psx_mod_set_fixed_display_aspect(uint32_t,uint32_t);\nint psx_mod_set_frame_interpolation_blend(uint32_t);\n');return folder
    def test_the_display_mod_is_added_once_with_a_backup_and_a_valid_manifest(self):
        import tomllib
        folder=self.kit();self.assertEqual(self.ports.apply_display_mod(folder),'applied');self.assertEqual(self.ports.apply_display_mod(folder),'present')
        cmake=(folder/'psxrecomp/runtime/runtime.cmake').read_text();self.assertEqual(cmake.count('mod_builtin_deck.c'),1);self.assertTrue((folder/'psxrecomp/runtime/runtime.cmake.orig').is_file())
        manifest=tomllib.loads((folder/'psxrecomp/mods/builtin/packages/psx.deck.display/1.0.0/manifest.toml').read_text());self.assertEqual({f['id'] for f in manifest['feature']},{'interpolation','widescreen'});self.assertEqual({p['id'] for p in manifest['plugin']},{'psx.deck.interpolation','psx.deck.widescreen'})
        self.assertIn('psx_mod_set_frame_interpolation(0)',(folder/'psxrecomp/runtime/src/mod_builtin_deck.c').read_text())
    def test_a_kit_whose_framework_lacks_the_plugin_interface_is_left_alone(self):
        folder=self.kit();(folder/'psxrecomp/runtime/include/mod_plugins.h').write_text('int other(void);\n');self.assertEqual(self.ports.apply_display_mod(folder),'incompatible');self.assertFalse((folder/'psxrecomp/runtime/src/mod_builtin_deck.c').exists())
    def test_enhance_kit_enables_the_display_features_and_keeps_edited_state(self):
        folder=self.kit();pkg=folder/'build/mods/packages'
        for pid in ('psx.enhancement.pgxp','psx.deck.display'):(pkg/pid/'1.0.0').mkdir(parents=True);(pkg/pid/'1.0.0/manifest.toml').write_text('x')
        (folder/'build/mods/state.toml').write_text('format_version = 2\n');self.ports.enhance_kit(folder)
        import tomllib;state=tomllib.loads((folder/'build/mods/state.toml').read_text());self.assertEqual({(f['package_id'],f['id']) for f in state['feature']},{('psx.enhancement.pgxp','pgxp'),('psx.deck.display','interpolation'),('psx.deck.display','widescreen')})
        (folder/'build/mods/state.toml').write_text('format_version = 2\n[[feature]]\npackage_id = "x.other"\nid = "y"\nenabled = true\n');before=(folder/'build/mods/state.toml').read_text();self.ports.enhance_kit(folder);self.assertEqual((folder/'build/mods/state.toml').read_text(),before)

class WiiUpdateTests(unittest.TestCase):
    def setUp(self):
        import tempfile;self.root=pathlib.Path(tempfile.mkdtemp());self.addCleanup(shutil.rmtree,self.root,True)
        self.folder=self.root/'Apps/MarioKartWii';(self.folder/'.steamdeck').mkdir(parents=True);(self.folder/'.steamdeck/runner.json').write_text('{"type":"flatpak","app_id":"io.example.Wheel"}')
        self.tool=self.folder/'WiiCompiled-Setup-x86_64.AppImage';self.tool.write_bytes(b'\x7fELFold');(self.folder/'version.txt').write_text('v0.2.33')
        self.apps=[{'name':'Mario Kart Wii','repository':'patchzyy/Wiicompiled','installed':'v0.2.33','skipped':'','folder':str(self.folder)}]
        self.home=self.root/'home';self.home.mkdir()
    def release(self,payload=b'\x7fELFnew'):
        import hashlib
        return {'tag_name':'v0.2.34','html_url':'https://x/r','body':'n','assets':[{'name':'WiiCompiled-Setup-x86_64.AppImage','browser_download_url':'https://x/a','digest':'sha256:'+hashlib.sha256(payload).hexdigest()}]}
    def opener(self,payload):
        class Response(io.BytesIO):
            headers={'Content-Length':str(len(payload))}
            def __enter__(self):return self
            def __exit__(self,*a):return False
        return lambda url,timeout=0:Response(payload)
    def test_the_installation_is_found_with_its_flatpak_runner_and_the_update_is_reported_once(self):
        from deck_library import wiiupdate
        with patch('deck_library.updates.quiver_apps',return_value=self.apps):
            found=wiiupdate.installations(None,self.home);self.assertEqual(found[0]['command'][:2],['flatpak','run']);self.assertEqual(found[0]['data_home'],self.home/'.var/app/io.example.Wheel/data')
            self.assertEqual(wiiupdate.check(None,lambda url:self.release(),self.home),{'name':'Mario Kart Wii','installed':'v0.2.33','latest':'v0.2.34','page':'https://x/r'})
            self.assertEqual(updates.check_quiver(None,lambda url:self.release(),self.home),[])
        with patch('deck_library.updates.quiver_apps',return_value=[{**self.apps[0],'installed':'v0.2.34'}]):self.assertIsNone(wiiupdate.check(None,lambda url:self.release(),self.home))
    def test_a_download_whose_hash_differs_is_refused_and_the_old_tool_stays(self):
        from deck_library import wiiupdate
        image=self.root/'mk.iso';image.write_bytes(b'RMCP01'+b'0'*100)
        with patch('deck_library.updates.quiver_apps',return_value=self.apps):item=wiiupdate.installations(None,self.home)[0]
        info=wiiupdate.latest(lambda url:self.release(b'\x7fELFother'))
        with self.assertRaisesRegex(ValueError,'SHA-256'):wiiupdate.update(item,info,image,opener=self.opener(b'\x7fELFnew'),run=lambda *a,**k:0)
        self.assertEqual(self.tool.read_bytes(),b'\x7fELFold');self.assertEqual((self.folder/'version.txt').read_text(),'v0.2.33');self.assertFalse(list(self.folder.glob('*.download')))
    def test_update_installs_the_new_tool_runs_the_install_and_failure_restores_the_previous_one(self):
        from deck_library import wiiupdate
        image=self.root/'mk.iso';image.write_bytes(b'RMCP01'+b'0'*100);payload=b'\x7fELFnew'
        with patch('deck_library.updates.quiver_apps',return_value=self.apps):item=wiiupdate.installations(None,self.home)[0]
        item['data_home']=self.home;info=wiiupdate.latest(lambda url:self.release(payload));calls=[]
        usage=type('U',(),{'free':50_000_000_000})()
        with patch('deck_library.wiiupdate.shutil.disk_usage',return_value=usage):tag=wiiupdate.update(item,info,image,opener=self.opener(payload),run=lambda command,cwd,env,log,progress,cancel:calls.append(command))
        self.assertEqual(tag,'v0.2.34');self.assertEqual(self.tool.read_bytes(),payload);self.assertEqual((self.folder/'version.txt').read_text(),'v0.2.34');self.assertEqual(calls[0][-3:-1],['install','--game']);self.assertIn('--command='+str(self.tool),calls[0]);self.assertEqual(calls[0][:2],['flatpak','run']);self.assertEqual(calls[0][calls[0].index('install')-1],'org.kde.Sdk//6.11');self.assertIn('--share=network',calls[0]);self.assertIn('--env=XDG_DATA_HOME='+str(self.home/'.var/app/io.example.Wheel/data'),calls[0]);self.assertFalse((self.folder/(self.tool.name+'.previous')).exists())
        (self.folder/'version.txt').write_text('v0.2.33');self.tool.write_bytes(b'\x7fELFold')
        def failing(*a,**k):raise RuntimeError('boom')
        with patch('deck_library.wiiupdate.shutil.disk_usage',return_value=usage),self.assertRaises(RuntimeError):wiiupdate.update(item,info,image,opener=self.opener(payload),run=failing)
        with patch('deck_library.wiiupdate.shutil.disk_usage',return_value=type('U',(),{'free':1})()),self.assertRaisesRegex(RuntimeError,'20 GB'):wiiupdate.update(item,info,image,opener=self.opener(payload),run=failing)
        self.assertEqual(self.tool.read_bytes(),b'\x7fELFold');self.assertEqual((self.folder/'version.txt').read_text(),'v0.2.33')
