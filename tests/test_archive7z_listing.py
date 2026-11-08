"""The 7z/RAR extractor understands the listing format of old and current 7-Zip and extracts names literally."""
import pathlib,shutil,subprocess,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
from deck_library import archive7z

CURRENT="Path = d\nSize = 0\nAttributes = D drwxr-xr-x\nEncrypted = -\n\nPath = d/a.txt\nSize = 3\nAttributes = A -rw-r--r--\nEncrypted = -\n"
OLD="Path = d\nFolder = +\nSize = 0\nAttributes = D\n\nPath = d/a.txt\nFolder = -\nSize = 3\nAttributes = A\n"

class ListingTests(unittest.TestCase):
    def test_folders_are_recognised_in_both_listing_formats(self):
        self.assertTrue(archive7z.is_folder({'Attributes':'D drwxr-xr-x'}));self.assertTrue(archive7z.is_folder({'Folder':'+'}))
        self.assertTrue(archive7z.is_folder({'Attributes':'D'}));self.assertFalse(archive7z.is_folder({'Attributes':'A -rw-r--r--'}))
        self.assertFalse(archive7z.is_folder({'Attributes':'A'}));self.assertFalse(archive7z.is_folder({}))
    def run_extract(self,listing):
        calls=[]
        def run(args,**kwargs):
            calls.append(args)
            if args[1]=='l':return SimpleNamespace(stdout=listing)
            kwargs['stdout'].write(b'abc');return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as temp,patch.object(archive7z.shutil,'which',return_value='7z'),patch.object(archive7z.subprocess,'run',side_effect=run):
            out=pathlib.Path(temp)/'out';archive7z.extract(pathlib.Path(temp)/'g.7z',out)
            return calls,(out/'d').is_dir(),(out/'d/a.txt').read_bytes()
    def test_current_and_old_listings_extract_the_same_tree_with_literal_names(self):
        for listing in (CURRENT,OLD):
            calls,folder,data=self.run_extract(listing)
            self.assertTrue(folder);self.assertEqual(data,b'abc')
            extract=[c for c in calls if c[1]=='x'];self.assertEqual(len(extract),1);self.assertIn('-spd',extract[0])

@unittest.skipUnless(shutil.which('7z') or shutil.which('7zz'),'7-Zip not installed')
class RealArchiveTests(unittest.TestCase):
    def test_a_real_archive_with_folders_and_a_wildcard_character_extracts_exactly(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);(root/'src/d').mkdir(parents=True)
            (root/'src/d/a.txt').write_text('hi');(root/'src/d/b*c.txt').write_text('star');(root/'src/d/bxc.txt').write_text('plain')
            subprocess.run([shutil.which('7z') or shutil.which('7zz'),'a','-bso0','-bsp0',str(root/'t.7z'),'d'],cwd=root/'src',check=True,capture_output=True)
            archive7z.extract(root/'t.7z',root/'out')
            self.assertEqual((root/'out/d/b*c.txt').read_text(),'star');self.assertEqual((root/'out/d/bxc.txt').read_text(),'plain')

if __name__=='__main__':unittest.main()
