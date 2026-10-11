"""Community port catalog page: browse, install and update ports from GitHub releases."""
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
from . import ports

class CatalogMixin:
    def catalog_page(self):
        from .gui import label,button
        box=self.catalog_box;self.reset_page(box)
        head=Gtk.Box(spacing=12);titles=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        titles.pack_start(label('Catálogo de ports','hero'),False,False,0)
        titles.pack_start(label('Proyectos de la comunidad (lista pública de Quiver). Se instalan en ~/ports desde el último release de GitHub.','subtitle'),False,False,0)
        head.pack_start(titles,True,True,0);head.pack_end(button('Actualizar lista',lambda _:self.load_catalog(True)),False,False,0);box.pack_start(head,False,False,0)
        self.catalog_search=Gtk.SearchEntry();self.catalog_search.set_placeholder_text('Buscar port');self.catalog_search.connect('search-changed',lambda _:self.fill_catalog());box.pack_start(self.catalog_search,False,False,0)
        self.catalog_status=label('Cargando catálogo…','status');box.pack_start(self.catalog_status,False,False,0)
        self.catalog_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);box.pack_start(self.catalog_rows,False,False,0)
        box.show_all();self.pages.set_visible_child_name('catalog');self.load_catalog(False)

    def load_catalog(self,force):
        self.catalog_status.set_text('Cargando catálogo…')
        def work():
            try:apps=ports.catalog(self.store,force)
            except Exception as error:GLib.idle_add(self.catalog_loaded,None,str(error));return
            GLib.idle_add(self.catalog_loaded,apps,'')
        threading.Thread(target=work,daemon=True).start()

    def catalog_loaded(self,apps,error):
        if apps is None:self.catalog_status.set_text('No se pudo cargar el catálogo: '+error);return False
        self.catalog_apps=apps;self.fill_catalog();return False

    def fill_catalog(self):
        from .gui import label,button
        if not hasattr(self,'catalog_apps'):return
        self.reset_page(self.catalog_rows);text=self.catalog_search.get_text().casefold().strip();installed=ports.records(self.store)
        updates={u['repository'] for u in (getattr(self,'update_state',None) or {}).get('catalog') or []}
        matches=[a for a in self.catalog_apps if text in (a['name']+' '+a['repository']).casefold()]
        self.catalog_status.set_text(f'{len(matches)} de {len(self.catalog_apps)} ports'+(' · se muestran los primeros 60' if len(matches)>60 else ''))
        for item in matches[:60]:
            row=Gtk.Box(spacing=12);row.get_style_context().add_class('card');texts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
            texts.pack_start(label(item['name'],'title'),False,False,0);record=installed.get(item['repository'])
            texts.pack_start(label(item['repository']+(' · instalado '+record['tag'] if record else ''),'muted'),False,False,0);row.pack_start(texts,True,True,0)
            if record and item['repository'] in updates:row.pack_end(button('Actualizar',lambda _,i=item:self.install_port(i,True),True),False,False,0)
            elif record:row.pack_end(label('Instalado','good'),False,False,0)
            else:row.pack_end(button('Instalar',lambda _,i=item:self.install_port(i,False)),False,False,0)
            self.catalog_rows.pack_start(row,False,False,0)
        self.catalog_rows.show_all()

    def install_port(self,item,replace):
        if getattr(self,'port_busy',False):self.set_status('Ya hay una instalación en curso.');return
        self.port_busy=True;self.set_status('Instalando '+item['name']+'…')
        def work():
            try:record=ports.install(item,self.store,progress=lambda text:GLib.idle_add(self.set_status,text),replace=replace);GLib.idle_add(self.port_installed,item,record)
            except Exception as error:GLib.idle_add(self.port_failed,item,str(error))
        threading.Thread(target=work,daemon=True).start()

    def port_installed(self,item,record):
        self.port_busy=False
        if record['executable']:self.set_status(f'{item["name"]} {record["tag"]} instalado.')
        else:self.message('Ejecutable no identificado',f'{item["name"]} se instaló en ~/ports/{record["folder"]}, pero hay varios ejecutables posibles. Elegir el correcto con «Agregar juegos → Elegir un juego o una app».')
        if getattr(self,'update_state',None):self.update_state['catalog']=[u for u in self.update_state.get('catalog') or [] if u['repository']!=item['repository']];self.refresh_update_badges()
        self.discover()
        if self.pages.get_visible_child_name()=='catalog':self.fill_catalog()
        return False

    def port_failed(self,item,text):
        self.port_busy=False;self.set_status('No se pudo instalar '+item['name']+'.');self.message('Instalación de '+item['name'],text);return False
