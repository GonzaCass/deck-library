import pathlib,shlex,struct,sys,tempfile,unittest
from unittest.mock import Mock,patch
from deck_library import shattered,proton_tools,port_removal
from deck_library.models import Entry,Store


class ShatteredTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name)
        self.steam=self.root/'Steam';self.account=self.steam/'userdata/1/config';self.account.mkdir(parents=True)
        self.prefix=self.steam/'steamapps/compatdata/123/pfx';self.prefix.mkdir(parents=True)
        self.game=self.prefix/'drive_c/game';self.game.mkdir(parents=True);self.exe=self.game/'Game.exe';self.pe(self.exe)
        for file in ('user.reg','system.reg','userdef.reg'):(self.prefix/file).write_text('WINE REGISTRY Version 2\n')
        self.store=Store(self.root/'private');self.entry=Entry('Spider-Man Shattered Dimensions',[str(self.exe)],kind='steam',platform='Windows',source=str(self.exe),metadata={'steam_appid':123,'steam_account':str(self.account)})
        self.store.save([self.entry]);self.config('proton_10')
        self.shortcut_patch=patch('deck_library.steam_inventory.shortcuts',return_value=[{'appid':123,'exe':'"'+str(self.exe)+'"'}]);self.shortcut_patch.start();self.addCleanup(self.shortcut_patch.stop)
        for p in (patch.object(proton_tools,'libraries',return_value=[self.steam]),patch.object(proton_tools,'resolve',return_value=self.root/'Proton 10.0/proton'),patch.object(port_removal,'in_use',return_value=False),patch.object(shattered,'tool',return_value=['protontricks'])):
            p.start();self.addCleanup(p.stop)
        self.commands=[]

    def pe(self,path):
        path.parent.mkdir(parents=True,exist_ok=True);data=bytearray(160);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,80);data[80:86]=b'PE\0\0L\x01';path.write_bytes(data)

    def config(self,tool):
        file=self.steam/'config/config.vdf';file.parent.mkdir(exist_ok=True)
        file.write_text('"InstallConfigStore" { "Software" { "Valve" { "Steam" { "CompatToolMapping" { "123" { "name" "'+tool+'" } } } } } }')

    def runner(self,command,progress,**kwargs):
        self.commands.append((command,kwargs))
        if '-q' in command:
            (self.prefix/'winetricks.log').write_text('d3dx9_43\nxact\n');self.pe(self.prefix/'drive_c/windows/syswow64/d3dx9_43.dll')
        if '-c' in command:
            reg=pathlib.Path(shlex.split(command[command.index('-c')+1])[-1]);values=reg.read_text().splitlines()[3:]
            section=shattered.REGISTRY.split('\\',1)[1].replace('\\','\\\\')
            (self.prefix/'user.reg').write_text('WINE REGISTRY Version 2\n['+section+'] 1\n'+'\n'.join(values)+'\n')

    def test_applies_only_fixed_components_to_existing_prefix_and_preserves_game_saves_and_steam(self):
        save=self.prefix/'drive_c/users/steamuser/save.dat';save.parent.mkdir(parents=True);save.write_text('save')
        game_before=self.exe.read_bytes();config=(self.steam/'config/config.vdf').read_bytes()
        result=shattered.apply(self.entry,self.store,language='ESN',runner=self.runner)
        self.assertEqual(result['state'],'applied');self.assertTrue((self.game/'d3dx9_43.dll').is_file())
        self.assertEqual(self.exe.read_bytes(),game_before);self.assertEqual(save.read_text(),'save');self.assertEqual((self.steam/'config/config.vdf').read_bytes(),config)
        self.assertEqual(self.commands[0][0],['protontricks','123','-q','d3dx9_43','xact'])
        self.assertEqual(self.commands[0][1]['env']['PROTON_VERSION'],'Proton 10.0')
        self.assertTrue((pathlib.Path(result['backup'])/'0').is_file());self.assertTrue((self.store.root/'fixes'/(self.entry.id+'-shattered.json')).is_file())
        self.assertIn('"AudioLanguage"="ESN"',(self.prefix/'user.reg').read_text())

    def test_repeat_does_not_reinstall_dependencies_or_replace_existing_local_dll(self):
        shattered.apply(self.entry,self.store,runner=self.runner)
        self.commands.clear();target=self.game/'d3dx9_43.dll';target.write_bytes(b'custom local DLL')
        shattered.apply(self.entry,self.store,language='keep',runner=self.runner)
        self.assertEqual(self.commands,[]);self.assertEqual(target.read_bytes(),b'custom local DLL')

    def test_wrong_proton_missing_prefix_and_changed_shortcut_do_not_run_commands(self):
        self.config('proton_11')
        with self.assertRaisesRegex(ValueError,'Proton 10.0'):shattered.apply(self.entry,self.store,runner=self.runner)
        self.config('proton_10');(self.prefix/'user.reg').unlink()
        with self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        (self.prefix/'user.reg').write_text('registry')
        with patch('deck_library.steam_inventory.shortcuts',return_value=[{'appid':123,'exe':'/another/Game.exe'}]),self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertFalse(self.commands)

    def test_running_game_symlink_and_conflicting_appid_files_are_preserved(self):
        with patch.object(port_removal,'in_use',return_value=True),self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        external=self.root/'outside.reg';external.write_text('outside');(self.prefix/'user.reg').unlink();(self.prefix/'user.reg').symlink_to(external)
        with self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertEqual(external.read_text(),'outside');self.assertFalse(self.commands)
        (self.prefix/'user.reg').unlink();(self.prefix/'user.reg').write_text('original')
        for name in ('steam_appid.txt','steam_appid.txt.disabled'):(self.game/name).write_text('original')
        with self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertFalse(self.commands)

    def test_failed_installer_or_registry_verification_never_records_success(self):
        with self.assertRaises(RuntimeError):shattered.apply(self.entry,self.store,runner=lambda *a,**k:None)
        self.runner(['protontricks','123','-q'],None)
        with self.assertRaises(RuntimeError):shattered.apply(self.entry,self.store,language='ESN',runner=lambda *a,**k:None)
        self.assertFalse((self.store.root/'fixes'/(self.entry.id+'-shattered.json')).exists())
        self.assertTrue(list((self.store.root/'fix-backups'/self.entry.id).glob('*/0')))

    def test_disables_an_existing_appid_file_with_a_backup(self):
        original=self.game/'steam_appid.txt';original.write_text('123')
        result=shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertFalse(original.exists());self.assertEqual((self.game/'steam_appid.txt.disabled').read_text(),'123')
        self.assertTrue(any(p.is_file() and p.read_bytes()==b'123' for p in pathlib.Path(result['backup']).iterdir()))

    def test_title_matching_does_not_apply_to_another_spiderman_or_generic_game_exe(self):
        from deck_library.presets import public_game_id
        self.assertTrue(shattered.matches(self.entry));self.assertEqual(public_game_id(self.entry),'spiderman-shattered-dimensions')
        console=Entry(self.entry.name,['dolphin','game.iso'],kind='emulated',platform='Wii',source='game.iso');self.assertFalse(shattered.matches(console))
        for name in ('Spider-Man: Edge of Time','Game','Spider-Man 2'):
            self.entry.name=name;self.assertFalse(shattered.matches(self.entry))
            with self.assertRaises(ValueError):shattered.inspect(self.entry)

    def test_command_runner_reports_progress_failure_and_timeout(self):
        lines=[];shattered.run([sys.executable,'-c','print("progress")'],lines.append)
        self.assertEqual(lines,['progress'])
        with self.assertRaisesRegex(RuntimeError,'error 7'):shattered.run([sys.executable,'-c','raise SystemExit(7)'],lines.append)
        with self.assertRaisesRegex(RuntimeError,'tiempo de espera'):shattered.run([sys.executable,'-c','import time; time.sleep(5)'],lines.append,timeout=.1)

    def test_wrong_binary_architecture_is_not_modified(self):
        data=bytearray(self.exe.read_bytes());data[84:86]=b'd\x86';self.exe.write_bytes(data)
        with self.assertRaises(ValueError):shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertFalse(self.commands);self.assertFalse((self.store.root/'fixes').exists())

    def test_audio_only_is_the_default_and_keeps_all_language_values(self):
        original='WINE REGISTRY Version 2\n[Software\\\\Activision\\\\Spider-Man (TM) SD\\\\Settings\\\\Game] 1\n"AudioLanguage"="FRA"\n"Language"="FRA"\n"Locale"="FRA"\n"TextLanguage"="FRA"\n'
        (self.prefix/'user.reg').write_text(original)
        result=shattered.apply(self.entry,self.store,runner=self.runner)
        self.assertEqual(result['language'],'keep');self.assertEqual((self.prefix/'user.reg').read_text(),original)
        self.assertTrue(self.commands);self.assertTrue(all('-c' not in command for command,_ in self.commands))
