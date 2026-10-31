"""Opt-in GTK checks: DECK_LIBRARY_UI_TESTS=1 python -m unittest discover -s tests -p test_gui_deck.py."""
import os,pathlib,tempfile,unittest
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('DECK_LIBRARY_UI_TESTS')=='1' and os.environ.get('DISPLAY'),'requires GTK and a disposable display')
class DeckUITests(unittest.TestCase):
    def setUp(self):
        from deck_library import gui,gui_shell
        from deck_library.installations import DEFAULTS
        from deck_library.models import Store,Entry
        from deck_library.inline_pages import InlineDialog
        self.inline=InlineDialog
        self.gui=gui;self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.store.save([Entry('Juego de prueba',['/bin/true'],kind='emulated',platform='Switch',source='/tmp/test.nsp',game_id='0100000000000000')])
        self.patches=[patch.object(gui_shell,'Store',return_value=self.store),patch.object(gui_shell,'settings',return_value={**DEFAULTS,'onboarding_complete':True,'start_page':'library','check_updates':False,'artwork_provider':'off','animations':False,'community_ratings':False,'eden_config':str(pathlib.Path(self.temp.name)/'eden')}),patch.object(gui.Window,'discover',return_value=False),patch.object(gui.Window,'load_catalog',return_value=None),patch.object(gui_shell,'find_accounts',return_value=[]),patch.object(gui_shell,'active_account',return_value=None)]
        from deck_library import eden_controls
        self.patches.append(patch.object(eden_controls,'status',return_value='ok'))
        from deck_library import port_locations
        self.patches.append(patch.object(port_locations,'candidates',return_value=[]))
        self.patches.append(patch.object(gui.Window,'check_missing_roms',return_value=False))
        for p in self.patches:p.start()
        from gi.repository import Gtk,Gdk
        provider=Gtk.CssProvider();provider.load_from_data(gui.CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.w=gui.Window();self.w.resize(1280,760);self.w.show_all();self.settle()
    def test_gtaiv_filter_action_does_not_reapply_the_full_recipe(self):
        from deck_library import gtaiv
        from deck_library.models import Entry
        from gi.repository import Gtk,GLib
        original=self.inline.run
        def drive(page):
            def apply():
                next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Quitar filtro de color').clicked()
                GLib.timeout_add(250,lambda:(page.response(Gtk.ResponseType.CLOSE),False)[1]);return False
            GLib.timeout_add(150,apply);return original(page)
        entry=Entry('GTA IV',['steam','steam://run/12210'],'steam','Windows',metadata={'gtaiv_root':'/example/GTAIV','gtaiv_settings':'/example/SETTINGS.CFG'})
        with patch.object(gtaiv,'installed_release',return_value='5.1.2'),patch.object(gtaiv,'apply') as full,patch.object(gtaiv,'remove_color_filter',return_value='/example/backup') as remove,patch.object(self.inline,'run',drive):
            self.w.gtaiv_dialog(entry)
        full.assert_not_called();remove.assert_called_once_with('/example/GTAIV',self.store);self.assertFalse(self.w.inline_workflows)

    def test_gtaiv_latest_choice_uses_the_selected_pinned_recipe(self):
        from deck_library import gtaiv
        from deck_library.models import Entry
        from gi.repository import Gtk,GLib
        original=self.inline.run
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        def drive(page):
            def apply():
                combo=next(c for c in walk(page) if isinstance(c,Gtk.ComboBoxText))
                self.assertEqual(combo.get_active_id(),'4.0.5');combo.set_active_id('5.1.2')
                next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Aplicar arreglo de GTA IV').clicked()
                GLib.timeout_add(250,lambda:(page.response(Gtk.ResponseType.CLOSE),False)[1]);return False
            GLib.timeout_add(150,apply);return original(page)
        entry=Entry('GTA IV',['steam','steam://run/12210'],'steam','Windows',metadata={'gtaiv_root':'/example/GTAIV','gtaiv_settings':'/example/SETTINGS.CFG'})
        with patch.object(gtaiv,'apply',return_value='/example/backup') as apply,patch.object(self.inline,'run',drive):self.w.gtaiv_dialog(entry)
        self.assertEqual(apply.call_args.kwargs,{'release':'5.1.2'});self.assertFalse(self.w.inline_workflows)

    def test_startup_missing_rom_can_be_moved_and_keeps_game_identity(self):
        from deck_library import gui_rom_locations
        from deck_library.models import Entry
        target=pathlib.Path(self.temp.name)/'new.iso';target.write_bytes(b'rom')
        old=Entry('Missing game',['dolphin','-e','/missing/game.iso'],'emulated','Wii','/missing/game.iso')
        self.w.entries=[old];self.store.save([old])
        gui_rom_locations.RomLocationsMixin.check_missing_roms(self.w);self.settle()
        page=self.w.inline_workflows[-1]
        actions=self.w.control_targets(page)
        self.assertIn('Se borró',[c.get_accessible().get_name() for c in actions])
        with patch.object(self.w,'pick_file',return_value=str(target)):
            next(c for c in actions if c.get_accessible().get_name()=='Se movió').clicked();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.store.load()[0].id,old.id)
        self.assertEqual(self.store.load()[0].source,str(target))

    def test_missing_rom_later_and_back_preserve_everything(self):
        from deck_library import gui_rom_locations
        gui_rom_locations.RomLocationsMixin.check_missing_roms(self.w);self.settle()
        self.assertTrue(self.w.inline_workflows)
        self.w.controller_action('back');self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(len(self.store.load()),1)
        gui_rom_locations.RomLocationsMixin.check_missing_roms(self.w);self.settle();self.assertFalse(self.w.inline_workflows)

    def test_conversion_progress_and_result_stay_visible_until_continue(self):
        from gi.repository import Gtk
        from deck_library import switch_extract
        import threading
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        release=threading.Event();entered=threading.Event();done=[]
        result={'path':self.temp.name,'files':10,'size':1024,'update':False}
        def convert(*args):entered.set();release.wait(5);return result
        with patch.object(switch_extract,'find_keys',return_value=['/fake/prod.keys']),patch.object(switch_extract,'tool_path',return_value='/fake/nstool'),patch.object(switch_extract,'Job') as job:
            job.return_value.convert.side_effect=convert
            page=self.w.switch_convert_page(on_done=done.append);self.settle()
            choose=next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Elegir')
            with patch.object(self.w,'pick_file',return_value='/fake/game.nsp'):choose.clicked()
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Convertir').clicked();self.settle()
            self.assertTrue(entered.is_set())
            progress=next(c for c in walk(page) if isinstance(c,Gtk.ProgressBar))
            self.assertTrue(progress.get_mapped());self.assertIs(progress.get_parent().get_parent(),page)
            self.assertTrue(any(isinstance(c,Gtk.Label) and c.get_text()=='Cancelar' and c.get_mapped() for c in walk(page)))
            self.w.controller_action('back');self.settle();self.assertIn(page,self.w.inline_workflows)
            release.set();self.settle()
            self.assertEqual(done,[]);self.assertIn(page,self.w.inline_workflows);self.assertEqual(progress.get_fraction(),1)
            self.assertTrue(any(isinstance(c,Gtk.Label) and c.get_text()=='Conversión completada. La carpeta está lista.' for c in walk(page)))
            with patch.object(switch_extract,'leftovers',return_value=[]):
                next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Usar esta carpeta').clicked();self.settle()
            self.assertEqual(done,[self.temp.name]);self.assertNotIn(page,self.w.inline_workflows)

    def test_conversion_failure_is_visible_and_can_be_retried(self):
        from gi.repository import Gtk
        from deck_library import switch_extract
        with patch.object(switch_extract,'find_keys',return_value=['/fake/prod.keys']),patch.object(switch_extract,'tool_path',return_value='/fake/nstool'),patch.object(switch_extract,'Job') as job:
            job.return_value.convert.side_effect=ValueError('Invalid test keys')
            page=self.w.switch_convert_page();self.settle()
            choose=next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Elegir')
            with patch.object(self.w,'pick_file',return_value='/fake/game.nsp'):choose.clicked()
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Convertir').clicked();self.settle()
            self.assertIn(page,self.w.inline_workflows)
            self.assertTrue(next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Convertir').get_sensitive())
            self.assertTrue(page.back_button.get_sensitive());page.destroy()

    def test_missing_port_offers_inline_location_recovery_and_back_without_launching(self):
        from deck_library import ports
        from deck_library.models import Entry,atomic_json
        from gi.repository import Gtk
        folder=pathlib.Path(self.temp.name)/'lost'
        record={'repository':'owner/Game','name':'Game','folder':'Game','executable':'game.AppImage','runtime':'linux','install_path':str(folder)}
        atomic_json(self.store.root/'ports.json',{'owner/Game':record})
        entry=Entry('Game',[str(folder/'game.AppImage')],source=str(folder/'game.AppImage'),metadata={'port_repository':'owner/Game'})
        self.w.entries=[entry];self.store.save([entry]);self.w.select_game(entry);self.settle()
        targets=self.w.control_targets(self.w.detail)
        locate=next(c for c in targets if c.get_accessible().get_name()=='Buscar carpeta');self.assertTrue(locate.get_mapped())
        with patch('deck_library.gui_actions.subprocess.Popen') as popen:
            self.w.play(entry);self.settle();popen.assert_not_called()
        page=self.w.inline_workflows[-1]
        labels=[c.get_accessible().get_name() for c in self.w.control_targets(page)]
        self.assertIn('Elegir carpeta del port',labels);self.assertIn('Reinstalar port',labels)
        self.w.controller_action('back');self.settle();self.assertFalse(self.w.inline_workflows)

    def test_port_install_choice_can_reuse_an_existing_folder_without_a_download(self):
        from deck_library import ports
        from gi.repository import Gtk
        item=ports.clean({'repository':'owner/Game','name':'Game'})
        with patch.object(ports,'install') as install:
            self.w.install_port(item,False);self.settle()
            page=self.w.inline_workflows[-1]
            controls=self.w.control_targets(page);reuse=next(c for c in controls if c.get_accessible().get_name()=='Usar instalación existente')
            reuse.clicked();self.settle();install.assert_not_called()
        page=self.w.inline_workflows[-1]
        target=pathlib.Path(self.temp.name)/'External Game';target.mkdir();exe=target/'game.AppImage';exe.write_bytes(b'ELF');exe.chmod(0o755)
        with patch.object(self.w,'pick_file',return_value=str(target)):
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Elegir carpeta del port').clicked();self.settle()
        self.assertEqual(ports.records(self.store)[item['repository']]['install_path'],str(target))
        self.assertFalse((target/'.deck-library-port.json').exists());page.destroy();self.settle()
        self.assertTrue(any(e.source==str(exe) for e in self.w.entries))

    def test_install_choice_download_continues_the_actual_installation(self):
        from deck_library import ports
        item=ports.clean({'repository':'owner/Game','name':'Game'})
        page=self.w.port_install_choice(item)
        with patch.object(self.w,'install_port') as install:
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Descargar port').clicked();self.settle()
        install.assert_called_once_with(item,False,runtime='auto',location_chosen=True);self.assertFalse(self.w.inline_workflows)

    def test_switch_wizard_reuses_a_compiled_game_in_a_different_folder_without_keys(self):
        from deck_library import ports,switch_port,switch_extract
        from deck_library.models import atomic_json
        from gi.repository import GLib
        item=ports.clean({'repository':switch_port.REPOSITORY})
        atomic_json(self.store.root/'ports.json',{item['repository']:{**item,'runtime':'linux','inputs':{}}})
        target=pathlib.Path(self.temp.name)/'SD Card/Compiled'
        for name in ('exefs/main','romfs.bin','swgame.so'):
            file=target/'extracted'/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'fixture')
        def choose():
            page=self.w.inline_workflows[-1]
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Usar juego ya compilado').clicked();return False
        GLib.timeout_add(180,choose)
        with patch.object(self.w,'pick_file',return_value=str(target)),patch.object(switch_extract,'find_keys',return_value=[]):
            self.assertTrue(self.w.port_inputs(item))
        self.assertEqual(ports.records(self.store)[item['repository']]['game_data_dir'],str(target));self.assertFalse(self.w.inline_workflows)

    def test_offer_deck_controls_asks_once_and_applies_or_remembers_refusal(self):
        from deck_library import eden_controls
        entry=self.w.entries[0]
        with patch.object(eden_controls,'status',return_value='missing'),patch.object(eden_controls,'apply') as apply,patch.object(self.w,'confirm',return_value=True) as confirm:
            self.w.offer_deck_controls(entry);confirm.assert_called_once();apply.assert_called_once()
        with patch.object(eden_controls,'status',return_value='missing'),patch.object(eden_controls,'apply') as apply,patch.object(self.w,'confirm',return_value=False),patch('deck_library.installations.save_settings'):
            self.w.offer_deck_controls(entry);apply.assert_not_called();self.assertEqual(self.w.preferences['eden_controls_declined'],'missing')
        with patch.object(eden_controls,'status',return_value='missing'),patch.object(self.w,'confirm') as confirm:
            self.w.offer_deck_controls(entry);confirm.assert_not_called()
    def settle(self):
        from gi.repository import GLib
        loop=GLib.MainLoop();GLib.timeout_add(150,lambda:(loop.quit(),False)[1]);loop.run()
    def tearDown(self):
        from gi.repository import Gtk
        self.w.disconnect_by_func(Gtk.main_quit);self.w.destroy()
        # Finish pending popup/focus events before constructing the next test window.
        self.settle()
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_update_count_stays_legible_in_active_and_inactive_tabs(self):
        from gi.repository import Gtk
        def luminance(color):
            values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in (color.red,color.green,color.blue)]
            return .2126*values[0]+.7152*values[1]+.0722*values[2]
        control=self.w.nav_buttons['Actualizaciones'];context=control.get_style_context()
        with patch.object(self.w,'pending_updates',return_value=[{}]*12):self.w.refresh_update_badges()
        for active in (False,True):
            if active:context.add_class('active')
            else:context.remove_class('active')
            self.settle();badge=self.w.update_badge;style=badge.get_style_context();fg=style.get_color(Gtk.StateFlags.NORMAL);bg=style.get_background_color(Gtk.StateFlags.NORMAL)
            bright,dark=sorted((luminance(fg),luminance(bg)),reverse=True)
            self.assertGreaterEqual((bright+.05)/(dark+.05),4.5);self.assertGreater(bg.alpha,.99)
            self.assertTrue(badge.get_mapped());self.assertEqual(badge.get_text(),'12');self.assertGreaterEqual(badge.get_allocated_width(),badge.get_layout().get_pixel_size().width)
        with patch.object(self.w,'pending_updates',return_value=[]):self.w.refresh_update_badges()
        self.assertFalse(self.w.update_badge.get_visible())

    def test_running_version_and_update_state_stay_visible_and_refresh_automatically(self):
        from deck_library import __version__
        self.w.preferences['auto_update']=False;self.w.preferences['check_updates']=True
        # The version no longer takes a row on every page: it ends the Settings page, and Updates shows it too.
        self.w.settings_page();self.settle();self.assertTrue(self.w.version_label.get_mapped());self.assertIn(__version__,self.w.version_label.get_text())
        self.w.library_stack.show();self.w.open_library();self.settle();self.assertFalse(self.w.version_label.get_mapped())
        self.w.updates_page();self.w.app_update_ready({'app':{'version':'99.0.0','notes':'New release'}});self.settle()
        self.assertIn('99.0.0',self.w.version_label.get_text());self.assertTrue(self.w.update_banner.get_mapped())
        def labels(widget):
            from gi.repository import Gtk
            return ([widget.get_text()] if isinstance(widget,Gtk.Label) else [])+[text for child in (widget.get_children() if isinstance(widget,Gtk.Container) else []) for text in labels(child)]
        self.assertIn('Deck Library 99.0.0',labels(self.w.updates_box))
        self.w.app_update_ready({'app_error':'offline'});self.settle();self.assertIn('No se pudo comprobar',self.w.version_label.get_text());self.assertTrue(self.w.update_banner.get_mapped())
        self.w.settings_page();self.w.resize(840,640);self.settle();position=self.w.version_label.translate_coordinates(self.w,0,0)
        self.assertGreaterEqual(position[0],0);self.assertLessEqual(position[0]+self.w.version_label.get_allocated_width(),840)

    def test_home_inbox_appears_after_verified_admin_login_and_disappears_after_logout(self):
        from unittest.mock import Mock
        self.w.preferences['owner_mode']=False;self.w.home_page();self.settle()
        def received():return any(c.get_accessible().get_name()=='Bandeja de entrada' for c in self.w.control_targets(self.w.pages.get_visible_child()))
        self.assertFalse(received())
        client=Mock();client.session.return_value={'token':'test-owner','login':'Owner'};client.me.return_value={'admin':True}
        with patch.object(self.w,'signed_in',return_value=True),patch.object(self.w,'community_client',return_value=client):
            self.w.check_owner_mode();self.settle();self.assertTrue(self.w.preferences['owner_mode']);self.assertTrue(received())
        with patch.object(self.w,'signed_in',return_value=False):self.w.check_owner_mode();self.settle()
        self.assertFalse(self.w.preferences['owner_mode']);self.assertFalse(received())

    def test_home_has_one_support_entry_no_tools_or_verified_link_and_pinned_storage(self):
        from gi.repository import Gtk
        from deck_library.models import Entry
        self.w.entries=[Entry('Port '+str(i),['/bin/true',str(i)],kind='port') for i in range(18)]
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        for width,height in ((1280,800),(840,640)):
            self.w.resize(width,height);self.w.home_page();self.settle()
            shell=self.w.pages.get_visible_child();captions=[w.get_label() for w in walk(shell) if isinstance(w,Gtk.Button)]
            self.assertEqual(captions.count('Solicitudes y reportes'),1)
            for removed in ('Verificados','Ver biblioteca','Ayuda','Instalaciones y carpetas','Duplicados y conflictos','Ver actualizaciones'):self.assertNotIn(removed,captions)
            support=self.w.home_support_button;before=support.translate_coordinates(self.w,0,0)
            scroll=self.w.home_box.get_ancestor(Gtk.ScrolledWindow);adjustment=scroll.get_vadjustment();self.assertGreater(adjustment.get_upper(),adjustment.get_page_size())
            adjustment.set_value(adjustment.get_upper()-adjustment.get_page_size());self.settle()
            self.assertEqual(support.translate_coordinates(self.w,0,0),before);self.assertTrue(support.get_mapped());self.assertLess(before[1]+support.get_allocated_height(),height/2)
            free=next(w for w in walk(shell) if isinstance(w,Gtk.Label) and 'GiB libres' in w.get_text());self.assertLess(free.translate_coordinates(self.w,0,0)[1],before[1]);self.assertLessEqual(self.w.get_size().width,width)

    def test_inline_commands_stay_above_long_forms_and_support_combines_inbox_and_creation(self):
        from gi.repository import Gtk
        page=self.w.support_page();self.settle()
        captions=[w.get_label() for w in self.w.control_targets(page) if isinstance(w,Gtk.Button)]
        self.assertIn('Nueva solicitud',captions);self.assertIn('Reportar un problema',captions);self.assertNotIn('Mis solicitudes y respuestas',captions)
        self.assertLess(page.actions.translate_coordinates(self.w,0,0)[1],page.scroll.translate_coordinates(self.w,0,0)[1]);page.destroy()
        page=self.w.request_game_page();page.get_content_area().pack_start(Gtk.Label(label='Long form\n'*120),False,False,0);page.get_content_area().show_all();self.settle()
        send=next(w for w in self.w.control_targets(page) if isinstance(w,Gtk.Button) and w.get_label()=='Enviar solicitud');before=send.translate_coordinates(self.w,0,0)
        adjustment=page.scroll.get_vadjustment();adjustment.set_value(adjustment.get_upper()-adjustment.get_page_size());self.settle()
        self.assertEqual(send.translate_coordinates(self.w,0,0),before);self.assertLess(before[1]+send.get_allocated_height(),page.scroll.translate_coordinates(self.w,0,0)[1]+1)
        page.destroy()

    def test_profile_apply_stays_fixed_and_secondary_actions_move_to_the_game_menu(self):
        from gi.repository import Gtk
        self.w.select_game(self.w.entries[0]);self.settle()
        scroll=self.w.profile_card_box.get_ancestor(Gtk.ScrolledWindow);content_y=scroll.translate_coordinates(self.w,0,0)[1]
        for control in (self.w.profile_apply,self.w.profile_apply_play):
            self.assertLess(control.translate_coordinates(self.w,0,0)[1],content_y);self.assertTrue(control.get_mapped())
        menu=self.w.game_header_secondary;menu.set_active(True);self.settle()
        self.assertTrue(self.w.profile_rate.get_mapped());self.assertTrue(self.w.profile_restore.get_mapped())
        menu.set_active(False)

    def test_game_navigation_is_identical_for_emulated_ports_windows_and_minecraft(self):
        from deck_library.models import Entry
        from gi.repository import Gtk
        entries=[self.w.entries[0],Entry('Native',['/bin/true']),Entry('Windows',['/bin/true'],kind='steam',platform='Windows'),Entry('Instance',['/bin/true'],kind='minecraft',platform='Minecraft')]
        for entry in entries:
            self.w.entries=[entry];self.w.select_game(entry);self.settle()
            self.assertEqual(list(self.w.game_section_controls),['profiles','controls','content'])
            self.assertEqual([c.get_label() for c in self.w.game_section_controls.values()],['Ajustes','Controles','Juego y archivos'])
            buttons=[c for c in self.w.control_targets(self.w.detail) if isinstance(c,Gtk.Button)]
            self.assertEqual(sum(c.get_label()=='Comunidad' for c in buttons),1)
            self.assertNotIn('Buscar en la comunidad',[c.get_label() for c in buttons])
            self.w.game_section_controls['content'].clicked();self.settle();self.assertEqual(self.w.game_tab,'content')
            self.w.controller_action('back');self.settle();self.assertEqual(self.w.game_tab,'profiles')
        entry=Entry('Windows',['/bin/true'],kind='steam',platform='Windows',metadata={'steam_appid':123})
        self.w.entries=[entry];self.w.select_game(entry);self.w.game_steam_button.clicked();self.settle()
        self.assertEqual(self.w.game_tab,'content');self.assertTrue(self.w.game_section_controls['content'].get_style_context().has_class('active'))
        self.w.open_game_section('files');self.assertEqual(self.w.game_tab,'content');self.assertIsNone(self.w.game_pages.get_child_by_name('files'))

    def test_automatic_refresh_is_quiet_and_defers_library_work_while_editing(self):
        import time
        self.w.preferences['check_updates']=True;self.w.catalog_ready=True;self.w.live_catalog_checked=time.monotonic()-1000
        with patch.object(self.w,'discover') as discover,patch.object(self.w,'check_updates') as updates,patch.object(self.w,'load_catalog') as catalog:
            self.assertTrue(self.w.live_refresh());discover.assert_called_once_with(quiet=True);updates.assert_called_once();catalog.assert_called_once_with(False)
            discover.reset_mock();catalog.reset_mock();self.w.editor_dirty=True;self.w.live_catalog_checked=0
            self.assertTrue(self.w.live_refresh());discover.assert_not_called();catalog.assert_not_called()
        self.w.editor_dirty=False

    def test_unchanged_background_discovery_preserves_game_selection_and_widgets(self):
        from deck_library.models import Entry
        self.w.select_game(self.w.entries[0]);self.settle();card=self.w.profile_cards[0];selection=self.w.profile_selection
        copies=[Entry.from_dict(e.to_dict()) for e in self.w.entries]
        self.w.discovery_quiet=True;self.w.discover_busy=True
        with patch.object(self.w,'show_detail') as detail,patch.object(self.w,'render') as render,patch.object(self.w,'set_status') as status:
            self.w.discovered(copies);detail.assert_not_called();render.assert_not_called();status.assert_not_called()
        self.assertIs(self.w.profile_cards[0],card);self.assertIs(self.w.profile_selection,selection);self.assertFalse(self.w.discover_busy)

    def test_inline_refresh_timer_is_removed_when_its_page_closes(self):
        from gi.repository import GLib
        page=self.w.support_page();self.settle()
        with patch.object(self.w,'signed_in',return_value=False):
            identifier=self.w.watch_page(page,lambda:None)
        self.assertIsNotNone(GLib.MainContext.default().find_source_by_id(identifier))
        page.destroy();self.settle();self.assertIsNone(GLib.MainContext.default().find_source_by_id(identifier));self.assertNotIn(identifier,self.w.ui_sources)

    def test_background_inventory_keeps_newer_saved_options_and_defers_during_a_form(self):
        from deck_library.models import Entry
        old=Entry.from_dict(self.w.entries[0].to_dict());saved=Entry.from_dict(old.to_dict());saved.metadata['personal_setting']='latest';self.store.save([saved])
        self.w.discovery_quiet=True
        with patch('deck_library.steam_inventory.merge_steam',side_effect=lambda entries:entries),patch.object(self.w,'discovered'):
            self.w.discovery_snapshot_ready([old]);self.assertEqual(self.store.load()[0].metadata['personal_setting'],'latest')
        self.w.editor_dirty=True
        with patch.object(self.store,'merge') as merge:self.w.discovery_snapshot_ready([old]);merge.assert_not_called()
        self.w.editor_dirty=False

    def test_admin_inbox_refresh_preserves_a_reply_draft_and_then_loads_new_rows(self):
        from unittest.mock import Mock
        from gi.repository import Gtk
        client=Mock();client.session.return_value={'token':'admin-fixture','login':'Owner'}
        row={'id':'1234abcd','title':'Example','state':'new','platform':'Windows','category':'port','login':'Player','details':'Details'}
        client.request.return_value={'requests':[row]};watch={}
        def track(page,callback,interval=20,ready=None):watch.update(callback=callback,ready=ready)
        with patch.object(self.w,'community_client',return_value=client),patch.object(self.w,'watch_page',side_effect=track):
            page=self.w.owner_requests_page();self.settle()
            response=next(c for c in self.w.control_targets(page) if isinstance(c,Gtk.TextView));response.get_buffer().set_text('Draft reply')
            self.assertFalse(watch['ready']());before=client.request.call_count
            client.request.return_value={'requests':[{**row,'note':'New note','updated':2}]};watch['callback']();self.settle()
            self.assertEqual(client.request.call_count,before);self.assertEqual(response.get_buffer().get_text(response.get_buffer().get_start_iter(),response.get_buffer().get_end_iter(),True),'Draft reply')
            response.get_buffer().set_text('');self.assertTrue(watch['ready']());watch['callback']();self.settle();self.assertGreater(client.request.call_count,before)
            self.assertIsNone(response.get_parent());page.destroy()

    def test_manual_reload_buttons_are_absent_from_library_home_support_and_updates(self):
        from gi.repository import Gtk
        def captions(root):return [c.get_label() for c in self.w.control_targets(root) if isinstance(c,Gtk.Button)]
        self.w.open_library();self.settle();self.assertNotIn('Actualizar biblioteca',captions(self.w.pages.get_visible_child()))
        self.w.home_page();self.settle();self.assertNotIn('Actualizar biblioteca',captions(self.w.pages.get_visible_child()))
        page=self.w.support_page();self.settle();self.assertNotIn('Actualizar',captions(page));page.destroy()
        self.w.updates_page();self.settle();self.assertNotIn('Buscar actualizaciones',captions(self.w.pages.get_visible_child()))

    def test_shattered_fix_is_a_single_action_and_reports_completion_inside_the_app(self):
        from deck_library.models import Entry
        from deck_library import shattered
        import time
        entry=Entry('Spider-Man Shattered Dimensions',['/bin/true'],kind='steam',platform='Windows');self.w.entries=[entry]
        with patch.object(shattered,'inspect',side_effect=ValueError('Setup required')):
            self.w.select_game(entry);self.settle()
        actions=[c for c in self.w.control_targets(self.w.detail) if c.get_accessible().get_name()=='Aplicar arreglo'];self.assertEqual(len(actions),1)
        result={'backup':str(pathlib.Path(self.temp.name)/'backup')}
        with patch.object(shattered,'apply',return_value=result) as apply:
            actions[0].clicked();deadline=time.monotonic()+2
            while self.w.profile_job and time.monotonic()<deadline:self.settle()
            self.assertFalse(self.w.profile_job);apply.assert_called_once();self.assertEqual(apply.call_args.args[2],'keep');page=self.w.inline_workflows[-1]
            self.assertTrue(any(c.get_accessible().get_name()=='Volver al juego' for c in self.w.control_targets(page)))
            with patch.object(shattered,'inspect',side_effect=ValueError('Setup required')):self.w.controller_action('back');self.settle()
            self.assertFalse(self.w.inline_workflows)

    def test_sending_a_problem_report_opens_the_same_personal_inbox(self):
        import time
        from gi.repository import Gtk
        from community.server import API,digest
        api=API(self.store.root/'reports.sqlite3',client_id='test')
        with api.db() as db:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest('player'),'oidc:test:player','Player',time.time()+300))
        class Client:
            def session(_):return {'token':'player','login':'Player'}
            def request(_,path,body=None):return api.handle('GET' if body is None else 'POST',path,{},body or {},'player')
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        with patch.object(self.w,'signed_in',return_value=True),patch.object(self.w,'community_client',return_value=Client()),patch.object(self.w,'confirm',return_value=True):
            self.w.bug_report_page();self.settle();page=self.w.inline_workflows[-1]
            next(w for w in walk(page.get_content_area()) if isinstance(w,Gtk.Entry)).set_text('Example startup error')
            next(w for w in walk(page.get_content_area()) if isinstance(w,Gtk.TextView)).get_buffer().set_text('The library does not load after opening it.')
            next(w for w in self.w.control_targets(page) if w.get_accessible().get_name()=='Preparar reporte').clicked();self.settle()
            next(w for w in self.w.control_targets(page) if w.get_accessible().get_name()=='Enviar diagnóstico').clicked();self.settle();self.settle()
            rows=api.handle('GET','/v1/me/requests',{}, {},'player')['requests'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['category'],'report')
            next(w for w in self.w.control_targets(page) if w.get_accessible().get_name()=='Ver mis reportes').clicked();self.settle()
            hub=self.w.inline_workflows[-1];self.assertTrue(any(isinstance(w,Gtk.Label) and w.get_text()=='Example startup error' for w in walk(hub)));hub.destroy()

    def test_switch_install_asks_directly_and_accepts_an_extracted_folder_without_keys(self):
        from gi.repository import Gtk,GLib
        from deck_library import ports,switch_extract
        from deck_library.models import atomic_json
        item=ports.clean({'name':'Savage Wind','repository':'ReviveDX/SavageWindRecomp'})
        dump=pathlib.Path(self.temp.name)/'dump';(dump/'exefs').mkdir(parents=True);(dump/'exefs/main').write_bytes(b'NSO0');(dump/'romfs').mkdir()
        atomic_json(self.store.root/'ports.json',{item['repository']:{**item,'inputs':{}}})
        def choose():
            page=self.w.inline_workflows[-1]
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Usar carpeta ya extraída').clicked();return False
        GLib.timeout_add(180,choose)
        with patch.object(self.w,'pick_file',return_value=str(dump)) as pick,patch.object(self.w,'confirm') as confirm,patch.object(switch_extract,'find_keys',return_value=[]):
            self.assertTrue(self.w.port_inputs(item));confirm.assert_not_called();pick.assert_called_once_with('Elegir carpeta con exefs y romfs',folder=True)
        self.assertEqual(ports.records(self.store)[item['repository']]['inputs']['original_data'],str(dump));self.assertEqual(self.w.inline_workflows,[])

    def test_a_previously_installed_switch_port_uses_the_same_preparation_wizard(self):
        from deck_library import ports,switch_port
        from deck_library.models import Entry,atomic_json
        repository='ReviveDX/SavageWindRecomp'
        entry=Entry('Savage Wind',['/bin/true'],kind='port',metadata={'port_repository':repository,'configured':True})
        atomic_json(self.store.root/'ports.json',{repository:{'repository':repository,'folder':'savage','runtime':'linux','setup':'','configured':False}})
        with patch.object(switch_port,'prepared',return_value=False),patch.object(self.w,'configure_port') as configure:
            self.w.select_game(entry);self.settle();self.assertEqual(self.w.game_play_button.get_label(),'Preparar');self.w.game_play_button.clicked();configure.assert_called_once()

    def test_admin_text_reply_creates_a_visible_notice_and_opening_it_marks_only_that_reply_read(self):
        import time
        from gi.repository import Gtk
        from community.server import API,digest
        api=API(self.store.root/'support.sqlite3',client_id='test');api.admins={'admin'}
        with api.db() as db:
            for token,login in [('admin-token','admin'),('user-token','player')]:db.execute('INSERT INTO tokens VALUES(?,?,?,?)',(digest(token),'oidc:test:'+login,login,time.time()+300))
        identifier=api.handle('POST','/v1/requests',{}, {'title':'Example game','platform':'PC','category':'native','details':'Controller does not respond'},'user-token')['id']
        token=['admin-token']
        class Client:
            def session(_):return {'token':token[0],'login':token[0]}
            def request(_,path,body=None):return api.handle('GET' if body is None else 'POST',path,{},body or {},token[0])
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        with patch.object(self.w,'signed_in',return_value=True),patch.object(self.w,'community_client',return_value=Client()):
            page=self.w.owner_requests_page();self.settle()
            view=next(c for c in walk(page) if isinstance(c,Gtk.TextView));view.get_buffer().set_text('Select the SDL controller profile.')
            next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Enviar respuesta').clicked();self.settle();page.destroy()
            token[0]='user-token';self.w.poll_request_replies();self.settle()
            self.assertTrue(self.w.request_notice.get_mapped());self.assertEqual(self.w.request_unread_count,1)
            page=self.w.my_requests_page();self.settle();self.settle()
            self.assertIn('Select the SDL controller profile.',[c.get_text() for c in walk(page) if isinstance(c,Gtk.Label)])
            self.assertEqual(api.handle('GET','/v1/me/requests',{}, {},'user-token')['unread'],0);self.assertFalse(self.w.request_notice.get_visible());page.destroy()

    def test_completed_installs_are_not_offered_as_updates(self):
        self.w.start_transfer('example/port');self.w.finish_transfer('example/port');self.w.update_state={'catalog':[],'ports':[]};self.w.updates_page();self.settle()
        self.assertFalse(self.w.pending_updates());self.assertFalse(self.w.transfer_views.get('example/port'))

    def test_a_bundled_profile_can_be_rated_directly_then_returns_to_its_details(self):
        from gi.repository import Gtk,GLib
        from deck_library import presets
        from deck_library.community import Client
        profile=presets.recommended(self.w.entries[0],self.store)[0]
        row={'id':'test-profile','preset':profile,'author':'Deck Library','rating':4.0,'ratings':1}
        original=self.inline.run;seen=[]
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        def run(page):
            def check():
                try:
                    stack=next(w for w in walk(page) if isinstance(w,Gtk.Stack));self.assertEqual(stack.get_visible_child_name(),'feedback')
                    next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Enviar valoración').clicked()
                    def finish():
                        try:self.assertEqual(stack.get_visible_child_name(),'profile');seen.append(True)
                        finally:page.response(Gtk.ResponseType.CLOSE)
                        return False
                    GLib.timeout_add(350,finish)
                except Exception:page.response(Gtk.ResponseType.CLOSE);raise
                return False
            GLib.timeout_add(250,check);return original(page)
        Client(self.store,'https://presets.jokerlan.xyz').remember({'token':'local-test-token','login':'Player'})
        with patch.object(Client,'me',return_value={'login':'Player','admin':False}),patch.object(Client,'search',return_value=[row]),patch.object(Client,'comments',return_value=[]),patch.object(Client,'rate',return_value={'ok':True}) as rate,patch.object(self.inline,'run',run):
            self.w.community_dialog(self.w.entries[0],profile['id'],mode='feedback');rate.assert_called_once_with(row,5,'')
        self.assertEqual(seen,[True])

    def test_gaming_mode_can_install_an_app_update_and_requests_only_reopening_the_app(self):
        from deck_library import gui_updates,updates,__version__
        self.w.preferences['auto_update']=False;self.w.update_state={'app':{'version':'99.0.0','archive':'https://example.com/app','checksum':'https://example.com/checksum','name':'test'}}
        with patch.object(gui_updates.motion,'gaming_mode',return_value=True),patch.object(updates,'install_update',return_value='99.0.0') as install,patch.object(self.w,'message') as message:
            self.w.port_busy=True;self.w.install_app_update(automatic=True);install.assert_not_called();self.assertTrue(self.w.app_update_retry);self.w.port_busy=False
            self.w.install_app_update();self.settle();install.assert_called_once();message.assert_not_called()
            self.assertEqual(self.w.update_installed,'99.0.0');self.assertIn(__version__,self.w.version_label.get_text());self.assertIn('99.0.0',self.w.version_label.get_text())
            self.assertEqual(self.w.banner_action.get_label(),'Cerrar y abrir de nuevo desde Steam')

    def test_search_opens_keyboard_only_after_an_explicit_action(self):
        from gi.repository import Gtk
        self.assertTrue(self.w.search.get_input_hints()&Gtk.InputHints.INHIBIT_OSK);self.assertIn('X: teclado',self.w.search.get_placeholder_text())
        with patch('shutil.which',return_value='/usr/bin/steam'),patch('subprocess.Popen') as launch:
            self.w.search.grab_focus();self.settle();launch.assert_not_called()
            self.w.controller_action('search');launch.assert_called_once();self.assertIn('steam://open/keyboard',launch.call_args.args[0][1])
            self.assertIs(self.w.get_focus(),self.w.search)
            self.w.last_keyboard_request=0;self.w.search.emit('icon-press',Gtk.EntryIconPosition.PRIMARY,None);self.assertEqual(launch.call_count,2)

    def test_gamepad_reaches_filters_and_changes_the_library_view(self):
        self.w.filter_toggle.clicked();self.settle()
        from gi.repository import Gtk
        targets=self.w.control_targets(self.w)
        for picker in (self.w.platform_picker,self.w.type_picker,self.w.view_picker):
            self.assertIn(picker,targets);self.assertTrue(picker.get_can_focus())
        self.w.platform_picker.grab_focus();self.w.controller_action('right');self.settle()
        self.assertIs(self.w.navigation_focus(self.w),self.w.type_picker)
        self.w.view_picker.grab_focus();self.w.controller_action('activate');self.settle()
        self.assertIsInstance(Gtk.grab_get_current(),Gtk.MenuShell)
        self.w.controller_action('down');self.w.last_controller_action=('',0);self.w.controller_action('activate');self.settle()
        self.assertEqual(self.w.view,'list')
        self.w.platform_picker.grab_focus();self.w.last_controller_action=('',0);self.w.controller_action('activate');self.settle()
        self.w.controller_action('back');self.settle()
        self.assertNotIsInstance(Gtk.grab_get_current(),Gtk.MenuShell)

    def test_touch_drag_fallback_scrolls_and_leaves_short_taps_unclaimed(self):
        from gi.repository import Gtk
        from unittest.mock import Mock
        self.populate_games(40);scroll=self.w.library_stack.get_visible_child();adjustment=scroll.get_vadjustment();gesture=Mock()
        self.assertTrue(scroll.get_kinetic_scrolling());self.assertEqual(scroll._deck_drag.get_propagation_phase(),Gtk.PropagationPhase.CAPTURE)
        scroll._deck_drag_begin(gesture,50,200);scroll._deck_drag_update(gesture,2,-4);gesture.set_state.assert_not_called()
        scroll._deck_drag_update(gesture,0,-120);self.assertGreaterEqual(adjustment.get_value(),100);gesture.set_state.assert_called_once_with(Gtk.EventSequenceState.CLAIMED)

    def test_last_focused_cover_includes_its_caption_inside_the_viewport(self):
        from deck_library.models import atomic_json
        self.populate_games(45);target=self.w.entries[-1].id
        atomic_json(self.store.root/'pending.json',{'ids':[target]});self.w.refresh_pending()
        self.w.focus_library(target);self.settle()
        scroll=self.w.library_stack.get_visible_child();adjustment=scroll.get_vadjustment();visual=self.w.library_targets[target].library_focus_visual;point=visual.translate_coordinates(scroll.get_child().get_child(),0,0)
        self.assertGreaterEqual(point[1],adjustment.get_value()-1);self.assertLessEqual(point[1]+visual.get_allocated_height(),adjustment.get_value()+adjustment.get_page_size()+1)

    def test_completed_changes_show_a_readable_dismissible_notice(self):
        windows=self.application_windows();self.w.set_status('Descargando port…');self.assertFalse(self.w.toast_widget.get_reveal_child())
        self.w.set_status('Carátula guardada.');self.settle();notice=self.w.toast_widget
        self.assertTrue(notice.get_reveal_child());self.assertEqual(notice.text.get_text(),'Carátula guardada.');self.assertEqual(self.application_windows(),windows)
        notice.hide_text();self.assertFalse(notice.get_reveal_child())

    def test_pages_stay_inside_deck_window_and_list_has_thumbnail(self):
        for page in ('covers','list','platforms'):
            self.w.view=page;self.w.render();self.settle();self.assertLessEqual(self.w.get_size().width,1280);self.assertLessEqual(self.w.get_size().height,760)
        row=self.w.list.get_row_at_index(0);self.assertTrue(any(isinstance(c,self.gui.Poster) for c in row.get_child().get_children()))

    def test_home_uses_real_totals_and_returns_to_the_same_port_with_back(self):
        from deck_library.models import Entry
        self.w.entries.extend([Entry('Port A',['/bin/true']),Entry('Port B',['/bin/true','b'])]);self.w.render();self.w.home_page();self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'home');self.assertEqual(self.w.home_counts['Juegos'].get_text(),'3');self.assertEqual(self.w.home_counts['Ports instalados'].get_text(),'2')
        entry=self.w.entries[-1];self.w.home_targets[entry.id].clicked();self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'detail')
        self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'home');self.assertIs(self.w.get_focus(),self.w.home_targets[entry.id])
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)
        self.w.last_controller_action=('',0);self.w.controller_action('next_tab');self.assertEqual(self.w.pages.get_visible_child_name(),'library')

    def test_home_remains_the_initial_page_when_the_window_is_first_mapped(self):
        from deck_library import gui_shell
        from gi.repository import Gtk
        with patch.object(gui_shell,'settings',return_value={**self.w.preferences,'start_page':'home'}):other=self.gui.Window()
        try:
            other.show_all();self.settle();self.assertEqual(other.pages.get_visible_child_name(),'home');self.assertEqual(other.home_counts['Juegos'].get_text(),'1')
        finally:other.disconnect_by_func(Gtk.main_quit);other.destroy();self.settle()

    def test_an_existing_install_without_a_start_page_opens_the_complete_library(self):
        from deck_library import gui_shell
        from gi.repository import Gtk
        preferences={k:v for k,v in self.w.preferences.items() if k!='start_page'}
        with patch.object(gui_shell,'settings',return_value=preferences):other=self.gui.Window()
        try:
            other.show_all();self.settle();self.assertEqual(other.pages.get_visible_child_name(),'library')
        finally:other.disconnect_by_func(Gtk.main_quit);other.destroy();self.settle()

    def test_home_shows_all_ports_in_portrait_and_mouse_wheel_keeps_working(self):
        from gi.repository import Gtk,Gdk
        from deck_library.models import Entry
        self.w.entries.extend(Entry('Port '+str(i),['/bin/true',str(i)]) for i in range(12))
        self.w.home_page();self.settle();self.settle()
        self.assertEqual(len(self.w.home_targets),12)
        for card in self.w.home_targets.values():
            cover=card.get_child().get_children()[0]
            self.assertAlmostEqual(cover.get_allocated_width()/cover.get_allocated_height(),2/3,delta=.01)
        scroll=self.w.home_box.get_ancestor(Gtk.ScrolledWindow);adjustment=scroll.get_vadjustment()
        self.assertEqual(adjustment.get_value(),0)
        event=Gdk.Event.new(Gdk.EventType.SCROLL);event.direction=Gdk.ScrollDirection.DOWN;event.window=scroll.get_window();event.set_device(Gdk.Display.get_default().get_default_seat().get_pointer())
        scroll.emit('scroll-event',event);self.settle();self.assertGreater(adjustment.get_value(),0)
        position=adjustment.get_value();self.w.home_page();self.settle();self.settle()
        self.assertAlmostEqual(adjustment.get_value(),position,delta=1)
        self.w.open_library();self.settle();self.w.home_page();self.settle()
        self.assertEqual(adjustment.get_value(),0)

    def test_port_cards_show_the_original_disc_id_without_opening_details(self):
        import time
        from deck_library import ports
        from gi.repository import Gtk
        self.w.catalog_page();self.w.catalog_apps=[ports.clean(ports.BUILTIN[0])];self.w.catalog_search.set_text('SLUS-00875')
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):
            self.w.fill_catalog();self.settle()
            # SearchEntry may emit its debounced change after this explicit fill.
            # Wait for the replacement card's allocation before inspecting its image.
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                rows=self.w.catalog_rows.get_children()
                if rows and rows[0].catalog_image.get_allocated_height()>=140:break
                self.settle()
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        self.assertTrue(any('SLUS-00875' in value for value in labels(self.w.catalog_rows)))
        row=self.w.catalog_rows.get_children()[0];self.assertGreaterEqual(row.catalog_image.get_allocated_height(),140)

    def test_deck_text_and_primary_actions_fit_at_readable_sizes(self):
        from gi.repository import Gtk,Gdk,Pango
        self.w.resize(1280,800);self.settle()
        font=self.w.library_count.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        pixels=font.get_size()/Pango.SCALE
        if not font.get_size_is_absolute():pixels*=max(96,Gdk.Screen.get_default().get_resolution())/72
        self.assertGreaterEqual(pixels,15)
        for control in self.w.navigation_controls:
            x,y=control.translate_coordinates(self.w,0,0)
            self.assertGreaterEqual(x,0);self.assertLessEqual(x+control.get_allocated_width(),1280)
            self.assertGreaterEqual(control.get_allocated_height(),36)
        self.w.select_game(self.w.entries[0]);self.settle()
        self.assertGreaterEqual(self.w.game_play_button.get_allocated_height(),44)
        for card in self.w.profile_cards[:3]:
            viewport=card.get_ancestor(Gtk.ScrolledWindow);point=card.translate_coordinates(viewport,0,0)
            self.assertGreaterEqual(point[1],0)
            self.assertLessEqual(point[1]+card.get_allocated_height(),viewport.get_allocated_height())

    def test_compact_profiles_keep_full_details_behind_a_controller_disclosure(self):
        from gi.repository import Gtk
        self.w.resize(1280,800);self.w.select_game(self.w.entries[0]);self.settle()
        self.assertEqual(len(self.w.profile_card_box.get_children()),3)
        self.assertTrue(all(card.get_allocated_height()<=150 for card in self.w.profile_cards[:3]))
        disclosure=self.w.profile_disclosure
        self.assertFalse(disclosure.revealer.get_reveal_child())
        with patch('deck_library.presets.apply',side_effect=AssertionError('Preview must not apply settings')):
            disclosure.control.grab_focus();self.w.last_controller_action=('',0);self.w.controller_action('activate');self.settle()
            self.assertTrue(disclosure.revealer.get_child_revealed())
            def labels(widget):
                if isinstance(widget,Gtk.Label):yield widget
                if isinstance(widget,Gtk.Container):
                    for child in widget.get_children():yield from labels(child)
            self.assertTrue(any(l.get_mapped() and l.get_text()==self.w.profile_selection['objective'] for l in labels(disclosure)))
            self.w.profile_cards[1].clicked();self.settle()
            self.assertFalse(disclosure.revealer.get_reveal_child())
            disclosure.control.clicked();self.settle()
            self.assertTrue(any(l.get_text()==self.w.profile_selection['objective'] for l in labels(disclosure)))
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)
        x,y=self.w.profile_apply.translate_coordinates(self.w,0,0)
        self.assertLessEqual(y+self.w.profile_apply.get_allocated_height(),640)

    def test_coloured_compatibility_badges_keep_the_percentage_and_readable_contrast(self):
        from gi.repository import Gtk
        from deck_library.gui_catalog import compatibility_badge
        self.w.reset_page(self.w.catalog_box);badges=[]
        for score,level in ((88,'alta'),(72,'media'),(50,'baja'),(8,'muy baja')):
            label=compatibility_badge({'score':score,'level':level});self.w.catalog_box.pack_start(label,False,False,0);badges.append(label)
            self.assertIn(str(score)+'%',label.get_text())
        self.w.catalog_box.get_ancestor(Gtk.ScrolledWindow).show_all();self.w.pages.set_visible_child_name('catalog');self.settle()
        def luminance(color):
            values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in (color.red,color.green,color.blue)]
            return .2126*values[0]+.7152*values[1]+.0722*values[2]
        backgrounds=[]
        for label in badges:
            style=label.get_style_context();fg=style.get_color(Gtk.StateFlags.NORMAL);bg=style.get_background_color(Gtk.StateFlags.NORMAL)
            bright,dark=sorted((luminance(fg),luminance(bg)),reverse=True)
            self.assertGreaterEqual((bright+.05)/(dark+.05),4.5);self.assertGreater(bg.alpha,.99)
            backgrounds.append(bg.to_string())
        self.assertEqual(len(set(backgrounds)),4)

    def test_compatibility_guide_explains_the_score_inside_the_app(self):
        from gi.repository import Gtk,GLib
        self.w.catalog_page();self.settle();windows=self.application_windows();original=self.inline.run;seen=[]
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        def run(page):
            def check():
                content='\n'.join(labels(page))
                seen.append(self.application_windows()==windows and self.w.workflow_stack.get_visible_child() is page)
                seen.append(all(value in content for value in ('80–100%','55–79%','30–54%','0–29%','no es una probabilidad medida','No mide FPS','no se calibraron','+8','−15','180 días')))
                seen.append(self.w.get_size().width<=1280 and self.w.get_size().height<=800)
                self.w.last_controller_action=('',0);self.w.controller_action('back');return False
            GLib.timeout_add(120,check);return original(page)
        with patch.object(self.inline,'run',run):
            for width,height in ((1280,800),(840,640)):
                self.w.resize(width,height);self.settle();self.w.catalog_guide_button.grab_focus();self.w.catalog_guide_button.clicked();self.settle()
                self.assertFalse(self.w.inline_workflows);self.assertIs(self.w.get_focus(),self.w.catalog_guide_button)
                self.assertLessEqual(self.w.get_size().width,width);self.assertLessEqual(self.w.get_size().height,height)
        self.assertEqual(seen,[True]*6)
    def test_deck_game_sections_keep_the_full_width_and_visible_navigation(self):
        from gi.repository import Gtk
        self.w.resize(1280,800);self.w.select_game(self.w.entries[0]);self.settle()
        self.assertFalse(self.w.game_breadcrumb.get_mapped())
        self.assertTrue(self.w.compact_game_back.get_mapped())
        self.assertLess(self.w.game_header.get_allocated_height(),100)
        scroll=self.w.profile_cards[0].get_ancestor(Gtk.ScrolledWindow)
        self.assertGreater(scroll.get_allocated_width(),1180,'Presets must use the space previously occupied by the sidebar.')
        self.assertNotIn('options',self.w.game_section_controls)
        for section in ('controls','content','profiles'):
            control=self.w.game_section_controls[section];control.emit('clicked');self.settle()
            self.assertEqual(self.w.game_tab,section)
            self.assertTrue(control.get_style_context().has_class('active'))
            for tab in self.w.game_section_controls.values():
                self.assertTrue(tab.get_mapped())
                x,y=tab.translate_coordinates(self.w,0,0)
                self.assertGreaterEqual(x,0);self.assertLessEqual(x+tab.get_allocated_width(),1280)
                self.assertGreaterEqual(tab.get_allocated_height(),44)

    def test_pending_queue_does_not_open_restart_dialog(self):
        from deck_library.models import atomic_json
        atomic_json(self.store.root/'pending.json',{'ids':['one'],'account':'test'})
        with patch.object(self.gui.Gtk.Dialog,'run',side_effect=AssertionError('Unexpected modal restart prompt')):
            self.w.queue_done({'state':'pending','count':1});self.assertTrue(self.w.pending_bar.get_visible());self.assertIn('Pendiente',self.w.pending_label.get_text())
        self.w.updates_page();self.settle()
        self.assertTrue(self.w.pending_bar.get_mapped())
        self.assertFalse(any(child.get_style_context().has_class('banner') for child in self.w.updates_box.get_children()))
        self.w.open_library();self.settle();self.assertTrue(self.w.pending_bar.get_mapped())
        (self.store.root/'pending.json').unlink();self.w.refresh_pending();self.assertFalse(self.w.pending_bar.get_visible())
    def test_dynamic_conflicts_keep_scroll_inside_dialog(self):
        from gi.repository import Gtk,GLib
        original=self.inline.run;sizes=[]
        def run(dialog):
            def capture():sizes.append(dialog.get_size());dialog.response(Gtk.ResponseType.CLOSE);return False
            GLib.timeout_add(300,capture);return original(dialog)
        rows=[{'title':'Coincidencia '+str(i),'note':'Revisar las rutas','paths':['/tmp/a','/tmp/b']} for i in range(50)]
        with patch('deck_library.conflicts.analyze',return_value=rows),patch.object(self.inline,'run',run):self.w.conflicts_page()
        self.assertLessEqual(sizes[0].height,760);self.assertLessEqual(sizes[0].width,1280)

    def test_long_confirmation_keeps_buttons_inside_screen(self):
        from gi.repository import Gtk,GLib
        original=self.inline.run;sizes=[]
        def run(dialog):
            def capture():sizes.append(dialog.get_size());dialog.response(Gtk.ResponseType.CANCEL);return False
            GLib.timeout_add(200,capture);return original(dialog)
        with patch.object(self.inline,'run',run):self.w.confirm('Vista previa','\n'.join('Opción: valor anterior → valor nuevo' for _ in range(80)))
        self.assertLessEqual(sizes[0].height,760)

    def test_game_profiles_are_inline_and_apply_with_the_visible_preview(self):
        from gi.repository import Gtk
        from deck_library import presets
        entry=self.w.entries[0]
        def buttons(widget):
            out=[widget] if isinstance(widget,Gtk.Button) else []
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():out.extend(buttons(child))
            return out
        with patch('deck_library.presets.preview',return_value=(pathlib.Path(self.temp.name)/'game.ini',[('Renderer.backend','0',1)])),patch('deck_library.presets.apply',return_value={'changes':1,'backup':'test'}) as apply,patch.object(self.inline,'run',side_effect=AssertionError('Unexpected modal profile selector')):
            self.w.show_detail(entry);self.w.pages.set_visible_child_name('detail');self.settle()
            self.assertFalse(any(isinstance(c,Gtk.StackSwitcher) for c in self.w.detail.get_children()))
            apply_button=next(b for b in buttons(self.w.detail) if b.get_label()=='Aplicar ajustes');self.assertTrue(apply_button.get_sensitive());apply_button.emit('clicked');self.settle();self.assertEqual(apply.call_count,1)
            self.assertEqual(self.w.pages.get_visible_child_name(),'detail')

    def test_profile_selection_is_read_only_and_apply_restore_round_trip(self):
        from deck_library import presets
        entry=self.w.entries[0]
        target=presets.target_for(entry,self.w.preferences['eden_config'])
        self.w.show_detail(entry);self.w.pages.set_visible_child_name('detail');self.settle()
        self.w.profile_cards[1].emit('clicked')
        self.assertFalse(target.exists())
        self.assertIn('performance',self.w.profile_selection['id'])
        with patch('deck_library.presets.busy',return_value=False):
            self.w.profile_apply.emit('clicked');self.settle()
            self.assertIn('use_asynchronous_shaders=true',target.read_text())
            self.assertFalse(self.w.profile_apply.get_sensitive())
            self.assertEqual(self.w.profile_apply.get_label(),'Aplicado')
            self.assertTrue(self.w.profile_restore.get_sensitive())
            self.w.profile_restore.emit('clicked')
        self.assertFalse(target.exists())
        self.assertTrue(self.w.profile_apply.get_sensitive())

    def test_apply_failure_stays_on_game_page_and_offers_retry(self):
        self.w.show_detail(self.w.entries[0]);self.w.pages.set_visible_child_name('detail')
        with patch('deck_library.presets.apply',side_effect=RuntimeError('El emulador está abierto')),patch.object(self.gui.Gtk.Dialog,'run',side_effect=AssertionError('Unexpected modal error')):
            self.w.profile_apply.emit('clicked');self.settle()
        self.assertIn('El emulador está abierto',self.w.profile_status.get_text())
        self.assertEqual(self.w.profile_apply.get_label(),'Reintentar')
        self.assertTrue(self.w.profile_apply.get_sensitive())
        self.assertTrue(all(card.get_sensitive() for card in self.w.profile_cards))

    def test_inherited_eden_settings_are_not_mistaken_for_an_applied_profile(self):
        from deck_library import presets
        entry=self.w.entries[0];profile=presets.recommended(entry,self.store)[0]
        target=presets.target_for(entry,self.w.preferences['eden_config']);target.parent.mkdir(parents=True)
        updates={section:{**values,**{key+'\\use_global':'true' for key in values}} for section,values in profile['settings'].items()}
        target.write_text(presets.patch_ini('',updates))
        self.w.select_game(entry)
        self.assertTrue(self.w.profile_apply.get_sensitive())
        self.assertNotEqual(self.w.profile_apply.get_label(),'Aplicado')

    def test_disclosure_and_game_tools_keep_primary_actions_inside_deck(self):
        from gi.repository import Gtk
        self.w.show_detail(self.w.entries[0]);self.w.pages.set_visible_child_name('detail');self.settle()
        for expanded in (True,False):
            self.w.profile_disclosure.control.emit('clicked');self.settle()
            self.assertEqual(self.w.profile_disclosure.revealer.get_reveal_child(),expanded)
            x,y=self.w.profile_apply.translate_coordinates(self.w,0,0)
            self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
            self.assertLessEqual(y+self.w.profile_apply.get_allocated_height(),760)
        for section in ('controls','files','content','options','profiles'):
            self.w.open_game_section(section);self.settle()
            self.assertEqual(self.w.game_pages.get_visible_child_name(),'content' if section=='files' else section)
            self.assertLessEqual(self.w.get_size().width,1280)
            self.assertLessEqual(self.w.get_size().height,760)

    def test_motion_reaches_a_settled_state_and_can_be_disabled(self):
        from gi.repository import Gtk,GLib
        from deck_library import motion
        Gtk.Settings.get_default().set_property('gtk-enable-animations',True)
        self.w.show_detail(self.w.entries[0]);self.w.pages.set_visible_child_name('detail')
        self.assertEqual(self.w.game_header.get_opacity(),0)
        self.settle();self.assertGreater(self.w.game_header.get_opacity(),0)
        self.settle();self.settle();self.assertEqual(self.w.game_header.get_opacity(),1)
        disclosure=self.w.profile_disclosure
        disclosure.control.emit('clicked');self.settle();self.settle()
        self.assertTrue(disclosure.revealer.get_child_revealed())
        Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
        motion.fade_in(self.w.game_header)
        self.assertEqual(self.w.game_header.get_opacity(),1)

    def test_background_refresh_keeps_unsaved_manual_options(self):
        from gi.repository import Gtk
        entry=self.w.entries[0]
        self.w.show_detail(entry);self.w.pages.set_visible_child_name('detail');self.w.open_game_section('options');self.settle()
        page=self.w.game_pages.get_visible_child()
        def switches(widget):
            if isinstance(widget,Gtk.Switch):return [widget]
            return [s for c in widget.get_children() for s in switches(c)] if isinstance(widget,Gtk.Container) else []
        control=switches(page)[0];control.set_active(not control.get_active())
        self.assertTrue(self.w.editor_dirty)
        self.w.show_detail(entry)
        self.assertIs(self.w.game_pages.get_visible_child(),page)
        with patch.object(self.w,'confirm',return_value=False):self.w.back_from_game()
        self.assertEqual(self.w.game_tab,'options')
        with patch.object(self.w,'confirm',return_value=True):self.w.back_from_game()
        self.assertEqual(self.w.game_tab,'profiles')

    def test_small_window_uses_compact_header_and_keeps_save_visible(self):
        self.w.resize(840,520);self.settle();self.settle()
        self.w.select_game(self.w.entries[0]);self.settle()
        self.assertLess(self.w.game_header.get_allocated_height(),100)
        for section in ('profiles','options','controls'):
            self.w.open_game_section(section);self.settle()
            self.assertLessEqual(self.w.get_size().width,840)
            self.assertLessEqual(self.w.get_size().height,520)

    def test_nested_game_sections_and_inline_workflows_flush_the_root_layout(self):
        from gi.repository import Gtk
        self.w.select_game(self.w.entries[0]);self.settle()
        with patch.object(self.w,'check_resize',wraps=self.w.check_resize) as resize:
            for section in ('controls','content','options','profiles'):
                self.w.open_game_section(section);self.settle()
                page=self.w.game_pages.get_visible_child()
                self.assertGreater(page.get_allocated_width(),100)
                self.assertGreater(page.get_allocated_height(),50)
                self.assertTrue(resize.called,'Nested section did not flush the fullscreen layout.')
                resize.reset_mock()
            page=self.inline(title='Validación de navegación',transient_for=self.w)
            page.add_button('Volver',Gtk.ResponseType.CLOSE);page.connect('response',lambda *_:page.destroy());page._mount();self.settle()
            self.assertTrue(resize.called);resize.reset_mock()
            self.w.controller_action('back');self.settle()
            self.assertFalse(self.w.inline_workflows);self.assertTrue(resize.called)

    def test_first_use_skip_is_remembered_and_guide_remains_accessible(self):
        from deck_library.installations import settings
        self.w.start_wizard();self.assertEqual(self.w.pages.get_visible_child_name(),'welcome')
        self.w.wizard_next();self.w.wizard_detection_ready({'emudeck':{'installed':False},'emulators':{},'prism':{}})
        self.assertTrue(self.w.wizard_checks);self.assertFalse(any(w.get_active() for w in self.w.wizard_checks.values()))
        self.w.leave_wizard(False);self.assertTrue(settings(self.store)['onboarding_complete']);self.assertTrue(settings(self.store)['onboarding_skipped'])
        self.w.open_library();self.w.help_page();self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'help');self.assertTrue(self.w.help_button.get_style_context().has_class('active'))
        self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertFalse(self.w.help_button.get_style_context().has_class('active'))
        self.w.settings_page();self.w.help_page();self.settle();self.w.leave_help();self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'settings')

    def test_validated_games_and_bug_report_fit_without_external_dialogs(self):
        from gi.repository import Gtk
        def widgets(root):
            yield root
            if isinstance(root,Gtk.Container):
                for child in root.get_children():yield from widgets(child)
        for width,height in ((1280,800),(840,640)):
            self.w.resize(width,height);self.settle();self.w.validated_page();self.settle()
            self.assertLessEqual(self.w.get_allocated_width(),width)
            self.assertEqual(self.w.pages.get_visible_child_name(),'validated');self.assertFalse(self.w.inline_workflows)
            captions=[w.get_text() for w in widgets(self.w.validated_box) if isinstance(w,Gtk.Label)]
            self.assertIn('Naruto: Rise of a Ninja',captions);self.assertIn('Mario Kart Wii',captions)
            self.w.bug_report_page(self.w.entries[0]);self.settle()
            page=self.w.inline_workflows[-1];controls=[w for w in widgets(page) if isinstance(w,Gtk.Button)]
            send=next(w for w in controls if w.get_label()=='Enviar diagnóstico');self.assertFalse(send.get_sensitive())
            entry=next(w for w in widgets(page.get_content_area()) if isinstance(w,Gtk.Entry));entry.set_text('Test problem')
            editors=[w for w in widgets(page.get_content_area()) if isinstance(w,Gtk.TextView)];editors[0].get_buffer().set_text('Open a game; expected play, actual error')
            next(w for w in controls if w.get_label()=='Preparar reporte').clicked();self.settle();self.assertTrue(send.get_sensitive())
            entry.set_text('Changed problem');self.assertFalse(send.get_sensitive())
            self.assertLessEqual(self.w.get_allocated_width(),width)
            page.response(Gtk.ResponseType.CLOSE);self.settle()

    def test_guide_link_opens_validated_tab_and_restores_navigation(self):
        self.w.help_page();self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'help');self.assertFalse(self.w.inline_workflows)
        self.w.nav_buttons['Verificados'].clicked();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
        self.assertTrue(all(c.get_sensitive() for c in self.w.navigation_controls))

    def test_validated_tab_supports_filtering_controller_tabs_and_back_from_a_game(self):
        from deck_library.models import Entry
        entry=Entry('Naruto: Rise of a Ninja',['/bin/true'],metadata={'port_repository':'jorjbarbosa/naruto-rise-recomp'})
        self.w.entries.append(entry);self.w.render();self.w.nav_buttons['Verificados'].clicked();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
        self.assertTrue(self.w.nav_buttons['Verificados'].get_style_context().has_class('active'))
        self.w.validated_search.set_text('does not exist');self.w.validated_search.emit('search-changed');self.settle()
        self.assertFalse(self.w.validated_targets[entry.id].get_mapped())
        self.w.validated_search.set_text('Naruto');self.w.validated_search.emit('search-changed');self.settle()
        self.assertTrue(self.w.validated_targets[entry.id].get_mapped());self.w.validated_targets[entry.id].clicked();self.settle()
        self.assertEqual(self.w.detail_origin,'validated');self.assertEqual(self.w.pages.get_visible_child_name(),'detail')
        self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
        self.assertIs(self.w.get_focus(),self.w.validated_targets[entry.id])
        with patch.object(self.w,'open_keyboard') as keyboard:
            self.w.last_controller_action=('',0);self.w.controller_action('search');self.settle();keyboard.assert_called_once_with(self.w.validated_search)
        self.w.validated_search.grab_focus()
        self.assertIs(self.w.get_focus(),self.w.validated_search)
        self.w.last_controller_action=('',0);self.w.controller_action('next_tab');self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'catalog')
        self.w.last_controller_action=('',0);self.w.controller_action('previous_tab');self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
        self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'library')

    def test_naruto_profiles_and_proton_selector_fit_the_game_page(self):
        from deck_library.models import Entry
        from deck_library import proton_selection,proton_tools
        root=pathlib.Path(self.temp.name);exe=root/'narutorise_launcher.exe';exe.write_bytes(b'MZ');(root/'narutorise.version').write_text('0.3.0-beta');(root/'narutorise.toml').write_text('renderer = "native"\nnative_backend = "vulkan"\nframe_rate = 60\n')
        entry=Entry('Naruto: Rise of a Ninja',['python3','-m','deck_library.port_runtime',str(root)],source=str(exe),platform='Windows',metadata={'port_repository':'jorjbarbosa/naruto-rise-recomp'})
        self.store.save([entry]);self.w.entries=[entry]
        tools={'Proton 11.0':root/'Proton 11.0/proton','Proton 9.0 (Beta)':root/'Proton 9.0 (Beta)/proton'}
        with patch.object(proton_tools,'installed',return_value=tools),patch.object(proton_selection,'default_tool',return_value=tools['Proton 11.0']),patch.object(proton_selection,'busy',return_value=False):
            for width,height in ((1280,800),(840,640)):
                self.w.resize(width,height);self.w.select_game(entry);self.w.open_game_section('content');self.settle()
                self.assertEqual(len(self.w.profile_cards),3)
                self.assertEqual(self.w.proton_combo.get_active_id(),'')
                self.w.proton_combo.set_active_id('Proton 9.0 (Beta)');self.assertTrue(self.w.proton_save_button.get_sensitive())
                control=self.w.proton_save_button
                self.assertFalse(control.caption.get_line_wrap())
                self.assertLessEqual(self.w.get_allocated_width(),width)
            self.w.proton_save_button.clicked();self.settle()
            self.assertEqual(self.store.load()[0].metadata['proton_version'],'Proton 9.0 (Beta)')
            self.assertFalse((self.store.root/'pending.json').exists())
            self.assertEqual(self.w.proton_combo.get_active_id(),'Proton 9.0 (Beta)')

    def test_steam_button_never_wraps_at_deck_and_compact_sizes(self):
        from deck_library.models import Entry,atomic_json
        entry=Entry('Naruto: Rise of a Ninja',['/bin/true'],platform='Xbox 360',kind='port')
        self.w.entries=[entry]
        for width,height in ((1280,800),(840,640)):
            self.w.resize(width,height);self.w.select_game(entry);self.settle()
            for pending in (False,True):
                if pending:atomic_json(self.store.root/'pending.json',{'ids':[entry.id]})
                else:(self.store.root/'pending.json').unlink(missing_ok=True)
                self.w.refresh_game_steam();self.settle()
                control=self.w.game_steam_button;caption=control.caption
                self.assertFalse(caption.get_line_wrap())
                self.assertEqual(caption.get_layout().get_line_count(),1)
                self.assertGreaterEqual(caption.get_allocated_width(),caption.get_layout().get_pixel_size()[0])
                point=control.translate_coordinates(self.w,0,0)
                self.assertLessEqual(point[0]+control.get_allocated_width(),self.w.get_allocated_width())

    def test_pending_steam_action_changes_the_button_without_another_prompt(self):
        from deck_library.models import atomic_json
        entry=self.w.entries[0];self.w.select_game(entry)
        self.assertEqual(self.w.game_steam_button.get_label(),'Agregar a Steam')
        atomic_json(self.store.root/'pending.json',{'ids':[entry.id]})
        self.w.refresh_pending()
        self.assertEqual(self.w.game_steam_button.get_label(),'Pendiente en Steam')
        with patch.object(self.w,'pending_details') as details,patch.object(self.w,'single_steam') as queue:
            self.w.game_steam_button.emit('clicked');details.assert_called_once();queue.assert_not_called()

    def test_deferred_apply_keeps_its_target_after_changing_games(self):
        from deck_library.models import Entry
        entry=self.w.entries[0];other=Entry('Otro juego',['/bin/true'],kind='emulated',platform='Switch',game_id='0100000000000001')
        self.w.select_game(entry)
        with patch('deck_library.presets.apply',return_value={'changes':1}) as apply:
            self.w.profile_apply.emit('clicked');self.w.select_game(other);self.settle()
        self.assertEqual(apply.call_args.args[0].id,entry.id)
        self.assertEqual(self.w.selected.id,other.id)
        self.assertNotIn('Ajustes guardados.',self.w.profile_status.get_text())
        self.assertTrue(self.w.profile_apply.get_sensitive())

    def test_favourites_and_recent_games_can_order_the_library(self):
        from deck_library import history
        from deck_library.models import Entry
        self.w.entries.extend([Entry('Zeta',['/bin/true','z']),Entry('alfa',['/bin/true','al'])]);zeta,alfa=self.w.entries[-2:]
        self.assertFalse(self.w.is_favorite(zeta));self.w.toggle_favorite(zeta);self.assertTrue(self.w.is_favorite(zeta))
        self.w.library_sort='favorites';self.assertEqual(self.w.visible()[0].name,'Zeta')
        history.record(self.store,alfa.id,now=500);self.w.library_sort='recent';self.assertEqual(self.w.visible()[0].name,'alfa')
        self.w.library_sort='name';names=[e.name.casefold() for e in self.w.visible()];self.assertEqual(names,sorted(names))
        self.w.toggle_favorite(zeta);self.assertFalse(self.w.is_favorite(zeta))

    def test_apply_and_play_applies_the_profile_then_opens_the_game(self):
        entry=self.w.entries[0];self.w.select_game(entry);self.settle()
        self.assertTrue(self.w.profile_apply_play.get_sensitive())
        with patch.object(self.w,'launch_from_game') as launch,patch.object(self.w,'offer_deck_controls'):
            self.w.profile_apply_play.emit('clicked');self.settle();self.settle()
        launch.assert_called_once();self.assertEqual(launch.call_args[0][0].id,entry.id)

    def test_home_offers_to_continue_with_the_games_opened_most_recently(self):
        from gi.repository import Gtk
        from deck_library import history
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        self.w.home_page();self.settle();self.assertNotIn('Continuar jugando',list(labels(self.w.home_box)))
        history.record(self.store,self.w.entries[0].id);self.w.home_page();self.settle();self.assertIn('Continuar jugando',list(labels(self.w.home_box)))

    def test_verified_games_show_their_fix_and_offer_to_request_a_game(self):
        from gi.repository import Gtk
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        self.w.validated_page();self.settle();texts=list(labels(self.w.pages.get_visible_child()))
        for expected in ('Grand Theft Auto IV','Spider-Man: Shattered Dimensions','Arreglo','Reportar un problema o hacer una solicitud','Lo aplica Deck Library'):self.assertIn(expected,texts)

    def test_a_game_request_explains_that_no_files_are_sent_and_shows_the_reference_number(self):
        from gi.repository import Gtk
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        with patch('deck_library.community.Client.request',return_value={'id':'abcd1234','received':True}) as request:
            page=self.w.request_game_page();self.settle();everything=list(walk(page.get_content_area()))
            texts=[w.get_text() for w in everything if isinstance(w,Gtk.Label)];self.assertIn('No adjuntar archivos ni enlaces de descarga de juegos.',texts)
            entry=next(w for w in everything if isinstance(w,Gtk.Entry));send=next(w for w in walk(page) if hasattr(w,'get_label') and not isinstance(w,Gtk.Label) and w.get_label()=='Enviar solicitud')
            send.emit('clicked');self.settle();request.assert_not_called();entry.set_text('Mi juego')
            next(w for w in everything if isinstance(w,Gtk.ComboBoxText) and w.get_accessible().get_name()=='Tipo de solicitud').set_active_id('emulated')
            next(w for w in everything if isinstance(w,Gtk.TextView)).get_buffer().set_text('No responde el mando')
            send.emit('clicked');self.settle();self.settle()
            sent=request.call_args[0];self.assertEqual(sent[0],'/v1/requests');self.assertEqual(sent[1]['title'],'Mi juego');self.assertEqual(set(sent[1]),{'title','platform','details','category','repository'});self.assertEqual(sent[1]['category'],'emulated')
            self.assertTrue(any('abcd1234' in w.get_text() for w in walk(page.get_content_area()) if isinstance(w,Gtk.Label)))
        page.response(Gtk.ResponseType.CLOSE);self.settle()

    def test_the_update_notice_can_be_closed_and_returns_only_when_it_changes(self):
        self.w.app_update_ready({'app':{'version':'99.0.0','notes':'x'}});self.settle();self.assertTrue(self.w.update_banner.get_mapped());self.assertTrue(self.w.banner_close.get_mapped())
        self.w.banner_close.clicked();self.settle();self.assertFalse(self.w.update_banner.get_visible())
        self.w.app_update_ready({'app':{'version':'99.0.0','notes':'x'}});self.settle();self.assertFalse(self.w.update_banner.get_visible())
        self.w.app_update_ready({'app':{'version':'99.1.0','notes':'x'}});self.settle();self.assertTrue(self.w.update_banner.get_mapped())

    def test_the_options_and_menu_buttons_open_the_library_filters_and_the_game_options(self):
        self.w.open_library();self.settle();self.assertFalse(self.w.filter_scroll.get_visible())
        self.w.last_controller_action=('',0);self.w.controller_action('menu');self.settle();self.assertTrue(self.w.filter_scroll.get_visible())
        self.w.last_controller_action=('',0);self.w.controller_action('options');self.settle();self.assertFalse(self.w.filter_scroll.get_visible())
        self.w.select_game(self.w.entries[0]);self.settle();self.w.last_controller_action=('',0);self.w.controller_action('options');self.settle()
        self.assertTrue(any(m.get_active() for m in self.w.game_menus))

    def test_tools_and_inline_pages_use_an_arrow_instead_of_a_back_button(self):
        from gi.repository import Gtk
        page=self.w.iso_extract_page();self.settle()
        self.assertTrue(page.back_button.get_visible());self.assertEqual(page.back_button.get_accessible().get_name(),'Volver')
        self.assertFalse(any(isinstance(b,Gtk.Button) and b.get_label()=='Volver' and b.get_visible() for b in page.actions.get_children()))
        page.back_button.clicked();self.settle();self.assertFalse(self.w.inline_workflows)

    def test_opening_a_game_starts_at_overview_and_focuses_play(self):
        entry=self.w.entries[0];self.w.select_game(entry);self.w.open_game_section('options');self.w.open_library();self.w.select_game(entry);self.settle()
        self.assertEqual(self.w.game_tab,'profiles')
        self.assertIs(self.w.get_focus(),self.w.game_play_button)
    def test_library_associates_the_original_without_removing_its_entry(self):
        from deck_library.models import Entry
        self.w.preferences['prefer_ports']=True
        self.w.entries=[Entry('Same',['a'],kind='port'),Entry('Same',['b'],kind='emulated',platform='Wii')]
        self.assertEqual(len(self.w.shown_entries()[0]),1)
        self.assertEqual(len(self.w.entries),2)
        self.w.preferences['unlinked_originals']=[self.w.entries[1].id]
        self.assertEqual(len(self.w.shown_entries()[0]),2)
        self.assertFalse(hasattr(self.w,'prefer_ports'))

    def test_associated_rom_badge_and_last_cover_fit_with_pending_changes(self):
        from gi.repository import Gtk
        from deck_library.models import Entry,atomic_json
        self.w.resize(1280,800);self.populate_games(40)
        rom=pathlib.Path(self.temp.name)/'owned.iso';rom.write_bytes(b'owned')
        port=Entry('ZZ Final Game',['port']);original=Entry(port.name,['emulator'],kind='emulated',platform='Wii',source=str(rom))
        self.w.entries.extend([port,original]);self.w.checked={original.id};atomic_json(self.store.root/'pending.json',{'ids':[port.id]});self.w.refresh_pending();self.w.render();self.settle();self.w.focus_library(port.id);self.settle()
        self.assertFalse(self.w.checked)
        self.assertNotIn(original.id,self.w.library_targets)
        visual=self.w.library_targets[port.id].library_focus_visual
        self.assertIn('ROM encontrada',[c.get_text() for c in visual.get_children() if isinstance(c,Gtk.Label)])
        scroll=self.w.library_stack.get_visible_child();position=visual.translate_coordinates(scroll,0,0)
        self.assertGreaterEqual(position[1],0);self.assertLessEqual(position[1]+visual.get_allocated_height(),scroll.get_allocated_height())
        self.w.platform_filter='Wii';self.assertEqual(self.w.visible(),[port])
        self.w.type_filter='emulator';self.assertEqual(self.w.visible(),[original])
        self.w.focus_library(original.id);self.settle()
        self.assertEqual(self.w.get_focus().library_entry_id,port.id)

    def test_install_and_prepare_workers_start_and_clear_their_progress(self):
        import threading,time
        from deck_library import ports
        from deck_library.models import atomic_json
        item=ports.clean({'repository':'K0NL/B2recomp'})
        record={**item,'configured':False,'executable':'B2recomp'}
        folder=pathlib.Path(self.temp.name)/'B2';folder.mkdir();(folder/'B2recomp').touch();record['install_path']=str(folder)
        with patch.object(ports,'install',return_value=record) as install,patch.object(self.w,'port_installed',return_value=False) as installed:
            self.w.install_port(item,False,location_chosen=True)
            until=time.monotonic()+3
            while not installed.called and time.monotonic()<until:self.settle()
            installed.assert_called_once();self.assertIsInstance(install.call_args.kwargs['cancel'],threading.Event)
        self.w.port_busy=False;self.w.port_jobs.clear()
        for setup in ('b2recomp','original_data','dante'):
            record.update(setup=setup);atomic_json(self.store.root/'ports.json',{item['repository']:record})
            with patch.object(ports,'requirements',return_value=[]),patch.object(ports,'configure',return_value={**record,'configured':True}) as configure:
                self.w.configure_port(item,automatic=True)
                until=time.monotonic()+3
                while self.w.port_busy and time.monotonic()<until:self.settle()
                configure.assert_called_once();self.assertFalse(self.w.port_busy);self.assertNotIn(item['repository'],self.w.port_jobs)
                self.assertIn('cancel',configure.call_args.kwargs)
                self.assertEqual(self.w.transfers[item['repository']].state['phase'],'done')

    def test_dante_install_requires_a_valid_original_before_preparing(self):
        from deck_library import ports
        from deck_library.models import atomic_json
        from test_dante_savage import xex
        from gi.repository import Gtk,GLib
        item=ports.clean({'repository':'florinp93/hells-gate-recomp','name':'Dante’s Inferno'})
        folder=pathlib.Path(self.temp.name)/'Dante';folder.mkdir();(folder/'dantes_inferno.exe').write_bytes(b'MZfixture')
        record={**item,'executable':'dantes_inferno.exe','tag':'test','install_path':str(folder)};atomic_json(self.store.root/'ports.json',{item['repository']:record})
        original=pathlib.Path(self.temp.name)/'own-dump';original.mkdir();xex(original/'default.xex')
        run_original=self.inline.run;seen=[];errors=[]
        def run(page):
            def check():
                try:
                    ready=page._buttons[Gtk.ResponseType.OK];seen.append(ready.get_sensitive())
                    controls=self.w.control_targets(page);names=[c.get_accessible().get_name() for c in controls]
                    self.assertIn('Elegir ISO de Xbox 360',names)
                    self.assertNotIn('Elegir ISO de Xbox',names)
                    next(c for c in controls if c.get_accessible().get_name()=='Elegir carpeta extraída').clicked()
                    seen.append(ready.get_sensitive())
                except Exception as e:errors.append(str(e))
                page.response(Gtk.ResponseType.CANCEL);return False
            GLib.timeout_add(150,check);return run_original(page)
        with patch.object(self.w,'pick_file',return_value=str(original)),patch.object(self.inline,'run',run),patch.object(ports,'configure') as configure,patch.object(self.w,'play') as play:
            self.w.port_installed(item,record);configure.assert_not_called();play.assert_not_called()
        self.assertEqual(errors,[]);self.assertEqual(seen,[False,True]);self.assertFalse(self.w.port_busy)
        self.assertEqual(self.w.transfers[item['repository']].state['phase'],'awaiting_input')

    def test_port_input_picker_validates_before_preparing_without_a_native_dialog(self):
        import hashlib
        from gi.repository import Gtk,GLib
        from deck_library import ports
        from deck_library.models import atomic_json
        rom=pathlib.Path(self.temp.name)/'outside.gba';rom.write_bytes(b'owned')
        record={'repository':'a/test','setup':'rom','rom':{'systems':['gba'],'sizes':[5],'sha1':{hashlib.sha1(b'owned').hexdigest():'baserom.gba'},'name':'Test'}}
        atomic_json(self.store.root/'ports.json',{'a/test':record});original_run=self.inline.run;seen=[];windows=self.application_windows()
        def run(page):
            def select():
                ready=page._buttons[Gtk.ResponseType.OK];seen.append(ready.get_sensitive())
                choose=next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Elegir ROM');choose.clicked()
                seen.append(ready.get_sensitive());page.response(Gtk.ResponseType.OK);return False
            GLib.timeout_add(200,select);return original_run(page)
        with patch.object(self.w,'pick_file',return_value=str(rom)),patch.object(self.inline,'run',run):self.assertTrue(self.w.port_inputs({'repository':'a/test','name':'Test'}))
        self.assertEqual(seen,[False,True]);self.assertEqual(self.application_windows(),windows)
        self.assertEqual(ports.records(self.store)['a/test']['inputs']['rom'],str(rom));self.assertEqual(rom.read_bytes(),b'owned')

    def test_naruto_iso_preparation_stays_inline_and_offers_the_right_original(self):
        from gi.repository import Gtk,GLib
        from deck_library import ports
        from deck_library.models import atomic_json
        item=ports.clean({'repository':'Auremana666/Naruto-The-Broken-Bond-PC-Port','name':'Naruto: The Broken Bond'})
        atomic_json(self.store.root/'ports.json',{item['repository']:item})
        iso=pathlib.Path(self.temp.name)/'owned.iso';data=bytearray(65636);data[65536:65554]=b'MICROSOFT*XBOX*MEDIA';iso.write_bytes(data)
        original_run=self.inline.run;seen=[];errors=[];windows=self.application_windows()
        def run(page):
            def choose():
                try:
                    ready=page._buttons[Gtk.ResponseType.OK];seen.append(ready.get_sensitive())
                    controls=self.w.control_targets(page);names=[c.get_accessible().get_name() for c in controls]
                    self.assertIn('Elegir carpeta extraída',names);self.assertNotIn('Elegir ISO de Xbox',names)
                    next(c for c in controls if c.get_accessible().get_name()=='Elegir ISO de Xbox 360').clicked()
                    seen.append(ready.get_sensitive())
                except Exception as error:errors.append(str(error))
                page.response(Gtk.ResponseType.OK);return False
            GLib.timeout_add(200,choose);return original_run(page)
        with patch.object(self.w,'pick_file',return_value=str(iso)) as choose_file,patch.object(self.inline,'run',run),patch.object(ports,'ports_root',return_value=pathlib.Path(self.temp.name)/'ports'):self.assertTrue(self.w.port_inputs(item))
        self.assertEqual(choose_file.call_args.kwargs['patterns'],('*.iso',));self.assertFalse(choose_file.call_args.kwargs['folder'])
        self.assertEqual(errors,[]);self.assertEqual(seen,[False,True]);self.assertEqual(self.application_windows(),windows)
        self.assertEqual(ports.records(self.store)[item['repository']]['inputs']['original_data'],str(iso));self.assertEqual(iso.read_bytes(),data)

    def test_naruto_rise_old_install_can_select_an_iso_inside_the_app(self):
        from gi.repository import Gtk,GLib
        from deck_library import ports
        from deck_library.models import atomic_json
        from test_iso_import import create_iso
        repo='jorjbarbosa/naruto-rise-recomp';item=ports.clean({'repository':repo,'name':'Naruto: Rise of a Ninja'})
        record={**item,'original_data':{**item['original_data']}};record['original_data'].pop('iso');record['original_data'].pop('extract_iso')
        atomic_json(self.store.root/'ports.json',{repo:record});iso=pathlib.Path(self.temp.name)/'owned.iso';create_iso(iso)
        original_run=self.inline.run;seen=[];errors=[];windows=self.application_windows()
        def run(page):
            def choose():
                try:
                    ready=page._buttons[Gtk.ResponseType.OK];seen.append(ready.get_sensitive());controls=self.w.control_targets(page)
                    names=[c.get_accessible().get_name() for c in controls];self.assertIn('Elegir carpeta extraída',names)
                    next(c for c in controls if c.get_accessible().get_name()=='Elegir ISO de Xbox 360').clicked();seen.append(ready.get_sensitive())
                except Exception as error:errors.append(str(error))
                page.response(Gtk.ResponseType.OK);return False
            GLib.timeout_add(200,choose);return original_run(page)
        with patch.object(self.w,'pick_file',return_value=str(iso)),patch.object(self.inline,'run',run),patch.object(ports,'ports_root',return_value=pathlib.Path(self.temp.name)/'ports'):self.assertTrue(self.w.port_inputs(item))
        self.assertEqual(errors,[]);self.assertEqual(seen,[False,True]);self.assertEqual(self.application_windows(),windows)
        self.assertEqual(ports.records(self.store)[repo]['inputs']['original_data'],str(iso))

    def test_iso_cleanup_stays_inline_and_deletes_only_after_explicit_confirmation(self):
        import time
        from gi.repository import Gtk,GLib
        from deck_library import ports,iso_import
        from deck_library.models import atomic_json
        from test_iso_import import create_iso
        root=pathlib.Path(self.temp.name);repo='jorjbarbosa/naruto-rise-recomp';item=ports.clean({'repository':repo,'name':'Naruto: Rise of a Ninja'})
        folder=root/'ports'/item['folder'];folder.mkdir(parents=True);iso=root/'owned.iso';create_iso(iso)
        record={**item,'configured':True,'inputs':{'original_data':str(iso)}};atomic_json(self.store.root/'ports.json',{repo:record})
        iso_import.prepare(folder,iso,record['original_data'],lambda _:None);(folder/'user').mkdir();(folder/'user/save').write_text('progress')
        original_mount=self.inline._mount;windows=self.application_windows()
        for mode in ('keep','decline','delete'):
            parent=self.inline(title='Port details',transient_for=self.w);parent.port_repository=repo;parent._mount();self.settle()
            errors=[];started=[False];deadline=time.monotonic()+5
            def mount(page):
                original_mount(page)
                def act():
                    if page._closed:return False
                    try:
                        if not started[0]:
                            started[0]=True
                            if mode!='keep':next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Eliminar ISO').clicked()
                        if mode=='delete' and getattr(self.w,'port_busy',False) and time.monotonic()<deadline:return True
                        if mode=='delete':self.assertFalse(iso.exists());self.assertFalse(self.w.port_busy)
                        else:self.assertTrue(iso.exists())
                    except Exception as error:errors.append(str(error))
                    page.response(Gtk.ResponseType.CLOSE);return False
                GLib.timeout_add(100,act)
            with patch.object(ports,'ports_root',return_value=root/'ports'),patch.object(self.w,'confirm',return_value=mode=='delete') as confirm,patch.object(self.inline,'_mount',mount):
                self.w.iso_cleanup_page(item)
                while self.w.inline_workflows and time.monotonic()<deadline:self.settle()
                self.assertFalse(self.w.inline_workflows)
                self.assertEqual(self.w.pages.get_visible_child_name(),'library')
                self.assertTrue(all(c.get_sensitive() for c in self.w.navigation_controls))
                self.assertEqual(confirm.call_count,0 if mode=='keep' else 1)
            self.assertEqual(errors,[]);self.assertEqual(self.application_windows(),windows);self.assertEqual(iso.exists(),mode!='delete')
        self.assertTrue((folder/'game/default.xex').is_file());self.assertEqual((folder/'user/save').read_text(),'progress')

    def exercise_full_iso_install_flow(self,delete):
        import io,time,zipfile
        from gi.repository import Gtk,GLib
        from deck_library import ports,project2099
        from test_iso_import import create_iso,xex
        root=pathlib.Path(self.temp.name);iso=root/'owned.iso';create_iso(iso)
        item=ports.clean({'repository':'jorjbarbosa/naruto-rise-recomp','name':'Naruto: Rise of a Ninja'});payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as archive:archive.writestr('narutorise_launcher.exe',b'MZfixture');archive.writestr('narutorise.exe',b'MZfixture')
        release={'tag_name':'test','assets':[{'name':'Naruto-win64.zip','browser_download_url':'https://github.com/owner/repo/test.zip'}]}
        original_mount=self.inline._mount;seen=[];errors=[];windows=self.application_windows()
        def mount(page):
            already_mounted=page._mounted;original_mount(page)
            if already_mounted:return
            def act():
                try:
                    def headings(widget):
                        yield widget
                        if isinstance(widget,Gtk.Container):
                            for child in widget.get_children():yield from headings(child)
                    title=next(child.get_text() for child in headings(page) if isinstance(child,Gtk.Label) and child.get_style_context().has_class('inline-page-heading'))
                    if title.startswith('Instalar '):
                        next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Descargar port').clicked();return False
                    if title.startswith('Preparar '):
                        seen.append('original');next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Elegir ISO de Xbox 360').clicked()
                        self.assertTrue(page._buttons[Gtk.ResponseType.OK].get_sensitive());page.response(Gtk.ResponseType.OK);return False
                    seen.append('cleanup');self.assertEqual(title,'Liberar espacio');self.assertTrue(iso.exists())
                    if delete:
                        next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Eliminar ISO').clicked()
                        deadline=time.monotonic()+4
                        def finish():
                            if self.w.port_busy and time.monotonic()<deadline:return True
                            if iso.exists():errors.append('ISO not removed after confirmation')
                            page.response(Gtk.ResponseType.CLOSE);return False
                        GLib.timeout_add(50,finish)
                    else:page.response(Gtk.ResponseType.CLOSE)
                except Exception as error:errors.append(str(error));page.response(Gtk.ResponseType.CLOSE)
                return False
            GLib.timeout_add(100,act)
        with patch.object(ports,'ports_root',return_value=root/'ports'),patch.object(ports,'release_for',return_value=release),patch.object(ports,'download',side_effect=lambda _,target,**kw:target.write_bytes(payload.getvalue())),patch.object(project2099,'proton_path',return_value=pathlib.Path('/fake/proton')),patch.object(self.w,'pick_file',return_value=str(iso)),patch.object(self.w,'confirm',return_value=True),patch.object(self.inline,'_mount',mount):
            self.w.install_port(item,False);deadline=time.monotonic()+5
            while ('cleanup' not in seen or getattr(self.w,'port_busy',False) or self.w.inline_workflows) and time.monotonic()<deadline:self.settle()
        self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertFalse(self.w.inline_workflows);self.assertTrue(all(c.get_sensitive() for c in self.w.navigation_controls))
        self.assertEqual(errors,[]);self.assertEqual(seen,['original','cleanup']);self.assertEqual(iso.exists(),not delete)
        record=ports.records(self.store)[item['repository']];self.assertTrue(record['configured'])
        self.assertEqual((root/'ports'/record['folder']/'game/default.xex').read_bytes(),xex());self.assertEqual(self.application_windows(),windows)

    def test_install_port_requests_the_iso_extracts_it_and_offers_keep_at_the_end(self):self.exercise_full_iso_install_flow(False)

    def test_install_port_can_remove_the_iso_only_after_the_final_cleanup_choice(self):self.exercise_full_iso_install_flow(True)

    def test_port_detail_offers_proton_as_an_explicit_alternative(self):
        from gi.repository import Gtk,GLib
        from deck_library import ports
        item=ports.clean({'repository':'a/test','name':'Test'})
        release={'assets':[{'name':'Test-linux-x64.zip'},{'name':'Test-win64.zip'}]};original_run=self.inline.run;seen=[]
        def run(page):
            def choose():
                buttons=self.w.control_targets(page);proton=next((c for c in buttons if c.get_accessible().get_name()=='Instalar con Proton'),None)
                seen.append(proton is not None)
                if proton:proton.clicked()
                else:page.response(Gtk.ResponseType.CLOSE)
                return False
            GLib.timeout_add(300,choose);return original_run(page)
        with patch.object(ports,'release_for',return_value=release),patch.object(ports,'icon_path',return_value=''),patch.object(self.w,'install_port') as install,patch.object(self.inline,'run',run):
            self.w.port_details(item);self.settle();install.assert_called_once();self.assertEqual(install.call_args.kwargs['runtime'],'proton')
        self.assertEqual(seen,[True])
    def test_pending_page_shows_the_operation_name_without_another_dialog(self):
        from gi.repository import Gtk
        from deck_library.models import atomic_json
        entry=self.w.entries[0];atomic_json(self.store.root/'pending.json',{'ids':[entry.id]})
        with patch.object(self.inline,'run',side_effect=AssertionError('Unexpected pending modal')):self.w.pending_details()
        self.assertEqual(self.w.pages.get_visible_child_name(),'pending')
        def labels(widget):
            result=[widget.get_text()] if isinstance(widget,Gtk.Label) else []
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():result.extend(labels(child))
            return result
        self.assertIn('Agregar acceso directo: '+entry.name,labels(self.w.pending_box))

    def test_tabs_reuse_cover_widgets_and_controller_navigation(self):
        from gi.repository import Gtk
        original_cards=list(self.w.covers.get_children())
        self.w.pages.set_visible_child_name('settings');self.w.open_library()
        self.assertEqual(original_cards,list(self.w.covers.get_children()))
        self.w.controller_action('next_tab');self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
        self.w.last_controller_action=('',0);self.w.controller_action('next_tab');self.assertEqual(self.w.pages.get_visible_child_name(),'catalog')
        self.w.controller_action('back');self.assertEqual(self.w.pages.get_visible_child_name(),'library')
        tile=self.w.covers.get_children()[0].get_child();button=next(c for c in tile.get_children() if isinstance(c,Gtk.Button))
        button.grab_focus();self.w.last_controller_action=('',0);self.w.controller_action('activate')
        self.assertEqual(self.w.pages.get_visible_child_name(),'detail')
        # A held button / Steam keyboard echo cannot trigger the newly focused Play button.
        with patch.object(self.w,'play',side_effect=AssertionError('Duplicate controller activation')):
            self.w.controller_action('activate')
        self.w.last_controller_action=('',0);self.w.controller_action('back');self.assertEqual(self.w.pages.get_visible_child_name(),'library',str((self.w.inline_workflows,self.w.game_tab,self.w.current_popover(self.w),Gtk.grab_get_current())))

    def test_library_refresh_allocates_new_covers_without_switching_pages(self):
        with patch.object(self.w,'check_resize',wraps=self.w.check_resize) as resize:
            self.populate_games(40)
            self.assertEqual(self.w.pages.get_visible_child_name(),'library')
            self.assertTrue(resize.called)
            for control in self.w.library_targets.values():
                self.assertGreater(control.get_allocated_width(),100)
                self.assertGreater(control.get_allocated_height(),100)

    def test_update_progress_is_measured_and_inline(self):
        self.w.update_state={'catalog':[{'name':'Test port','repository':'example/test','installed':'v1','latest':'v2'}]}
        self.w.updates_page();self.w.start_transfer('example/test');self.w.transfer_event('example/test',{'phase':'download','done':25,'total':100})
        box,bar,status=self.w.transfer_views['example/test'][0]
        self.assertTrue(box.get_visible());self.assertEqual(bar.get_fraction(),.25);self.assertIn('25%',status.get_text())
        self.assertIs(box.get_toplevel(),self.w)
        self.w.finish_transfer('example/test');self.assertEqual(bar.get_fraction(),1)

    def test_community_dialog_bounds_and_guided_publication(self):
        from gi.repository import Gtk,GLib
        from deck_library.community import Client
        original=self.inline.run;sizes=[];labels=[]
        def walk(widget):
            if isinstance(widget,Gtk.Button):labels.append(widget.get_label())
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():walk(child)
        def run(dialog):
            def capture():
                sizes.append(dialog.get_size());walk(dialog)
                stacks=[]
                def find(widget):
                    if isinstance(widget,Gtk.Stack):stacks.append(widget)
                    if isinstance(widget,Gtk.Container):
                        for child in widget.get_children():find(child)
                find(dialog)
                stack=stacks[0];self.assertEqual(stack.get_visible_child_name(),'publish')
                dialog.response(Gtk.ResponseType.CLOSE);return False
            GLib.timeout_add(200,capture);return original(dialog)
        with patch.object(Client,'search',return_value=[]),patch.object(self.inline,'run',run):self.w.community_dialog(self.w.entries[0],mode='publish')
        self.assertLessEqual(sizes[0].width,1280);self.assertLessEqual(sizes[0].height,760)
        self.assertIn('Revisar mis ajustes',labels);self.assertIn('Publicar perfil',labels)

    def test_manual_profile_review_survives_login_and_publishes_the_same_draft(self):
        from gi.repository import Gtk,GLib
        from deck_library import presets
        from deck_library.community import Client
        from deck_library.gui_account import AccountPane
        from deck_library.profile_composer import ProfileComposer
        original=self.inline.run;session={};errors=[];checked=[]
        def widgets(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from widgets(child)
        def run(dialog):
            def close():dialog.response(Gtk.ResponseType.CLOSE);return False
            def finish():
                try:
                    publish.assert_called_once();value=publish.call_args.args[0]
                    self.assertEqual(value['author'],'qa-user');self.assertEqual(value['instructions'],'Enable Vulkan before playing.')
                    self.assertTrue(any('Los demás usuarios ya pueden verlo' in w.get_text() for w in widgets(dialog) if isinstance(w,Gtk.Label)))
                    checked.append(True)
                except Exception as error:errors.append(error)
                return close()
            def edit():
                try:
                    composer=next(w for w in widgets(dialog) if isinstance(w,ProfileComposer))
                    composer.instructions.get_buffer().set_text('Enable Vulkan before playing.')
                    self.assertEqual(composer.profile()['id'],composer.profile()['id'])
                    controls={w.get_label():w for w in widgets(dialog) if isinstance(w,Gtk.Button)}
                    submit=controls['Publicar perfil'];self.assertFalse(submit.get_sensitive())
                    controls['Revisar mis ajustes'].clicked();self.assertTrue(submit.get_sensitive())
                    composer.notes.get_buffer().set_text('Tested with Vulkan.');self.assertFalse(submit.get_sensitive())
                    controls['Revisar mis ajustes'].clicked();submit.clicked()
                    stack=next(w for w in widgets(dialog) if isinstance(w,Gtk.Stack));self.assertEqual(stack.get_visible_child_name(),'account')
                    session['login']='qa-user';next(w for w in widgets(dialog) if isinstance(w,AccountPane)).on_change()
                    self.assertEqual(stack.get_visible_child_name(),'publish');self.assertEqual(composer.read(composer.instructions),'Enable Vulkan before playing.')
                    submit.clicked();GLib.timeout_add(250,finish)
                except Exception as error:errors.append(error);return close()
                return False
            timer=GLib.timeout_add(5000,close);GLib.timeout_add(200,edit)
            try:return original(dialog)
            finally:
                if GLib.MainContext.default().find_source_by_id(timer):GLib.source_remove(timer)
        with patch.object(presets,'export_current',side_effect=ValueError('No captured settings')),patch.object(Client,'session',side_effect=lambda:session),patch.object(Client,'search',return_value=[]),patch.object(Client,'publish',return_value={'status':'approved','id':'a'*32}) as publish,patch.object(self.inline,'run',run):
            self.w.community_dialog(self.w.entries[0],mode='publish')
        if errors:raise errors[0]
        self.assertTrue(checked,'Publication did not complete.')

    def test_community_internal_tabs_flush_layout_without_starting_login(self):
        from gi.repository import Gtk,GLib
        from deck_library.community import Client
        original=self.inline.run;checks=[];scroll_checks=[]
        def run(dialog):
            tabs=[]
            def find(widget):
                if isinstance(widget,Gtk.Stack):tabs.append(widget)
                if isinstance(widget,Gtk.Container):
                    for child in widget.get_children():find(child)
            find(dialog);stack=tabs[0];names=iter(('publish','account','browse'));last=[None]
            def next_page():
                if last[0] is not None:
                    page=stack.get_visible_child()
                    checks.append((last[0],resize.called,page.get_allocated_width(),page.get_allocated_height()))
                    if last[0]=='publish':
                        tab=next((c for c in self.w.control_targets(dialog) if c.get_accessible().get_name()=='Compartir mis ajustes'),None)
                        if tab:tab.grab_focus()
                        adjustment=page.get_children()[-1].get_vadjustment()
                        before=adjustment.get_value();self.w.controller_action('scroll_down')
                        scroll_checks.append((tab is not None,adjustment.get_upper()>adjustment.get_page_size(),adjustment.get_value()>before))
                name=next(names,None)
                if name is None:dialog.response(Gtk.ResponseType.CLOSE);return False
                resize.reset_mock();stack.set_visible_child_name(name);last[0]=name;return True
            GLib.timeout_add(120,next_page);return original(dialog)
        with patch.object(Client,'search',return_value=[]),patch.object(Client,'start') as login,patch.object(self.w,'check_resize',wraps=self.w.check_resize) as resize,patch.object(self.inline,'run',run):
            self.w.community_dialog(self.w.entries[0]);login.assert_not_called()
        self.assertEqual([v[0] for v in checks],['publish','account','browse'])
        for name,flushed,width,height in checks:
            self.assertTrue(flushed,name);self.assertGreater(width,100,name);self.assertGreater(height,50,name)
        self.assertEqual(scroll_checks,[(True,True,True)],'Right stick must scroll content while the tab is focused.')

    def test_catalog_recent_order_and_existing_ctr_alternative(self):
        from deck_library import ports
        from deck_library.models import Entry
        self.w.catalog_page();self.w.entries.append(Entry('Crash Team Racing: Turbocharged',['/bin/true']))
        old=ports.clean({'repository':'test/old','name':'Old'},source='Quiver actual');old['added_at']=100
        recent=ports.clean({'repository':'CTR-tools/ctr-native','name':'CTR Native'},source='Quiver actual');recent.update(added_at=200,game_title='Crash Team Racing')
        self.w.catalog_apps=[old,recent]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        record=self.w.catalog_installation(recent);self.assertTrue(record['alternative']);self.assertEqual(record['entry'].name,'Crash Team Racing: Turbocharged')
        self.assertEqual(self.w.catalog_sort.get_active_id(),'recent')
        self.w.resize(840,520);self.settle();self.assertLessEqual(self.w.get_size().width,840)

    def test_catalog_shows_and_searches_game_title_with_project_and_description(self):
        from deck_library import ports
        from gi.repository import Gtk
        self.w.catalog_page();item=ports.clean({'repository':'author/native','name':'Native Project','game_title':'Original Game','description':'A native port of the original game.'},source='Quiver actual');self.w.catalog_apps=[item]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):
            self.w.catalog_search.set_text('Original Game');self.w.fill_catalog();self.settle()
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        content=list(labels(self.w.catalog_rows))
        for text in ('Original Game','Native Project','A native port of the original game.'):self.assertIn(text,content)
        row=self.w.catalog_rows.get_children()[0];image=row.catalog_image
        self.assertEqual(image.get_storage_type(),Gtk.ImageType.ICON_NAME)
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)

    def test_catalog_click_opens_internal_details_without_installing(self):
        from deck_library import ports
        from gi.repository import Gtk,GLib
        item=ports.clean({'repository':'author/native','name':'GSRecomp','game_title':'Golden Sun','description':'Native adaptation.','category':'Game Boy Advance','supported_os':['linux'],'release_version':'v1.2'})
        self.w.catalog_page();self.w.catalog_apps=[item];self.w.catalog_search.set_text('Golden Sun')
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        open_=self.w.catalog_rows.get_children()[0].catalog_open;original=self.inline.run;seen=[]
        def run(page):
            def check():
                seen.append(self.w.workflow_stack.get_visible_child() is page)
                def labels(widget):
                    if isinstance(widget,Gtk.Label):yield widget.get_text()
                    if isinstance(widget,Gtk.Container):
                        for child in widget.get_children():yield from labels(child)
                content=list(labels(page))
                for text in ('Golden Sun','Port: GSRecomp','Native adaptation.','Versión disponible: v1.2'):seen.append(text in content)
                self.w.last_controller_action=('',0);self.w.controller_action('back');return False
            GLib.timeout_add(150,check);return original(page)
        with patch.object(self.inline,'run',run),patch.object(ports,'icon_path',return_value=''),patch.object(ports,'requirements',return_value=[]),patch.object(self.w,'install_port') as install:open_.clicked();install.assert_not_called()
        self.assertTrue(all(seen));self.assertEqual(len(seen),5);self.assertFalse(self.w.inline_workflows)

    def test_update_notes_and_options_are_reachable_with_the_controller(self):
        from gi.repository import Gtk
        self.w.update_state={'catalog':[{'name':'Test port','repository':'example/test','installed':'v1','latest':'v2','notes':'- First change\n- Second change\n- Third change\n- Fourth change'}]}
        self.w.updates_page();self.settle()
        targets=self.w.control_targets(self.w);expanders=[c for c in targets if isinstance(c,Gtk.Expander)]
        self.assertEqual(len(expanders),2);notes=next(c for c in expanders if 'v2' in c.get_label());self.assertFalse(notes.get_expanded())
        self.w.last_controller_action=('',0);notes.grab_focus();self.w.controller_action('activate');self.settle();self.assertTrue(notes.get_expanded())
        self.w.last_controller_action=('',0);self.w.controller_action('activate');self.settle();self.assertFalse(notes.get_expanded())
        def labels(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from labels(child)
        shown='\n'.join(labels(self.w.updates_box));self.assertIn('First change',shown);self.assertIn('Third change',shown)

    def test_a_signed_out_user_sees_a_register_or_sign_in_button_and_a_signed_in_one_sees_the_name(self):
        import json
        path=self.store.root/'community-session.json';path.unlink(missing_ok=True)
        self.w.refresh_account_button();self.assertEqual(self.w.account_button.get_label(),'Cuenta');self.assertIn('iniciar sesión',self.w.account_button.get_tooltip_text());self.assertFalse(self.w.signed_in())
        url=self.w.preferences.get('community_url','https://presets.jokerlan.xyz');path.write_text(json.dumps({'server':url,'token':'t','login':'jugador'}))
        self.w.refresh_account_button();self.assertEqual(self.w.account_button.get_label(),'jugador');self.assertTrue(self.w.signed_in())
        path.unlink()

    def test_game_names_show_a_tooltip_only_when_cut_and_never_with_a_controller(self):
        from gi.repository import Gtk
        from deck_library.ui_components import tooltip_when_cut
        label=Gtk.Label(label='Nombre muy corto');tooltip_when_cut(label,'Nombre muy corto')
        class Tip:
            text=''
            def set_text(self,value):self.text=value
        label.set_ellipsize(3);label.set_max_width_chars(4);window=Gtk.Window();window.add(label);window.show_all();self.settle()
        tip=Tip();self.assertTrue(label.tooltip_query(label,0,0,False,tip));self.assertEqual(tip.text,'Nombre muy corto')
        window.controller_mode=True;self.assertFalse(label.tooltip_query(label,0,0,False,Tip()))
        window.destroy()
        self.w.controller_mode=False;self.w.disable_tooltips();self.assertFalse(Gtk.Settings.get_default().get_property('gtk-enable-tooltips'));Gtk.Settings.get_default().set_property('gtk-enable-tooltips',True)

    def catalog_texts(self):
        from gi.repository import Gtk
        def walk(widget):
            if isinstance(widget,Gtk.Label):yield widget.get_text()
            if isinstance(widget,Gtk.Button) and widget.get_label():yield widget.get_label()
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        return list(walk(self.w.catalog_rows))

    def test_catalog_marks_review_state_and_offers_uninstall_and_all_games(self):
        from deck_library import ports
        from deck_library.models import atomic_json
        item=ports.clean({'repository':'OpenRA/OpenRA','name':'OpenRA','category':'PC','supported_os':['linux']});other=ports.clean({'repository':'someone/else','name':'Else','category':'PC'})
        atomic_json(self.store.root/'ports.json',{item['repository']:{**item,'executable':'x.AppImage','tag':'r1','verified':True}})
        self.w.catalog_page();self.w.catalog_apps=[item,other];self.w.catalog_search.set_text('')
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        joined='\n'.join(self.catalog_texts());self.assertIn('Desinstalar',joined);self.assertIn('Instalar todos los juegos',joined);self.assertIn('Integración revisada',joined);self.assertIn('Integración sin revisar',joined)

    def test_catalog_distinguishes_tested_versions_known_issues_and_other_installed_variants(self):
        from deck_library import ports,broken_bond
        from deck_library.models import Entry
        good=ports.clean({'repository':broken_bond.COMPATIBLE,'release_version':'v2.5'})
        old=ports.clean({'repository':broken_bond.ORIGINAL,'release_version':'v0.1.0-beta'})
        entry=Entry('Naruto: The Broken Bond',['/bin/true'],metadata={'port_repository':broken_bond.ORIGINAL,'port_tag':'v0.1.0-beta'})
        self.w.entries=[entry];self.w.catalog_page();self.w.catalog_apps=[good,old];self.w.catalog_search.set_text('Naruto: The Broken Bond')
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog();self.settle()
        captions=self.catalog_texts()
        for value in ('Verificado en Deck','Problema conocido · v0.1.0-beta','Otra variante instalada','Ver variante probada','2 variantes'):self.assertIn(value,captions)
        self.assertNotIn('Instalado · v0.1.0-beta',captions[:captions.index('Verificado en Deck')])
        self.w.catalog_search.set_text('BLACK');self.w.catalog_apps=[ports.clean({'repository':'tgp482/black-xberecomp','name':'BLACK'})]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog();self.settle()
        captions=self.catalog_texts();self.assertNotIn('Sin validar en Steam Deck',captions);self.assertIn('4 variantes',captions)
        self.assertFalse(any(value.startswith('Verificado en Deck') for value in captions))

    def test_variant_details_explain_installed_revision_and_offer_the_managed_migration(self):
        from deck_library import ports,broken_bond
        from deck_library.models import Entry,atomic_json
        from gi.repository import Gtk,GLib
        entry=Entry('Naruto: The Broken Bond',['/bin/true'],metadata={'port_repository':broken_bond.ORIGINAL,'port_tag':'v0.1.0-beta'})
        self.w.entries=[entry];self.store.save([entry]);atomic_json(self.store.root/'ports.json',{broken_bond.ORIGINAL:{'folder':'Old','tag':'v0.1.0-beta'}})
        item=ports.clean({'repository':broken_bond.ORIGINAL,'release_version':'v0.1.0-beta'});original=self.inline.run;seen=[]
        def run(page):
            def check():
                controls=self.w.control_targets(page);migration=next(c for c in controls if c.get_accessible().get_name()=='Cambiar a la variante probada')
                seen.append(migration.get_mapped());migration.grab_focus();self.w.controller_action('activate');return False
            GLib.timeout_add(200,check);return original(page)
        with patch.object(self.inline,'run',run),patch.object(ports,'icon_path',return_value=''),patch.object(ports,'requirements',return_value=[]),patch.object(ports,'release_for',return_value={'tag_name':'v0.1.0-beta','assets':[]}),patch.object(self.w,'repair_broken_bond') as repair:
            self.w.port_details(item);self.settle();repair.assert_called_once_with(entry)
        self.assertTrue(all(seen));self.assertFalse(self.w.inline_workflows)

    def test_known_problem_install_can_be_declined_without_downloading(self):
        from deck_library import ports,broken_bond
        item=ports.clean({'repository':broken_bond.ORIGINAL,'release_version':'v0.1.0-beta'})
        with patch.object(self.w,'confirm',return_value=False) as confirm,patch.object(ports,'install') as install:
            self.w.install_port(item,False,location_chosen=True);install.assert_not_called();self.assertEqual(confirm.call_args.args[0],'Problema conocido en esta versión')

    def test_old_broken_bond_offers_the_black_screen_repair_in_the_game_overview(self):
        from gi.repository import Gtk
        from deck_library.models import Entry
        from deck_library import broken_bond
        entry=Entry('Broken Bond',['/bin/true'],metadata={'port_repository':broken_bond.ORIGINAL})
        from deck_library.models import atomic_json
        atomic_json(self.store.root/'ports.json',{broken_bond.ORIGINAL:{'folder':'Old','tag':'v0.1.0-beta'}})
        self.store.save([entry]);self.w.entries=[entry]
        def widgets(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from widgets(child)
        for width,height in ((1280,800),(840,640)):
            self.w.resize(width,height);self.w.select_game(entry);self.settle()
            button=next(w for w in widgets(self.w.detail) if isinstance(w,Gtk.Button) and w.get_label()=='Corregir pantalla negra')
            button.grab_focus();self.w.reveal_focus(button);self.settle();self.assertTrue(button.get_mapped());self.assertLessEqual(self.w.get_allocated_width(),width)
            with patch.object(self.w,'confirm',return_value=False),patch.object(broken_bond,'repair') as repair:
                button.clicked();repair.assert_not_called()

    def test_iso_file_filter_keeps_folders_accepts_uppercase_and_can_show_all_files(self):
        from gi.repository import Gtk
        from deck_library.inline_pages import InlineFileChooser
        root=pathlib.Path(self.temp.name);(root/'subfolder').mkdir()
        for name in ('game.iso','GAME.ISO','notes.txt','game.zip'):(root/name).write_text('fixture')
        page=InlineFileChooser(title='Elegir ISO',transient_for=self.w,patterns=('*.iso',),filter_name='ISO (*.iso)');page.load(root);page._mount();self.settle()
        visible={row.path.name for row in page.files.get_children()};self.assertEqual(visible,{'subfolder','game.iso','GAME.ISO'})
        page.path.set_text(str(root/'notes.txt'));page.open_path();page.response(Gtk.ResponseType.OK)
        self.assertIsNone(page._answer);self.assertIn('filtro',page.status.get_text())
        page.file_filter.set_active_id('all');self.assertIn('notes.txt',{row.path.name for row in page.files.get_children()})
        page.response(Gtk.ResponseType.CANCEL);page.destroy();self.assertFalse(self.w.inline_workflows)

    def test_permanent_removal_has_a_visible_red_header_button_and_cancellation_preserves_the_port(self):
        from gi.repository import Gtk
        from deck_library import ports
        from deck_library.models import Entry,atomic_json
        root=pathlib.Path(self.temp.name)/'ports';folder=root/'sample';folder.mkdir(parents=True);(folder/'game').write_bytes(b'\x7fELF')
        record={'repository':'test/sample','name':'Sample port','folder':'sample','executable':'game'};atomic_json(folder/'.deck-library-port.json',record);atomic_json(self.store.root/'ports.json',{'test/sample':record})
        entry=Entry('Sample port',[str(folder/'game')],source=str(folder/'game'),id=ports.port_id('test/sample'),metadata={'port_repository':'test/sample'})
        self.store.save([entry]);self.w.entries=[entry];self.w.select_game(entry);self.w.open_game_section('files');self.settle()
        def widgets(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from widgets(child)
        button=self.w.game_delete_button
        self.assertTrue(button.get_mapped());self.assertEqual(button.get_label(),'Eliminar');self.assertTrue(button.get_style_context().has_class('danger'))
        button.clicked();self.settle();page=self.w.inline_workflows[-1]
        choices=[w for w in widgets(page) if isinstance(w,Gtk.Button) and (w.get_accessible().get_name() or '').startswith('Juego y datos ·')]
        self.assertEqual(len(choices),1)
        with patch.object(ports,'ports_root',return_value=root),patch.object(self.w,'confirm',return_value=False) as confirm:
            choices[0].clicked();confirm.assert_called_once();self.assertIn('partidas',confirm.call_args.args[1]);self.assertIn(str(folder),confirm.call_args.args[1]);self.assertTrue(confirm.call_args.kwargs['danger']);self.assertTrue(folder.is_dir())
        with patch.object(ports,'ports_root',return_value=root),patch.object(self.w,'confirm',return_value=True):
            self.w.delete_game_data(entry)
            import time
            deadline=time.monotonic()+3
            while self.w.port_busy and time.monotonic()<deadline:self.settle()
        self.assertFalse(self.w.port_busy);self.assertFalse(folder.exists());self.assertFalse(self.store.load());self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertFalse(self.w.inline_workflows)

    def test_library_only_removal_can_be_cancelled_hidden_and_restored_without_deleting_data(self):
        from gi.repository import Gtk
        from deck_library.installations import settings
        entry=self.w.entries[0];self.w.select_game(entry);self.settle()
        self.w.game_delete_button.clicked();self.settle();self.w.controller_action('back');self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.w.shown_entries()[0],[entry])
        self.w.game_delete_button.clicked();self.settle();page=self.w.inline_workflows[-1]
        choice=next(c for c in self.w.control_targets(page) if (c.get_accessible().get_name() or '').startswith('Solo de la biblioteca ·'))
        choice.clicked();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertEqual(self.w.shown_entries()[0],[])
        self.assertEqual(self.store.load(),[entry]);self.assertIn(entry.id,settings(self.store)['hidden_entries'])
        self.w.hidden_games_dialog();self.settle();page=self.w.inline_workflows[-1]
        restore=next(c for c in self.w.control_targets(page) if c.get_accessible().get_name()=='Restaurar');restore.clicked();self.settle()
        self.assertEqual(self.w.shown_entries()[0],[entry]);self.assertNotIn(entry.id,settings(self.store)['hidden_entries'])
        page.destroy()

    def test_delete_button_fits_deck_and_compact_screens_without_wrapping(self):
        entry=self.w.entries[0]
        for width,height in ((1280,800),(840,640)):
            self.w.resize(width,height);self.w.select_game(entry);self.settle()
            button=self.w.game_delete_button;self.assertTrue(button.get_mapped());self.assertFalse(button.caption.get_line_wrap())
            x,y=button.translate_coordinates(self.w,0,0)
            self.assertGreaterEqual(x,0);self.assertLessEqual(x+button.get_allocated_width(),width)
            self.assertLessEqual(self.w.get_size().width,width)

    def test_an_unreviewed_port_asks_once_before_installing(self):
        from deck_library import ports
        item=ports.clean({'repository':'someone/else','name':'Else','category':'PC'})
        with patch.object(ports,'install',side_effect=ValueError('stop')) as install,patch.object(self.w,'confirm',return_value=False) as confirm,patch.object(self.w,'port_failed'):
            self.w.install_port(item,False,location_chosen=True);confirm.assert_called_once();install.assert_not_called();self.assertFalse(self.w.preferences.get('unreviewed_acknowledged'))
        import time
        with patch.object(ports,'install',side_effect=ValueError('stop')) as install,patch.object(self.w,'confirm',return_value=True) as confirm,patch.object(self.w,'port_failed') as failed:
            self.w.install_port(item,False,location_chosen=True);until=time.monotonic()+3
            while not failed.called and time.monotonic()<until:self.settle()
            confirm.assert_called_once();self.assertTrue(self.w.preferences.get('unreviewed_acknowledged'))
        self.w.port_busy=False;self.w.port_jobs.clear()
        with patch.object(ports,'install',side_effect=ValueError('stop')),patch.object(self.w,'confirm') as confirm,patch.object(self.w,'port_failed') as failed:
            self.w.install_port(item,False,location_chosen=True);until=time.monotonic()+3
            while not failed.called and time.monotonic()<until:self.settle()
            confirm.assert_not_called()
        self.w.port_busy=False;self.w.port_jobs.clear()

    def test_catalog_artwork_is_displayed_from_the_downloaded_image(self):
        from gi.repository import GdkPixbuf,Gtk
        self.w.catalog_generation=1;path=pathlib.Path(self.temp.name)/'cover.png';pixbuf=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,60,90);pixbuf.fill(0xff0000ff);pixbuf.savev(str(path),'png',[],[])
        image=Gtk.Image();self.w.show_icon(image,str(path),1);self.assertEqual(image.get_storage_type(),Gtk.ImageType.PIXBUF);self.assertGreater(image.get_pixbuf().get_height(),0)

    def test_community_profiles_are_visible_without_a_disclosure(self):
        import time
        from deck_library import presets
        from gi.repository import Gtk
        entry=self.w.entries[0];profile={**presets.recommended(entry,self.store)[0],'id':'player-profile'};self.w.community_rating_cache={entry.id:(time.monotonic(),[{'id':'shared-1','preset':profile,'author':'Player','rating':4.5,'ratings':2}])}
        self.w.select_game(entry);self.settle();panel=self.w.community_profile_box
        self.assertTrue(panel.get_mapped());self.assertEqual(len(panel.get_children()),1);self.assertIsNone(panel.get_ancestor(Gtk.Revealer))
        self.assertGreater(len(self.w.profile_cards),3)
        self.assertIsNotNone(self.w.profile_cards[-1].get_ancestor(Gtk.Revealer))  # saved/generic alternatives have their own explanation
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)

    def test_transfer_cancel_and_error_dismiss_are_inline(self):
        import threading
        key='test/game';self.w.update_state={'catalog':[{'name':'Game','repository':key,'installed':'v1','latest':'v2'}]};self.w.updates_page();event=threading.Event();self.w.port_jobs={key:event};self.w.start_transfer(key)
        box,_,_=self.w.transfer_views[key][0];self.assertEqual(box.transfer_control.get_label(),'Cancelar');box.transfer_control.clicked();self.assertTrue(event.is_set())
        self.w.port_jobs.pop(key);self.w.finish_transfer(key,'No hay archivo Linux');self.assertEqual(box.transfer_control.get_label(),'Descartar');box.transfer_control.clicked();self.assertFalse(box.get_visible())

    def test_project2099_update_is_actionable(self):
        self.w.update_state={'project2099':{'name':'Project-2099','repository':'GenryTheFox0/Project-2099','installed':'v4','latest':'v5','notes':''}}
        self.w.updates_page()
        from gi.repository import Gtk
        def controls(widget):
            if isinstance(widget,Gtk.Button):yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from controls(child)
        action=next(b for b in controls(self.w.updates_box) if b.get_label()=='Actualizar')
        with patch.object(self.w,'update_project2099') as update:action.clicked();update.assert_called_once()

    def test_portrait_canvas_has_no_side_bands(self):
        import cairo
        from unittest.mock import Mock
        from gi.repository import GdkPixbuf
        poster=self.gui.Poster(self.w.entries[0],'');poster.pixbuf=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,200,100);poster.pixbuf.fill(0xff0000ff)
        surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,160,240);poster.draw_poster(Mock(get_allocated_width=lambda:160,get_allocated_height=lambda:240),cairo.Context(surface));surface.flush()
        self.assertEqual(bytes(surface.get_data()[:4]),b'\x00\x00\xff\xff')

    def test_account_panel_is_native_and_does_not_start_access_automatically(self):
        from deck_library.gui_account import AccountPane
        from deck_library.community import Client
        client=Client(self.store,'https://presets.example.org')
        with patch.object(client,'start') as start:
            pane=AccountPane(client);pane.show_all();self.settle()
            self.assertTrue(pane.login.get_visible());self.assertTrue(pane.login.caption.get_visible());self.assertTrue(pane.register.get_visible());self.assertTrue(pane.register.caption.get_visible());self.assertFalse(pane.logout.get_visible());self.assertFalse(pane.cancel_button.get_visible());self.assertEqual(pane.stack.get_visible_child_name(),'intro');start.assert_not_called();pane.destroy()

    def test_account_pending_access_is_cancelled_with_controller(self):
        from deck_library.gui_account import AccountPane
        from deck_library.community import Client
        pane=AccountPane(Client(self.store,'https://presets.example.org'));pane.wait='pending';generation=pane.generation
        self.assertTrue(pane.handle_controller('back',self.w));self.assertIsNone(pane.wait);self.assertGreater(pane.generation,generation);self.assertIsNone(pane.timer);pane.destroy()

    def test_account_dialog_fits_small_deck_window(self):
        from deck_library.gui_account import account_dialog
        from gi.repository import Gtk,GLib
        self.w.resize(840,640);self.settle();sizes=[];original=self.inline.run
        def run(dialog):
            def capture():sizes.append(dialog.get_size());dialog.response(Gtk.ResponseType.CLOSE);return False
            GLib.timeout_add(200,capture);return original(dialog)
        with patch.object(self.inline,'run',run):account_dialog(self.w)
        self.assertLessEqual(sizes[0].width,840);self.assertLessEqual(sizes[0].height,640)

    def populate_games(self,count=20):
        from deck_library.models import Entry
        self.w.entries=[Entry('Juego %02d'%i,['/bin/true',str(i)],platform='Linux') for i in range(count)]
        self.w.render();self.settle();self.w.focus_library();self.settle()

    def test_controller_cards_highlight_move_and_restore_without_selecting(self):
        self.populate_games();first=self.w.entries[0].id;second=self.w.entries[1].id
        self.assertEqual(self.w.get_focus().library_entry_id,first)
        self.assertTrue(self.w.library_targets[first].get_parent().get_style_context().has_class('game-focused'))
        self.w.controller_action('right');self.settle();self.assertEqual(self.w.get_focus().library_entry_id,second)
        self.assertFalse(self.w.library_targets[first].get_parent().get_style_context().has_class('game-focused'))
        self.assertTrue(self.w.library_targets[second].get_parent().get_style_context().has_class('game-focused'));self.assertFalse(self.w.checked)
        self.w.controller_action('activate');self.w.controller_action('back');self.settle();self.assertEqual(self.w.get_focus().library_entry_id,second)
        self.w.render();self.settle();self.assertEqual(self.w.get_focus().library_entry_id,second)

    def test_controller_grid_vertical_movement_and_auto_scroll(self):
        self.populate_games(35);first=self.w.entries[0].id
        self.w.controller_action('down');self.settle();focus=self.w.get_focus();self.assertNotEqual(focus.library_entry_id,first)
        x0,y0=self.w.library_targets[first].translate_coordinates(self.w.covers,0,0);x,y=focus.translate_coordinates(self.w.covers,0,0)
        self.assertGreater(y,y0);self.assertLess(abs(x-x0),3)
        last=self.w.entries[-1].id;self.w.focus_library(last);self.settle();scroll=self.w.library_stack.get_visible_child();adjustment=scroll.get_vadjustment()
        self.assertGreater(adjustment.get_value(),0)
        point=self.w.library_targets[last].translate_coordinates(scroll.get_child().get_child(),0,0)
        self.assertLessEqual(point[1]+self.w.library_targets[last].get_allocated_height(),adjustment.get_value()+adjustment.get_page_size()+1)

    def test_right_stick_scrolls_without_changing_focus(self):
        self.populate_games(30);first=self.w.get_focus();scroll=self.w.library_stack.get_visible_child();adjustment=scroll.get_vadjustment();before=adjustment.get_value()
        self.w.controller_action('scroll_down');self.settle();self.assertGreater(adjustment.get_value(),before);self.assertIs(self.w.get_focus(),first)
        for _ in range(7):self.w.last_controller_action=('',0);self.w.controller_action('scroll_down');self.settle()
        focus=self.w.get_focus();point=focus.translate_coordinates(scroll.get_child().get_child(),0,0);self.assertGreater(point[1]+focus.get_allocated_height(),adjustment.get_value());self.assertLess(point[1],adjustment.get_value()+adjustment.get_page_size())

    def test_controller_list_focus_is_visible_and_survives_filters(self):
        self.w.view='list';self.populate_games(10);first=self.w.entries[0].id
        self.w.controller_action('down');self.settle();self.assertEqual(self.w.get_focus().library_entry_id,self.w.entries[1].id)
        self.assertTrue(self.w.get_focus().get_style_context().has_class('game-focused'))
        self.w.search.set_text('Juego 00');self.settle();self.w.focus_library();self.assertEqual(self.w.get_focus().library_entry_id,first);self.assertFalse(self.w.checked)
        self.w.controller_action('activate');self.assertEqual(self.w.pages.get_visible_child_name(),'detail')

    def test_real_sdl_sticks_move_cards_and_scroll(self):
        import ctypes as C,time
        from deck_library.gamepad import SDL,Repeater
        self.populate_games(30)
        try:driver=SDL()
        except OSError as error:self.skipTest(str(error))
        lib=driver.lib;joystick=None;index=-1
        signatures=[('SDL_JoystickAttachVirtual',[C.c_int,C.c_int,C.c_int,C.c_int],C.c_int),('SDL_JoystickOpen',[C.c_int],C.c_void_p),('SDL_JoystickSetVirtualAxis',[C.c_void_p,C.c_int,C.c_int16],C.c_int),('SDL_JoystickSetVirtualButton',[C.c_void_p,C.c_int,C.c_uint8],C.c_int),('SDL_JoystickDetachVirtual',[C.c_int],C.c_int),('SDL_JoystickClose',[C.c_void_p],None)]
        try:
            for name,args,result in signatures:
                if not hasattr(lib,name):self.skipTest('SDL virtual-controller support unavailable')
                function=getattr(lib,name);function.argtypes=args;function.restype=result
            index=lib.SDL_JoystickAttachVirtual(1,6,15,0);self.assertGreaterEqual(index,0)
            joystick=lib.SDL_JoystickOpen(index);pad=lib.SDL_GameControllerOpen(index);self.assertTrue(pad)
            # Open only our virtual pad; do not consume a physical controller.
            driver.pads[lib.SDL_JoystickGetDeviceInstanceID(index)]=pad
            repeat=Repeater()
            def read():driver.enumerated=time.monotonic();return driver.read()
            first=self.w.get_focus().library_entry_id
            lib.SDL_JoystickSetVirtualAxis(joystick,0,14000)
            actions=read();self.assertIn('right',actions)
            for action in repeat.events(actions,0):self.w.controller_action(action)
            self.settle();self.assertNotEqual(self.w.get_focus().library_entry_id,first);focused=self.w.get_focus()
            lib.SDL_JoystickSetVirtualAxis(joystick,0,0);repeat.events(read(),.1)
            lib.SDL_JoystickSetVirtualAxis(joystick,3,22000)
            actions=read();self.assertIn('scroll_down',actions)
            for action in repeat.events(actions,.2):self.w.controller_action(action)
            self.settle();self.assertIs(self.w.get_focus(),focused);self.assertGreater(self.w.library_stack.get_visible_child().get_vadjustment().get_value(),0)
            chosen=focused.library_entry_id;lib.SDL_JoystickSetVirtualAxis(joystick,3,0);repeat.events(read(),.3)
            lib.SDL_JoystickSetVirtualButton(joystick,0,1)
            for action in repeat.events(read(),.4):self.w.controller_action(action)
            self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'detail');self.assertTrue(self.w.game_play_button.get_style_context().has_class('controller-focus'))
            lib.SDL_JoystickSetVirtualButton(joystick,0,0);repeat.events(read(),.5);lib.SDL_JoystickSetVirtualButton(joystick,1,1)
            for action in repeat.events(read(),.6):self.w.controller_action(action)
            self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertEqual(self.w.get_focus().library_entry_id,chosen)
        finally:
            if joystick:lib.SDL_JoystickClose(joystick)
            if index>=0:lib.SDL_JoystickDetachVirtual(index)
            driver.close()

    def test_detail_controls_keep_the_focus_marker_and_circle_goes_back(self):
        self.populate_games(5);chosen=self.w.entries[1].id;self.w.focus_library(chosen)
        self.w.controller_action('activate');self.settle()
        play=self.w.game_play_button;self.assertTrue(play.get_style_context().has_class('controller-focus'))
        self.w.controller_action('right');self.settle();focus=self.w.get_focus()
        self.assertIsNot(focus,play);self.assertTrue(focus.get_style_context().has_class('controller-focus'));self.assertFalse(play.get_style_context().has_class('controller-focus'))
        self.assertIn('B / ○',[item.get_children()[0].get_text() for item,_ in self.w.controller_hint.items.values()])
        self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertEqual(self.w.get_focus().library_entry_id,chosen)

    def test_profile_focus_survives_detail_refresh_and_section_back(self):
        self.w.controller_mode=True;entry=self.w.entries[0];self.w.select_game(entry);self.settle();self.assertTrue(self.w.profile_cards)
        profile=self.w.profile_cards[1];identifier=profile.profile_id;profile.grab_focus();self.settle();self.assertTrue(profile.get_style_context().has_class('controller-focus'))
        self.w.show_detail(entry);self.settle();self.assertEqual(self.w.get_focus().profile_id,identifier);self.assertTrue(self.w.get_focus().get_style_context().has_class('controller-focus'))
        self.w.open_game_section('files');self.settle();self.assertTrue(self.w.get_focus().get_style_context().has_class('controller-focus'))
        self.w.controller_action('back');self.settle();self.assertEqual(self.w.game_tab,'profiles');self.assertIs(self.w.get_focus(),self.w.game_play_button);self.assertTrue(self.w.get_focus().get_style_context().has_class('controller-focus'))

    def test_circle_closes_popover_before_leaving_game(self):
        from gi.repository import Gtk
        self.w.select_game(self.w.entries[0]);self.settle()
        controls=self.w.control_targets(self.w);menu=next(c for c in controls if isinstance(c,Gtk.MenuButton))
        menu.grab_focus();menu.clicked();self.settle();popover=menu.get_popover();self.assertTrue(popover.get_mapped())
        items=self.w.control_targets(popover);self.assertGreater(len(items),1);items[0].grab_focus();self.w.controller_action('down');self.settle();self.assertIs(self.w.get_focus(),items[1]);self.assertTrue(items[1].get_style_context().has_class('controller-focus'))
        self.w.controller_action('back');self.settle();self.assertFalse(popover.get_mapped());self.assertEqual(self.w.pages.get_visible_child_name(),'detail');self.assertIs(self.w.get_focus(),menu)

    def test_modal_controller_focus_badges_and_circle_cancel(self):
        from gi.repository import Gtk,GLib
        dialog=Gtk.Dialog(title='Prueba',transient_for=self.w,modal=True);dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE);button=Gtk.Button(label='Acción');dialog.get_content_area().pack_start(button,True,True,0)
        self.w.prepare_controller_window(dialog);dialog.show_all();button.grab_focus();self.settle()
        self.assertTrue(button.get_style_context().has_class('controller-focus'));self.assertTrue(dialog._deck_controller_hints.get_visible())
        GLib.idle_add(lambda:(self.w.controller_action('back',dialog),False)[1]);self.assertEqual(dialog.run(),Gtk.ResponseType.CANCEL);dialog.destroy()

    def application_windows(self):
        from gi.repository import Gtk
        # GTK may lazily allocate hidden tooltip/pop-up windows in headless sessions.
        return {window for window in Gtk.Window.list_toplevels() if window.get_visible() and window.get_window_type()==Gtk.WindowType.TOPLEVEL}

    def test_notice_is_an_internal_page_and_circle_restores_the_game_focus(self):
        from gi.repository import Gtk
        self.w.select_game(self.w.entries[0]);self.settle();focus=self.w.game_play_button;focus.grab_focus()
        windows=self.application_windows();self.w.message('Aviso','Detalle del cambio.');self.settle()
        page=self.w.inline_workflows[-1]
        self.assertNotIsInstance(page,Gtk.Window);self.assertIs(self.w.workflow_stack.get_visible_child(),page)
        self.assertEqual(self.application_windows(),windows)
        self.assertTrue(self.w.get_focus().get_style_context().has_class('controller-focus'))
        self.w.controller_action('back');self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertIs(self.w.workflow_stack.get_visible_child(),self.w.pages);self.assertIs(self.w.get_focus(),focus)

    def test_nested_inline_pages_restore_the_parent_without_changing_window_size(self):
        from gi.repository import Gtk,GLib
        import time
        self.w.resize(840,640);self.settle();until=time.monotonic()+3
        while tuple(self.w.get_size())!=(840,640) and time.monotonic()<until:self.settle()  # the window manager applies the resize asynchronously
        size=self.w.get_size();windows=self.application_windows()
        parent=self.inline(title='Carátulas',transient_for=self.w);parent.add_button('Volver',Gtk.ResponseType.CLOSE);parent._mount();self.settle()
        child=self.inline(title='Elegir archivo',transient_for=parent);child.add_button('Cancelar',Gtk.ResponseType.CANCEL)
        seen=[]
        def check():
            seen.append(self.w.workflow_stack.get_visible_child() is child);seen.append(self.application_windows()==windows);self.w.last_controller_action=('',0);self.w.controller_action('back');return False
        GLib.timeout_add(120,check);self.assertEqual(child.run(),Gtk.ResponseType.CANCEL);child.destroy();self.settle()
        self.assertEqual(seen,[True,True]);self.assertIs(self.w.workflow_stack.get_visible_child(),parent);self.assertEqual(self.w.get_size(),size)
        parent.destroy();self.assertFalse(self.w.inline_workflows)

    def test_confirmation_and_artwork_use_only_the_main_window(self):
        from gi.repository import Gtk,GLib
        from deck_library import cover_provider
        windows=self.application_windows();original=self.inline.run;seen=[]
        def run(page):
            def check():
                seen.append(self.w.workflow_stack.get_visible_child() is page and self.application_windows()==windows);page.response(Gtk.ResponseType.OK);return False
            GLib.timeout_add(100,check);return original(page)
        with patch.object(self.inline,'run',run),patch.object(cover_provider,'search',return_value=[]):
            self.assertTrue(self.w.confirm('Aplicar cambio','Detalle','Aplicar'));self.w.artwork_dialog(self.w.entries[0])
        self.assertEqual(seen,[True,True]);self.assertFalse(self.w.inline_workflows)

    def test_inline_file_browser_validates_files_folders_and_overwrite(self):
        from gi.repository import Gtk
        from deck_library.inline_pages import InlineFileChooser
        root=pathlib.Path(self.temp.name);file=root/'cover.png';file.write_bytes(b'image');folder=root/'games';folder.mkdir()
        page=InlineFileChooser(transient_for=self.w);page.load(root);page._mount();self.settle()
        page.response(Gtk.ResponseType.OK);self.assertIsNone(page._answer)
        page.open_row(page.files,next(row for row in page.files.get_children() if row.path==folder));self.assertEqual(page.folder,folder)
        page.load(root);row=next(row for row in page.files.get_children() if row.path==file);page.select(page.files,row);page.response(Gtk.ResponseType.OK);self.assertEqual(page.get_filename(),str(file));self.assertEqual(page._answer,Gtk.ResponseType.OK);page.destroy()
        page=InlineFileChooser(transient_for=self.w,action=Gtk.FileChooserAction.SAVE);page.load(root);page.set_current_name('cover.png');page.set_do_overwrite_confirmation(True);page._mount()
        with patch.object(self.w,'confirm',return_value=False):page.response(Gtk.ResponseType.OK)
        self.assertIsNone(page._answer)
        with patch.object(self.w,'confirm',return_value=True):page.response(Gtk.ResponseType.OK)
        self.assertEqual(page._answer,Gtk.ResponseType.OK);page.destroy()
        page=InlineFileChooser(transient_for=self.w,action=Gtk.FileChooserAction.SELECT_FOLDER);page.load(root)
        self.assertTrue(all(row.path.is_dir() for row in page.files.get_children()));page.response(Gtk.ResponseType.OK);self.assertEqual(page.get_filename(),str(root));page.destroy()

    def test_inline_busy_setup_cannot_be_closed_with_circle(self):
        from gi.repository import Gtk
        page=self.inline(title='Preparando',transient_for=self.w);page.add_button('Cerrar',Gtk.ResponseType.CLOSE);page.set_response_sensitive(Gtk.ResponseType.CLOSE,False);page._mount();self.settle()
        self.w.controller_action('back');self.assertIsNone(page._answer)
        page.set_response_sensitive(Gtk.ResponseType.CLOSE,True);self.w.last_controller_action=('',0);self.w.controller_action('back');self.assertEqual(page._answer,Gtk.ResponseType.CANCEL);page.destroy()

    def test_header_steam_action_uses_existing_queue_and_fits_compact_width(self):
        button=self.w.steam_library_button;self.assertEqual(button.get_label(),'Agregar a Steam');self.assertEqual(button.get_tooltip_text(),'Agregar Deck Library a Steam')
        with patch.object(self.w,'current_account',return_value=pathlib.Path('/tmp/steam/config')),patch.object(self.w,'run_queue') as queued:
            button.clicked();queued.assert_called_once()
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)

    def test_the_header_fits_the_deck_width_without_a_slider(self):
        from gi.repository import Gtk
        self.w.resize(1280,800);self.settle()
        scroll=self.w.nav_buttons['Ports'].get_ancestor(Gtk.ScrolledWindow);adjustment=scroll.get_hadjustment()
        self.assertLessEqual(adjustment.get_upper(),adjustment.get_page_size()+1)

    def test_launcher_error_does_not_block_library_and_opens_details_only_on_request(self):
        from deck_library.models import atomic_json
        path=self.store.root/'launch-notice.json';atomic_json(path,{'message':'Falta el ejecutable.'})
        self.w.poll_sync();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertFalse(path.exists());self.assertTrue(self.w.launch_notice_banner.get_mapped())
        self.assertTrue(all(c.get_sensitive() for c in self.w.navigation_controls))
        self.assertEqual(self.w.pages.get_visible_child_name(),'library')
        self.assertTrue((self.store.root/'last-launch-error.json').is_file());self.w.poll_sync();self.assertFalse(self.w.inline_workflows)
        self.w.launch_error_page();self.settle();self.assertEqual(len(self.w.inline_workflows),1)
        self.w.controller_action('back');self.settle();self.assertFalse(self.w.inline_workflows)
        dismiss=next(c for c in self.w.control_targets(self.w.launch_notice_banner) if c.get_accessible().get_name()=='Descartar aviso')
        dismiss.clicked();self.w.show_all();self.settle();self.assertFalse(self.w.launch_notice_banner.get_mapped())

    def test_previous_game_error_can_open_its_library_entry_and_stays_in_help(self):
        from deck_library.models import atomic_json
        entry=self.w.entries[0];value={'message':'Test game error','entry_id':entry.id,'game':entry.name,'time':1}
        atomic_json(self.store.root/'launch-notice.json',value);self.w.poll_sync();self.settle()
        self.assertIn(entry.name,self.w.launch_notice_label.get_text())
        self.w.help_page();self.settle()
        next(c for c in self.w.control_targets(self.w.pages.get_visible_child()) if c.get_accessible().get_name()=='Último error de un juego').clicked();self.settle()
        self.assertEqual(len(self.w.inline_workflows),1);details=self.w.inline_workflows[-1]
        next(c for c in self.w.control_targets(details) if c.get_accessible().get_name()=='Abrir juego en mi biblioteca').clicked();self.settle()
        self.assertFalse(self.w.inline_workflows);self.assertEqual(self.w.selected.id,entry.id)
        self.assertEqual(self.w.pages.get_visible_child_name(),'detail')
        self.assertTrue(all(c.get_sensitive() for c in self.w.navigation_controls))

    def test_initial_library_shows_the_configured_view(self):
        self.assertEqual(self.w.library_stack.get_visible_child_name(),self.w.view)

    def test_controller_cannot_activate_hidden_play_after_returning(self):
        self.w.select_game(self.w.entries[0]);self.settle();play=self.w.game_play_button
        self.w.open_library();play.grab_focus();self.w.last_controller_action=('',0)
        with patch.object(self.w,'play',side_effect=AssertionError('Hidden play activated')):self.w.controller_action('activate')
        self.assertEqual(self.w.pages.get_visible_child_name(),'library')

    def test_gaming_mode_switches_catalog_and_back_without_stack_snapshots(self):
        from gi.repository import Gtk,GLib
        from deck_library import ports,motion
        errors=[]
        handler=GLib.log_set_handler('Gtk',GLib.LogLevelFlags.LEVEL_CRITICAL,lambda domain,level,message,data:errors.append(message),None)
        try:
            with patch.dict(os.environ,{'SteamGameId':'12345'}):
                Gtk.Settings.get_default().set_property('gtk-enable-animations',True);self.w.apply_motion()
                Gtk.Settings.get_default().set_property('gtk-enable-animations',True)
                self.w.catalog_page();self.w.catalog_apps=[ports.clean({'repository':'test/game','name':'Game'})]
                with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
                for _ in range(3):
                    self.w.open_library();self.w.last_controller_action=('',0);self.w.controller_action('next_tab');self.settle()
                    self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
                    self.w.last_controller_action=('',0);self.w.controller_action('next_tab');self.settle()
                    self.assertEqual(self.w.pages.get_visible_child_name(),'catalog');self.assertTrue(self.w.catalog_rows.get_mapped());self.assertEqual(self.w.pages.get_transition_type(),Gtk.StackTransitionType.NONE)
                    self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library');self.assertTrue(self.w.covers.get_mapped())
                self.w.select_game(self.w.entries[0]);self.settle();self.w.open_game_section('files');self.settle();self.assertEqual(self.w.game_pages.get_transition_type(),Gtk.StackTransitionType.NONE)
                self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle();self.assertEqual(self.w.game_tab,'profiles')
                self.w.last_controller_action=('',0);self.w.controller_action('back');self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library')
                self.assertTrue(motion.enabled());self.assertFalse(motion.page_transitions())
            self.assertFalse(errors)
        finally:GLib.log_remove_handler('Gtk',handler)

    def test_gamepad_recovers_when_gtk_focus_is_lost_but_gamescope_keeps_app_active(self):
        from unittest.mock import Mock
        from gi.repository import Gtk
        from deck_library.gamepad import Driver,Repeater
        from deck_library import ports
        driver=Driver.__new__(Driver);driver.window=self.w;driver.sdl=Mock();driver.focus=Mock();driver.repeat=Repeater()
        self.w.catalog_page();self.w.catalog_apps=[ports.clean({'repository':'test/game','name':'Game'})]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        self.w.open_library();self.settle()
        with patch.object(Gtk.Window,'list_toplevels',return_value=[]):
            driver.focus.focused.return_value=True;driver.sdl.read.return_value={'next_tab'};driver.poll();self.settle()
            self.assertEqual(self.w.pages.get_visible_child_name(),'validated')
            driver.sdl.read.return_value=set();driver.poll();self.w.last_controller_action=('',0)
            driver.sdl.read.return_value={'next_tab'};driver.poll();self.settle()
            self.assertEqual(self.w.pages.get_visible_child_name(),'catalog')
            driver.sdl.read.return_value=set();driver.poll();self.w.last_controller_action=('',0)
            driver.sdl.read.return_value={'back'};driver.poll();self.settle();self.assertEqual(self.w.pages.get_visible_child_name(),'library')
            # Steam's own menu or another app must keep its input.
            driver.sdl.read.return_value=set();driver.poll();driver.focus.focused.return_value=False;driver.sdl.read.return_value={'next_tab'};driver.poll();self.assertEqual(self.w.pages.get_visible_child_name(),'library')
            driver.sdl.read.return_value=set();driver.poll();driver.focus.focused.return_value=None;driver.sdl.read.return_value={'next_tab'};driver.poll();self.assertEqual(self.w.pages.get_visible_child_name(),'library')

    def test_gaming_page_recovers_a_mapped_but_unallocated_viewport(self):
        from gi.repository import Gdk
        from deck_library import ports
        self.w.catalog_page();self.w.catalog_apps=[ports.clean({'repository':'test/game','name':'Game'})]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        self.settle();page=self.w.pages.get_visible_child()
        small=Gdk.Rectangle();small.width=small.height=1
        page.size_allocate(small)
        self.assertLessEqual(page.get_allocated_width(),1)
        self.w.pages.allocate_visible_page()
        self.assertEqual(page.get_allocated_width(),self.w.pages.get_allocated_width())
        self.assertEqual(page.get_allocated_height(),self.w.pages.get_allocated_height())

    def test_controller_poll_keeps_running_inside_a_port_details_workflow(self):
        import time
        from unittest.mock import Mock
        from gi.repository import Gtk,GLib
        from deck_library import ports
        from deck_library.gamepad import Driver,Repeater
        self.w.catalog_page();self.w.catalog_apps=[ports.clean({'repository':'example/native','name':'Native Game'})]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):self.w.fill_catalog()
        self.settle();self.w.catalog_rows.get_children()[0].catalog_open.grab_focus()
        driver=Driver.__new__(Driver);driver.window=self.w;driver.focus=Mock();driver.focus.focused.return_value=True;driver.repeat=Repeater();driver.sdl=Mock()
        state={'reads':0,'opened':None,'back':False,'closed':False,'timeout':False};loop=GLib.MainLoop()
        def read():
            state['reads']+=1
            if state['reads']==1:return {'activate'}
            if self.w.inline_workflows:
                if state['opened'] is None:state['opened']=time.monotonic()
                elif time.monotonic()-state['opened']>.15 and not state['back']:state['back']=True;return {'back'}
            elif state['opened'] is not None:state['closed']=True;loop.quit()
            return set()
        driver.sdl.read.side_effect=read
        def watchdog():
            state['timeout']=True
            for page in list(self.w.inline_workflows):page.cancel()
            loop.quit();return False
        poll=GLib.timeout_add(25,driver.poll);deadline=GLib.timeout_add(1800,watchdog)
        try:
            with patch.object(ports,'icon_path',return_value=''),patch.object(ports,'requirements',return_value=[]),patch.object(ports,'release_for',return_value={'assets':[]}):loop.run()
            self.assertFalse(state['timeout'],'The SDL timeout stopped delivering B while the port page ran its nested loop.')
            self.assertTrue(state['back']);self.assertTrue(state['closed']);self.assertFalse(self.w.inline_workflows);self.assertGreater(state['reads'],4)
        finally:
            for source in (poll,deadline):
                if GLib.MainContext.default().find_source_by_id(source):GLib.source_remove(source)

    def test_controller_timeout_recovers_from_a_callback_error(self):
        import io
        from unittest.mock import Mock
        from deck_library.gamepad import Driver
        driver=Driver.__new__(Driver);driver.window=self.w
        driver.poll_input=Mock(side_effect=[RuntimeError('temporary input failure'),True])
        with patch('sys.stderr',new_callable=io.StringIO) as log:
            self.assertTrue(driver.poll());self.assertIn('temporary input failure',log.getvalue());self.assertTrue(driver.poll())

    def test_unchanged_controller_focus_leaves_idle_callbacks_available(self):
        import time
        from unittest.mock import Mock
        from gi.repository import Gtk,GLib
        from deck_library.gamepad import Driver,Repeater
        driver=Driver.__new__(Driver);driver.window=self.w;driver.focus=Mock();driver.focus.focused.return_value=True;driver.repeat=Repeater();driver.sdl=Mock();driver.sdl.read.return_value=set()
        self.w.search.grab_focus();self.settle()
        loop=GLib.MainLoop();completed=[]
        def slow_tree_scan(*_):time.sleep(.045);return None
        def idle():completed.append(True);loop.quit();return False
        def start_idle():GLib.idle_add(idle);return False
        with patch.object(Gtk.Window,'list_toplevels',return_value=[]),patch.object(self.w,'current_popover',side_effect=slow_tree_scan) as scan:
            poll=GLib.timeout_add(25,driver.poll);start=GLib.timeout_add(80,start_idle);deadline=GLib.timeout_add(450,lambda:(loop.quit(),False)[1])
            try:
                loop.run()
                self.assertTrue(completed,'Controller polling starved catalog and button idle callbacks.')
                self.assertEqual(scan.call_count,0,'Unchanged focus must not scan the page at 40 Hz.')
            finally:
                for source in (poll,start,deadline):
                    if GLib.MainContext.default().find_source_by_id(source):GLib.source_remove(source)

    def test_portintegration_source_can_be_filtered_in_catalog(self):
        from deck_library import ports
        self.w.catalog_page();self.w.catalog_apps=[ports.clean({'repository':'source/one','name':'New game'},source='PortIntegration'),ports.clean({'repository':'source/two','name':'Existing game'},source='Quiver actual')]
        with patch.object(self.w,'load_icons'),patch.object(self.w,'check_kits'):
            self.w.fill_catalog();self.w.catalog_source.set_active_id('PortIntegration');self.settle()
        self.assertEqual(self.w.catalog_source.get_active_id(),'PortIntegration');self.assertEqual(len(self.w.catalog_rows.get_children()),1)
        self.assertEqual(self.w.catalog_rows.get_children()[0].catalog_open.get_accessible().get_name(),'Ver detalles de New game')

    def test_profile_composer_captures_edits_and_saves_without_login(self):
        from gi.repository import Gtk,GLib
        from deck_library.profile_composer import ProfileComposer
        from deck_library.community import Client
        from deck_library import presets
        config=pathlib.Path(self.temp.name)/'eden';config.mkdir(exist_ok=True);(config/'qt-config.ini').write_text('[Renderer]\nresolution_setup=3\n')
        original=self.inline.run;seen=[]
        def widgets(root):
            yield root
            if isinstance(root,Gtk.Container):
                for child in root.get_children():yield from widgets(child)
        def run(page):
            def check():
                try:
                    composer=next(w for w in widgets(page) if isinstance(w,ProfileComposer));self.assertIn('resolution_setup',composer.read(composer.settings))
                    composer.instructions.get_buffer().set_text('Usar Proton 9.0; comando de referencia: echo prueba')
                    composer.runtime.set_active_id('proton');composer.version.set_text('Proton 9.0')
                    composer.notes.get_buffer().set_text('Prueba local de la interfaz')
                    save=next(w for w in widgets(page) if isinstance(w,Gtk.Button) and w.get_label()=='Guardar localmente');save.clicked()
                    values=[v for v in presets.catalog(self.store) if v['author']=='Usuario']
                    self.assertEqual(len(values),1);self.assertIn('echo prueba',values[0]['instructions']);self.assertEqual(values[0]['runtime']['version'],'Proton 9.0')
                    self.assertLessEqual(page.get_size().width,1280);seen.append(True)
                finally:page.response(Gtk.ResponseType.CLOSE)
                return False
            GLib.timeout_add(250,check);return original(page)
        with patch.object(Client,'search',return_value=[]),patch.object(Client,'session',return_value={}),patch.object(Client,'publish') as publish,patch.object(self.inline,'run',run):
            self.w.community_dialog(self.w.entries[0],mode='publish');publish.assert_not_called()
        self.assertEqual(seen,[True])

    def test_manual_port_profile_shows_instructions_without_apply(self):
        from deck_library.models import Entry,atomic_json
        from deck_library import presets
        e=Entry('Native Port',['port']);value=presets.export_current(e,'Native Port — manual','Player',self.store);value['instructions']='Elegir pantalla completa en el juego.'
        atomic_json(self.store.root/'presets'/(value['id']+'.json'),value)
        self.w.entries.append(e);self.w.select_game(e);self.settle()
        self.assertFalse(self.w.profile_apply.get_sensitive());self.assertTrue(self.w.profile_disclosure.revealer.get_reveal_child())
        self.assertEqual(self.w.profile_disclosure.control.get_label(),'Ver instrucciones')

    def test_original_separation_and_reassociation_persist_from_ui(self):
        from gi.repository import Gtk,GLib
        from deck_library.models import Entry
        from deck_library.installations import settings
        port=Entry('Game',['port']);rom=pathlib.Path(self.temp.name)/'game.iso';rom.write_bytes(b'RMCP01')
        original=Entry('Game',['emulator'],kind='emulated',platform='Wii',source=str(rom));self.w.entries=[port,original];self.w.render()
        run_original=self.inline.run;seen=[]
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        def run(page):
            def check():
                try:
                    next(w for w in walk(page) if isinstance(w,Gtk.Button) and w.get_label()=='Mostrar ROM en la biblioteca').clicked()
                    self.assertEqual(len(self.w.visible()),2);self.assertIn(original.id,settings(self.store)['unlinked_originals'])
                    next(w for w in walk(page) if isinstance(w,Gtk.Button) and w.get_label()=='Ocultar ROM duplicada').clicked()
                    self.assertEqual(self.w.visible(),[port]);self.assertNotIn(original.id,settings(self.store)['unlinked_originals']);self.assertTrue(rom.exists());seen.append(True)
                finally:page.response(Gtk.ResponseType.CLOSE)
                return False
            GLib.timeout_add(200,check);return run_original(page)
        with patch.object(self.inline,'run',run):self.w.originals_dialog(port)
        self.assertEqual(seen,[True])

    def test_gaming_settings_also_hide_adding_the_app_to_steam(self):
        from gi.repository import Gtk
        from deck_library import motion
        def labels(root):
            result=[root.get_text()] if isinstance(root,Gtk.Label) else []
            if isinstance(root,Gtk.Container):
                for child in root.get_children():result.extend(labels(child))
            return result
        with patch.object(motion,'gaming_mode',return_value=True):self.w.tools_page()
        self.assertNotIn('Deck Library en Steam',labels(self.w.tools_box))
        with patch.object(motion,'gaming_mode',return_value=False):self.w.tools_page()
        self.assertIn('Deck Library en Steam',labels(self.w.tools_box))
        for expected in ('Convertir un juego de Switch','Extraer una ISO de Xbox o Xbox 360'):self.assertIn(expected,labels(self.w.tools_box))
        self.w.settings_page();self.assertNotIn('Deck Library en Steam',labels(self.w.settings_box));self.assertIn('Mantenimiento',labels(self.w.settings_box))

    def test_a_port_that_needs_an_update_asks_for_the_base_and_the_update_files(self):
        from gi.repository import Gtk
        from deck_library.gui_switch import minimum_for
        def labels(widget):
            result=[widget.get_text()] if isinstance(widget,Gtk.Label) else []
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():result.extend(labels(child))
            return result
        minimum=minimum_for('RevivedX/SavageWindRecomp');self.assertEqual(minimum['label'],'1.9.0');self.assertIsNone(minimum_for('k0nl/b2recomp'))
        page=self.w.switch_convert_page(minimum=minimum);self.settle();text=' '.join(labels(page))
        self.assertIn('1.9.0',text);self.assertIn('Actualización (si está en otro archivo)',text);self.assertIn('Juego (XCI o NSP)',text)
        page.destroy();page=self.w.switch_convert_page();self.settle();self.assertIn('Actualización (opcional)',' '.join(labels(page)));page.destroy()

    def test_async_community_results_receive_visible_row_allocations(self):
        from gi.repository import Gtk,GLib
        from deck_library import presets
        from deck_library.community import Client
        value={**presets.recommended(self.w.entries[0],self.store)[0],'id':'player-profile'}
        result={'id':'test','preset':value,'author':'Player','rating':None,'ratings':0}
        original=self.inline.run;seen=[]
        def rows(widget):
            if isinstance(widget,Gtk.ListBoxRow):yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from rows(child)
        def run(page):
            def check():
                try:
                    row=next(rows(page));self.assertTrue(row.get_mapped());self.assertGreater(row.get_allocated_width(),100);self.assertGreater(row.get_allocated_height(),40);seen.append(True)
                finally:page.response(Gtk.ResponseType.CLOSE)
                return False
            GLib.timeout_add(300,check);return original(page)
        with patch.object(Client,'search',return_value=[result]),patch.object(Client,'comments',return_value=[]),patch.object(self.inline,'run',run):self.w.community_dialog(self.w.entries[0])
        self.assertEqual(seen,[True])

    def test_deck_library_hides_secondary_filters_until_requested(self):
        self.assertFalse(self.w.filter_scroll.get_mapped());self.assertTrue(self.w.filter_toggle.get_mapped())
        for view in ('covers','list'):
            self.w.view=view;self.w.render();self.settle();self.w.focus_library(self.w.entries[0].id)
            self.w.last_controller_action=('',0);self.w.controller_action('up');self.settle()
            self.assertIs(self.w.get_focus(),self.w.search)
            self.w.last_controller_action=('',0);self.w.controller_action('right');self.settle()
            self.assertIs(self.w.get_focus(),self.w.filter_toggle)
        self.w.filter_toggle.clicked();self.settle();self.assertTrue(self.w.platform_picker.get_mapped())
        self.w.type_picker.set_active_id('port');self.settle();self.assertIn('1',self.w.filter_toggle.get_label())
        self.w.filter_toggle.clicked();self.settle();self.assertFalse(self.w.filter_scroll.get_mapped());self.assertIs(self.w.get_focus(),self.w.filter_toggle)

    def test_community_list_and_profile_use_full_width_and_circle_returns_to_list(self):
        from gi.repository import Gtk,GLib
        from deck_library import presets
        from deck_library.community import Client
        profile={**presets.recommended(self.w.entries[0],self.store)[0],'id':'player-profile'};value={'id':'test-profile','preset':profile,'author':'Player','rating':4.5,'ratings':2}
        original=self.inline.run;seen=[]
        def walk(widget):
            yield widget
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():yield from walk(child)
        def run(page):
            def check():
                try:
                    stack=next(w for w in walk(page) if isinstance(w,Gtk.Stack));row=next(w for w in walk(page) if isinstance(w,Gtk.ListBoxRow))
                    self.assertGreater(row.get_allocated_width(),1000);row.get_child().clicked()
                    self.assertEqual(stack.get_visible_child_name(),'profile')
                    use=next(w for w in walk(page) if isinstance(w,Gtk.Button) and w.get_label()=='Usar este perfil')
                    def back():
                        try:
                            self.assertTrue(use.get_mapped());x,y=use.translate_coordinates(self.w,0,0);self.assertGreaterEqual(y,0);self.assertLess(y+use.get_allocated_height(),self.w.get_allocated_height())
                            self.w.controller_action('back');self.assertEqual(stack.get_visible_child_name(),'browse');self.assertIn(page,self.w.inline_workflows);seen.append(True)
                        finally:page.response(Gtk.ResponseType.CLOSE)
                        return False
                    GLib.timeout_add(180,back)
                except Exception:
                    page.response(Gtk.ResponseType.CLOSE);raise
                return False
            GLib.timeout_add(250,check);return original(page)
        with patch.object(Client,'search',return_value=[value]),patch.object(Client,'comments',return_value=[]),patch.object(self.inline,'run',run):self.w.community_dialog(self.w.entries[0])
        self.assertEqual(seen,[True])
