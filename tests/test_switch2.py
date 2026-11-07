import json,pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import discovery,port_patterns

PREFS=lambda roots,emulators=None:{'rom_roots':[str(r) for r in roots],'port_roots':[],'quiver_roots':[],'emulators':emulators or {}}

class Switch2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.temp.name)
        # Minecraft instances and the host's flatpak list are not what is being checked here, and asking flatpak is slow.
        self.patches=[patch.object(discovery,'prism_entries',return_value=[]),patch('deck_library.discovery.shutil.which',return_value=None)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.temp.cleanup()
    def fork(self,name='Eglantine-x86_64.AppImage'):
        folder=self.home/'Applications';folder.mkdir(exist_ok=True);path=folder/name;path.write_bytes(b'\x7fELF');path.chmod(0o755);return path
    def test_games_in_a_switch2_folder_become_switch_2_games_run_by_the_fork_not_eden(self):
        roms=self.home/'roms';(roms/'switch2').mkdir(parents=True);(roms/'switch').mkdir();(roms/'switch2/Mario Kart World [0100152000022000].nsp').write_bytes(b'x');(roms/'switch/Zelda [01007EF00011E000].nsp').write_bytes(b'x')
        eden=self.home/'eden.AppImage';eden.write_bytes(b'\x7fELF');fork=self.fork()
        found={e.name:e for e in discovery.scan(self.home,preferences=PREFS([roms],{'eden':[str(eden)]}))}
        two=found['Mario Kart World'];one=found['Zelda']
        self.assertEqual((two.platform,one.platform),('Switch 2','Switch'));self.assertEqual(two.command[0],str(fork));self.assertEqual(two.command[1:3],['-f','-g']);self.assertEqual(one.command[0],str(eden))
        self.assertEqual(one.metadata.get('adapter'),'eden');self.assertNotEqual(two.metadata.get('adapter'),'eden')
        self.assertEqual(two.game_id.upper(),'0100152000022000')

    def test_the_nx2_folder_name_is_accepted_and_the_chosen_program_wins_over_a_detected_fork(self):
        roms=self.home/'roms';(roms/'nx2').mkdir(parents=True);(roms/'nx2/Game.xci').write_bytes(b'x');self.fork();chosen=self.home/'my-emulator';chosen.write_bytes(b'\x7fELF')
        entry=discovery.scan(self.home,preferences=PREFS([roms],{'switch2':[str(chosen)]}))[0]
        self.assertEqual((entry.platform,entry.command[0]),('Switch 2',str(chosen)))

    def test_nothing_is_listed_without_an_emulator_and_every_known_fork_name_is_detected(self):
        roms=self.home/'roms';(roms/'switch2').mkdir(parents=True);(roms/'switch2/Game.nsp').write_bytes(b'x')
        self.assertEqual([e for e in discovery.scan(self.home,preferences=PREFS([roms])) if e.platform=='Switch 2'],[])
        for name in ('Lichii-x86_64.AppImage','Orchid.AppImage','selevet-eglantine.AppImage'):
            path=self.fork(name);self.assertEqual(discovery.available_emulators(self.home,PREFS([roms]))['switch2']['command'],[str(path)]);path.unlink()

    def test_updates_and_dlc_are_not_listed_as_games(self):
        roms=self.home/'roms';(roms/'switch2').mkdir(parents=True);(roms/'switch2/Game [0100152000022800].nsp').write_bytes(b'x');(roms/'switch2/Game [0100152000022000].nsp').write_bytes(b'x');(roms/'switch2/dlc').mkdir();(roms/'switch2/dlc/Extra.nsp').write_bytes(b'x');self.fork()
        names=[e.source for e in discovery.scan(self.home,preferences=PREFS([roms])) if e.platform=='Switch 2'];self.assertEqual(len(names),1);self.assertIn('22000',names[0])

    def test_the_platform_has_its_own_label_and_requirement_and_switch_1_keeps_its_own(self):
        for raw in ('Switch 2','Nintendo Switch 2','switch2','NX2'):self.assertEqual(port_patterns.platform_info(raw)['short'],'Switch 2',raw)
        for raw in ('Switch','Nintendo Switch'):self.assertEqual(port_patterns.platform_info(raw)['short'],'Switch',raw)
        pattern=port_patterns.classify_port({'repository':'a/b','name':'Game','list':'Switch 2'});self.assertEqual((pattern['kind'],pattern['roms_folder']),('switch2','switch2'))
        self.assertIn('Eden oficial',pattern['summary'])

    def test_the_fork_list_comes_with_its_source_and_only_links_to_the_projects(self):
        data=json.loads((pathlib.Path(__file__).resolve().parent.parent/'catalog/switch2-emulators.json').read_text(encoding='utf-8'))
        self.assertTrue(data['source'].startswith('https://github.com/'));self.assertGreaterEqual(len(data['emulators']),6)
        for row in data['emulators']:self.assertTrue(row['url'].startswith(('https://github.com/','https://gitlab.com/')),row['name']);self.assertTrue(row['note'])

if __name__=='__main__':unittest.main()
