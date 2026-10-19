"""Public profiles, real ratings/comments and guided publication with a private account."""
import threading
from gi.repository import Gtk,GLib
from .community import Client
from . import presets,profile_display
from .ui_components import ActionButton,text

class CommunityMixin:
    def community_dialog(self,e,profile_id=None,mode='browse'):
        dialog=Gtk.Dialog(title='Comunidad · '+e.name,transient_for=self,modal=True)
        width,height=self.get_size();dialog.set_default_size(min(1040,width-48),min(700,height-64));dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(18);box.set_spacing(12)
        client=Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz'))
        alive=[True];busy=[False];selected=[None];prepared=[None]
        header=Gtk.Box(spacing=12);header.pack_start(text('Ajustes comunitarios','section-title'),True,True,0);account=text('','meta');header.pack_end(account,False,False,0);box.pack_start(header,False,False,0)
        tabs=Gtk.Box(spacing=8);box.pack_start(tabs,False,False,0)
        stack=Gtk.Stack();stack.set_homogeneous(False);stack.set_vexpand(True);stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE);stack.set_transition_duration(120);box.pack_start(stack,True,True,0)
        def add_page(widget,name):
            viewport=self.new_scroll();viewport.set_vexpand(True);viewport.add(widget);stack.add_named(viewport,name)
        status=text('','status',100);box.pack_end(status,False,False,0)
        browse=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);add_page(browse,'browse')
        pane=Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL);pane.set_position(340);browse.pack_start(pane,True,True,0)
        rows=Gtk.ListBox();rows.set_selection_mode(Gtk.SelectionMode.SINGLE);scroll=self.new_scroll();scroll.add(rows);pane.pack1(scroll,resize=True,shrink=True)
        right=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);right.set_margin_start(14);pane.pack2(right,resize=True,shrink=True)
        name=text('Seleccioná un perfil','title',50);score=text('','rating');right.pack_start(name,False,False,0);right.pack_start(score,False,False,0)
        comments=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);comment_scroll=self.new_scroll();comment_scroll.add(comments);right.pack_start(comment_scroll,True,True,0)
        rating=Gtk.ComboBoxText()
        for n in range(1,6):rating.append(str(n),str(n)+' '+('★'*n))
        rating.set_active_id('5');right.pack_start(text('Tu valoración','title'),False,False,0);right.pack_start(rating,False,False,0)
        right.pack_start(text('Comentario (opcional)','meta'),False,False,0);note=Gtk.TextView();note.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);note_scroll=self.new_scroll();note_scroll.set_size_request(-1,70);note_scroll.add(note);right.pack_start(note_scroll,False,False,0)
        post=Gtk.Box(spacing=8);right.pack_start(post,False,False,0)
        publish_page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);add_page(publish_page,'publish')
        publish_page.pack_start(text('Compartir mi configuración actual','section-title'),False,False,0)
        publish_page.pack_start(text('Se comparten las opciones permitidas del juego, sin rutas, claves ni archivos personales. El aporte queda pendiente de revisión.','muted',100),False,False,0)
        title=Gtk.Entry();title.set_text(e.name+' — mis ajustes');publish_page.pack_start(text('Nombre del perfil'),False,False,0);publish_page.pack_start(title,False,False,0)
        objective=Gtk.ComboBoxText()
        for key in ('Equilibrado','Rendimiento','Calidad','Personalizado'):objective.append(key,key)
        objective.set_active_id('Equilibrado');publish_page.pack_start(text('Objetivo'),False,False,0);publish_page.pack_start(objective,False,False,0)
        description=Gtk.Entry();description.set_placeholder_text('Qué probaste y cómo funcionó');publish_page.pack_start(text('Descripción'),False,False,0);publish_page.pack_start(description,False,False,0)
        review=text('','muted',100);review_scroll=self.new_scroll();review_scroll.add(review);publish_page.pack_start(review_scroll,True,True,0)
        publication=Gtk.Box(spacing=10);publish_page.pack_start(publication,False,False,0)
        from .gui_account import AccountPane
        def refresh_account():account.set_text('Sesión: '+client.session()['login'] if client.session().get('login') else 'Sin sesión')
        def run(job,done):
            if busy[0] or not alive[0]:return
            busy[0]=True;status.set_text('Conectando…')
            def finish(value,error):
                busy[0]=False
                if not alive[0]:return False
                if error:status.set_text(error)
                else:status.set_text('');done(value)
                return False
            def work():
                try:GLib.idle_add(finish,job(),None)
                except Exception as error:GLib.idle_add(finish,None,str(error))
            threading.Thread(target=work,daemon=True).start()
        def show_comments(value):
            self.reset_page(comments)
            if not value:comments.pack_start(text('Todavía no hay comentarios.','muted'),False,False,0)
            for item in value:
                panel=self.card(comments,(item.get('author') or 'Usuario')+(' · '+str(item['rating'])+' ★' if item.get('rating') else ''))
                panel.pack_start(text(item.get('notes') or ('Le funcionó' if item['result']=='works' else 'Informó problemas'),'muted',65),False,False,0)
            comments.show_all()
        def chosen(_,row):
            selected[0]=getattr(row,'value',None)
            if not selected[0]:return
            value=selected[0];name.set_text(profile_display.title(value['preset']));score.set_text(rating_caption(value))
            if value.get('status')=='pending':show_comments([]);status.set_text('Este aporte está pendiente de revisión.');return
            run(lambda:client.comments(value),lambda result:show_comments(result) if selected[0] is value else None)
        rows.connect('row-selected',chosen)
        def found(values):
            selected[0]=None;self.reset_page(rows)
            for value in values:
                row=Gtk.ListBoxRow();row.value=value;body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6);body.set_border_width(10);body.pack_start(text(profile_display.title(value['preset']),'title',34),False,False,0);body.pack_start(text(rating_caption(value),'rating'),False,False,0);body.pack_start(text(value['author']+(' · Pendiente de revisión' if value.get('status')=='pending' else ''),'meta'),False,False,0);row.add(body);rows.add(row)
            rows.show_all()
            wanted=next((r for r in rows.get_children() if r.value['preset']['id']==profile_id or 'community-'+r.value['id']==profile_id),rows.get_row_at_index(0))
            if wanted:rows.select_row(wanted)
            else:name.set_text('No hay perfiles publicados para este juego.');show_comments([])
        def search(_,mine=False):run(lambda:client.search(e,mine=mine),found)
        def auth_needed():
            if client.session().get('login'):return False
            stack.set_visible_child_name('account');status.set_text('Iniciá sesión para continuar.');return True
        def download(_):
            if not selected[0]:status.set_text('Seleccioná un perfil.');return
            try:
                value=client.download(selected[0]);self.profile_choice[e.id]=value['id'];self.game_tab='profiles';dialog.response(Gtk.ResponseType.CLOSE);GLib.idle_add(lambda:(self.show_detail(e),False)[1])
            except Exception as error:status.set_text(str(error))
        def rate(_):
            if auth_needed():return
            if not selected[0]:status.set_text('Seleccioná un perfil.');return
            buffer=note.get_buffer();notes=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True);value=selected[0]
            def done(_):status.set_text('Valoración guardada.');self.community_rating_cache.pop(e.id,None) if hasattr(self,'community_rating_cache') else None;search(None)
            run(lambda:client.rate(value,int(rating.get_active_id()),notes),done)
        def review_profile(_):
            if auth_needed():return
            try:
                value=presets.export_current(e,title.get_text().strip(),client.session()['login'],self.store,self.preferences.get('eden_config') or None);value['objective']=objective.get_active_id();value['notes']=description.get_text().strip();presets.validate(value);prepared[0]=value
                lines=[profile_display.title(value),'Objetivo: '+value['objective'],'Autor: '+value['author'],'Licencia: MIT','']
                for section,options in value['settings'].items():
                    for key,setting in options.items():lines.append(key+': '+profile_display.value_text(value['adapter']['id'],key,setting))
                review.set_text('\n'.join(lines));submit.set_sensitive(True)
            except Exception as error:status.set_text(str(error))
        def submit_profile(_):
            if auth_needed() or not prepared[0]:return
            def done(_):submit.set_sensitive(False);status.set_text('Perfil enviado. Podés ver su estado en Mis aportes.');prepared[0]=None
            value=prepared[0];run(lambda:client.publish(value),done)
        def changed(*_):prepared[0]=None;submit.set_sensitive(False)
        publication.pack_start(ActionButton('Revisar mis ajustes','sliders',review_profile,'violet-outline'),False,False,0);submit=ActionButton('Publicar perfil','upload',submit_profile,'violet');submit.set_sensitive(False);publication.pack_start(submit,False,False,0)
        title.connect('changed',changed);objective.connect('changed',changed);description.connect('changed',changed)
        account_page=AccountPane(client,refresh_account);add_page(account_page,'account')
        dialog.account_controller=lambda action:account_page.handle_controller(action,dialog) if stack.get_visible_child_name()=='account' else False
        for caption,page,icon in [('Perfiles','browse','community'),('Compartir mis ajustes','publish','upload'),('Mi cuenta','account','controller')]:tabs.pack_start(ActionButton(caption,icon,lambda _,p=page:stack.set_visible_child_name(p),'violet-outline' if page=='publish' else 'quiet'),False,False,0)
        browse_actions=Gtk.Box(spacing=10);browse.pack_end(browse_actions,False,False,0);browse_actions.pack_start(ActionButton('Usar este perfil','download',download,'violet'),False,False,0);browse_actions.pack_start(ActionButton('Actualizar','refresh',search),False,False,0);browse_actions.pack_start(ActionButton('Mis aportes','upload',lambda w:search(w,True)),False,False,0)
        post.pack_start(ActionButton('Publicar opinión','community',rate,'violet-outline'),False,False,0)
        refresh_account();dialog.show_all();stack.set_visible_child_name(mode);search(None);dialog.run();alive[0]=False
        account_page.close()
        dialog.destroy()


def rating_caption(value):
    count=value.get('ratings',0);rating=value.get('rating')
    return f'★ {rating:.1f}/5 · {count} valoraciones' if count and rating is not None else '★ Sin valoraciones'
