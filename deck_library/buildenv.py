"""Build environment for ports that compile on first run.

SteamOS is read-only and ships no compiler or headers. The KDE SDK Flatpak has CMake, Ninja, GCC,
Python 3 and the SDL3/Vulkan/X11/Wayland/ALSA headers, and installs per user without root, so such
ports (setup kits that generate and compile the game from the user's own disc) run inside it.
"""
import shutil,subprocess
from .runtime import clean_environment

SDK='org.kde.Sdk'
BRANCH='6.11'
REMOTE='flathub'

def flatpak():return shutil.which('flatpak') or '/usr/bin/flatpak'

def installed(run=subprocess.run):
    """True when the SDK is available to this user or system-wide."""
    try:return run([flatpak(),'info','--user',SDK+'//'+BRANCH],capture_output=True,timeout=20,env=clean_environment()).returncode==0 or run([flatpak(),'info',SDK+'//'+BRANCH],capture_output=True,timeout=20,env=clean_environment()).returncode==0
    except (OSError,subprocess.TimeoutExpired):return False

def install(progress=print,popen=subprocess.Popen):
    """Install the SDK for the current user from Flathub. Streams flatpak's own output as progress."""
    process=popen([flatpak(),'install','--user','-y','--noninteractive',REMOTE,SDK+'//'+BRANCH],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=clean_environment())
    tail=[]
    for line in process.stdout:
        line=line.strip()
        if line:tail=(tail+[line])[-8:];progress(line[:140])
    if process.wait():raise RuntimeError('No se pudo instalar el SDK de KDE desde Flathub:\n'+'\n'.join(tail[-4:]))

def wrap(command):
    """Command line that runs `command` inside the SDK with network, display, audio, input and the home folder."""
    return [flatpak(),'run','--devel','--share=network','--share=ipc','--socket=x11','--socket=wayland','--socket=pulseaudio','--device=all','--filesystem=home','--branch='+BRANCH,'--command='+command[0],SDK,*command[1:]]

def is_wrapped(command):
    return len(command)>1 and command[0].endswith('flatpak') and any(part==SDK for part in command)

def looks_like_kit(folder):
    """Setup kits ship CMake sources and a README-SETUP next to their launcher."""
    import pathlib
    folder=pathlib.Path(folder);return (folder/'CMakeLists.txt').is_file() and (folder/'README-SETUP.txt').is_file()
