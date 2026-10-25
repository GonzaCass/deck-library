import pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import eden_controls

class EdenControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.config=pathlib.Path(self.tmp.name)/'eden';self.config.mkdir()
        self.file=self.config/'qt-config.ini'

    def test_status_missing_other_ok(self):
        self.assertEqual(eden_controls.status(self.config),'missing')
        self.file.write_text('[Controls]\nplayer_0_button_a=[empty]\n');self.assertEqual(eden_controls.status(self.config),'missing')
        self.file.write_text('[Controls]\nplayer_0_button_a="engine:sdl,port:0,guid:0300000000000001,button:1"\n');self.assertEqual(eden_controls.status(self.config),'other')
        self.file.write_text('[Controls]\nplayer_0_button_a="'+eden_controls.SDL+',button:1"\n');self.assertEqual(eden_controls.status(self.config),'ok')

    def test_apply_maps_the_deck_keeps_everything_else_and_backs_up(self):
        self.file.write_text('[Controls]\nplayer_1_button_a=KEEP\n[System]\nlanguage_index=5\n')
        with patch.object(eden_controls,'emulator_busy',return_value=False):backup=eden_controls.apply(self.config)
        text=self.file.read_text()
        self.assertIn('player_1_button_a=KEEP',text);self.assertIn('language_index=5',text);self.assertIn('player_0_button_zl=',text)
        self.assertEqual(eden_controls.status(self.config),'ok');self.assertEqual(backup.read_text(),'[Controls]\nplayer_1_button_a=KEEP\n[System]\nlanguage_index=5\n')

    def test_apply_refuses_while_eden_runs(self):
        with patch.object(eden_controls,'emulator_busy',return_value=True),self.assertRaises(RuntimeError):eden_controls.apply(self.config)

if __name__=='__main__':unittest.main()
