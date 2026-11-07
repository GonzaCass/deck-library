import time,unittest
from deck_library import originals
from deck_library.library_view import entry_type
from deck_library.models import Entry

def reference_pairs(entries,excluded=()):
    """The straightforward pairing, kept to prove the faster one gives the same answer."""
    result=[];ports=[e for e in entries if entry_type(e)=='port' and e.metadata.get('configured') is not False];title_platforms={}
    for e in entries:
        if entry_type(e)=='emulator':title_platforms.setdefault(originals.key(e.name),set()).add(originals.platform_key(e.platform))
    for original in entries:
        if entry_type(original)!='emulator' or original.id in excluded:continue
        matches=[]
        for port in ports:
            platform=originals.original_platform(port)
            if platform and platform!=originals.platform_key(original.platform):continue
            if original.game_id and port.game_id:
                if original.game_id.upper()==port.game_id.upper():matches.append(port)
                continue
            title=originals.key(original.name)
            if not title or not platform and len(title_platforms.get(title,()))>1:continue
            if title in {originals.key(port.name),originals.key(port.metadata.get('game_title',''))}:matches.append(port)
        if matches:result.append((original,matches))
    return result

def library(count):
    platforms=['Switch','PlayStation 2','Wii','GameCube','PSP','Xbox 360']
    entries=[]
    for i in range(count):
        if i%7==0:
            entries.append(Entry(f'Juego {i%40}',['/bin/true'],kind='port',platform='Linux',source=f'/tmp/p{i}',metadata={'original_platform':platforms[i%len(platforms)]} if i%2 else {},game_id=f'ID{i%30:04d}' if i%3==0 else ''))
        else:
            entries.append(Entry(f'Juego {i%40}' if i%5 else f'Juego, The {i%40}',['/bin/true',str(i)],kind='emulated',platform=platforms[i%len(platforms)],source=f'/tmp/{i}.iso',game_id=f'id{i%30:04d}' if i%4==0 else ''))
    return entries

class LibraryScaleTests(unittest.TestCase):
    def test_pairing_gives_the_same_answer_as_the_straightforward_version(self):
        entries=library(400);fast=originals.pairs(entries);slow=reference_pairs(entries)
        self.assertTrue(fast)
        self.assertEqual([(o.id,[p.id for p in m]) for o,m in fast],[(o.id,[p.id for p in m]) for o,m in slow])
        excluded={fast[0][0].id};self.assertEqual([o.id for o,_ in originals.pairs(entries,excluded)],[o.id for o,_ in reference_pairs(entries,excluded)])

    def test_a_library_of_thousands_of_games_is_paired_in_seconds(self):
        entries=library(4000);start=time.perf_counter();originals.pairs(entries);elapsed=time.perf_counter()-start
        self.assertLess(elapsed,8,f'Pairing 4000 games took {elapsed:.1f} s; it must not grow with the square of the library.')

if __name__=='__main__':unittest.main()
