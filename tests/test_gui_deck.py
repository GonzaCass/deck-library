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

    def test_touch_drag_fallback_scrolls_and_leaves_short_taps_unclaimed(self):
        from gi.repository import Gtk
        from unittest.mock import Mock
        self.populate_games(40);scroll=self.w.library_stack.get_visible_child();adjustment=scroll.get_vadjustment();gesture=Mock()
        self.assertTrue(scroll.get_kinetic_scrolling());self.assertEqual(scroll._deck_drag.get_propagation_phase(),Gtk.PropagationPhase.CAPTURE)
        scroll._deck_drag_begin(gesture,50,200);scroll._deck_drag_update(gesture,2,-4);gesture.set_state.assert_not_called()
        scroll._deck_drag_update(gesture,0,-120);self.assertGreaterEqual(adjustment.get_value(),100);gesture.set_state.assert_called_once_with(Gtk.EventSequenceState.CLAIMED)

    def test_last_focused_cover_includes_its_caption_inside_the_viewport(self):
        self.populate_games(45);target=self.w.entries[-1].id;self.w.focus_library(target);self.settle()
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
                for text in ('Juego','Golden Sun','Port','GSRecomp','Native adaptation.','Versión disponible: v1.2'):seen.append(text in content)
                self.w.last_controller_action=('',0);self.w.controller_action('back');return False
            GLib.timeout_add(150,check);return original(page)
        with patch.object(self.inline,'run',run),patch.object(ports,'icon_path',return_value=''),patch.object(ports,'requirements',return_value=[]),patch.object(self.w,'install_port') as install:open_.clicked();install.assert_not_called()
        self.assertTrue(all(seen));self.assertEqual(len(seen),7);self.assertFalse(self.w.inline_workflows)

    def test_catalog_artwork_is_displayed_from_the_downloaded_image(self):
        from gi.repository import GdkPixbuf,Gtk
        self.w.catalog_generation=1;path=pathlib.Path(self.temp.name)/'cover.png';pixbuf=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,60,90);pixbuf.fill(0xff0000ff);pixbuf.savev(str(path),'png',[],[])
        image=Gtk.Image();self.w.show_icon(image,str(path),1);self.assertEqual(image.get_storage_type(),Gtk.ImageType.PIXBUF);self.assertGreater(image.get_pixbuf().get_height(),0)

    def test_community_profiles_are_visible_without_a_disclosure(self):
        import time
        from deck_library import presets
        from gi.repository import Gtk
        entry=self.w.entries[0];profile=presets.recommended(entry,self.store)[0];self.w.community_rating_cache={entry.id:(time.monotonic(),[{'id':'shared-1','preset':profile,'author':'Player','rating':4.5,'ratings':2}])}
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
        self.w.resize(840,640);self.settle();size=self.w.get_size();windows=self.application_windows()
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
        button=self.w.steam_library_button;self.assertEqual(button.get_label(),'Añadir Deck Library a Steam')
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
