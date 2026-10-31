import pathlib,tempfile,unittest,struct,json
from unittest.mock import patch
from deck_library import runtime_components as c,pe_imports,proton_selection,proton_tools,game_fixes
from deck_library.models import Entry,Store
from pe_fixture import image


class RuntimeComponentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name);self.store=Store(self.root/'data')
        self.exe=self.root/'game.exe';self.exe.write_bytes(image(['vcruntime140.dll','msvcp140.dll']))
        self.entry=Entry('Test',[str(self.exe)],source=str(self.exe),platform='Windows');self.store.save([self.entry])
        self.prefix=c.prefix_for(self.entry,self.store);self.prefix.mkdir(parents=True);(self.prefix/'user.reg').write_text('REGISTRY')
        self.tool=self.root/'Proton 11.0/proton';self.tool.parent.mkdir();self.tool.write_text('')
        for name in ('wine','wineserver'):
            p=self.tool.parent/'files/bin'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('')
        self.script=self.root/'tools/winetricks';self.script.parent.mkdir();self.script.write_text('')
    def test_pe_reader_handles_32_and_64_bit_imports_without_loading_code(self):
        for arch in ('x86','x64'):
            self.exe.write_bytes(image(['KERNEL32.dll','vcruntime140.dll'],arch));value=pe_imports.inspect(self.exe)
            self.assertEqual(value['architecture'],arch);self.assertEqual(value['imports'],['kernel32.dll','vcruntime140.dll'])
    def test_corrupt_pe_is_unknown_and_never_ready(self):
        for value in (b'MZ',b'not windows',image()[:300]):
            self.exe.write_bytes(value);self.assertEqual(c.inspect(self.entry,self.store)['state'],'unknown')
        data=bytearray(image(['vcruntime140.dll']));struct.pack_into('<I',data,512+12,0xffff0000);self.exe.write_bytes(data)
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'unknown')
    def test_status_checks_dll_architecture_not_just_receipt_or_filename(self):
        value=c.inspect(self.entry,self.store);self.assertEqual(value['state'],'missing');self.assertEqual(value['components'][0]['verb'],'vcrun2022')
        (self.prefix/'winetricks.log').write_text('vcrun2022\n')
        folder=self.prefix/'drive_c/windows/system32';folder.mkdir(parents=True)
        for name in ('vcruntime140.dll','msvcp140.dll'):(folder/name).write_bytes(image(architecture='x86'))
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'missing')
        for name in ('vcruntime140.dll','msvcp140.dll'):(folder/name).write_bytes(image())
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'present')
    def test_no_known_imports_is_unknown_instead_of_claiming_everything_installed(self):
        self.exe.write_bytes(image(['kernel32.dll','d3d11.dll']))
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'unknown')
    def test_local_dlls_are_checked_before_prefix_and_x86_uses_syswow64(self):
        for name in ('vcruntime140.dll','msvcp140.dll'):(self.root/name).write_bytes(image())
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'present')
        self.exe.write_bytes(image(['d3dx9_43.dll'],'x86'));folder=self.prefix/'drive_c/windows/syswow64';folder.mkdir(parents=True);(folder/'d3dx9_43.dll').write_bytes(image(architecture='x86'))
        self.assertEqual(c.inspect(self.entry,self.store)['state'],'present')
    def test_preparation_targets_exact_prefix_and_verifies_files_and_log(self):
        commands=[]
        def run(command,progress,**kwargs):
            commands.append((command,kwargs['env']))
            (self.prefix/'winetricks.log').write_text('vcrun2022\n')
            folder=self.prefix/'drive_c/windows/system32';folder.mkdir(parents=True,exist_ok=True)
            for name in ('vcruntime140.dll','msvcp140.dll'):(folder/name).write_bytes(image())
        with patch.object(c,'tool_for',return_value=self.tool),patch.object(c,'script',return_value=self.script),patch('deck_library.shattered.tool',return_value=['flatpak','run']),patch('deck_library.port_removal.in_use',return_value=False):
            result=c.prepare(self.entry,['vcrun2022'],self.store,runner=run)
        self.assertEqual(result['state'],'installed');self.assertEqual(commands[0][1]['WINEPREFIX'],str(self.prefix))
        self.assertIn('--env=WINEPREFIX='+str(self.prefix),commands[0][0]);self.assertEqual(commands[0][0][-2:],['-q','vcrun2022'])
        self.assertEqual((pathlib.Path(result['backup'])/'user.reg').read_text(),'REGISTRY')
    def test_failure_retains_backup_and_does_not_publish_installed_receipt(self):
        with patch.object(c,'tool_for',return_value=self.tool),patch.object(c,'script',return_value=self.script),patch('deck_library.shattered.tool',return_value=['flatpak','run']),patch('deck_library.port_removal.in_use',return_value=False):
            with self.assertRaises(RuntimeError):c.prepare(self.entry,['vcrun2022'],self.store,runner=lambda *a,**k:None)
        self.assertFalse((self.store.root/'dependencies'/(self.entry.id+'.json')).exists())
        records=list((self.store.root/'dependency-backups'/self.entry.id).glob('*/result.json'));self.assertEqual(json.loads(records[0].read_text())['state'],'failed')
    def test_new_proton_prefix_supplied_components_skip_redistributable_installation(self):
        (self.prefix/'user.reg').unlink();self.exe.write_bytes(image(['d3dcompiler_47.dll']))
        def initialize(command,progress,**kwargs):
            self.assertEqual(command[1:],["run","cmd.exe","/c","exit","0"])
            (self.prefix/'user.reg').write_text('REGISTRY');p=self.prefix/'drive_c/windows/system32';p.mkdir(parents=True);(p/'d3dcompiler_47.dll').write_bytes(image())
        with patch.object(c,'tool_for',return_value=self.tool),patch.object(c,'script') as download,patch('deck_library.port_removal.in_use',return_value=False):
            result=c.prepare(self.entry,['d3dcompiler_47'],self.store,runner=initialize)
        self.assertEqual(result['state'],'present');download.assert_not_called()

    def test_dependency_runner_can_cancel_a_running_process(self):
        from deck_library.shattered import run
        from deck_library.ports import Cancelled
        import threading,sys
        event=threading.Event();timer=threading.Timer(0.15,event.set);timer.start()
        try:
            with self.assertRaises(Cancelled):run([sys.executable,'-c','import time; time.sleep(30)'],lambda _:None,timeout=5,cancel=event)
        finally:timer.cancel()

    def test_busy_game_is_not_modified(self):
        with patch.object(c,'tool_for',return_value=self.tool),patch('deck_library.port_removal.in_use',return_value=True),self.assertRaises(ValueError):
            c.prepare(self.entry,['vcrun2022'],self.store)
        self.assertFalse((self.store.root/'dependency-backups').exists())

    def test_download_integrity_is_checked_before_script_is_saved(self):
        import io,hashlib
        with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong script')):
            with self.assertRaises(ValueError):c.script(self.store,lambda _:None)
        target=self.store.root/'tools/runtime-components'/('winetricks-'+c.WINETRICKS_TAG)
        self.assertFalse(target.exists())
        with patch.object(c,'WINETRICKS_SHA256',hashlib.sha256(b'trusted').hexdigest()),patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'trusted')):
            self.assertEqual(c.script(self.store,lambda _:None).read_bytes(),b'trusted')

    def test_arbitrary_verbs_and_unobserved_components_are_refused(self):
        for verbs in (['../../evil'],['physx']):
            with self.assertRaises(ValueError):c.prepare(self.entry,verbs,self.store)
    def test_steam_prefix_resolution_refuses_two_distinct_prefixes(self):
        entry=Entry('Steam',['steam','steam://run/115320'],'steam','Windows',str(self.exe),metadata={'steam_appid':115320,'steam_store':True})
        roots=[self.root/'Steam',self.root/'SD']
        for root in roots:
            p=root/'steamapps/compatdata/115320/pfx';p.mkdir(parents=True);(p/'user.reg').write_text('')
        with patch.object(proton_tools,'libraries',return_value=roots),self.assertRaises(ValueError):c.prefix_for(entry,self.store)
        (roots[1]/'steamapps/compatdata/115320/pfx/user.reg').unlink()
        with patch.object(proton_tools,'libraries',return_value=roots):self.assertEqual(c.prefix_for(entry,self.store),roots[0]/'steamapps/compatdata/115320/pfx')
    def test_legacy_visual_cpp_can_be_detected_in_winsxs(self):
        self.exe.write_bytes(image(['msvcr90.dll','d3dx9_36.dll'],'x86'))
        value=c.inspect(self.entry,self.store)
        self.assertEqual({r['verb'] for r in value['components']},{'vcrun2008','d3dx9_36'})
        target=self.prefix/'drive_c/windows/winsxs/x86_microsoft.vc90.crt_test/msvcr90.dll';target.parent.mkdir(parents=True);target.write_bytes(image(architecture='x86'))
        value=c.inspect(self.entry,self.store);self.assertEqual(next(r for r in value['components'] if r['verb']=='vcrun2008')['state'],'present')

    def test_xact_verb_matches_the_executable_architecture(self):
        for arch,verb in [('x86','xact'),('x64','xact_x64')]:
            self.exe.write_bytes(image(['xaudio2_7.dll'],arch))
            self.assertEqual([r['verb'] for r in c.inspect(self.entry,self.store)['components']],[verb])

    def test_known_steam_games_are_discovered_from_manifests_with_case_insensitive_exe(self):
        root=self.root/'Steam';folder=root/'steamapps/common/Conviction/src/SYSTEM';folder.mkdir(parents=True)
        (folder/'Conviction_game.exe').write_bytes(image())
        (root/'steamapps/appmanifest_33220.acf').write_text('"AppState" { "installdir" "Conviction" "name" "Splinter Cell Conviction" }')
        with patch.object(proton_tools,'libraries',return_value=[root]):entries=game_fixes.discover()
        self.assertEqual(len(entries),1);self.assertEqual(entries[0].metadata['steam_appid'],33220)
        self.assertEqual(entries[0].source,str(folder/'Conviction_game.exe'));self.assertTrue(entries[0].metadata['steam_store'])
        (root/'steamapps/appmanifest_33220.acf').write_text('"AppState" { "installdir" "../../outside" "name" "Bad" }')
        with patch.object(proton_tools,'libraries',return_value=[root]):self.assertFalse(game_fixes.discover())

    def test_automatic_proton_uses_confirmed_installed_build_and_keeps_explicit_choice(self):
        entry=Entry('Naruto',['python3','-m','deck_library.port_runtime',str(self.root)],source=str(self.exe),metadata={'port_repository':'JorjBarbosa/Naruto-Rise-Recomp'})
        with patch.object(proton_tools,'installed',return_value={'Proton 11.0':self.tool}):
            self.assertEqual(proton_selection.automatic_version(entry,self.store),'Proton 11.0')
            command,_=proton_selection.launch_command(entry,entry.command,{},self.store)
            self.assertEqual(command[-2:],['--proton','Proton 11.0'])
        entry.metadata['proton_version']='Proton 9.0 (Beta)'
        with patch.object(proton_tools,'installed',return_value={'Proton 11.0':self.tool,'Proton 9.0 (Beta)':self.tool}):
            command,_=proton_selection.launch_command(entry,entry.command,{},self.store)
            self.assertEqual(command[-2:],['--proton','Proton 9.0 (Beta)'])

    def test_only_bundled_confirmed_profiles_recommend_proton(self):
        entry=Entry('Naruto',[str(self.exe)],source=str(self.exe),metadata={'port_repository':'JorjBarbosa/Naruto-Rise-Recomp'})
        self.assertEqual(game_fixes.recommendation(entry,self.store)['version'],'Proton 11.0')
        from deck_library import presets
        custom={'id':'custom','runtime':{'kind':'proton','version':'Unknown'},'tested':{'status':'user-confirmed'}}
        with patch.object(presets,'recommended',return_value=[custom]):self.assertIsNone(game_fixes.recommendation(entry,self.store))

    def test_fix_links_match_appid_or_exact_title_and_ignore_emulated_names(self):
        entry=Entry('PROTOTYPE 2',['game.exe'],platform='Windows');self.assertEqual(game_fixes.for_entry(entry)[0]['id'],'prototype-2')
        entry.name='Prototype 2 unrelated';self.assertEqual(game_fixes.for_entry(entry),[])
        entry.metadata['steam_appid']=33220;self.assertEqual(game_fixes.for_entry(entry)[0]['id'],'splinter-cell-conviction')
        entry.kind='emulated';self.assertEqual(game_fixes.for_entry(entry),[])
