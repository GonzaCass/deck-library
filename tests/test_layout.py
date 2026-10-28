import pathlib,tempfile,unittest
from deck_library import layout,ports,switch_extract

class LayoutTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.home=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_the_folder_and_its_subfolders_are_created_in_the_home(self):
        self.assertTrue(layout.ensure(self.home))
        for kind in ('ports','roms','switch','iso'):self.assertTrue((self.home/'DeckLibrary'/kind).is_dir())
        self.assertTrue(layout.ensure(self.home))
        with self.assertRaises(ValueError):layout.folder('other',self.home)
    def test_a_fresh_home_installs_ports_in_the_deck_library_folder(self):
        self.assertEqual(ports.ports_root(self.home),self.home/'DeckLibrary/ports');self.assertEqual(layout.display_ports(self.home),'~/DeckLibrary/ports');self.assertEqual(ports.display_root(self.home),'~/DeckLibrary/ports')
    def test_an_existing_ports_folder_with_content_keeps_being_used_and_an_empty_one_does_not(self):
        (self.home/'ports').mkdir();self.assertEqual(ports.ports_root(self.home),self.home/'DeckLibrary/ports')
        (self.home/'ports/quiver-launcher').mkdir();self.assertEqual(ports.ports_root(self.home),self.home/'ports');self.assertEqual(layout.display_ports(self.home),'~/ports')
    def test_conversions_and_extractions_default_to_the_deck_library_folder(self):
        self.assertEqual(switch_extract.default_root(self.home),self.home/'DeckLibrary/switch')
    def test_an_unwritable_home_never_raises(self):
        blocker=self.home/'file';blocker.write_text('x');self.assertFalse(layout.ensure(blocker))
    def test_roms_and_ports_placed_in_the_folder_are_scanned(self):
        from deck_library import installations
        found=installations.report(self.home,{})
        self.assertIn(str(self.home/'DeckLibrary/roms'),found['rom_roots']);self.assertIn(str(self.home/'DeckLibrary/ports'),found['port_roots'])

if __name__=='__main__':unittest.main()
