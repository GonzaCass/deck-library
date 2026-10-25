import pathlib,tempfile,unittest
from unittest.mock import patch
from deck_library import ports
from deck_library.conflicts import analyze

class CompatibilityTests(unittest.TestCase):
    def item(self,**extra):return {'name':'Juego','repository':'autor/juego','folder':'juego','list':'PC','source':'','note':'',**extra}
    def test_levels_follow_the_install_route(self):
        self.assertEqual(ports.compatibility(self.item(supported_os=['linux','windows'],release_version='1',release_at=9e9))['level'],'media')
        self.assertEqual(ports.compatibility(self.item(supported_os=['windows'],release_version='1'))['level'],'baja')
        self.assertEqual(ports.compatibility(self.item(supported_os=['android'],release_version='1'))['level'],'muy baja')
        self.assertEqual(ports.compatibility(self.item(package_role='source-only'))['level'],'muy baja')
        self.assertEqual(ports.compatibility(self.item(repository='openra/openra',supported_os=['linux'],release_version='1'))['level'],'alta')

    def test_score_is_bounded_and_explained(self):
        for extra in ({},{'source_status':'Totalmente Jogável','supported_os':['linux'],'release_version':'1','release_at':9e9},{'source_status':'Em Desenvolvimento'}):
            fit=ports.compatibility(self.item(**extra));self.assertTrue(0<=fit['score']<=100);self.assertTrue(fit['reasons'])

class EnvironmentTests(unittest.TestCase):
    def test_two_eden_configs_saves_and_app_copies_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            home=pathlib.Path(folder)
            for config in (home/'.config/eden',home/'.var/app/dev.eden_emu.eden/config/eden'):config.mkdir(parents=True);(config/'qt-config.ini').write_text('[Controls]\n')
            for save in (home/'.local/share/eden/nand/user/save',home/'.var/app/dev.eden_emu.eden/data/eden/nand/user/save'):(save/'0').mkdir(parents=True);(save/'0/x').write_text('1')
            for app in (home/'Applications/DeckLibrary',home/'ports/deck-library-copy'):app.mkdir(parents=True);(app/'app.py').write_text('')
            with patch('deck_library.conflicts.shutil.which',return_value=None):kinds={row['kind'] for row in analyze([],home=home)}
            self.assertTrue({'eden-config','eden-saves','app'}<=kinds)

    def test_a_clean_home_reports_nothing(self):
        with tempfile.TemporaryDirectory() as folder,patch('deck_library.conflicts.shutil.which',return_value=None):
            self.assertEqual(analyze([],home=pathlib.Path(folder)),[])
