#!/usr/bin/env python3
"""Build a source release from an explicit allowlist; never include private libraries."""
import hashlib,pathlib,tarfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
import sys;sys.path.insert(0,str(ROOT))
from deck_library import __version__ as VERSION
files=[ROOT/name for name in ('app.py','AGENTS.md','install.py','launch.sh','Instalar.sh','README.md','LEEME.md','LICENSE','.gitignore','.github/workflows/test.yml','catalog/ports.json','catalog/validated-games.json','catalog/port-variants.json','assets/icon.svg','assets/icon.png','assets/screenshot.png','assets/screenshot-game.png','assets/welcome.png','docs/VALIDATION.md','docs/PRESETS.md','docs/COMMUNITY-PRESETS.md','docs/GTAIV.md','docs/PROJECT2099.md','docs/DMC3-CRIMSON.md','docs/SPIDER-MAN-SHATTERED-DIMENSIONS.md','docs/PORTS.md','tools/build_release.py')]
for folder in ('deck_library','tests'):
    files.extend(sorted((ROOT/folder).glob('*.py')))
files.extend(sorted((ROOT/'presets').glob('*.json')))
files.extend(sorted((ROOT/'deck_library/i18n_en').glob('*.json')))
files.extend(sorted((ROOT/'assets/steam').glob('*.png')))
files.append(ROOT/'assets/steam/previous-defaults.json')
files.extend(sorted(p for p in (ROOT/'assets/tools').rglob('*') if p.is_file()))
files.extend(sorted(p for p in (ROOT/'assets/fonts').glob('*') if p.suffix in ('.woff2','.txt')))
files.append(ROOT/'tools/render_art.py')
files.extend([ROOT/'tools/import_art.py',ROOT/'assets/brand.png',ROOT/'docs/ARTWORK.md'])
files.extend(ROOT/'docs'/name for name in ('README.md','REFERENCE.md','REFERENCE.es.md'))
files.append(ROOT/'tools/i18n_extract.py')
files.extend([ROOT/'tools/audit_ports.py',ROOT/'docs/PORT-INSTALLATION-AUDIT.md',ROOT/'catalog/installation-audit.json'])
files.extend([ROOT/'.github/ISSUE_TEMPLATE/bug_report.md',ROOT/'.dockerignore',ROOT/'docs/DECK-INTERFACE.md',ROOT/'docs/V1-CHECKLIST.md',ROOT/'docs/CHANGELOG.md',ROOT/'docs/HISTORIAL.md',ROOT/'tools/sync_readme.py'])
files.extend(sorted(p for p in (ROOT/'community').iterdir() if p.is_file() and p.name in ('__init__.py','server.py','requests.py','oidc.py','keycloak-client.json','Dockerfile','compose.yaml','.env.example','README.md')))
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
