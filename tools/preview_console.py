#!/usr/bin/env python3
"""Render or open the native console UI with a disposable sample library.

Example: xvfb-run -a python3 tools/preview_console.py dist/preview --width 1280 --height 800
Interactive: python3 tools/preview_console.py --interactive
Requires GTK 3/PyGObject and a display. Never launches a game or reads a personal library.
"""
import argparse,os,pathlib,sys,tempfile
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=pathlib.Path,nargs='?',default=ROOT/'dist/console-preview')
    parser.add_argument('--interactive',action='store_true',help='Keep the preview window open for mouse and keyboard review.')
    parser.add_argument('--no-animations',action='store_true',help='Disable motion in the interactive preview. Captures always use reduced motion.')
    parser.add_argument('--all-pages',action='store_true',help='Also render settings, appearance, tools, catalog, updates and help.')
    parser.add_argument('--real-games',action='store_true',help='Use known game titles and locally cached public cover artwork.')
    parser.add_argument('--download-artwork',action='store_true',help='Download public artwork for the real-game fixtures into the ignored local cache.')
    parser.add_argument('--page',choices=('home','library','settings','tools','catalog','updates','help','validated','game','port'),default='home')
    parser.add_argument('--width',type=int,default=1280);parser.add_argument('--height',type=int,default=800)
    parser.add_argument('--theme',choices=('dark','light'),default='dark')
    parser.add_argument('--scale',choices=('normal','large','xlarge'),default='normal')
    parser.add_argument('--language',choices=('es','en'),default='es');parser.add_argument('--empty',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    os.environ['DECK_LIBRARY_UI_TESTS']='1';os.environ['GDK_BACKEND']='x11'
    from deck_library import gui,gui_shell,ui_theme,i18n,history
    from deck_library.installations import DEFAULTS
    from deck_library.models import Store,Entry
    from gi.repository import Gtk,Gdk,GLib
    images={}
    if args.real_games or args.download_artwork:
        args.real_games=True
        from demo_library import artwork
        images=artwork(ROOT/'dist/demo-artwork',args.download_artwork)
    with tempfile.TemporaryDirectory() as folder:
        store=Store(folder)
        from demo_library import fictional_entries
        entries=[] if args.empty else fictional_entries(store,args.language)
        if args.real_games and not args.empty:
            from demo_library import entries as real_entries
            entries=real_entries(store,images)
        store.save(entries)
        import time
        for index,entry in enumerate(entries):history.record(store,entry.id,now=int(time.time())-index*3600)
        prefs={**DEFAULTS,'onboarding_complete':True,'start_page':'home','check_updates':False,'artwork_provider':'off','animations':args.interactive and not args.no_animations,'community_ratings':False,'theme':args.theme,'ui_scale':args.scale,'language':args.language}
        prefs['eden_config']=str(store.root/'demo-eden');prefs['favorites']=[entry.id for entry in entries[:2]]
        def catalog(window,*_):
            from deck_library import ports
            GLib.idle_add(window.catalog_loaded,[ports.clean(item) for item in ports.BUILTIN[:8]],'')
        def kits(window,values,generation):
            for _,widget in values:GLib.idle_add(window.show_requirements,widget,[],generation)
        def icons(window,values,generation):
            from deck_library.artwork import normalized
            known={normalized(name):art.get('hero') or art.get('cover') for name,art in images.items()}
            for item,widget in values:
                path=known.get(normalized(item.get('cover_title') or item.get('game_title') or item['name']))
                if path:GLib.idle_add(window.show_icon,widget,path,generation)
        from deck_library import presets
        import copy
        demo_values={}
        def current_values(entry,*_):
            if entry.id not in demo_values:
                demo_values[entry.id]={section:{key:False if rule is bool else rule[0] for key,rule in options.items()} for section,options in presets.REGISTRY.get(presets.adapter_for(entry),{}).items()}
            return copy.deepcopy(demo_values[entry.id])
        def apply_preview(entry,profile,*a,**kw):
            values=current_values(entry)
            for section,options in profile['settings'].items():values.setdefault(section,{}).update(options)
            demo_values[entry.id]=values
            return {'changes':sum(len(options) for options in profile['settings'].values()),'backup':'demo'}
        patches=[patch.object(gui_shell,'Store',return_value=store),patch.object(gui_shell,'settings',return_value=prefs),patch.object(gui.Window,'discover',return_value=False),patch.object(gui.Window,'load_catalog',catalog),patch.object(gui.Window,'load_icons',return_value=None),patch.object(gui.Window,'check_kits',return_value=None),patch.object(gui.Window,'check_missing_roms',return_value=False),patch.object(gui_shell,'find_accounts',return_value=[]),patch.object(gui_shell,'active_account',return_value=None),patch.object(gui.Window,'in_steam',return_value=False),patch('deck_library.artwork.find_accounts',return_value=[])]
        patches.append(patch('deck_library.community.Client.search',return_value=[]))
        patches.append(patch.object(gui.Window,'check_kits',kits))
        patches.append(patch.object(gui.Window,'load_icons',icons))
        patches.extend([patch.object(presets,'current_values',current_values),patch.object(presets,'apply',apply_preview),patch.object(gui.Window,'offer_deck_controls',return_value=None)])
        from deck_library.gui_console import ConsoleBackdrop
        original_cover=ConsoleBackdrop.set_cover
        heroes={art['cover']:art['hero'] for art in images.values() if art.get('cover') and art.get('hero')}
        patches.append(patch.object(ConsoleBackdrop,'set_cover',lambda backdrop,path:original_cover(backdrop,heroes.get(path,path))))
        install_message='Vista previa: no se instalan archivos.' if args.language=='es' else 'Preview: no files are installed.'
        patches.append(patch.object(gui.Window,'install_port',lambda window,*a,**kw:window.toast(install_message)))
        patches.append(patch.object(gui.Window,'apply_game_profile',lambda window,*a,**kw:window.toast(install_message)))
        patches.append(patch.object(gui.Window,'restore_game_profile',lambda window,*a,**kw:window.toast(install_message)))
        from deck_library import ports,updates
        demo_notes='• Correcciones de controles.\n• Mejoras en la carga inicial.\n• Compatibilidad con Vulkan.' if args.language=='es' else '• Controller fixes.\n• Faster startup.\n• Vulkan compatibility.'
        patches.append(patch.object(updates,'cached',return_value={'catalog':[{'name':'Circuito norte' if args.language=='es' else 'Northern Circuit','repository':'example/demo-port','installed':'1.0','latest':'1.1','notes':demo_notes,'page':'https://example.invalid/demo-release'}]}))
        def port_icon(store,item,**_):return images.get(item.get('cover_title') or item.get('game_title') or item['name'],{}).get('cover','')
        patches.extend([patch.object(ports,'icon_path',port_icon),patch.object(ports,'release_for',return_value={'tag_name':'demo','assets':[{'name':'demo-linux-x86_64.zip','browser_download_url':'https://example.invalid/demo.zip'}]}),patch.object(ports,'requirements',return_value=[(None,'Vista previa · archivos originales no comprobados.' if args.language=='es' else 'Preview · original files have not been checked.')])])
        for item in patches:item.start()
        preview_message='Vista previa: el juego no está instalado.' if args.language=='es' else 'Preview: the game is not installed.'
        play_patch=patch.object(gui.Window,'play',lambda window,entry:window.toast(preview_message));play_patch.start()
        i18n.setup(prefs);ui_theme.set_theme(args.theme)
        Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme',args.theme!='light')
        provider=Gtk.CssProvider();provider.load_from_data(ui_theme.css(args.scale,args.theme));gui.PROVIDER=provider
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        window=gui.Window();window.resize(args.width,args.height);window.show_all()
        window.set_title('Deck Library — Demo');window.shell_clock.set_text('14:30');window.dismiss_banner()
        demo=Gtk.Label(label='DEMO');demo.get_style_context().add_class('meta');window.shell_search.get_parent().pack_end(demo,False,False,8);demo.show()
        def show_page(name):
            if name=='game':
                if entries:window.select_game(entries[0])
            elif name=='port':
                window.catalog_page();window.port_details(ports.clean(ports.BUILTIN[0]))
            elif name=='library':window.open_library()
            else:getattr(window,name+'_page')()
        if args.interactive:
            GLib.idle_add(lambda:(show_page(args.page),False)[1])
            print('Interactive preview open. Close the window to finish.',flush=True)
            try:Gtk.main()
            finally:
                play_patch.stop()
                for item in reversed(patches):item.stop()
            return
        def settle():
            loop=GLib.MainLoop();GLib.timeout_add(250,lambda:(loop.quit(),False)[1]);loop.run()
        def shot(name):
            settle();surface=window.get_window()
            Gdk.pixbuf_get_from_window(surface,0,0,surface.get_width(),surface.get_height()).savev(str(args.output/(name+'.png')),'png',[],[])
            print(name,surface.get_width(),surface.get_height())
        shot('home');window.shell_menu.clicked();shot('menu');window.shell_menu.get_popover().popdown()
        window.open_library();shot('library')
        if entries:
            window.select_game(entries[0]);shot('game')
            if args.all_pages:
                window.game_header_secondary.set_active(True);shot('game-menu');window.game_header_secondary.get_popover().popdown()
                for section in ('options','controls','content','community'):
                    window.open_game_section(section);shot('game-'+section)
        if args.all_pages:
            for name in ('settings','tools','catalog','updates','help','validated'):
                show_page(name)
                if name=='updates':
                    from deck_library.ui_components import Reveal
                    def expand(widget):
                        if isinstance(widget,Reveal):widget.control.clicked()
                        elif isinstance(widget,Gtk.Container):
                            for child in widget.get_children():expand(child)
                    expand(window.updates_box)
                shot(name)
            window.settings_page()
            from deck_library.inline_pages import InlineDialog
            original=InlineDialog.run
            def capture(dialog):
                def save():
                    if hasattr(dialog,'port_repository'):
                        shot('port')
                        for name in ('requirements','compatibility','manage'):
                            dialog.section_tabs.buttons[name].clicked();shot('port-'+name)
                    else:shot('appearance')
                    dialog.response(Gtk.ResponseType.CANCEL);return False
                GLib.timeout_add(250,save);return original(dialog)
            with patch.object(InlineDialog,'run',capture):window.appearance_dialog()
            with patch.object(InlineDialog,'run',capture):show_page('port')
        window.disconnect_by_func(Gtk.main_quit);window.destroy()
        play_patch.stop()
        for item in reversed(patches):item.stop()


if __name__=='__main__':main()
