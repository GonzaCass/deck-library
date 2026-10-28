"""Community: a full-width profile list, followed by one readable profile at a time."""
import threading,json
from gi.repository import Gtk,GLib
from .inline_pages import InlineDialog
from .community import Client
from . import presets,profile_display,motion
from .ui_components import ActionButton,text

class CommunityMixin:
    def community_dialog(self,e,profile_id=None,mode='browse'):
        dialog=InlineDialog(title='Comunidad · '+e.name,transient_for=self,modal=True)
        dialog.add_button('Cerrar',Gtk.ResponseType.CLOSE)
        box=dialog.get_content_area();box.set_border_width(0);box.set_spacing(8)
        client=Client(self.store,self.preferences.get('community_url','https://presets.jokerlan.xyz'))
        alive=[True];busy=[False];selected=[None];auth_return=[None];reviewed=[None]
        tabs=Gtk.Box(spacing=6);box.pack_start(tabs,False,False,0)
        stack=Gtk.Stack();stack.set_homogeneous(False);stack.set_vexpand(True);stack.connect('notify::visible-child',self.refresh_layout)
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE if motion.page_transitions() else Gtk.StackTransitionType.NONE);stack.set_transition_duration(120 if motion.page_transitions() else 0)
        box.pack_start(stack,True,True,0)
        def add_page(widget,name):
            scroll=self.new_scroll();scroll.set_vexpand(True);scroll.add(widget);stack.add_named(scroll,name)
        status=text('','status',100);box.pack_end(status,False,False,0)
        browse=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);add_page(browse,'browse')
        browse_top=Gtk.Box(spacing=8);browse_top.pack_start(text('Perfiles del juego','section-title'),True,True,0);account=text('','meta');browse_top.pack_end(account,False,False,0);browse.pack_start(browse_top,False,False,0)
        rows=Gtk.ListBox();rows.set_selection_mode(Gtk.SelectionMode.NONE);browse.pack_start(rows,False,False,0)
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);add_page(detail,'profile')
        detail_back=ActionButton('Volver a perfiles','back',lambda _:back_to_profiles(),'quiet');detail.pack_start(detail_back,False,False,0)
        name=text('','title',70);score=text('','rating');detail.pack_start(name,False,False,0);detail.pack_start(score,False,False,0)
        information=text('','muted',100);information.set_selectable(True);detail.pack_start(information,False,False,0)
        detail.pack_start(text('Ajustes e instrucciones','section-title'),False,False,0)
        settings=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);detail.pack_start(settings,False,False,0)
        comment_page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12);add_page(comment_page,'comments')
        comment_page.pack_start(ActionButton('Volver al perfil','back',lambda _:stack.set_visible_child_name('profile'),'quiet'),False,False,0)
        comment_page.pack_start(text('Comentarios','section-title'),False,False,0)
        comments=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);comment_page.pack_start(comments,False,False,0)
        feedback=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);add_page(feedback,'feedback')
        feedback.pack_start(ActionButton('Volver al perfil','back',lambda _:stack.set_visible_child_name('profile'),'quiet'),False,False,0)
        feedback.pack_start(text('Valorar el perfil · 1 a 5 estrellas','section-title'),False,False,0)
        feedback.pack_start(text('Hace falta una cuenta. Se puede actualizar la valoración y añadir un comentario; no se puede valorar un perfil propio.','muted',85),False,False,0)
        rating=Gtk.ComboBoxText()
        for n in range(1,6):rating.append(str(n),str(n)+' '+('★'*n))
        rating.set_active_id('5');feedback.pack_start(rating,False,False,0)
        feedback.pack_start(text('Comentario (opcional)','meta'),False,False,0)
        note=Gtk.TextView();note.set_wrap_mode(Gtk.WrapMode.WORD_CHAR);note_scroll=self.new_scroll();note_scroll.set_size_request(-1,110);note_scroll.add(note);feedback.pack_start(note_scroll,False,False,0)
        publish_page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);add_page(publish_page,'publish')
        from .profile_composer import ProfileComposer
        composer=ProfileComposer(e,self.store,self.preferences.get('eden_config') or None,self.pick_file);publish_page.pack_start(composer,False,False,0)
        publication=Gtk.Box(spacing=8);publish_page.pack_start(publication,False,False,0)
        from .gui_account import AccountPane
        def refresh_account():
            login=client.session().get('login');account.set_text(login or 'Sin sesión')
            if login and auth_return[0]:
                stack.set_visible_child_name(auth_return[0]);auth_return[0]=None;status.set_text('Sesión iniciada. El borrador y el comentario se conservaron.')
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
        def show_comments(values):
            self.reset_page(comments)
            if not values:comments.pack_start(text('Todavía no hay comentarios.','muted'),False,False,0)
            for value in values:
                panel=self.card(comments,(value.get('author') or 'Usuario')+(' · '+str(value['rating'])+' ★' if value.get('rating') else ''))
                panel.pack_start(text(value.get('notes') or ('Le funcionó' if value.get('result')=='works' else 'Informó problemas'),'muted',95),False,False,0)
            comments.show_all();self.refresh_layout()
        def open_profile(value):
            selected[0]=value;p=value['preset'];name.set_text(profile_display.title(p));score.set_text(rating_caption(value))
            information.set_text(value.get('author','Usuario')+' · '+profile_display.verification(p)+'\n'+p['objective']+'\n'+p['adapter']['id']+' · '+', '.join(p['adapter']['versions']))
            self.reset_page(settings)
            from .gui_tools import SETTING_LABELS
            for section,options in p['settings'].items():
                for key,setting in options.items():
                    caption=SETTING_LABELS.get(p['adapter']['id'],{}).get(key,(key,''))[0]
                    row=Gtk.Box(spacing=12);row.pack_start(text(caption,limit=55),True,True,0);row.pack_end(text(profile_display.value_text(p['adapter']['id'],key,setting),'meta',40),False,False,0);settings.pack_start(row,False,False,0)
            for content in (p.get('notes'),p.get('instructions')):
                if content:label=text(content,'muted',100);label.set_selectable(True);settings.pack_start(label,False,False,0)
            runtime=p.get('runtime')
            if runtime:settings.pack_start(text('Entorno: '+runtime['kind']+' '+runtime.get('version','')+'\n'+runtime.get('launch_options',''),'muted',100),False,False,0)
            settings.show_all();show_comments([]);stack.set_visible_child_name('feedback' if mode=='feedback' and profile_id else 'profile')
            target=rating if stack.get_visible_child_name()=='feedback' else detail_back
            GLib.idle_add(lambda:(target.grab_focus(),self.mark_controller_focus(self,target),False)[-1])
            if value.get('status')=='pending':status.set_text('Pendiente de revisión.');return
            run(lambda:client.comments(value),lambda result:show_comments(result) if selected[0] is value else None)
        state={'mine':False}
        def found(values):
            self.reset_page(rows);everything=values
            if not values:rows.add(text('No hay perfiles para este juego. Se pueden compartir perfiles propios.','muted',95))
            for value in values:
                row=Gtk.ListBoxRow();row.value=value
                control=ActionButton(profile_display.title(value['preset']),'sliders',lambda _,v=value:open_profile(v),'quiet')
                control.get_style_context().add_class('community-profile-row');control.set_hexpand(True);control.set_halign(Gtk.Align.FILL);control.body.set_halign(Gtk.Align.FILL);control.body.set_hexpand(True);control.body.set_child_packing(control.caption,True,True,0,Gtk.PackType.START);control.caption.set_line_wrap(True);control.caption.set_max_width_chars(48)
                summary=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);summary.pack_start(text(rating_caption(value),'rating',40),False,False,0);summary.pack_start(text(value['author']+(' · Pendiente' if value.get('status')=='pending' else ''),'meta',40),False,False,0)
                control.body.pack_end(summary,False,False,0);row.add(control);rows.add(row)
            rows.show_all();self.refresh_layout()
            if profile_id:
                wanted=next((v for v in everything if v['preset']['id']==profile_id or 'community-'+v['id']==profile_id),None)
                if wanted:open_profile(wanted)
                elif mode=='feedback':stack.set_visible_child_name('browse');status.set_text('Este perfil es local. Publicarlo permite recibir valoraciones de la comunidad.')
        def search(_,mine=False):
            state['mine']=mine;run(lambda:client.search(e,mine=mine),found)
        def auth_needed(destination):
            if client.session().get('login'):return False
            auth_return[0]=destination;stack.set_visible_child_name('account');status.set_text('Iniciar sesión para continuar. El borrador se conserva.');return True
        def download(_):
            if not selected[0]:return
            try:
                value=client.download(selected[0]);self.profile_choice[e.id]=value['id'];self.game_tab='profiles';self.toast('Perfil guardado. Revisar los cambios y aplicarlo desde el juego.');dialog.response(Gtk.ResponseType.CLOSE)
            except Exception as error:status.set_text(str(error))
        def rate(_):
            if auth_needed('feedback') or not selected[0]:return
            buffer=note.get_buffer();notes=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True);value=selected[0]
            def done(_):
                self.community_rating_cache.pop(e.id,None) if hasattr(self,'community_rating_cache') else None
                stack.set_visible_child_name('profile');status.set_text('Opinión guardada.');self.toast('Opinión guardada')
                def refreshed(result):
                    show_comments(result)
                    def ratings_updated(values):
                        found(values)
                        updated=next((item for item in values if item['id']==value['id']),None)
                        if updated:
                            selected[0]=updated;score.set_text(rating_caption(updated))
                        status.set_text('Opinión guardada.')
                    run(lambda:client.search(e,mine=state['mine']),ratings_updated)
                run(lambda:client.comments(value),refreshed)
            run(lambda:client.rate(value,int(rating.get_active_id()),notes),done)
        def review_profile(_):
            try:
                value=composer.profile(client.session().get('login') or 'Usuario');reviewed[0]=json.dumps({k:v for k,v in value.items() if k!='author'},sort_keys=True);submit.set_sensitive(True);status.set_text('Perfil revisado. Guardarlo localmente o publicarlo con la cuenta.')
            except Exception as error:submit.set_sensitive(False);status.set_text(str(error))
        def save_local(_):
            try:client._save(composer.profile(client.session().get('login') or 'Usuario'));status.set_text('Perfil guardado en este dispositivo.');self.toast('Perfil guardado')
            except Exception as error:status.set_text(str(error))
        def submit_profile(_):
            if auth_needed('publish'):return
            try:value=composer.profile(client.session()['login'])
            except Exception as error:status.set_text(str(error));return
            fingerprint=json.dumps({k:v for k,v in value.items() if k!='author'},sort_keys=True)
            if reviewed[0]!=fingerprint:
                submit.set_sensitive(False);status.set_text('El borrador cambió. Revisar los ajustes antes de publicarlo.');return
            def done(result):
                submit.set_sensitive(False)
                pending=result.get('status')=='pending'
                status.set_text('El perfil espera revisión; todavía no es visible para otros usuarios.' if pending else 'Perfil publicado. Los demás usuarios ya pueden verlo desde este juego.')
                self.toast('Perfil enviado para revisión' if pending else 'Perfil publicado')
                state['mine']=True
                def refreshed(values):
                    found(values);status.set_text('El perfil espera revisión; todavía no es visible para otros usuarios.' if pending else 'Perfil publicado. Los demás usuarios ya pueden verlo desde este juego.')
                run(lambda:client.search(e,mine=True),refreshed)
            run(lambda:client.publish(value),done)
        publish_page.pack_start(text('1. Leer los ajustes del juego. 2. Describir dónde se probaron. 3. Revisar y publicar. El perfil aparecerá para quienes tengan el mismo juego y programa.','muted',85),False,False,0);publish_page.reorder_child(publish_page.get_children()[-1],0)
        publication.pack_start(ActionButton('Revisar mis ajustes','sliders',review_profile,'violet-outline'),False,False,0);publication.pack_start(ActionButton('Guardar localmente','check',save_local,'cyan'),False,False,0)
        submit=ActionButton('Publicar perfil','upload',submit_profile,'violet');submit.set_sensitive(False);publication.pack_start(submit,False,False,0)
        def draft_changed():reviewed[0]=None;submit.set_sensitive(False)
        composer.connect_changed(draft_changed)
        account_page=AccountPane(client,refresh_account);add_page(account_page,'account')
        def back_to_profiles():
            stack.set_visible_child_name('browse')
            target=next((r.get_child() for r in rows.get_children() if getattr(r,'value',None) is selected[0]),None)
            if target:GLib.idle_add(lambda:(target.grab_focus(),self.mark_controller_focus(self,target),False)[-1])
        def controller(action):
            current=stack.get_visible_child_name()
            if current=='account':return account_page.handle_controller(action,dialog)
            if action=='back' and current in ('profile','feedback','comments'):
                if current=='profile':back_to_profiles()
                else:stack.set_visible_child_name('profile');detail_back.grab_focus()
                return True
            return False
        dialog.account_controller=controller
        for caption,page,icon in [('Perfiles','browse','community'),('Compartir mis ajustes','publish','upload'),('Mi cuenta','account','controller')]:tabs.pack_start(ActionButton(caption,icon,lambda _,p=page:stack.set_visible_child_name(p),'quiet'),False,False,0)
        tools=Gtk.Box(spacing=8);browse.pack_start(tools,False,False,0);tools.pack_start(ActionButton('Actualizar','refresh',search,'quiet'),False,False,0);tools.pack_start(ActionButton('Mis aportes','upload',lambda w:search(w,True),'quiet'),False,False,0)
        detail_actions=Gtk.Box(spacing=8);detail.pack_start(detail_actions,False,False,0);detail.reorder_child(detail_actions,2);detail_actions.pack_start(ActionButton('Usar este perfil','download',download,'violet'),False,False,0);detail_actions.pack_start(ActionButton('Comentarios','community',lambda _:stack.set_visible_child_name('comments'),'quiet'),False,False,0);detail_actions.pack_start(ActionButton('Valorar este perfil','community',lambda _:stack.set_visible_child_name('feedback'),'quiet'),False,False,0)
        feedback.pack_start(ActionButton('Enviar valoración','community',rate,'violet'),False,False,0)
        refresh_account();dialog.show_all();stack.set_visible_child_name(mode);search(None);dialog.run();alive[0]=False;account_page.close();dialog.destroy()
        if self.selected and self.selected.id==e.id:self.show_detail(e)


def rating_caption(value):
    count=value.get('ratings',0);rating=value.get('rating')
    return f'★ {rating:.1f}/5 · {count} valoraciones' if count and rating is not None else '★ Sin valoraciones'
