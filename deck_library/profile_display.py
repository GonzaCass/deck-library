"""Plain-language presentation of profiles. Values come from the profile, never FPS estimates."""
from . import presets

TEST_STATES = {
    'proposal': 'Sin probar en este juego',
    'boot-tested': '✓ Comprobado · arranque',
    'user-confirmed': '✓ Comprobado · usuario',
}


def title(profile):
    name = profile['name']
    if ' — ' in name:
        name = name.split(' — ', 1)[1]
    return name[:1].upper() + name[1:]


def intent(profile):
    ident = profile['id']
    mode=title(profile).casefold()
    if mode=='calidad':return 'monitor',profile['objective']
    if mode=='rendimiento':return 'speed',profile['objective']
    if mode=='equilibrado':return 'sliders',profile['objective']
    if ident.endswith('-performance'):
        return 'speed', 'Compilación en segundo plano para reducir pausas.'
    if ident.endswith('-quality'):
        return 'monitor', 'Mayor resolución interna para una imagen más nítida.'
    if ident.endswith('-compatibility'):
        return 'shield', 'Mayor precisión gráfica; puede reducir el rendimiento.'
    if ident.endswith('-default'):
        return 'sliders', 'Un punto de partida para comparar imagen y rendimiento.'
    return 'monitor', profile['objective']


def value_text(adapter, key, value):
    if value == 'predeterminado' or value is None:
        return 'Del programa'
    choices = {
        ('eden', 'backend'): {0: 'OpenGL', 1: 'Vulkan'},
        ('eden', 'resolution_setup'): {1: '0,5×', 2: '0,75×', 3: '1×', 4: '1,25×', 5: '1,5×', 6: '2×'},
        ('eden', 'anti_aliasing'): {0: 'Sin suavizado', 1: 'FXAA', 2: 'SMAA'},
        ('eden', 'gpu_accuracy'): {0: 'Normal', 1: 'Alta'},
        ('eden', 'cpu_accuracy'): {0: 'Automática', 1: 'Precisa', 2: 'Insegura'},
        ('eden', 'use_docked_mode'): {False: 'Portátil', True: 'TV'},
    }
    if (adapter, key) in choices:
        return choices[adapter, key].get(value, str(value))
    if type(value) is bool:
        return 'Activado' if value else 'Desactivado'
    if key in ('resolution_multiplier', 'InternalResolution', 'ResolutionScale'):
        return f'{value:g}×' if isinstance(value, (int, float)) else str(value)
    return {'vulkan': 'Vulkan', 'opengl': 'OpenGL', 'borderless': 'Sin bordes', 'fullscreen': 'Pantalla completa', 'windowed': 'Ventana'}.get(str(value), str(value))


def highlights(profile):
    """Up to three concrete settings; no inferred speed or promises of compatibility."""
    adapter = profile['adapter']['id']
    settings = profile['settings']
    keys = {
        'eden': [('Renderer', 'resolution_setup', 'Resolución'), ('System', 'use_docked_mode', 'Modo'), ('Renderer', 'backend', 'Gráficos')],
        'wiicompiled': [('video', 'resolution_multiplier', 'Resolución'), ('video', 'graphics_api', 'Gráficos'), ('video', 'display_mode', 'Pantalla')],
        'duckstation': [('GPU', 'ResolutionScale', 'Resolución'), ('GPU', 'PGXPEnable', 'Geometría precisa'), ('Display', 'MaxFPS', 'Límite de FPS')],
        'dolphin': [('Video_Settings', 'InternalResolution', 'Resolución'), ('Video_Settings', 'MSAA', 'Suavizado')],
        'prism': [('General', 'MaxMemAlloc', 'Memoria máxima'), ('General', 'MinecraftWinWidth', 'Ancho de ventana')],
        'project2099': [('runtime', 'window_height', 'Alto de ventana'), ('runtime', 'present_effect', 'Escalado'), ('runtime', 'genry_eot_target_fps', 'Objetivo de FPS')],
    }.get(adapter, [])
    return [(name, value_text(adapter, key, settings[section][key])) for section, key, name in keys if key in settings.get(section, {})]


def differences(entry, profile, config_dir=None):
    """Normalize types so an INI's 'true' and a JSON's true are the same setting."""
    path, items = presets.preview(entry, profile, config_dir)
    adapter = presets.adapter_for(entry)
    inherited = set()
    if adapter == 'eden' and path.exists():
        local = presets.ini_parser(path.read_text())
        for section, options in profile['settings'].items():
            if not local.has_section(section):continue
            for option in options:
                if local[section].get(option+'\\use_global','').lower()=='true':inherited.add(section+'.'+option)
    changes = []
    for key, old, new in items:
        section, option = key.split('.', 1)
        rule = presets.REGISTRY[adapter].get(section, {}).get(option)
        if key in inherited:old='predeterminado'
        normalized = presets.typed(rule, old) if rule is not None else None
        if normalized != new:
            changes.append((key, normalized if normalized is not None else old, new))
    return path, changes
