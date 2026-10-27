import json,os,pathlib,struct,tempfile,unittest
from unittest.mock import patch
from deck_library.models import Entry,Store
from deck_library.steam import read_kv,write_kv,update_shortcuts,SteamRunningError,KVError,get,set_value
from deck_library.runtime import clean_environment,make_launcher,prepare_eden_profile,launch
from deck_library.discovery import scan,is_base_rom

class CoreTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_vdf_roundtrip_preserves_unknown_fields_and_unsigned_ids(self):
        obj={'shortcuts':(0,{'0':(0,{'appid':(2,struct.pack('<I',0xf1234567)),'appname':(1,'Prueba á "quoted"'),'custom':(7,b'12345678'),'tags':(0,{'4':(1,'Favoritos')})})})}
        data=write_kv(obj);self.assertEqual(write_kv(read_kv(data)),data)
    def test_steam_write_preserves_other_games_identity_and_backup(self):
        cfg=self.root/'config';cfg.mkdir();existing={'appname':(1,'Mi juego'),'appid':(2,struct.pack('<I',0xf0000001)),'LastPlayTime':(2,struct.pack('<I',500)),'tags':(0,{'1':(1,'Favoritos')})};other={'appname':(1,'Otro'),'exe':(1,'"/otro"')}
        old=write_kv({'shortcuts':(0,{'0':(0,existing),'9':(0,other)})});(cfg/'shortcuts.vdf').write_bytes(old)
        e=Entry('Mi juego',['/bin/true']);result,backup=update_shortcuts(cfg,[e],lambda _:self.root/'path with spaces.sh',lambda:False)
        root=read_kv((cfg/'shortcuts.vdf').read_bytes())['shortcuts'][1]
        self.assertEqual(root['9'][1],other);self.assertEqual(get(root['0'][1],'appid'),0xf0000001);self.assertEqual(get(root['0'][1],'LastPlayTime'),500)
        self.assertEqual(root['0'][1]['tags'],existing['tags']);self.assertEqual(pathlib.Path(backup).read_bytes(),old);self.assertEqual(get(root['0'][1],'AllowDesktopConfig'),0)
    def test_steam_is_not_written_when_running_or_racing(self):
        cfg=self.root/'config';cfg.mkdir();old=write_kv({'shortcuts':(0,{})});f=cfg/'shortcuts.vdf';f.write_bytes(old)
        with self.assertRaises(SteamRunningError):update_shortcuts(cfg,[Entry('Game',['/bin/true'])],lambda _:self.root/'x.sh',lambda:True)
        self.assertEqual(f.read_bytes(),old)
        with self.assertRaises(SteamRunningError):
            update_shortcuts(cfg,[Entry('Game',['/bin/true'])],lambda _:self.root/'x.sh',iter([False,True]).__next__)
        self.assertEqual(f.read_bytes(),old)
    def test_invalid_vdf_is_not_overwritten(self):
        cfg=self.root/'config';cfg.mkdir();f=cfg/'shortcuts.vdf';f.write_bytes(b'broken')
        with self.assertRaises((KVError,UnicodeError)):update_shortcuts(cfg,[Entry('Game',['/bin/true'])],lambda _:self.root/'x',lambda:False)
        self.assertEqual(f.read_bytes(),b'broken')
    def test_discovery_skips_dlc_and_prefers_saved_quiver_executable(self):
        home=self.root;emu=home/'Applications/Eden.AppImage';emu.parent.mkdir();emu.write_text('test')
        roms=home/'Emulation/roms/switch';roms.mkdir(parents=True)
        for name in ('Game [0100152000022000].nsp','Update [0100152000022800].nsp','DLC [0100152000023001].nsp'):(roms/name).write_text('test')
        folder=home/'ports/quiver-launcher/Apps/Port-Project';folder.mkdir(parents=True);exe=folder/'launch.sh';exe.write_text('#!/bin/sh');exe.chmod(0o755);(folder/'selected_executable.txt').write_text(str(exe));(folder/'Setup.AppImage').write_text('setup')
        found=scan(home);self.assertEqual(len(found),2);self.assertTrue(any(e.command==[str(exe)] for e in found));self.assertTrue(any(e.name=='Game' for e in found))
    def test_environment_keeps_steam_input_and_display_but_removes_runtime(self):
        env=clean_environment({'DISPLAY':':1','WAYLAND_DISPLAY':'gamescope-0','SteamAppId':'123','LD_PRELOAD':'bad.so','LD_LIBRARY_PATH':'/steam-runtime','APPIMAGE':'old','PATH':'/tmp/.mount_bad/bin:/usr/bin'})
        self.assertEqual(env['SteamAppId'],'123');self.assertEqual(env['DISPLAY'],':1');self.assertNotIn('LD_PRELOAD',env);self.assertNotIn('LD_LIBRARY_PATH',env);self.assertEqual(env['PATH'],'/usr/bin')
    def test_eden_profile_preserves_storage_and_controls_without_mods(self):
        home=self.root/'home';config=home/'.config/eden';config.mkdir(parents=True)
        (config/'qt-config.ini').write_text('[Data%20Storage]\nnand_directory=/KEEP/NAND\nload_directory=/OLD/MODS\n[Controls]\nplayer_0_button_a=KEEP\n')
        (config/'custom').mkdir();(config/'custom/game.ini').write_text('[Renderer]\nresolution_setup=3\n')
        graphics=home/'.config/lsfg-vk';graphics.mkdir();(graphics/'conf.toml').write_text('current_profile = "existing"\n')
        store=Store(self.root/'data');e=Entry('MK8',['/bin/true'],platform='Switch',mods=False)
        with patch('pathlib.Path.home',return_value=home):env=prepare_eden_profile(e,store,{})
        text=(pathlib.Path(env['XDG_CONFIG_HOME'])/'eden/qt-config.ini').read_text()
        self.assertEqual(env['DISABLE_AUTO_UPDATES'],'1')
        self.assertEqual((pathlib.Path(env['XDG_CONFIG_HOME'])/'lsfg-vk/conf.toml').read_text(),(graphics/'conf.toml').read_text())
        self.assertIn('nand_directory=/KEEP/NAND',text);self.assertIn('player_0_button_a=KEEP',text);self.assertNotIn('load_directory=/OLD/MODS',text);self.assertEqual((config/'qt-config.ini').read_text().count('/OLD/MODS'),1)
    def test_launcher_uses_quoted_arguments_and_no_shell_injection(self):
        store=Store(self.root/'data with spaces');e=Entry('Test',['/bin/true']);store.save([e]);p=make_launcher(e,store)
        import subprocess
        subprocess.run(['sh','-n',str(p)],check=True);self.assertIn("'"+str(store.root)+"'",p.read_text());self.assertTrue(os.access(p,os.X_OK))
    def test_launch_failure_is_recorded_without_silent_success(self):
        store=Store(self.root/'data');e=Entry('Failure',['/bin/sh','-c','exit 7'])
        self.assertEqual(launch(e,store,notify=False),7)
        self.assertEqual(json.loads((store.root/'logs'/(e.id+'.status.json')).read_text())['exit'],7)
    def test_library_rejects_unknown_schema(self):
        store=Store(self.root/'data');store.root.mkdir();store.path.write_text('{"schema":99,"entries":[]}')
        with self.assertRaises(ValueError):store.load()

class LauncherNoticeTests(unittest.TestCase):
    def test_launch_errors_are_recorded_without_opening_a_system_dialog(self):
        import contextlib,io
        from deck_library.runtime import show_error
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);output=io.StringIO()
            with patch('subprocess.run',side_effect=AssertionError('No native error dialogs')),contextlib.redirect_stderr(output):show_error('Falta el juego.',store)
            self.assertEqual(json.loads((store.root/'launch-notice.json').read_text())['message'],'Falta el juego.')
            self.assertIn('Falta el juego.',output.getvalue())
    def test_launch_failure_notice_identifies_the_game(self):
        from deck_library.runtime import show_error
        import contextlib,io
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stderr(io.StringIO()):
            store=Store(tmp);entry=Entry('Test',['/bin/false'])
            self.assertEqual(launch(entry,store),1)
            value=json.loads((store.root/'launch-notice.json').read_text())
            self.assertEqual(value['entry_id'],entry.id);self.assertEqual(value['game'],entry.name)
            self.assertIn('terminó con error',value['message'])


if __name__=='__main__':unittest.main()
