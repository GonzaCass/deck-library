"""Reviewed preparation metadata. Commands from remote catalogs are never executed."""

RECIPES={
 'portingpete/black-2006-recomp':{'package_role':'build-tool','preparation':'manual','source_note':'El paquete es un constructor, no un juego portable. Requiere los archivos extraídos de Xbox y un entorno Linux de compilación con LLVM, Rust, Mono y SDK de Windows. Deck Library todavía no automatiza ese entorno; conviene BLACK XBERecomp o Black Definitive HD para la instalación integrada con Proton.'},
 'k0nl/b2recomp':{'setup':'b2recomp','original_data':{'kind':'switch-dump','destination':'targets'},'package_role':'builder','preserve':['config','cache','build-linux/play/userdata','build/play/userdata'],'prefer_native_preview':True,'exe':'B2recomp','windows_exe':'B2recomp.exe','preparation':'launcher','source_note':'Constructor nativo para Linux/Steam Deck (versión de prueba). Elegir una carpeta con exefs y romfs de Bayonetta 2 v1.2. No acepta NSP/XCI cifrados. El asistente valida los archivos y compila el juego; después ofrece Jugar.'},
 'tgp482/black-xberecomp':{'setup':'original_data','original_data':{'destination':'assets','iso':True},'supported_os':['windows'],'windows_exe':'BLACK.exe','preparation':'launcher','source_note':'Windows con Proton. Colocá la ISO o los archivos extraídos de BLACK (Xbox, USA o Europa) en assets. El primer inicio compila el juego; no incluye los datos originales.'},
 'euspring1/blackdefinitivehdpc':{'preserve':['black.ini','savedata','mods'],'setup':'original_data','original_data':{'destination':'.','sha256':['df2739c372d254a90aeeccf5971d12097f22d89fbb90db021fda96dd4deb68f6']},'supported_os':['windows'],'windows_exe':'black.exe','preparation':'launcher','source_note':'Windows con Proton. Requiere los archivos originales de BLACK; consultar el README del proyecto para preparar la carpeta del juego.'},
 'spark198rus/black-pc':{'supported_os':['windows'],'windows_exe':'black.exe','preparation':'manual','source_note':'Windows de 32 bits con Proton. Requiere game/default.xbe (Xbox NTSC-U o PAL compatible), junto a la carpeta port. Las partidas están en port/savedata.'},
 'thenikito/littlebigplanet-3---pc':{'preparation':'manual','package_role':'source-only','source_note':'Proyecto experimental sin paquete publicado. Requiere compilar desde código y una copia extraída de PS4. El proyecto todavía informa limitaciones de arranque; no se ofrece como juego listo para instalar.'},
 'shagg88/athelas':{'supported_os':['windows'],'preparation':'launcher','source_note':'El asistente de Athelas permite elegir una ISO o los archivos extraídos de Xbox para The Two Towers y Return of the King. El juego de PC usa su carpeta instalada.'},
 'ctr-tools/ctr-native':{'setup':'ctr_native','disc':{'serial':'SCUS-94426','match':'crashteamracing','exclude':''},'preparation':'integrated','source_note':'Elegir el CUE/BIN NTSC-U. Se copia el BIN MODE2/2352 a assets/ctr-u.bin; la ISO de 2048 bytes por sector no sirve.'},
 'felipeprado0/spartanport':{'preparation':'launcher','source_note':'El asistente del port pide la carpeta del juego de PS4, extraída. No usa una ISO de PS3.'},
 'hayatog/iss_pc':{'preparation':'launcher','exe':'inFAMOUS Second Son','source_note':'El asistente pide la carpeta extraída de inFAMOUS Second Son de PS4 CUSA00223, con la actualización 1.07 integrada.'},
 'hedge-dev/unleashedrecomp':{'preparation':'launcher','source_note':'El importador del port prepara los archivos de Sonic Unleashed de Xbox 360. Se ofrece el paquete Windows con Proton cuando el único paquete Linux es Flatpak.'},
 '999sian/melee-pc':{'preparation':'launcher','source_note':'El asistente del port pide la imagen del disco de Super Smash Bros. Melee de GameCube.'},
 'jrickey/battleship':{'preparation':'launcher','source_note':'El asistente del port pide la ROM compatible de Super Smash Bros. de Nintendo 64.'},
 'matteo842/crashbandicoot-launcher':{'preparation':'launcher','source_note':'El asistente de Crash acepta un disco CHD o CUE con su BIN.'},
 'alexbeavs-ps1-ports/crash-bandicoot-3-warped-recomp':{'kit':True,'preparation':'launcher','source_note':'El asistente del kit pide el disco y la BIOS compatibles; genera y compila el juego en el primer inicio, dentro del SDK de KDE.'},
 'gumpolas/tootawersrecomp':{'preparation':'launcher','exe':'TwoTowers.sh','windows_exe':'The Two Towers Recompiled.exe','source_note':'Su lanzador pide la ISO/XISO USA de Xbox en el primer inicio. En Linux usa el selector de zenity si está instalado y, como alternativa, un terminal con twotowers-setup.'},
 'denkishi/ssbu-recomp':{'preparation':'manual','package_role':'build-tool','source_note':'El release contiene una herramienta de compilación, no un juego portable listo. El proceso completo utiliza el instalador del proyecto y los archivos de Super Smash Bros. Ultimate.'},
 'spacestate1/namco22-decompile':{'asset_prefix':'TimeCrisis-','windows_exe':'TimeCrisis.exe','preparation':'launcher','source_note':'Time Crisis pide timecris.zip de MAME 0.271 o posterior. El AppImage busca el ZIP junto al ejecutable, en su carpeta roms o en Descargas.'},
}

def preparation(item):
    if item.get('setup'):return 'integrated','Preparación integrada · Deck Library detecta o permite elegir los archivos originales.'
    mode=item.get('preparation','')
    if mode=='launcher':return mode,'Archivos originales · se eligen en el asistente del port.'
    if mode=='manual':return mode,'Preparación manual · requiere seguir las instrucciones del proyecto.'
    return 'unknown','Requisitos sin integrar · revisar la guía del proyecto antes de instalar.'
