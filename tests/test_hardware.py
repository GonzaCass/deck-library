import pathlib,tempfile,unittest
from deck_library import hardware

class HardwareTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_the_product_name_tells_lcd_from_oled(self):
        (self.root/'product_name').write_text('Jupiter\n');self.assertEqual(hardware.model(self.root),'steam-deck-lcd')
        (self.root/'product_name').write_text('Galileo\n');self.assertEqual(hardware.model(self.root),'steam-deck-oled')
    def test_the_board_name_is_used_when_the_product_name_is_not_known(self):
        (self.root/'product_name').write_text('Something else');(self.root/'board_name').write_text('GALILEO');self.assertEqual(hardware.model(self.root),'steam-deck-oled')
    def test_a_missing_or_unknown_name_is_just_unknown_and_never_raises(self):
        self.assertEqual(hardware.model(self.root),'unknown');(self.root/'product_name').write_text('Desktop PC');self.assertEqual(hardware.model(self.root),'unknown')
        self.assertEqual(hardware.model(self.root/'missing'),'unknown');self.assertEqual(hardware.describe('unknown'),'')
    def test_the_description_mentions_the_panel_without_limiting_anything(self):
        self.assertIn('60 Hz',hardware.describe('steam-deck-lcd'));self.assertIn('90 Hz',hardware.describe('steam-deck-oled'))
        self.assertTrue({'steam-deck-lcd','steam-deck-oled'}<=set(hardware.PANELS))

if __name__=='__main__':unittest.main()
