import importlib.util,json,os,pathlib,re,unittest
from unittest.mock import patch
from deck_library import i18n
from deck_library.i18n_en import EXACT

ROOT=pathlib.Path(__file__).resolve().parent.parent

def load_extract():
    spec=importlib.util.spec_from_file_location('i18n_extract',ROOT/'tools/i18n_extract.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class LanguageChoiceTests(unittest.TestCase):
    def detect(self,preferences=None,**env):
        clean={k:'' for k in ('DECK_LIBRARY_LANG','LC_ALL','LC_MESSAGES','LANGUAGE','LANG')}
        with patch.dict(os.environ,{**clean,**env}),patch('locale.getlocale',return_value=(None,None)):return i18n.detect(preferences)

    def test_a_saved_choice_wins_and_the_environment_overrides_it(self):
        self.assertEqual(self.detect({'language':'en'},LANG='es_AR.UTF-8'),'en');self.assertEqual(self.detect({'language':'es'},LANG='en_US.UTF-8'),'es')
        self.assertEqual(self.detect({'language':'es'},DECK_LIBRARY_LANG='en'),'en')

    def test_an_existing_installation_keeps_spanish_and_a_new_one_follows_the_system(self):
        self.assertEqual(self.detect({'onboarding_complete':True},LANG='en_US.UTF-8'),'es')
        self.assertEqual(self.detect({},LANG='en_US.UTF-8'),'en');self.assertEqual(self.detect({},LANG='es_ES.UTF-8'),'es');self.assertEqual(self.detect({'language':'auto'},LANG='es_AR.UTF-8'),'es')
        self.assertEqual(self.detect({'language':'auto'},LANG='fr_FR.UTF-8'),'en');self.assertEqual(self.detect({}),'en')

class TranslationTests(unittest.TestCase):
    def setUp(self):i18n.set_language('en')
    def tearDown(self):i18n.set_language('es')

    def test_exact_pattern_and_composite_texts_are_translated(self):
        self.assertEqual(i18n.translate('Jugar'),'Play');self.assertEqual(i18n.translate('34 juegos'),'34 games')
        self.assertEqual(i18n.translate('646 de 646 ports · se muestran los primeros 30'),'646 of 646 ports · showing the first 30')
        self.assertEqual(i18n.translate('Xbox  ·  Revisado  ·  Requiere originales'),'Xbox  ·  Reviewed  ·  Requires originals')
        self.assertEqual(i18n.translate('Instalando OpenRA…'),'Installing OpenRA…')

    def test_unknown_text_and_game_names_are_left_alone(self):
        for text in ('Mario Kart 8 Deluxe','/opt/games/Game','Biblioteca de Alejandría','','   '):self.assertEqual(i18n.translate(text),text)

    def test_spanish_mode_never_changes_anything(self):
        i18n.set_language('es');self.assertEqual(i18n.translate('Jugar'),'Jugar');self.assertEqual(i18n.language(),'es')

    def test_placeholder_only_keys_cannot_loop(self):
        self.assertEqual(i18n.translate('3×4'),'3×4');self.assertEqual(i18n.translate('12 34'),'12 34')

class CatalogTests(unittest.TestCase):
    def test_every_interface_string_has_an_english_translation(self):
        missing=load_extract().missing(ROOT)
        self.assertEqual(sorted(missing)[:10],[],'ejecutar tools/i18n_extract.py --missing y traducir')

    def test_placeholders_match_between_spanish_and_english(self):
        for key,value in EXACT.items():self.assertEqual(key.count('{}'),value.count('{}'),key)

    def test_english_text_has_no_spanish_punctuation_or_accents_except_when_kept_as_is(self):
        pattern=re.compile(r'[áéíóúñ¿¡«»]')
        for key,value in EXACT.items():
            if value!=key:self.assertIsNone(pattern.search(value),value)

    def test_the_language_selector_keeps_each_language_name_untranslated(self):
        for name in ('Español','English'):self.assertNotIn(name,EXACT)

@unittest.skipUnless(os.environ.get('DECK_LIBRARY_UI_TESTS')=='1' and os.environ.get('DISPLAY'),'requires GTK and a disposable display')
class WidgetBoundaryTests(unittest.TestCase):
    def test_widgets_show_english_and_go_back_to_spanish(self):
        import gi
        gi.require_version('Gtk','3.0')
        from gi.repository import Gtk
        i18n.set_language('en');i18n.install_gtk_hooks()
        try:
            label=Gtk.Label(label='Jugar');button=Gtk.Button(label='Cancelar');label2=Gtk.Label();label2.set_text('Buscando juegos e instalaciones…')
            combo=Gtk.ComboBoxText();combo.append('a','Todas las plataformas');combo.append_text('Automático');link=Gtk.LinkButton.new_with_label('https://example.org','Publicación original')
            expander=Gtk.Expander(label='Opciones de actualización');entry=Gtk.Entry();entry.set_placeholder_text('Buscar ports · X: teclado');label.set_tooltip_text('Cerrar')
            self.assertEqual(label.get_text(),'Play');self.assertEqual(button.get_label(),'Cancel');self.assertEqual(label2.get_text(),'Looking for games and installations…')
            self.assertEqual([row[0] for row in combo.get_model()],['All platforms','Automatic']);self.assertEqual(link.get_label(),'Original release')
            self.assertEqual(expander.get_label(),'Update options');self.assertEqual(entry.get_placeholder_text(),'Search ports · X: keyboard');self.assertEqual(label.get_tooltip_text(),'Close')
            self.assertEqual(Gtk.Label(label='Mario Kart 8 Deluxe').get_text(),'Mario Kart 8 Deluxe')
        finally:i18n.set_language('es')
        self.assertEqual(Gtk.Label(label='Jugar').get_text(),'Jugar')

if __name__=='__main__':unittest.main()
