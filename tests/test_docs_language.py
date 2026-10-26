import importlib.util,pathlib,re,unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent

def load_sync():
    spec=importlib.util.spec_from_file_location('sync_readme',ROOT/'tools/sync_readme.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class DocsLanguageTests(unittest.TestCase):
    def test_quick_starts_are_short_and_link_to_each_language(self):
        self.assertTrue(load_sync().main(check=True),'ejecutar tools/sync_readme.py')

    def test_english_half_has_no_spanish_prose(self):
        text=(ROOT/'README.md').read_text();english=text.split('<!-- BEGIN SPANISH')[0]
        english=re.sub(r'^\|.*\|$','',english,flags=re.M).replace('[Español](#español)','').replace('Español','').replace('Idioma','')
        english=re.sub(r'`[^`\n]+`|\]\([^)]*\)|https?://\S+','',english)
        found=sorted(set(re.findall(r'[A-Za-z]*[áéíóúñÁÉÍÓÚÑ¿¡][A-Za-z]*',english)))
        self.assertEqual(found,[])

    def test_spanish_quick_start_is_complete_and_detailed_notes_remain_available(self):
        spanish=(ROOT/'LEEME.md').read_text()
        for heading in ('Instalar','Abrir desde Steam','¿Ya está instalado?'):self.assertIn(heading,spanish)
        self.assertGreater(len((ROOT/'docs/REFERENCE.es.md').read_text().splitlines()),200)
        voseo=re.compile(r'\b(podés|tenés|querés|elegí|abrí|pulsá|revisá|vos|tu|tus)\b',re.I)
        for path in (ROOT/'LEEME.md',*sorted((ROOT/'docs').glob('*.md'))):
            if path.name=='DECK-INTERFACE.md':continue  # describes the removed forms
            self.assertIsNone(voseo.search(path.read_text()),path.name)

if __name__=='__main__':unittest.main()
