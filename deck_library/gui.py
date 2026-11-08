"""Deck Library: biblioteca, fichas de juego y asistente inicial."""
import json,os,pathlib,shlex,subprocess,sys,threading
import gi
gi.require_version('Gtk','3.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,Pango,GdkPixbuf
from . import motion
from . import __version__
from .models import Store,Entry
from .discovery import scan,available_emulators,nice_name,SYSTEMS
from .runtime import diagnostics,clean_environment
from .service import queue_entries,queue_removals,queue_controllers,restart_steam
from .steam import find_accounts,active_account
from .installations import settings,save_settings,report
from .gui_tools import ToolsMixin
from .gui_library import LibraryToolsMixin
from .gui_switch import SwitchMixin
from .gui_requests import RequestsMixin
from .gui_toolbox import ToolboxMixin
from .gui_community import CommunityMixin
from .gui_updates import UpdatesMixin
from .gui_catalog import CatalogMixin
from .library_view import TYPES,entry_type,visible_entries
from .experience import ExperienceMixin
from .artwork import find_cover

from .ui_theme import CSS,css,load_fonts
load_fonts()
PROVIDER=None

from .gui_widgets import TONES,label,wrap_row,WrapRow,button,PageStack,Banner,Poster

from .gui_actions import ActionsMixin
from .gui_shell import ShellMixin
from .gui_game import GameMixin
from .gui_progress import ProgressMixin
from .gui_input import InputMixin
from .gui_editor import EditorMixin

from .gui_originals import OriginalsMixin
from .gui_home import HomeMixin
from .gui_help import HelpMixin
from .gui_variants import VariantsMixin
from .gui_removal import RemovalMixin
from .gui_refresh import RefreshMixin
from .gui_shattered import ShatteredMixin
from .gui_port_locations import PortLocationsMixin

from .gui_rom_locations import RomLocationsMixin

from .gui_compatibility import CompatibilityMixin

class Window(CompatibilityMixin,RomLocationsMixin,PortLocationsMixin,ShatteredMixin,RefreshMixin,RemovalMixin,ToolboxMixin,RequestsMixin,SwitchMixin,VariantsMixin,HelpMixin,HomeMixin,OriginalsMixin,InputMixin,ProgressMixin,GameMixin,ShellMixin,EditorMixin,CommunityMixin,LibraryToolsMixin,ActionsMixin,CatalogMixin,UpdatesMixin,ExperienceMixin,ToolsMixin,Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self,title='Deck Library');self.init_shell()


def run():
    GLib.set_prgname('deck-library');GLib.set_application_name('Deck Library')
    from . import ui_theme
    chosen=settings(Store()).get('theme','dark');ui_theme.set_theme(chosen);Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',chosen!='light')
    Gtk.Window.set_default_icon_from_file(str(pathlib.Path(__file__).resolve().parent.parent/'assets/icon.png'))
    global PROVIDER
    PROVIDER=Gtk.CssProvider();PROVIDER.load_from_data(css(settings(Store()).get('ui_scale','normal'),chosen));Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),PROVIDER,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    from . import i18n
    i18n.setup(settings(Store()))
    window=Window();window.show_all();Gtk.main();i18n.dump_missed()
