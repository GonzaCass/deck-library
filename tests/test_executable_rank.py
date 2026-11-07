import io,pathlib,tempfile,unittest,zipfile
from unittest.mock import patch
from deck_library import port_packages,ports,project2099
from deck_library.models import Store

REPO='madelrandel-blip/NFSMW-Recompiled'
NAMES=(REPO.rsplit('/',1)[-1],'Need for Speed: Most Wanted (Xbox 360 Recomp)')

def package(files):
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w') as z:
        for name,data in files.items():z.writestr(name,data)
    return payload.getvalue()

class ExecutableRankTests(unittest.TestCase):
    def test_a_launcher_in_the_root_beats_the_engine_and_the_helpers_in_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in ('NFSMW Recomp.exe','data/nfsmw.exe','data/crashpad_handler.exe','data/vcruntime140.dll'):
                (root/name).parent.mkdir(parents=True,exist_ok=True);(root/name).write_bytes(b'MZfixture')
            ranked=[p.relative_to(root).as_posix() for p in port_packages.rank_executables(root,NAMES)]
            self.assertEqual(ranked[0],'NFSMW Recomp.exe');self.assertEqual(ranked[1],'data/nfsmw.exe');self.assertEqual(ranked[-1],'data/crashpad_handler.exe');self.assertNotIn('data/vcruntime140.dll',ranked)

    def test_the_name_of_the_project_decides_between_unrelated_programs_and_installers_rank_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            for name in ('Setup.exe','other.exe','CoolGame.exe'):(root/name).write_bytes(b'MZfixture')
            ranked=[p.name for p in port_packages.rank_executables(root,('someone/coolgame-port','Cool Game'))]
            self.assertEqual(ranked,['CoolGame.exe','other.exe','Setup.exe'])

    def test_linux_files_are_ranked_by_the_same_rules_and_libraries_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            (root/'lib').mkdir();(root/'lib/libfoo.so').write_bytes(b'\x7fELF');(root/'game').write_bytes(b'\x7fELF');(root/'tools').mkdir();(root/'tools/packer').write_bytes(b'\x7fELF')
            self.assertEqual([p.relative_to(root).as_posix() for p in port_packages.rank_executables(root,('x/game',),'linux')],['game','tools/packer'])

    def test_an_empty_or_unreadable_folder_gives_no_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'readme.txt').write_text('x');(root/'fake.exe').write_bytes(b'not a program')
            self.assertEqual(port_packages.rank_executables(root,NAMES),[])

class InstallAnyPackageTests(unittest.TestCase):
    def install(self,files,root,store,**kw):
        item=ports.clean({'repository':REPO,'name':NAMES[1]})
        release={'tag_name':'v1.0.2','assets':[{'name':'NFSMW-Recomp-1.0.2-Windows-x64.zip','browser_download_url':'https://github.com/'+REPO+'/asset.zip'}]}
        data=package(files)
        with patch.object(ports,'download',side_effect=lambda _,target,**k:target.write_bytes(data)),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')):
            return item,ports.install(item,store,root/'ports',get=lambda _:release,progress=lambda _:None,**kw)

    def test_a_package_with_a_launcher_and_an_engine_installs_with_the_launcher_and_keeps_the_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private')
            item,record=self.install({'NFSMW Recomp/NFSMW Recomp.exe':b'MZa','NFSMW Recomp/data/nfsmw.exe':b'MZb','NFSMW Recomp/data/nfsmw.toml':b'x'},root,store)
            self.assertEqual(record['runtime'],'proton');self.assertEqual(record['executable'],'NFSMW Recomp.exe');self.assertTrue(record['executable_guess'])
            self.assertEqual(record['executable_candidates'],['NFSMW Recomp.exe','data/nfsmw.exe'])
            changed=ports.set_executable(REPO,'data/nfsmw.exe',store);self.assertEqual(changed['executable'],'data/nfsmw.exe');self.assertFalse(changed['executable_guess'])
            self.assertEqual(ports.records(store)[REPO]['executable'],'data/nfsmw.exe')
            self.assertEqual(ports.entry_for(root/'ports'/item['folder']).source.replace('\\','/').rsplit('/',2)[-2:],['data','nfsmw.exe'])
            with self.assertRaises(ValueError):ports.set_executable(REPO,'../outside.exe',store)
            with self.assertRaises(ValueError):ports.set_executable(REPO,'missing.exe',store)

    def test_a_package_without_any_program_still_installs_so_the_user_can_choose_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private')
            item,record=self.install({'Game/readme.txt':b'x','Game/data.bin':b'y'},root,store)
            self.assertEqual(record['executable'],'');self.assertFalse(record['executable_guess']);self.assertTrue((root/'ports'/item['folder']/'data.bin').is_file())

    def test_an_unlabelled_package_with_nothing_recognisable_still_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);store=Store(root/'private');repo='someone/mystery-port'
            item=ports.clean({'repository':repo,'name':'Mystery Port'});release={'tag_name':'v1','assets':[{'name':'Mystery-Port-v1.zip','browser_download_url':'https://github.com/'+repo+'/a.zip'}]}
            data=package({'Mystery/readme.txt':b'x','Mystery/data/level1.dat':b'y'})
            with patch.object(ports,'download',side_effect=lambda _,target,**k:target.write_bytes(data)):
                record=ports.install(item,store,root/'ports',get=lambda _:release,progress=lambda _:None)
            self.assertEqual(record['executable'],'');self.assertTrue((root/'ports'/item['folder']/'data/level1.dat').is_file())
            (root/'ports'/item['folder']/'Mystery.x86_64').write_bytes(b'ELF');changed=ports.set_executable(repo,'Mystery.x86_64',store);self.assertEqual((changed['executable'],changed['runtime']),('Mystery.x86_64','linux'))

if __name__=='__main__':unittest.main()
