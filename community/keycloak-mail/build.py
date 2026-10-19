#!/usr/bin/env python3
"""Compile against the exact installed Keycloak jars, without downloading dependencies."""
import argparse,pathlib,subprocess,tempfile,shutil,os
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--keycloak-lib',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('deck-library-mail.jar'))
a=p.parse_args();root=pathlib.Path(__file__).resolve().parent
if not any(a.keycloak_lib.glob('*.jar')):raise SystemExit('No Keycloak jars found.')
classpath=os.pathsep.join(str(j.resolve()) for j in sorted(a.keycloak_lib.glob('*.jar')))
with tempfile.TemporaryDirectory(prefix='deck-mail-build-') as temp:
    classes=pathlib.Path(temp)/'classes';classes.mkdir()
    sources=sorted((root/'src').rglob('*.java'));tests=sorted((root/'tests').rglob('*.java'))
    subprocess.run(['javac','--release','21','-cp',classpath,'-d',str(classes),*[str(s) for s in sources+tests]],check=True)
    subprocess.run(['java','-cp',str(classes)+os.pathsep+classpath,'xyz.jokerlan.decklibrary.SenderPolicyTest'],check=True)
    for test in classes.rglob('*Test.class'):test.unlink()
    shutil.copytree(root/'resources',classes,dirs_exist_ok=True)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['jar','--create','--file',str(a.output.resolve()),'-C',str(classes),'.'],check=True)
print(a.output)
