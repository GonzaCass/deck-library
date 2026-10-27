import json,os,pathlib,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from deck_library import proton_selection as selection,proton_tools,port_runtime,runtime
from deck_library.models import Entry,Store

class ProtonSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=pathlib.Path(self.tmp.name);self.store=Store(self.home/'private');self.folder=self.home/'game';self.folder.mkdir()
        self.exe=self.folder/'game.exe';self.exe.write_bytes(b'MZ');self.record={'repository':'test/game','runtime':'proton','executable':'game.exe'};(self.folder/'.deck-library-port.json').write_text(json.dumps(self.record))
        self.entry=Entry('Game',[sys.executable,'-m','deck_library.port_runtime',str(self.folder)],source=str(self.exe),cwd=str(pathlib.Path.cwd()),platform='Windows',metadata={'port_repository':'test/game'})
        self.store.save([self.entry]);self.tools={}
        for name in ('Proton 11.0','Proton 9.0 (Beta)','GE-Proton10-26'):
            path=self.home/'.local/share/Steam/steamapps/common'/name/'proton';path.parent.mkdir(parents=True);path.write_text('#!/usr/bin/python3\nimport os,json,sys,pathlib\npathlib.Path(os.environ["DECK_LIBRARY_TEST_OUTPUT"]).write_text(json.dumps({"tool":pathlib.Path(__file__).parent.name,"prefix":os.environ["STEAM_COMPAT_DATA_PATH"],"appid":os.environ.get("SteamAppId"),"args":sys.argv[1:]}))\n');path.chmod(0o755);self.tools[name]=path
    def test_enumeration_handles_external_libraries_ge_and_rejects_paths(self):
        tools=proton_tools.installed(self.home);self.assertEqual(set(tools),set(self.tools));self.assertEqual(proton_tools.resolve('GE-Proton10-26',self.home),self.tools['GE-Proton10-26'])
        with self.assertRaises(ValueError):proton_tools.resolve('../../bin/sh',self.home)
        with self.assertRaises(ValueError):proton_tools.resolve('Proton 8.0',self.home)
    def test_preference_survives_scan_and_does_not_change_shortcut_identity(self):
        with patch.object(proton_tools,'installed',return_value=self.tools),patch.object(selection,'busy',return_value=False):selection.save(self.entry,'GE-Proton10-26',self.store)
        new=Entry('Game',self.entry.command,id=self.entry.id,source=str(self.exe),platform='Windows',metadata={'port_repository':'test/game'})
        self.store.merge([new],overwrite=False)
        self.assertEqual(self.store.load()[0].metadata['proton_version'],'GE-Proton10-26');self.assertEqual(self.store.load()[0].id,self.entry.id)
        with patch.object(proton_tools,'installed',return_value=self.tools):command,env=selection.launch_command(self.entry,self.entry.command,{},self.store)
        self.assertEqual(command[-2:],['--proton','GE-Proton10-26']);self.assertEqual(command.count('--proton'),1)
    def test_two_tools_keep_the_same_port_prefix_and_missing_selection_never_falls_back(self):
        with patch.object(proton_tools,'installed',return_value=self.tools):
            first,a=port_runtime.command_for(self.folder,self.store,'Proton 11.0');second,b=port_runtime.command_for(self.folder,self.store,'Proton 9.0 (Beta)')
            self.assertNotEqual(first[0],second[0]);self.assertEqual(a['STEAM_COMPAT_DATA_PATH'],b['STEAM_COMPAT_DATA_PATH'])
            with self.assertRaises(ValueError):port_runtime.command_for(self.folder,self.store,'Proton 8.0')
    def test_saved_proton_is_used_by_the_actual_steam_launcher_without_editing_steam(self):
        output=self.home/'output.json'
        stale=self.home/'old unpacked copy';(stale/'deck_library').mkdir(parents=True)
        (stale/'deck_library/__init__.py').write_text('')
        (stale/'deck_library/port_runtime.py').write_text('raise SystemExit("Stale runtime must not run")')
        self.entry.cwd=str(stale);self.store.save([self.entry])
        with patch.object(proton_tools,'installed',return_value=self.tools),patch.object(selection,'busy',return_value=False):selection.save(self.entry,'Proton 9.0 (Beta)',self.store)
        launcher=runtime.make_launcher(self.entry,self.store)
        env={**os.environ,'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'data'),'SteamAppId':'123','DECK_LIBRARY_TEST_OUTPUT':str(output)}
        result=subprocess.run([str(launcher)],cwd=pathlib.Path.cwd(),env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr);data=json.loads(output.read_text());self.assertEqual(data['tool'],'Proton 9.0 (Beta)');self.assertEqual(data['appid'],'123');self.assertEqual(data['args'][0],'run');self.assertTrue(data['prefix'].startswith(str(self.store.root)));self.assertFalse((self.store.root/'pending.json').exists())
    def test_raw_windows_exe_uses_proton_without_unix_execute_permissions(self):
        entry=Entry('Standalone',[str(self.exe)],source=str(self.exe),platform='Windows');self.assertEqual(selection.mode(entry),'exe');issues,_=runtime.diagnostics(entry,self.store);self.assertFalse(issues,issues)
        with patch.object(selection,'default_tool',return_value=self.tools['Proton 11.0']):command,env=selection.launch_command(entry,entry.command,{},self.store)
        self.assertEqual(command[0],str(self.tools['Proton 11.0']));self.assertIn(entry.id,env['STEAM_COMPAT_DATA_PATH'])
    def test_running_game_and_external_steam_shortcuts_are_not_rewritten(self):
        with patch.object(proton_tools,'installed',return_value=self.tools),patch.object(selection,'busy',return_value=True),self.assertRaises(RuntimeError):selection.save(self.entry,'Proton 11.0',self.store)
        self.assertNotIn('proton_version',self.store.load()[0].metadata)
        external=Entry('External',[str(self.exe)],kind='steam',platform='Windows',source=str(self.exe))
        self.assertEqual(selection.mode(external),'steam')
        with self.assertRaises(ValueError):selection.save(external,'Proton 11.0',self.store)
