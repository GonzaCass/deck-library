import pathlib,tempfile,unittest
from deck_library import history
from deck_library.models import Entry,Store

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.entries=[Entry('A',['/bin/true','a']),Entry('B',['/bin/true','b']),Entry('C',['/bin/true','c'])]
    def tearDown(self):self.temp.cleanup()
    def test_the_most_recently_opened_game_comes_first_and_unplayed_ones_are_left_out(self):
        history.record(self.store,self.entries[0].id,now=100);history.record(self.store,self.entries[2].id,now=200)
        self.assertEqual([e.name for e in history.recent(self.entries,self.store)],['C','A'])
        history.record(self.store,self.entries[0].id,now=300);self.assertEqual([e.name for e in history.recent(self.entries,self.store,limit=1)],['A'])
    def test_a_damaged_or_missing_history_is_treated_as_empty(self):
        self.assertEqual(history.load(self.store),{})
        (self.store.root).mkdir(parents=True,exist_ok=True);(self.store.root/'played.json').write_text('not json');self.assertEqual(history.load(self.store),{})
        (self.store.root/'played.json').write_text('[1,2]');self.assertEqual(history.load(self.store),{})
        history.record(self.store,'abc',now=5);self.assertEqual(history.load(self.store),{'abc':5})
    def test_the_history_keeps_only_the_latest_entries(self):
        for i in range(history.LIMIT+20):history.record(self.store,f'id{i}',now=i)
        loaded=history.load(self.store);self.assertEqual(len(loaded),history.LIMIT);self.assertIn(f'id{history.LIMIT+19}',loaded);self.assertNotIn('id0',loaded)
    def test_an_unwritable_folder_never_raises(self):
        blocker=pathlib.Path(self.temp.name)/'file';blocker.write_text('x');history.record(Store(blocker/'inside'),'abc')

if __name__=='__main__':unittest.main()
