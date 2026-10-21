#!/usr/bin/env python3
"""Build a source release from an explicit allowlist; never include private libraries."""
import hashlib,pathlib,tarfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
import sys;sys.path.insert(0,str(ROOT))
from deck_library import __version__ as VERSION
files=[ROOT/name for name in ('app.py','install.py','launch.sh','Instalar.sh','README.md','LEEME.md','LICENSE','.gitignore','.github/workflows/test.yml','catalog/ports.json','assets/icon.svg','assets/icon.png','assets/screenshot.png','assets/screenshot-game.png','assets/welcome.png','docs/VALIDATION.md','docs/PRESETS.md','docs/COMMUNITY-PRESETS.md','docs/GTAIV.md','docs/PROJECT2099.md','docs/DMC3-CRIMSON.md','docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md','docs/PORTS.md','tools/build_release.py')]
for folder in ('deck_library','tests'):
    files.extend(sorted((ROOT/folder).glob('*.py')))
files.extend(sorted((ROOT/'presets').glob('*.json')))
files.extend([ROOT/'.dockerignore',ROOT/'docs/DECK-INTERFACE.md',ROOT/'tools/sync_readme.py'])
files.extend(sorted(p for p in (ROOT/'community').iterdir() if p.is_file() and p.name in ('__init__.py','server.py','oidc.py','keycloak-client.json','Dockerfile','compose.yaml','.env.example','README.md')))
files.extend(sorted(p for p in (ROOT/'community/keycloak-theme').rglob('*') if p.is_file() and p.suffix in ('.properties','.css','.png')))
files.extend(sorted(p for p in (ROOT/'community/keycloak-mail').rglob('*') if p.is_file() and (p.suffix in ('.java','.py','.md') or p.name=='org.keycloak.email.EmailSenderProviderFactory')))
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
