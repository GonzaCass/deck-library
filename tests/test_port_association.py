import hashlib,io,json,pathlib,tarfile,tempfile,unittest,zipfile
from unittest.mock import patch
from deck_library import originals,ports,port_packages
from deck_library.library_view import visible_entries
from deck_library.models import Entry,Store,atomic_json

class AssociationTests(unittest.TestCase):
    def test_port_and_rom_share_one_tile_without_deleting_the_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            rom=pathlib.Path(tmp)/'game.iso';rom.write_bytes(b'original')
            original=Entry('Mario Kart Wii (PAL)',['emulator',str(rom)],kind='emulated',platform='Wii',source=str(rom))
            port=Entry('Mario Kart Wii',['port'],kind='wiicompiled',platform='WiiCompiled')
            store=Store(pathlib.Path(tmp)/'private');store.save([port,original]);shown,hidden=visible_entries(store.load())
            self.assertEqual(([e.id for e in shown],hidden),([port.id],1))
            self.assertEqual(len(store.load()),2);self.assertEqual(rom.read_bytes(),b'original')
            self.assertEqual(originals.rom_caption(originals.associations(store.load())[port.id]),'ROM encontrada')
            self.assertEqual(len(visible_entries(store.load(),association_exclusions=[original.id])[0]),2)
            rom.unlink();self.assertEqual(originals.rom_caption([original]),'ROM no disponible')

    def test_platforms_and_conflicting_ids_do_not_auto_associate(self):
        original=Entry('Same',['emu'],kind='emulated',platform='PlayStation',game_id='SLUS-00001')
        port=Entry('Same',['port'],game_id='SLUS-00002',metadata={'original_platform':'PlayStation'})
        self.assertEqual(originals.pairs([original,port]),[])
        port.game_id=original.game_id;port.metadata['original_platform']='PlayStation 2'
        self.assertEqual(originals.pairs([original,port]),[])
        port.metadata['original_platform']='ps1';self.assertEqual(originals.pairs([original,port]),[(original,[port])])
        port.metadata['configured']=False;self.assertEqual(originals.pairs([original,port]),[])

    def test_unknown_cross_platform_title_is_kept_separate_and_empty_names_do_not_match(self):
        one=Entry('Same',['ps1'],kind='emulated',platform='PlayStation');two=Entry('Same',['ps2'],kind='emulated',platform='PlayStation 2');port=Entry('Same',['port'])
        self.assertEqual(originals.pairs([one,two,port]),[])
        self.assertEqual(originals.key('Legend of Zelda, The - The Minish Cap'),originals.key('The Legend of Zelda - The Minish Cap'))

class ReviewedPackageTests(unittest.TestCase):
    def test_flattening_cannot_move_an_internal_link_outside_the_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private');old=root/'ports/Game';old.mkdir(parents=True);(old/'game').write_bytes(b'keep')
            payload=io.BytesIO()
            with tarfile.open(fileobj=payload,mode='w:gz') as tar:
                link=tarfile.TarInfo('wrapper/link');link.type=tarfile.SYMTYPE;link.linkname='../outside';tar.addfile(link)
            release={'assets':[{'name':'Game-linux-x64.tar.gz','browser_download_url':'https://github.com/a/game'}]}
            with patch.object(ports,'download',side_effect=lambda url,path,**kw:path.write_bytes(payload.getvalue())),self.assertRaisesRegex(ValueError,'enlace'):
                ports.install({'repository':'a/game','folderName':'Game'},store,root/'ports',get=lambda _:release,replace=True,progress=lambda _:None)
            self.assertEqual((old/'game').read_bytes(),b'keep')

    def test_internal_tar_libraries_are_supported_but_external_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);archive=root/'game.tar.gz';target=root/'out';target.mkdir()
            with tarfile.open(archive,'w:gz') as tar:
                file=tarfile.TarInfo('lib/libtest.so.1');file.size=3;tar.addfile(file,io.BytesIO(b'lib'))
                link=tarfile.TarInfo('lib/libtest.so');link.type=tarfile.SYMTYPE;link.linkname='libtest.so.1';tar.addfile(link)
            ports.extract(archive,target);self.assertEqual((target/'lib/libtest.so').read_bytes(),b'lib')
            with tarfile.open(archive,'w:gz') as tar:
                link=tarfile.TarInfo('escape');link.type=tarfile.SYMTYPE;link.linkname='../outside';tar.addfile(link)
            with self.assertRaises(ValueError):ports.extract(archive,target)

    def test_windows_zip_paths_become_real_directories_and_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);archive=root/'game.zip';target=root/'out';target.mkdir()
            with zipfile.ZipFile(archive,'w') as z:z.writestr('package\\ctr_native.exe',b'MZ')
            ports.extract(archive,target);self.assertEqual((target/'package/ctr_native.exe').read_bytes(),b'MZ')
            with zipfile.ZipFile(archive,'w') as z:z.writestr('..\\escape.exe',b'MZ')
            with self.assertRaises(ValueError):ports.extract(archive,target)
            self.assertFalse((root/'escape.exe').exists())

    def test_neutral_windows_zip_and_ctr_x86_offer_proton(self):
        plan=ports.package_plan({'repository':'Shagg88/Athelas'},[{'name':'Athelas-1.1.3-arm64.zip'},{'name':'Athelas-1.1.3.zip'}])
        self.assertEqual((plan['runtime'],plan['asset']['name']),('proton','Athelas-1.1.3.zip'))
        plan=ports.package_plan({'repository':'CTR-tools/ctr-native'},[{'name':'ctr-native-beta-7.1-linux-x86.tar.gz'},{'name':'ctr-native-beta-7_1-windows-x86.zip'}])
        self.assertEqual(plan['runtime'],'proton');self.assertIn('windows-x86',plan['asset']['name'])

    def test_time_crisis_selects_its_own_appimage_in_the_multi_game_release(self):
        plan=ports.package_plan({'repository':'spacestate1/namco22-decompile'},[{'name':n} for n in ('AceDriver-x86_64.AppImage','TimeCrisis2-x86_64.AppImage','TimeCrisis-x86_64.AppImage')])
        self.assertEqual(plan['asset']['name'],'TimeCrisis-x86_64.AppImage')
        self.assertIsNone(ports.package_plan({'repository':'Denkishi/ssbu-recomp'},[{'name':'ssbu-runtime-d3aa4c91ab.zip'}],runtime='proton'))
        plan=ports.package_plan({'repository':'JRickey/BattleShip'},[{'name':n} for n in ('BattleShip-JP-x86_64.AppImage','BattleShip-x86_64.AppImage')])
        self.assertEqual(plan['asset']['name'],'BattleShip-x86_64.AppImage')

    def test_explicit_proton_ignores_native_and_mac_packages(self):
        assets=[{'name':n} for n in ('Game-Linux-x86-64.zip','Game-Mac-x64.zip','Game.exe')]
        self.assertEqual(port_packages.select(assets)['runtime'],'linux')
        self.assertEqual(port_packages.select(assets,runtime='proton')['asset']['name'],'Game.exe')
        self.assertEqual(port_packages.select([{'name':'Unknown.zip'}])['runtime'],'detect')
        self.assertEqual(port_packages.select([{'name':'Unknown.zip'}],runtime='proton')['runtime'],'proton')

class PortInputTests(unittest.TestCase):
    def test_selected_rom_outside_emudeck_is_verified_and_used_for_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=pathlib.Path(tmp);store=Store(home/'private');folder=home/'ports/Test';folder.mkdir(parents=True);(folder/'game').write_bytes(b'ELF')
            rom=home/'manual.gba';rom.write_bytes(b'owned data');bad=home/'wrong.gba';bad.write_bytes(b'wrong data')
            spec={'sizes':[10],'sha1':{hashlib.sha1(rom.read_bytes()).hexdigest():'baserom.gba'},'name':'Test','systems':['gba']}
            record={'repository':'a/test','folder':'Test','setup':'rom','executable':'game','rom':spec,'configured':False}
            atomic_json(store.root/'ports.json',{'a/test':record})
            with self.assertRaisesRegex(ValueError,'SHA-1'):ports.set_input('a/test','rom',bad,store)
            self.assertNotIn('inputs',ports.records(store)['a/test'])
            ports.set_input('a/test','rom',rom,store)
            self.assertTrue(all(ok for ok,_ in ports.requirements(ports.records(store)['a/test'],[],home)))
            result=ports.configure('a/test',store,[],lambda _:None,home)
            self.assertTrue(result['configured']);self.assertEqual((folder/'baserom.gba').read_bytes(),rom.read_bytes());self.assertEqual(rom.read_bytes(),b'owned data')

    def test_ctr_native_copies_the_selected_raw_bin_into_its_own_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=pathlib.Path(tmp);store=Store(home/'private');folder=home/'ports/CTR';folder.mkdir(parents=True);(folder/'ctr_native.exe').write_bytes(b'MZ')
            disc=home/'disc.bin';disc.write_bytes(b'x'*2352)
            record={'repository':'CTR-tools/ctr-native','folder':'CTR','setup':'ctr_native','executable':'ctr_native.exe','disc':{'serial':'SCUS-94426'},'configured':False}
            atomic_json(store.root/'ports.json',{record['repository']:record})
            with patch.object(ports,'ps1_serial',return_value='SCUS-94426'):
                ports.set_input(record['repository'],'disc',disc,store);result=ports.configure(record['repository'],store,[],lambda _:None,home)
            self.assertTrue(result['configured']);self.assertEqual((folder/'assets/ctr-u.bin').read_bytes(),disc.read_bytes())
