"""Visible gameplay evidence and alternative ports, shared by catalog and library."""
from gi.repository import Gtk,GLib
from . import port_variants
from .ui_components import badge,text,ActionButton,Reveal

EXPLANATIONS={
 'verified':'La prueba corresponde a este repositorio y a esta versión. Revisar las limitaciones de la partida probada.',
 'version-unknown':'Hay una prueba de esta variante, pero falta confirmar la versión disponible.',
 'different-version':'La prueba corresponde a otra versión. Esta versión todavía no está validada.',
 'other-variant':'La prueba corresponde a otro repositorio. Esta variante todavía no está validada.',
 'unvalidated':'Todavía no hay una prueba de juego para esta variante. No significa que sea incompatible.'
}

class VariantsMixin:
    def port_variant_index(self,items=None):
        return port_variants.Index(self.catalog_entries() if items is None else items,self.entries)

    def variant_badge(self,assessment):
        control=badge(assessment['label'],assessment['tone'],42)
        control.set_tooltip_text(assessment['issue'] or EXPLANATIONS[assessment['state']]);return control

    def open_port_variant(self,item,page=None):
        if page is not None:page.response(Gtk.ResponseType.CLOSE)
        GLib.idle_add(lambda:(self.port_details(item),False)[1])

    def build_port_evidence(self,parent,item,page,index):
        assessment=index.assess(item);panel=self.card(parent,'Prueba de juego en Steam Deck')
        panel.pack_start(self.variant_badge(assessment),False,False,0)
        panel.pack_start(text(assessment['issue'] or EXPLANATIONS[assessment['state']],'muted',85),False,False,0)
        report=assessment['report']
        if report:
            panel.pack_start(text('Variante probada: '+report['repository'],'meta',85),False,False,0)
            panel.pack_start(text('Versión probada: '+report['version']+' · '+report['program'],'meta',85),False,False,0)
            detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
            for value in (report['result'],report['limitations'],'Fecha del registro: '+report['date'],'Steam Deck OLED' if report['hardware']=='steam-deck-oled' else 'Steam Deck LCD'):detail.pack_start(text(value,'muted',85),False,False,0)
            panel.pack_start(Reveal('Ver condiciones de la prueba',detail),False,False,0)
            if report['repository'].casefold()!=item['repository'].casefold():
                target=index.items.get(report['repository'].casefold())
                if target:panel.pack_start(ActionButton('Ver variante probada','check',lambda _:self.open_port_variant(target,page),'steam-outline'),False,False,0)
        installed=index.installed(item,self.entries)
        unidentified=self.catalog_installation(item)
        if unidentified and unidentified.get('unidentified'):
            panel.pack_start(text('Se encontró un port con nombre similar, pero su repositorio no está identificado.','muted',85),False,False,0)
        for entry in installed:
            actual=port_variants.entry_item(entry);state=index.assess(actual,actual['release_version'])
            panel.pack_start(text('Instalada: '+actual['repository']+' · '+(actual['release_version'] or 'Versión sin identificar'),'meta',85),False,False,0)
            panel.pack_start(self.variant_badge(state),False,False,0)
            if actual['repository'].casefold()!=item['repository'].casefold():panel.pack_start(text('Hay otra variante instalada. No se reemplaza al instalar esta.','muted',85),False,False,0)
            from . import broken_bond
            if actual['repository'].casefold()==broken_bond.ORIGINAL and broken_bond.status(entry,self.store)=='migrate':
                def repair(_,entry=entry):
                    page.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.repair_broken_bond(entry),False)[1])
                panel.pack_start(ActionButton('Cambiar a la variante probada','sliders',repair,'violet'),False,False,0)
        alternatives=index.alternatives(item)
        if alternatives:
            rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
            rows.pack_start(text('Cada repositorio es una variante independiente. Se comparan las pruebas disponibles; la versión más nueva o un porcentaje alto no validan el juego.','muted',85),False,False,0)
            for candidate in alternatives:
                row=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
                row.pack_start(text(candidate['repository'],'title',75),False,False,0)
                row.pack_start(self.variant_badge(index.assess(candidate)),False,False,0)
                row.pack_start(ActionButton('Ver esta variante','controller',lambda _,i=candidate:self.open_port_variant(i,page),'quiet'),False,False,0);rows.pack_start(row,False,False,0)
            panel.pack_start(Reveal('Comparar variantes · '+str(len(alternatives)+1),rows),False,False,0)

    def build_game_variant_notice(self,entry,parent):
        if not entry.metadata.get('port_repository'):return
        item=port_variants.entry_item(entry);index=self.port_variant_index();assessment=index.assess(item,item['release_version'])
        if not index.alternatives(item) and not assessment['report'] and not assessment['issue']:return
        row=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);parent.pack_start(row,False,False,0)
        row.pack_start(self.variant_badge(assessment),False,False,0)
        row.pack_start(text('Variante instalada: '+item['repository']+' · '+(item['release_version'] or 'Versión sin identificar'),'meta',85),False,False,0)
        if assessment['state']!='verified':row.pack_start(text(assessment['issue'] or EXPLANATIONS[assessment['state']],'muted',85),False,False,0)
        target=index.items.get(item['repository'].casefold(),item)
        row.pack_start(ActionButton('Ver prueba y variantes','check',lambda _:self.open_port_variant(target),'quiet'),False,False,0)
