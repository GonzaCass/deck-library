#!/usr/bin/env python3
"""Build a source release from an explicit allowlist; never include private libraries."""
import hashlib,pathlib,tarfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
import sys;sys.path.insert(0,str(ROOT))
from deck_library import __version__ as VERSION
files=[ROOT/name for name in ('app.py','install.py','launch.sh','Instalar.sh','README.md','LEEME.md','LICENSE','.gitignore','.github/workflows/test.yml','assets/icon.svg','assets/screenshot.png','assets/welcome.png','docs/VALIDATION.md','docs/PRESETS.md','docs/COMMUNITY-PRESETS.md','docs/GTAIV.md','docs/PROJECT2099.md','docs/DMC3-CRIMSON.md','tools/build_release.py')]
for folder in ('deck_library','tests'):
    files.extend(sorted((ROOT/folder).glob('*.py')))
files.extend(sorted((ROOT/'presets').glob('*.json')))
output=ROOT.parent/f'DeckLibrary-{VERSION}.tar.gz'
with tarfile.open(output,'w:gz') as archive:
    for path in files:
        info=archive.gettarinfo(str(path),arcname=f'DeckLibrary-{VERSION}/'+str(path.relative_to(ROOT)))
        info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
        with path.open('rb') as source:archive.addfile(info,source)
checksum=hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(output.suffix+'.sha256').write_text(f'{checksum}  {output.name}\n')
print(output)
print('Release files:',len(files),'— SHA256:',checksum)
