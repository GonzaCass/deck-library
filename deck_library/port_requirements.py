"""Original-media labels from reviewed local rules. Catalog names never prove a ROM's revision."""

REVIEWED={
    'auremana666/naruto-the-broken-bond-pc-port':('Xbox 360 · ISO propia','Naruto: The Broken Bond de Xbox 360. La ISO se copia a assets; el port verifica e importa los datos al arrancar. La comprobación del contenedor no garantiza la revisión del juego. Hay incidencias gráficas abiertas en Steam Deck.'),
    'jorjbarbosa/broken-bond-recomp':('Xbox 360 · 55530825 · revisión verificada','Carpeta extraída de Naruto: The Broken Bond. Requiere Title ID 55530825 y default.xex con SHA-256 8f70e79443e36b38e44b6a105dad51fb8909fb615d982753cabaac9b15f0d576. El ZIP portable no incluye el importador de ISO.'),
    'jorjbarbosa/naruto-rise-recomp':('Xbox 360 · 555307E5','Carpeta extraída de Naruto: Rise of a Ninja, con default.xex de Title ID 555307E5. El port confirma la revisión. La versión 0.3 incluye las correcciones Vulkan para Wine/Proton.'),
    'patchzyy/wiicompiled':('RMCP01 · PAL','Mario Kart Wii de Wii, edición PAL limpia RMCP01. La integración comprueba el identificador antes de preparar el port.'),
    'ctr-tools/ctr-native':('SCUS-94426 · NTSC-U','Crash Team Racing de PlayStation. Requiere CUE/BIN NTSC-U y BIN crudo MODE2/2352; una ISO de 2048 bytes por sector no sirve.'),
    'hayatog/iss_pc':('CUSA00223 · actualización 1.07','inFAMOUS Second Son de PS4, carpeta extraída CUSA00223 con la actualización 1.07 integrada.'),
    'k0nl/b2recomp':('Switch · versión 1.2','Bayonetta 2 de Switch, versión 1.2. Carpeta extraída con exefs/main y romfs; el constructor comprueba la versión. No acepta NSP/XCI cifrados.'),
    'revivedx/savagewindrecomp':('Switch · actualización 1.9.0','Breath of the Wild de Switch con exefs y romfs extraídos y la actualización integrada. El README actual pide 1.9.0; el AppImage Alpha 3 comprobado también presenta 1.8.2 en su asistente.'),
    'florinp93/hells-gate-recomp':('Xbox 360 · 454108CF','Dante’s Inferno de Xbox 360. ISO/XISO o carpeta con default.xex del Title ID 454108CF; no sirve la versión PS3. El Title ID identifica el juego, no garantiza cualquier revisión del disco.'),
    'tgp482/black-xberecomp':('Xbox · USA o Europa','BLACK de la Xbox original, edición USA o Europa. Acepta ISO o datos extraídos; el port comprueba la versión y compila en el primer inicio.'),
    'euspring1/blackdefinitivehdpc':('Xbox · NTSC-U','BLACK de Xbox, versión NTSC-U. Carpeta extraída con default.xbe; se exige el SHA-256 publicado por el proyecto.'),
    'spacestate1/namco22-decompile':('timecris.zip · MAME 0.271+','Time Crisis requiere timecris.zip de MAME 0.271 o posterior, según la integración revisada.'),
    'openra/openra':('Contenido desde el juego','El contenido original se descarga o se elige desde el propio juego, según el título de OpenRA.'),
}

def original_requirement(item):
    from .ports import BUILTIN,valid_repository
    repo=str(item.get('repository',''));key=repo.lower()
    source='https://github.com/'+repo if valid_repository(repo) and not key.startswith('web/') else ''
    if key in REVIEWED:
        label,details=REVIEWED[key];return {'label':label,'details':details,'known':True,'source':source}
    # Built-in integrations carry exact disc serials or hashes. Ignore similarly named remote fields.
    builtin=next((b for b in BUILTIN if b['repository'].lower()==key),None)
    if builtin:
        disc=builtin.get('disc') or {};rom=builtin.get('rom') or {};wiiu=builtin.get('wiiu') or {}
        label=disc.get('serial') or rom.get('name') or wiiu.get('name')
        if key=='alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp':label+=' · Rev 1'
        if key=='web/openpete':source='https://www.openpete.com/'
        if key=='web/ctr-turbocharged':source='https://ctr.cmzi.uk/'
        if key=='genrythefox0/project-2099':label='Xbox 360'
        if label:return {'label':label,'details':builtin.get('note',''),'known':True,'source':source}
    if key=='zeldaret/botw':return {'label':'Sin port jugable','details':'Proyecto de decompilación; no publica un juego ejecutable.','known':False,'source':source}
    return {'label':'ROM por confirmar','details':'La región, el identificador y la revisión del original todavía no están revisados en Deck Library. Consultar los requisitos del proyecto antes de elegir una ROM.','known':False,'source':source}
