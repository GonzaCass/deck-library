import hashlib,io,json,os,pathlib,struct,tarfile,tempfile,unittest
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
