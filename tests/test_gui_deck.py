"""Opt-in GTK checks: DECK_LIBRARY_UI_TESTS=1 python -m unittest discover -s tests -p test_gui_deck.py."""
import os,pathlib,tempfile,unittest
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('DECK_LIBRARY_UI_TESTS')=='1' and os.environ.get('DISPLAY'),'requires GTK and a disposable display')
class DeckUITests(unittest.TestCase):
    def setUp(self):
        from deck_library import gui,gui_shell
        from deck_library.installations import DEFAULTS
        from deck_library.models import Store,Entry
        self.gui=gui;self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
        self.store.save([Entry('Juego de prueba',['/bin/true'],kind='emulated',platform='Switch',source='/tmp/test.nsp',game_id='0100000000000000')])
        self.patches=[patch.object(gui_shell,'Store',return_value=self.store),patch.object(gui_shell,'settings',return_value={**DEFAULTS,'onboarding_complete':True,'check_updates':False,'artwork_provider':'off','animations':False,'eden_config':str(pathlib.Path(self.temp.name)/'eden')}),patch.object(gui.Window,'discover',return_value=False),patch.object(gui_shell,'find_accounts',return_value=[]),patch.object(gui_shell,'active_account',return_value=None)]
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
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_pages_stay_inside_deck_window_and_list_has_thumbnail(self):
        for page in ('covers','list','platforms'):
            self.w.view=page;self.w.render();self.settle();self.assertLessEqual(self.w.get_size().width,1280);self.assertLessEqual(self.w.get_size().height,760)
        row=self.w.list.get_row_at_index(0);self.assertTrue(any(isinstance(c,self.gui.Poster) for c in row.get_child().get_children()))
    def test_pending_queue_does_not_open_restart_dialog(self):
        from deck_library.models import atomic_json
        atomic_json(self.store.root/'pending.json',{'ids':['one'],'account':'test'})
        with patch.object(self.gui.Gtk.Dialog,'run',side_effect=AssertionError('Unexpected modal restart prompt')):
            self.w.queue_done({'state':'pending','count':1});self.assertTrue(self.w.pending_bar.get_visible());self.assertIn('Pendiente',self.w.pending_label.get_text())
        (self.store.root/'pending.json').unlink();self.w.refresh_pending();self.assertFalse(self.w.pending_bar.get_visible())
    def test_dynamic_conflicts_keep_scroll_inside_dialog(self):
        from gi.repository import Gtk,GLib
        original=Gtk.Dialog.run;sizes=[]
        def run(dialog):
            def capture():sizes.append(dialog.get_size());dialog.response(Gtk.ResponseType.CLOSE);return False
            GLib.timeout_add(300,capture);return original(dialog)
        rows=[{'title':'Coincidencia '+str(i),'note':'Revisar las rutas','paths':['/tmp/a','/tmp/b']} for i in range(50)]
        with patch('deck_library.conflicts.analyze',return_value=rows),patch.object(Gtk.Dialog,'run',run):self.w.conflicts_page()
        self.assertLessEqual(sizes[0].height,736);self.assertLessEqual(sizes[0].width,1280)

    def test_long_confirmation_keeps_buttons_inside_screen(self):
        from gi.repository import Gtk,GLib
        original=Gtk.Dialog.run;sizes=[]
        def run(dialog):
            def capture():sizes.append(dialog.get_size());dialog.response(Gtk.ResponseType.CANCEL);return False
            GLib.timeout_add(200,capture);return original(dialog)
        with patch.object(Gtk.Dialog,'run',run):self.w.confirm('Vista previa','\n'.join('Opción: valor anterior → valor nuevo' for _ in range(80)))
        self.assertLessEqual(sizes[0].height,736)

    def test_game_profiles_are_inline_and_apply_with_the_visible_preview(self):
        from gi.repository import Gtk
        from deck_library import presets
        entry=self.w.entries[0]
        def buttons(widget):
            out=[widget] if isinstance(widget,Gtk.Button) else []
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():out.extend(buttons(child))
            return out
        with patch('deck_library.presets.preview',return_value=(pathlib.Path(self.temp.name)/'game.ini',[('Renderer.backend','0',1)])),patch('deck_library.presets.apply',return_value={'changes':1,'backup':'test'}) as apply,patch.object(Gtk.Dialog,'run',side_effect=AssertionError('Unexpected modal profile selector')):
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
    def test_library_does_not_hide_an_emulator_copy_behind_a_port(self):
        from deck_library.models import Entry
        self.w.preferences['prefer_ports']=True
        self.w.entries=[Entry('Same',['a'],kind='port'),Entry('Same',['b'],kind='emulated',platform='Wii')]
        self.assertEqual(len(self.w.shown_entries()[0]),2)
        self.assertFalse(hasattr(self.w,'prefer_ports'))
    def test_pending_page_shows_the_operation_name_without_another_dialog(self):
        from gi.repository import Gtk
        from deck_library.models import atomic_json
        entry=self.w.entries[0];atomic_json(self.store.root/'pending.json',{'ids':[entry.id]})
        with patch.object(Gtk.Dialog,'run',side_effect=AssertionError('Unexpected pending modal')):self.w.pending_details()
        self.assertEqual(self.w.pages.get_visible_child_name(),'pending')
        def labels(widget):
            result=[widget.get_text()] if isinstance(widget,Gtk.Label) else []
            if isinstance(widget,Gtk.Container):
                for child in widget.get_children():result.extend(labels(child))
            return result
        self.assertIn('Agregar acceso: '+entry.name,labels(self.w.pending_box))
