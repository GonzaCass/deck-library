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
        self.patches=[patch.object(gui_shell,'Store',return_value=self.store),patch.object(gui_shell,'settings',return_value={**DEFAULTS,'onboarding_complete':True,'check_updates':False,'artwork_provider':'off','animations':False,'community_ratings':False,'eden_config':str(pathlib.Path(self.temp.name)/'eden')}),patch.object(gui.Window,'discover',return_value=False),patch.object(gui.Window,'load_catalog',return_value=None),patch.object(gui_shell,'find_accounts',return_value=[]),patch.object(gui_shell,'active_account',return_value=None)]
        for p in self.patches:p.start()
        from gi.repository import Gtk,Gdk
        provider=Gtk.CssProvider();provider.load_from_data(gui.CSS);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.w=gui.Window();self.w.resize(1280,760);self.w.show_all();self.settle()
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
    def test_deck_game_sections_keep_the_full_width_and_visible_navigation(self):
        from gi.repository import Gtk
        self.w.resize(1280,800);self.w.select_game(self.w.entries[0]);self.settle()
        self.assertFalse(self.w.game_breadcrumb.get_mapped())
        self.assertTrue(self.w.compact_game_back.get_mapped())
        self.assertLess(self.w.game_header.get_allocated_height(),100)
        scroll=self.w.profile_cards[0].get_ancestor(Gtk.ScrolledWindow)
        self.assertGreater(scroll.get_allocated_width(),1180,'Presets must use the space previously occupied by the sidebar.')
        for section in ('controls','content','options','profiles'):
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
            self.assertEqual(self.w.game_pages.get_visible_child_name(),section)
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

    def test_pending_steam_action_changes_the_button_without_another_prompt(self):
        from deck_library.models import atomic_json
        entry=self.w.entries[0];self.w.select_game(entry)
        self.assertEqual(self.w.game_steam_button.get_label(),'Agregar a Steam')
        atomic_json(self.store.root/'pending.json',{'ids':[entry.id]})
        self.w.refresh_pending()
        self.assertEqual(self.w.game_steam_button.get_label(),'Acceso pendiente')
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
        with patch.object(ports,'install',return_value=record) as install,patch.object(self.w,'port_installed',return_value=False) as installed:
            self.w.install_port(item,False)
            until=time.monotonic()+3
            while not installed.called and time.monotonic()<until:self.settle()
            installed.assert_called_once();self.assertIsInstance(install.call_args.kwargs['cancel'],threading.Event)
        self.w.port_busy=False;self.w.port_jobs.clear()
        for setup in ('b2recomp','original_data'):
            record.update(setup=setup);atomic_json(self.store.root/'ports.json',{item['repository']:record})
            with patch.object(ports,'requirements',return_value=[]),patch.object(ports,'configure',return_value={**record,'configured':True}) as configure:
                self.w.configure_port(item,automatic=True)
                until=time.monotonic()+3
                while self.w.port_busy and time.monotonic()<until:self.settle()
                configure.assert_called_once();self.assertFalse(self.w.port_busy);self.assertNotIn(item['repository'],self.w.port_jobs)
                self.assertEqual('cancel' in configure.call_args.kwargs,setup=='b2recomp')
                self.assertEqual(self.w.transfers[item['repository']].state['phase'],'done')

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
        self.assertIn('Agregar acceso: '+entry.name,labels(self.w.pending_box))

    def test_tabs_reuse_cover_widgets_and_controller_navigation(self):
        from gi.repository import Gtk
        original_cards=list(self.w.covers.get_children())
        self.w.pages.set_visible_child_name('settings');self.w.open_library()
        self.assertEqual(original_cards,list(self.w.covers.get_children()))
        self.w.controller_action('next_tab');self.assertEqual(self.w.pages.get_visible_child_name(),'catalog')
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
                        adjustment=page.get_vadjustment()
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
        self.w.refresh_account_button();self.assertEqual(self.w.account_button.get_label(),'Registrarse o iniciar sesión');self.assertFalse(self.w.signed_in())
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
        joined='\n'.join(self.catalog_texts());self.assertIn('Desinstalar',joined);self.assertIn('Instalar todos los juegos',joined);self.assertIn('Revisado',joined);self.assertIn('Sin revisar',joined)

    def test_an_unreviewed_port_asks_once_before_installing(self):
        from deck_library import ports
        item=ports.clean({'repository':'someone/else','name':'Else','category':'PC'})
        with patch.object(ports,'install',side_effect=ValueError('stop')) as install,patch.object(self.w,'confirm',return_value=False) as confirm,patch.object(self.w,'port_failed'):
            self.w.install_port(item,False);confirm.assert_called_once();install.assert_not_called();self.assertFalse(self.w.preferences.get('unreviewed_acknowledged'))
        import time
        with patch.object(ports,'install',side_effect=ValueError('stop')) as install,patch.object(self.w,'confirm',return_value=True) as confirm,patch.object(self.w,'port_failed') as failed:
            self.w.install_port(item,False);until=time.monotonic()+3
            while not failed.called and time.monotonic()<until:self.settle()
            confirm.assert_called_once();self.assertTrue(self.w.preferences.get('unreviewed_acknowledged'))
        self.w.port_busy=False;self.w.port_jobs.clear()
        with patch.object(ports,'install',side_effect=ValueError('stop')),patch.object(self.w,'confirm') as confirm,patch.object(self.w,'port_failed') as failed:
            self.w.install_port(item,False);until=time.monotonic()+3
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
        self.assertIsNone(self.w.profile_cards[-1].get_ancestor(Gtk.Revealer))
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
        button=self.w.steam_library_button;self.assertEqual(button.get_label(),'Añadir a Steam');self.assertEqual(button.get_tooltip_text(),'Añadir Deck Library a Steam')
        with patch.object(self.w,'current_account',return_value=pathlib.Path('/tmp/steam/config')),patch.object(self.w,'run_queue') as queued:
            button.clicked();queued.assert_called_once()
        self.w.resize(840,640);self.settle();self.assertLessEqual(self.w.get_size().width,840)

    def test_launcher_error_is_consumed_inside_the_application(self):
        from deck_library.models import atomic_json
        path=self.store.root/'launch-notice.json';atomic_json(path,{'message':'Falta el ejecutable.'})
        self.w.poll_sync();self.settle();self.assertEqual(len(self.w.inline_workflows),1);self.assertFalse(path.exists())
        self.w.poll_sync();self.assertEqual(len(self.w.inline_workflows),1)
        self.w.controller_action('back');self.settle();self.assertFalse(self.w.inline_workflows)

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
                    next(w for w in walk(page) if isinstance(w,Gtk.Button) and w.get_label()=='Mostrar separado').clicked()
                    self.assertEqual(len(self.w.visible()),2);self.assertIn(original.id,settings(self.store)['unlinked_originals'])
                    next(w for w in walk(page) if isinstance(w,Gtk.Button) and w.get_label()=='Asociar al port').clicked()
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
        with patch.object(motion,'gaming_mode',return_value=True):self.w.settings_page()
        self.assertNotIn('Deck Library en Steam',labels(self.w.settings_box))
        with patch.object(motion,'gaming_mode',return_value=False):self.w.settings_page()
        self.assertIn('Deck Library en Steam',labels(self.w.settings_box))

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
        self.w.filter_toggle.clicked();self.settle();self.assertFalse(self.w.filter_scroll.get_mapped());self.assertTrue(self.w.filter_toggle.has_focus())

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
