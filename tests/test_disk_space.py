"""Packages are not unpacked when their extracted size would not fit on the disk."""
import collections,io,pathlib,tarfile,tempfile,unittest,zipfile
from unittest.mock import patch
from deck_library import diskspace,ports

Usage=collections.namedtuple('Usage','total used free')

class DiskSpaceTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def zip(self,size):
        path=self.root/'p.zip'
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('game/data.bin',b'\0'*size)
        return path
    def test_a_package_larger_than_the_free_space_is_refused_before_writing(self):
        archive=self.zip(4096);target=self.root/'out'
        with patch.object(diskspace.shutil,'disk_usage',return_value=Usage(0,0,diskspace.MARGIN+1000)):
            with self.assertRaisesRegex(ValueError,'libres'):ports.extract(archive,target)
        self.assertFalse(target.exists() and any(target.rglob('*')),'nothing is written')
    def test_a_package_that_fits_is_extracted(self):
        archive=self.zip(4096);target=self.root/'out'
        with patch.object(diskspace.shutil,'disk_usage',return_value=Usage(0,0,diskspace.MARGIN+10_000)):ports.extract(archive,target)
        self.assertEqual((target/'game/data.bin').stat().st_size,4096)
    def test_tar_sizes_are_counted_too(self):
        path=self.root/'p.tar.gz'
        with tarfile.open(path,'w:gz') as tar:
            info=tarfile.TarInfo('g/big');info.size=8192;tar.addfile(info,io.BytesIO(b'\0'*8192))
        with patch.object(diskspace.shutil,'disk_usage',return_value=Usage(0,0,diskspace.MARGIN+100)):
            with self.assertRaisesRegex(ValueError,'libres'):ports.extract(path,self.root/'t')
    def test_the_check_walks_up_to_an_existing_folder(self):
        with patch.object(diskspace.shutil,'disk_usage',return_value=Usage(0,0,10**12)) as usage:
            diskspace.ensure_space(1,self.root/'a/b/c')
        self.assertEqual(usage.call_args[0][0],self.root)

if __name__=='__main__':unittest.main()
