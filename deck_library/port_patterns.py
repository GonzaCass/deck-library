"""Game identity mapping, platform badges, GitHub README extraction and media patterns for ports."""
import hashlib, json, pathlib, re, time
from .updates import fetch

README_TTL = 24 * 3600

# Known codenamed port repositories -> (Canonical Game Title, Canonical Platform)
CODENAME_REPOS = {
    'revivedx/savagewindrecomp': ('The Legend of Zelda: Breath of the Wild', 'Switch'),
    'zeldaret/botw': ('The Legend of Zelda: Breath of the Wild', 'Switch'),
    'kuraeow/ultratears': ('The Legend of Zelda: Tears of the Kingdom', 'Switch'),
    'harbourmasters/shipofharkinian': ('The Legend of Zelda: Ocarina of Time', 'Nintendo 64'),
    'harbourmasters/2ship2harkinian': ("The Legend of Zelda: Majora's Mask", 'Nintendo 64'),
    'zelda64recomp/zelda64recomp': ("The Legend of Zelda: Majora's Mask", 'Nintendo 64'),
    'zeldawwhdrecomp/zeldawwhdrecomp': ('The Legend of Zelda: The Wind Waker HD', 'Wii U'),
    '999sian/tmc': ('The Legend of Zelda: The Minish Cap', 'Game Boy Advance'),
    'zeldaret/tmc': ('The Legend of Zelda: The Minish Cap', 'Game Boy Advance'),
    'snesrev/zelda3': ('The Legend of Zelda: A Link to the Past', 'Super Nintendo'),
    'harbourmasters/spaghettikart': ('Mario Kart 64', 'Nintendo 64'),
    'harbourmasters/starship': ('Star Fox 64', 'Nintendo 64'),
    'harbourmasters/ghostship': ('Super Mario 64', 'Nintendo 64'),
    'florinp93/hells-gate-recomp': ('Dante’s Inferno', 'Xbox 360'),
    'k0nl/b2recomp': ('Bayonetta 2', 'Switch'),
    'hedge-dev/unleashedrecomp': ('Sonic Unleashed', 'Xbox 360'),
    'shagg88/athelas': ('The Lord of the Rings: The Return of the King', 'Xbox'),
    'gumpolas/tootawersrecomp': ('The Lord of the Rings: The Two Towers', 'Xbox'),
    'felipeprado0/spartanport': ('God of War III', 'PlayStation 4'),
    'hayatog/iss_pc': ('inFAMOUS: Second Son', 'PlayStation 4'),
    '999sian/melee-pc': ('Super Smash Bros. Melee', 'GameCube'),
    'jrickey/battleship': ('Super Smash Bros.', 'Nintendo 64'),
    'web/openpete': ('Spyro the Dragon', 'PlayStation'),
    'web/ctr-turbocharged': ('Crash Team Racing', 'PlayStation'),
    'ctr-tools/ctr-native': ('Crash Team Racing', 'PlayStation'),
    'genrythefox0/project-2099': ('Spider-Man: Edge of Time', 'Xbox 360'),
    'alexbeavs-ps1-ports/spider-man-recomp': ('Spider-Man', 'PlayStation'),
    'alexbeavs-ps1-ports/spider-man-2-enter-electro-recomp': ('Spider-Man 2: Enter Electro', 'PlayStation'),
    'alexbeavs-ps1-ports/crash-bandicoot-3-warped-recomp': ('Crash Bandicoot: Warped', 'PlayStation'),
    'matteo842/crashbandicoot-launcher': ('Crash Bandicoot', 'PlayStation'),
    'mstan/apeescaperecomp': ('Ape Escape', 'PlayStation'),
    'diasurgical/devilutionx': ('Diablo', 'PC'),
    'openmw/openmw': ('The Elder Scrolls III: Morrowind', 'PC'),
    'openrct2/openrct2': ('RollerCoaster Tycoon 2', 'PC'),
    'arx/arxlibertatis': ('Arx Fatalis', 'PC'),
    'bvschaik/julius': ('Caesar III', 'PC'),
    'keriew/augustus': ('Caesar III', 'PC'),
    'ihhub/fheroes2': ('Heroes of Might and Magic II', 'PC'),
    'vcmi/vcmi': ('Heroes of Might and Magic III', 'PC'),
    'corsixth/corsixth': ('Theme Hospital', 'PC'),
    'xproger/openlara': ('Tomb Raider', 'PlayStation'),
    'open-goal/jak-project': ('Jak and Daxter: The Precursor Legacy', 'PlayStation 2'),
    'k4zmu2a/spacecadetpinball': ('3D Pinball: Space Cadet', 'PC'),
    'fgsfdsfgs/perfect_dark': ('Perfect Dark', 'Nintendo 64'),
    'n64recomp/banjorecomp': ('Banjo-Kazooie', 'Nintendo 64'),
    'kislayk/goemon64recomp': ('Mystical Ninja Starring Goemon', 'Nintendo 64'),
    'am2r-community-developers/am2rlauncher': ('Metroid II: Return of Samus', 'Game Boy'),
}

CODENAME_NAMES = {
    'savage wind recomp': ('The Legend of Zelda: Breath of the Wild', 'Switch'),
    'savagewindrecomp': ('The Legend of Zelda: Breath of the Wild', 'Switch'),
    'ship of harkinian': ('The Legend of Zelda: Ocarina of Time', 'Nintendo 64'),
    '2ship2harkinian': ("The Legend of Zelda: Majora's Mask", 'Nintendo 64'),
    'spaghettikart': ('Mario Kart 64', 'Nintendo 64'),
    'spacecadetpinball': ('3D Pinball: Space Cadet', 'PC'),
}

NOISE_SUFFIX = re.compile(
    r'\s*(?:'
    r'\((?:[^)]*\b(?:recomp(?:iled)?|decomp(?:ilation)?|port|native|ps[1-5]|psx|psp|xbox(?:\s*360)?|xbla|switch|n64|gba|snes|pc|vulkan|c\+\+|engine|standalone|driftdroid|sunpad|odysseydecomp|ultratears|botw|rygt|sm64ex|gen2recomped|little planet|tobiichi)[^)]*)\)'
    r'|\[(?:[^\]]*\b(?:recomp|port|3sxw?|enhanced|hd updated)[^\]]*)\]'
    r'|\s+-\s+(?:PC\s+Port|Static\s+Recomp(?:ilation)?)'
    r'|\s+(?:Static\s+)?Recomp(?:iled|ilation)?$'
    r')\s*',
    re.I,
)


def strip_port_noise(title):
    cleaned = str(title or '').strip()
    if not cleaned:
        return ''
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = NOISE_SUFFIX.sub(' ', cleaned).strip(' -—·:')
    return re.sub(r'\s{2,}', ' ', cleaned).strip() or str(title).strip()


def resolve_game_identity(item):
    """Return (game_title, original_platform) for a catalog item dict."""
    repo = str(item.get('repository', '')).strip().lower()
    if repo in CODENAME_REPOS:
        return CODENAME_REPOS[repo]
    name_key = str(item.get('name', '')).strip().lower()
    if name_key in CODENAME_NAMES:
        return CODENAME_NAMES[name_key]
    raw_game = item.get('game_title') or item.get('cover_title') or ''
    if raw_game:
        cleaned = strip_port_noise(raw_game)
    else:
        cleaned = strip_port_noise(item.get('name', ''))
    info = platform_info(item.get('list', ''))
    return cleaned or item.get('name', ''), info['canonical']


def entry_display_title(entry):
    """Human-facing game title for a library Entry, resolving port codenames."""
    repo = str(entry.metadata.get('port_repository', '')).strip().lower()
    if repo in CODENAME_REPOS:
        return CODENAME_REPOS[repo][0]
    name_key = entry.name.strip().lower()
    if name_key in CODENAME_NAMES:
        return CODENAME_NAMES[name_key][0]
    meta_title = str(entry.metadata.get('game_title', '')).strip()
    if meta_title and meta_title.lower() != name_key:
        # Libretro titles like "Legend of Zelda, The - The Minish Cap" keep entry.name when entry.name is already clean
        if ', the' in meta_title.lower() and 'the ' in name_key:
            return strip_port_noise(entry.name)
        return strip_port_noise(meta_title)
    if entry.kind == 'port':
        return strip_port_noise(entry.name)
    return entry.name


def entry_port_project(entry):
    """Return the port project name when it differs from the resolved game title."""
    display = entry_display_title(entry)
    raw = entry.name.strip()
    if display.casefold() != raw.casefold() and strip_port_noise(raw).casefold() != display.casefold():
        return raw
    return ''


def platform_info(raw):
    """Normalize messy catalog category strings into (short, icon, canonical, tone)."""
    low = str(raw or '').strip().lower()
    if not low or 'utilit' in low:
        return {'short': 'Utilidad' if 'utilit' in low else 'Port', 'icon': 'sliders' if 'utilit' in low else 'controller', 'canonical': '', 'tone': 'neutral'}
    if 'switch 2' in low or 'switch2' in low or re.search(r'(?<![a-z0-9])nx2(?![a-z0-9])', low):
        return {'short': 'Switch 2', 'icon': 'plat-switch', 'canonical': 'Switch 2', 'tone': 'red'}
    if any(k in low for k in ('switch',)):
        return {'short': 'Switch', 'icon': 'plat-switch', 'canonical': 'Switch', 'tone': 'red'}
    if any(k in low for k in ('xbox 360', 'x360', 'rexglue')):
        return {'short': 'Xbox 360', 'icon': 'plat-xbox', 'canonical': 'Xbox 360', 'tone': 'green'}
    if any(k in low for k in ('xbox one', 'xone')):
        return {'short': 'Xbox One', 'icon': 'plat-xbox', 'canonical': 'Xbox One', 'tone': 'green'}
    if any(k in low for k in ('og xbox', 'xbox')):
        return {'short': 'Xbox', 'icon': 'plat-xbox', 'canonical': 'Xbox', 'tone': 'green'}
    if any(k in low for k in ('playstation 5', 'ps5')):
        return {'short': 'PS5', 'icon': 'plat-ps', 'canonical': 'PlayStation 5', 'tone': 'blue'}
    if any(k in low for k in ('playstation 4', 'ps4')):
        return {'short': 'PS4', 'icon': 'plat-ps', 'canonical': 'PlayStation 4', 'tone': 'blue'}
    if any(k in low for k in ('playstation 3', 'ps3')):
        return {'short': 'PS3', 'icon': 'plat-ps', 'canonical': 'PlayStation 3', 'tone': 'blue'}
    if any(k in low for k in ('playstation 2', 'ps2')):
        return {'short': 'PS2', 'icon': 'plat-ps', 'canonical': 'PlayStation 2', 'tone': 'blue'}
    if any(k in low for k in ('playstation portable', 'psp')):
        return {'short': 'PSP', 'icon': 'plat-ps', 'canonical': 'PSP', 'tone': 'blue'}
    if any(k in low for k in ('vita', 'psvita')):
        return {'short': 'PS Vita', 'icon': 'plat-ps', 'canonical': 'PS Vita', 'tone': 'blue'}
    if any(k in low for k in ('playstation', 'ps1', 'psx')):
        return {'short': 'PS1', 'icon': 'plat-ps', 'canonical': 'PlayStation', 'tone': 'blue'}
    if any(k in low for k in ('wii u', 'wiiu')):
        return {'short': 'Wii U', 'icon': 'plat-nintendo', 'canonical': 'Wii U', 'tone': 'blue'}
    if 'gamecube' in low or low == 'gcn' or low.startswith('gc'):
        return {'short': 'GameCube', 'icon': 'plat-nintendo', 'canonical': 'GameCube', 'tone': 'violet'}
    if 'wii' in low:
        return {'short': 'Wii', 'icon': 'plat-nintendo', 'canonical': 'Wii', 'tone': 'blue'}
    if any(k in low for k in ('nintendo 64', 'n64')):
        return {'short': 'N64', 'icon': 'plat-nintendo', 'canonical': 'Nintendo 64', 'tone': 'red'}
    if any(k in low for k in ('super nintendo', 'snes')):
        return {'short': 'SNES', 'icon': 'plat-nintendo', 'canonical': 'Super Nintendo', 'tone': 'violet'}
    if any(k in low for k in ('game boy advance', 'gba')):
        return {'short': 'GBA', 'icon': 'plat-nintendo', 'canonical': 'Game Boy Advance', 'tone': 'violet'}
    if any(k in low for k in ('game boy color', 'gbc')):
        return {'short': 'GBC', 'icon': 'plat-nintendo', 'canonical': 'Game Boy Color', 'tone': 'yellow'}
    if low == 'gb' or 'game boy' in low:
        return {'short': 'Game Boy', 'icon': 'plat-nintendo', 'canonical': 'Game Boy', 'tone': 'yellow'}
    if '3ds' in low:
        return {'short': '3DS', 'icon': 'plat-nintendo', 'canonical': 'Nintendo 3DS', 'tone': 'red'}
    if 'nds' in low or 'nintendo ds' in low:
        return {'short': 'DS', 'icon': 'plat-nintendo', 'canonical': 'Nintendo DS', 'tone': 'red'}
    if low == 'nes' or 'entertainment system' in low:
        return {'short': 'NES', 'icon': 'plat-nintendo', 'canonical': 'NES', 'tone': 'red'}
    if 'nintendo' in low:
        return {'short': 'Nintendo', 'icon': 'plat-nintendo', 'canonical': 'Nintendo', 'tone': 'red'}
    if any(k in low for k in ('sega', 'dreamcast', 'saturn', 'genesis', 'megadrive', 'rdk', 'retro engine')) or low == 'gen':
        return {'short': 'SEGA', 'icon': 'plat-sega', 'canonical': 'SEGA', 'tone': 'blue'}
    if 'arcade' in low:
        return {'short': 'Arcade', 'icon': 'plat-arcade', 'canonical': 'Arcade', 'tone': 'yellow'}
    if 'cdi' in low or 'cd-i' in low:
        return {'short': 'CD-i', 'icon': 'disc', 'canonical': 'CD-i', 'tone': 'neutral'}
    if 'mobile' in low or 'android' in low or 'ios' in low:
        return {'short': 'Móvil', 'icon': 'controller', 'canonical': 'Mobile', 'tone': 'neutral'}
    if low == 'pc' or low.startswith('pc,') or '2d game' in low:
        return {'short': 'PC', 'icon': 'plat-pc', 'canonical': 'PC', 'tone': 'blue'}
    return {'short': raw[:14] if raw else 'Port', 'icon': 'controller', 'canonical': '', 'tone': 'neutral'}


# Universal port installation media patterns across all platforms
PATTERNS = {
    'Switch': {
        'kind': 'switch',
        'short': 'NSP / XCI + prod.keys',
        'summary': 'Requiere el juego de Switch (NSP o XCI + prod.keys) o carpeta exefs/romfs.',
        'button': 'Convertir NSP / XCI o elegir carpeta',
        'extensions': ('*.nsp', '*.xci', '*.nsz'),
        'roms_folder': 'switch',
    },
    'Switch 2': {
        'kind': 'switch2',
        'short': 'NSP / XCI de Switch 2 + prod.keys',
        'summary': 'Experimental: hace falta un emulador de Switch 2 (forks de Eden como Eglantine), el juego propio, prod.keys y firmware. Eden oficial no los ejecuta.',
        'button': 'Elegir carpeta del juego',
        'extensions': ('*.nsp', '*.xci'),
        'roms_folder': 'switch2',
    },
    'Xbox 360': {
        'kind': 'xbox360',
        'short': 'ISO de Xbox 360 o default.xex',
        'summary': 'Requiere la ISO propia de Xbox 360 o una carpeta extraída con default.xex.',
        'button': 'Elegir ISO de Xbox 360 o carpeta',
        'extensions': ('*.iso', '*.xex'),
        'roms_folder': 'xbox360',
    },
    'Xbox': {
        'kind': 'xbox',
        'short': 'ISO / XISO de Xbox o default.xbe',
        'summary': 'Requiere la ISO/XISO de Xbox clásica o carpeta extraída con default.xbe.',
        'button': 'Elegir ISO de Xbox o carpeta',
        'extensions': ('*.iso', '*.xiso', '*.xbe'),
        'roms_folder': 'xbox',
    },
    'PlayStation': {
        'kind': 'ps1',
        'short': 'Disco BIN/CUE + BIOS PS1',
        'summary': 'Requiere la imagen del disco de PS1 (.bin/.cue, .iso o .chd) y en algunos kits la BIOS SCPH.',
        'button': 'Elegir disco de PS1 / BIOS',
        'extensions': ('*.cue', '*.bin', '*.chd', '*.iso'),
        'roms_folder': 'psx',
    },
    'PlayStation 2': {
        'kind': 'disc',
        'short': 'ISO de PS2',
        'summary': 'Requiere la imagen ISO propia del juego de PlayStation 2.',
        'button': 'Elegir ISO de PS2',
        'extensions': ('*.iso', '*.chd', '*.cso'),
        'roms_folder': 'ps2',
    },
    'PSP': {
        'kind': 'disc',
        'short': 'ISO / CSO de PSP',
        'summary': 'Requiere la imagen ISO o CSO del juego de PSP.',
        'button': 'Elegir ISO de PSP',
        'extensions': ('*.iso', '*.cso', '*.chd'),
        'roms_folder': 'psp',
    },
    'PlayStation 3': {
        'kind': 'folder',
        'short': 'ISO descifrada o carpeta de PS3',
        'summary': 'Requiere la carpeta del juego de PS3 (PS3_GAME / EBOOT.BIN) o una ISO descifrada, que se extrae con «Extraer una ISO».',
        'button': 'Elegir carpeta del juego',
        'extensions': (),
        'roms_folder': 'ps3',
    },
    'PlayStation 4': {
        'kind': 'folder',
        'short': 'Carpeta extraída de PS4',
        'summary': 'Requiere los archivos extraídos del juego de PS4 (eboot.bin y datos).',
        'button': 'Elegir carpeta del juego',
        'extensions': (),
        'roms_folder': 'ps4',
    },
    'PlayStation 5': {
        'kind': 'folder',
        'short': 'Carpeta extraída de PS5',
        'summary': 'Requiere los archivos extraídos del juego original.',
        'button': 'Elegir carpeta del juego',
        'extensions': (),
        'roms_folder': 'ps5',
    },
    'GameCube': {
        'kind': 'disc',
        'short': 'ISO / RVZ de GameCube',
        'summary': 'Requiere la imagen ISO, GCM o RVZ del disco de GameCube.',
        'button': 'Elegir imagen de GameCube',
        'extensions': ('*.iso', '*.gcm', '*.rvz', '*.ciso'),
        'roms_folder': 'gc',
    },
    'Wii': {
        'kind': 'disc',
        'short': 'ISO / WBFS / RVZ de Wii',
        'summary': 'Requiere la imagen del disco de Wii (.iso, .wbfs o .rvz).',
        'button': 'Elegir imagen de Wii',
        'extensions': ('*.iso', '*.wbfs', '*.rvz'),
        'roms_folder': 'wii',
    },
    'Wii U': {
        'kind': 'wiiu',
        'short': 'WUA / WUX / WUD o carpeta Wii U',
        'summary': 'Requiere el juego de Wii U (.wua, .wux/.wud con keys.txt, o carpeta extraída).',
        'button': 'Elegir archivo o carpeta de Wii U',
        'extensions': ('*.wua', '*.wux', '*.wud', '*.rpx'),
        'roms_folder': 'wiiu',
    },
    'Nintendo 64': {
        'kind': 'rom',
        'short': 'ROM de Nintendo 64 (.z64)',
        'summary': 'Requiere la ROM original de Nintendo 64 (normalmente formato .z64 big-endian).',
        'button': 'Elegir ROM de N64',
        'extensions': ('*.z64', '*.n64', '*.v64', '*.rom'),
        'roms_folder': 'n64',
    },
    'Super Nintendo': {
        'kind': 'rom',
        'short': 'ROM de Super Nintendo (.sfc / .smc)',
        'summary': 'Requiere la ROM original de SNES (.sfc o .smc).',
        'button': 'Elegir ROM de SNES',
        'extensions': ('*.sfc', '*.smc', '*.zip'),
        'roms_folder': 'snes',
    },
    'Game Boy Advance': {
        'kind': 'rom',
        'short': 'ROM de GBA (.gba)',
        'summary': 'Requiere la ROM original de Game Boy Advance (.gba).',
        'button': 'Elegir ROM de GBA',
        'extensions': ('*.gba', '*.zip'),
        'roms_folder': 'gba',
    },
    'Game Boy Color': {
        'kind': 'rom',
        'short': 'ROM de GBC (.gbc)',
        'summary': 'Requiere la ROM original de Game Boy Color (.gbc).',
        'button': 'Elegir ROM de GBC',
        'extensions': ('*.gbc', '*.gb', '*.zip'),
        'roms_folder': 'gbc',
    },
    'Game Boy': {
        'kind': 'rom',
        'short': 'ROM de Game Boy (.gb)',
        'summary': 'Requiere la ROM original de Game Boy (.gb).',
        'button': 'Elegir ROM de Game Boy',
        'extensions': ('*.gb', '*.gbc', '*.zip'),
        'roms_folder': 'gb',
    },
    'NES': {
        'kind': 'rom',
        'short': 'ROM de NES (.nes)',
        'summary': 'Requiere la ROM original de NES (.nes).',
        'button': 'Elegir ROM de NES',
        'extensions': ('*.nes', '*.zip'),
        'roms_folder': 'nes',
    },
    'Nintendo DS': {
        'kind': 'rom',
        'short': 'ROM de Nintendo DS (.nds)',
        'summary': 'Requiere la ROM original de Nintendo DS (.nds).',
        'button': 'Elegir ROM de DS',
        'extensions': ('*.nds', '*.zip'),
        'roms_folder': 'nds',
    },
    'Nintendo 3DS': {
        'kind': 'rom',
        'short': 'ROM de 3DS (.3ds / .cia)',
        'summary': 'Requiere el volcado desencriptado de Nintendo 3DS (.3ds, .cci o .cia).',
        'button': 'Elegir ROM de 3DS',
        'extensions': ('*.3ds', '*.cci', '*.cia', '*.cxi'),
        'roms_folder': '3ds',
    },
    'SEGA': {
        'kind': 'rom',
        'short': 'ROM / imagen de SEGA',
        'summary': 'Requiere la ROM o imagen original de SEGA (.md, .bin, .cue, .chd o Data.rsdk).',
        'button': 'Elegir ROM o archivo de datos',
        'extensions': ('*.md', '*.gen', '*.bin', '*.cue', '*.chd', '*.iso', '*.rsdk'),
        'roms_folder': 'genesis',
    },
    'Arcade': {
        'kind': 'rom',
        'short': 'ROMset de Arcade (.zip)',
        'summary': 'Requiere el archivo .zip de la ROM de Arcade (MAME).',
        'button': 'Elegir ZIP de Arcade',
        'extensions': ('*.zip', '*.7z'),
        'roms_folder': 'arcade',
    },
    'PC': {
        'kind': 'pc',
        'short': 'Datos del juego de PC (Steam / GOG)',
        'summary': 'Motor nativo o reimplementación: suele requerir copiar la carpeta de datos del juego original de PC (Steam o GOG), salvo juegos libres completos.',
        'button': 'Elegir carpeta de datos de PC',
        'extensions': (),
        'roms_folder': '',
    },
}


def classify_port(item):
    """Detect the media requirement pattern for any port in the catalog."""
    _, canonical = resolve_game_identity(item)
    if not canonical:
        canonical = platform_info(item.get('list', ''))['canonical']
    text_blob = ' '.join((item.get('name', ''), item.get('description', ''), item.get('note', ''), item.get('source_note', ''))).lower()
    if not canonical:
        if any(w in text_blob for w in ('nintendo switch', 'nsp', 'xci', 'romfs', 'exefs')):
            canonical = 'Switch'
        elif any(w in text_blob for w in ('xbox 360', 'default.xex', 'xbla')):
            canonical = 'Xbox 360'
        elif any(w in text_blob for w in ('default.xbe', 'xiso', 'original xbox')):
            canonical = 'Xbox'
        elif any(w in text_blob for w in ('nintendo 64', '.z64', 'n64recomp')):
            canonical = 'Nintendo 64'
        elif any(w in text_blob for w in ('psx', 'ps1', 'scph', 'playstation 1')):
            canonical = 'PlayStation'
    if canonical in PATTERNS:
        return {**PATTERNS[canonical], 'platform': canonical}
    return {
        'kind': 'generic',
        'platform': canonical or 'Original',
        'short': 'Archivos del juego original',
        'summary': 'Revisar en la descripción de GitHub qué archivo o carpeta del juego original solicita este port.',
        'button': 'Elegir archivo o carpeta',
        'extensions': (),
        'roms_folder': '',
    }


def format_markdown(raw):
    """Convert raw GitHub Markdown into clean, readable plain text for console UI."""
    if not raw:
        return ''
    text = raw.replace('\r\n', '\n')
    # Strip HTML and Markdown reference comments, badges/shields, pure HTML img/picture/div tags
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    text = re.sub(r'^\s*\[(?:comment|//)\]:.*$', '', text, flags=re.I | re.M)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\[!\[[^\]]*\]\([^)]+\)\]\([^)]+\)', '', text)
    text = re.sub(r'<img\b[^>]*>', '', text, flags=re.I)
    text = re.sub(r'</?(?:p|div|center|picture|source|br|hr|details|summary|kbd|sub|sup|h[1-6]|a|span|strong|em|b|i|table|tr|td|th|thead|tbody)\b[^>]*>', '', text, flags=re.I)
    # Links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    lines = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            if stripped:
                lines.append('    ' + line.rstrip())
            continue
        if not stripped:
            if lines and lines[-1] != '':
                lines.append('')
            continue
        # Skip markdown table separator rows
        if re.fullmatch(r'[\s|:-]+', stripped) and '|' in stripped:
            continue
        heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if heading:
            title = re.sub(r'[*_`]+', '', heading.group(2)).strip()
            if title:
                if lines and lines[-1] != '':
                    lines.append('')
                lines.append('▸ ' + title.upper() if len(heading.group(1)) <= 2 else '• ' + title)
            continue
        bullet = re.match(r'^[-*+]\s+(.*)$', stripped)
        if bullet:
            content = re.sub(r'\*\*([^*]+)\*\*', r'\1', bullet.group(1))
            content = content.replace('`', '')
            lines.append('  • ' + content.strip())
            continue
        clean_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', stripped)
        clean_line = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', clean_line)
        clean_line = clean_line.replace('`', '')
        lines.append(clean_line)
    result = '\n'.join(lines).strip()
    return result[:9000] + ('\n…' if len(result) > 9000 else '')


def fetch_readme(store, repository):
    """Fetch and cache a port's GitHub README.md (network off the GTK thread)."""
    from .ports import valid_repository
    if not valid_repository(repository) or repository.lower().startswith('web/'):
        return ''
    cache_dir = pathlib.Path(store.root) / 'catalog-readmes'
    key = hashlib.sha256(repository.lower().encode()).hexdigest()[:24]
    cache_file = cache_dir / (key + '.txt')
    if cache_file.is_file() and time.time() - cache_file.stat().st_mtime < README_TTL:
        try:
            return cache_file.read_text(errors='replace')
        except OSError:
            pass
    url = f'https://raw.githubusercontent.com/{repository}/HEAD/README.md'
    try:
        raw = fetch(url).decode('utf-8', errors='replace')
    except Exception:
        if cache_file.is_file():
            try:
                return cache_file.read_text(errors='replace')
            except OSError:
                pass
        return ''
    formatted = format_markdown(raw)
    if formatted:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(formatted)
        except OSError:
            pass
    return formatted
