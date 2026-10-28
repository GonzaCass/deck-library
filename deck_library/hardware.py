"""Which Steam Deck this is, read from the firmware's product name. It only informs: nothing in the app is ever limited by it,
because a Deck docked to a TV or a monitor can use other refresh rates."""
import pathlib

DMI=pathlib.Path('/sys/devices/virtual/dmi/id')
# Product names as reported by Valve's firmware. Galileo (OLED) was confirmed on a real Deck (product_name and board_name); Jupiter (LCD) is still to be confirmed.
MODELS={'jupiter':'steam-deck-lcd','galileo':'steam-deck-oled'}
PANELS={'steam-deck-lcd':'Steam Deck LCD · panel de 60 Hz','steam-deck-oled':'Steam Deck OLED · panel de hasta 90 Hz'}

def model(root=None):
    """'steam-deck-lcd', 'steam-deck-oled' or 'unknown'. Never raises: a missing or odd file simply means unknown."""
    root=pathlib.Path(root or DMI)
    for name in ('product_name','board_name'):
        try:value=(root/name).read_text(errors='replace').strip().casefold()
        except OSError:continue
        if value in MODELS:return MODELS[value]
    return 'unknown'

def describe(identifier=None):
    """One line for Settings, or '' when the model is not a known Steam Deck."""
    return PANELS.get(identifier if identifier is not None else model(),'')
