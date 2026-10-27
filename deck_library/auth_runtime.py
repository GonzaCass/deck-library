"""Optional WebKit runtime; the library itself keeps running natively on SteamOS."""
import os,pathlib,shutil,subprocess,sys
BRANCHES=('50','49','48')
class MissingRuntime(Exception):pass

def command(helper,socket_id,run=subprocess.run):
    probe=run([sys.executable,'-c',"import gi;gi.require_version('Gtk','3.0');gi.require_version('WebKit2','4.1')"],capture_output=True,timeout=10)
    if probe.returncode==0:return [sys.executable,str(helper),str(socket_id)]
    flatpak=shutil.which('flatpak')
    if flatpak:
        for branch in BRANCHES:
            ref='org.gnome.Platform//'+branch
            result=run([flatpak,'info',ref],capture_output=True,timeout=10)
            if result.returncode==0:return [flatpak,'run','--socket=x11','--share=ipc','--share=network','--filesystem='+str(pathlib.Path(helper).parent)+':ro','--env=GDK_BACKEND=x11','--command=python3',ref,str(helper),str(socket_id)]
    raise MissingRuntime('El inicio de sesión integrado necesita un componente adicional de Flathub.')

def install(progress,cancel):
    from .setup_wii import run_logged
    if not shutil.which('flatpak'):raise MissingRuntime('Falta Flatpak para instalar el componente de inicio de sesión. Se puede usar el navegador.')
    # Keep system remotes and runtimes untouched; this installs for the current user.
    commands=[['flatpak','remote-add','--user','--if-not-exists','flathub','https://flathub.org/repo/flathub.flatpakrepo'],['flatpak','install','--user','--noninteractive','-y','flathub','org.gnome.Platform//50']]
    import io
    for args in commands:
        with io.StringIO() as log:run_logged(args,str(pathlib.Path.home()),dict(os.environ),log,progress,cancel)
