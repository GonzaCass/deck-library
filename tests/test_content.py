import hashlib,pathlib,struct,tempfile,unittest,zipfile
from unittest.mock import patch
from deck_library.content import pfs_entries,install_nsp,content_installed,install_mod_zip
from deck_library.models import Entry,Store

def nsp(path,parts):
    names=b'';table=b'';data=b''
    for name,value in parts:
        table+=struct.pack('<QQII',len(data),len(value),len(names),0);names+=name.encode()+b'\0';data+=value
    path.write_bytes(b'PFS0'+struct.pack('<III',len(parts),len(names),0)+table+names+data)

def nca(value,meta=False):return hashlib.sha256(value).hexdigest()[:32]+('.cnmt.nca' if meta else '.nca'),value

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.config=self.root/'eden';self.config.mkdir();self.nand=self.root/'NAND';(self.config/'qt-config.ini').write_text('[Data%20Storage]\nnand_directory='+str(self.nand)+'\n');self.package=self.root/'update.nsp'
    def tearDown(self):self.tmp.cleanup()
    def test_nsp_content_installs_once_without_changing_the_source(self):
        parts=[nca(b'METADATA',True),nca(b'OWNED GAME DATA')];nsp(self.package,parts);original=self.package.read_bytes()
        with patch('deck_library.content.emulator_busy',return_value=False):
            first=install_nsp(self.package,self.config);second=install_nsp(self.package,self.config)
        self.assertEqual(first['count'],2);self.assertEqual(second['count'],0);self.assertEqual(self.package.read_bytes(),original);self.assertTrue(content_installed(self.package,pathlib.Path(first['target'])))
    def test_bad_hash_commits_none_and_does_not_overwrite_existing_content(self):
        nsp(self.package,[nca(b'GOOD META',True),('0'*32+'.nca',b'BAD HASH')])
        with patch('deck_library.content.emulator_busy',return_value=False):
            with self.assertRaises(ValueError):install_nsp(self.package,self.config)
        self.assertEqual(list((self.nand/'user/Contents/registered').glob('*.nca')),[])
    def test_traversal_truncation_and_eden_open_are_rejected(self):
        nsp(self.package,[('../escape.nca',b'BAD')])
        with self.assertRaises(ValueError):pfs_entries(self.package)
        nsp(self.package,[nca(b'META',True)]);self.package.write_bytes(self.package.read_bytes()[:-1])
        with self.assertRaises(ValueError):pfs_entries(self.package)
        nsp(self.package,[nca(b'META',True)])
        with patch('deck_library.content.emulator_busy',return_value=True):
            with self.assertRaises(RuntimeError):install_nsp(self.package,self.config)
    def test_mod_zip_checks_title_and_paths_and_backs_up_replaced_mod(self):
        entry=Entry('Game',['/bin/true'],platform='Switch',game_id='0100152000022000');path=self.root/'My Mod.zip';store=Store(self.root/'private')
        with zipfile.ZipFile(path,'w') as archive:archive.writestr('atmosphere/contents/0100152000022000/romfs/data.bin',b'ORIGINAL')
        with patch('deck_library.content.emulator_busy',return_value=False):
            first=install_mod_zip(path,entry,store,self.config)
            with zipfile.ZipFile(path,'w') as archive:archive.writestr('atmosphere/contents/0100152000022000/romfs/data.bin',b'UPDATED')
            second=install_mod_zip(path,entry,store,self.config)
        self.assertEqual(first['files'],1);self.assertEqual((pathlib.Path(second['backup'])/'romfs/data.bin').read_bytes(),b'ORIGINAL')
        with zipfile.ZipFile(path,'w') as archive:archive.writestr('../escape',b'BAD')
        with patch('deck_library.content.emulator_busy',return_value=False):
            with self.assertRaises(ValueError):install_mod_zip(path,entry,store,self.config)
