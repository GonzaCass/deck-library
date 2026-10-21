#!/usr/bin/env python3
"""Rebuild the Spanish half of README.md from LEEME.md, so GitHub shows a full English section followed by a full Spanish one."""
import pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parent.parent
BEGIN='<!-- BEGIN SPANISH: generated from LEEME.md by tools/sync_readme.py; edit LEEME.md instead -->'
END='<!-- END SPANISH -->'

def spanish_section(leeme):
    body=leeme.strip().split('\n',1)[1].strip() if leeme.lstrip().startswith('# ') else leeme.strip()
    return '# Español\n\n**[English](#deck-library)** · Español\n\n'+body

def build(readme,leeme):
    block=BEGIN+'\n'+spanish_section(leeme)+'\n'+END
    if BEGIN in readme:
        return re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),lambda _:block,readme,flags=re.S)
    return readme.rstrip('\n')+'\n\n---\n\n'+block+'\n'

def main(check=False):
    readme=(ROOT/'README.md').read_text();updated=build(readme,(ROOT/'LEEME.md').read_text())
    if check:return updated==readme
    (ROOT/'README.md').write_text(updated);return True

if __name__=='__main__':
    ok=main('--check' in sys.argv)
    if not ok:print('README.md está desactualizado: ejecutar tools/sync_readme.py');sys.exit(1)
