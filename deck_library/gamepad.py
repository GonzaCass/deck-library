"""Optional SDL2 controller polling. No window, video subsystem or exclusive input grab."""
import ctypes as C
import ctypes.util,time

DIRECTIONS=('up','down','left','right')
SCROLL_DIRECTIONS=tuple('scroll_'+key for key in DIRECTIONS)

def stick_direction(x,y,previous=None,enter=10000,leave=6500):
    """A modest dead zone and hysteresis keep diagonals and resting sticks stable."""
    magnitude=max(abs(x),abs(y))
    if magnitude<(leave if previous else enter):return None
    if previous in ('left','right') and abs(x)>=abs(y)*.85 and abs(x)>=leave:
        direction='right' if x>0 else 'left'
    elif previous in ('up','down') and abs(y)>=abs(x)*.85 and abs(y)>=leave:
        direction='down' if y>0 else 'up'
    else:direction=('right' if x>0 else 'left') if abs(x)>abs(y) else ('down' if y>0 else 'up')
    if direction!=previous and magnitude<enter:return None
    return direction

class Repeater:
    def __init__(self):self.held=set();self.next={}
    def events(self,pressed,now=None):
        now=time.monotonic() if now is None else now;pressed=set(pressed);out=[]
        for key in sorted(pressed):
            if key not in self.held:out.append(key);self.next[key]=now+.35
            elif key in DIRECTIONS+SCROLL_DIRECTIONS and now>=self.next[key]:out.append(key);self.next[key]=now+.11
        self.held=pressed;self.next={k:v for k,v in self.next.items() if k in pressed};return out

class SDL:
    BUTTONS={0:'activate',1:'back',2:'search',9:'previous_tab',10:'next_tab',11:'up',12:'down',13:'left',14:'right'}
    def __init__(self):
        name=ctypes.util.find_library('SDL2')
        if not name:raise OSError('SDL2 no está disponible')
        self.lib=C.CDLL(name);self.pads={};self.sticks={};self.enumerated=0
        signatures={'SDL_InitSubSystem':([C.c_uint32],C.c_int),'SDL_QuitSubSystem':([C.c_uint32],None),'SDL_SetHint':([C.c_char_p,C.c_char_p],C.c_int),'SDL_NumJoysticks':([],C.c_int),'SDL_IsGameController':([C.c_int],C.c_int),'SDL_GameControllerOpen':([C.c_int],C.c_void_p),'SDL_GameControllerClose':([C.c_void_p],None),'SDL_JoystickGetDeviceInstanceID':([C.c_int],C.c_int32),'SDL_GameControllerName':([C.c_void_p],C.c_char_p),'SDL_GameControllerGetAttached':([C.c_void_p],C.c_int),'SDL_GameControllerGetButton':([C.c_void_p,C.c_int],C.c_uint8),'SDL_GameControllerGetAxis':([C.c_void_p,C.c_int],C.c_int16),'SDL_GameControllerUpdate':([],None),'SDL_PumpEvents':([],None)}
        for key,(args,restype) in signatures.items():fn=getattr(self.lib,key);fn.argtypes=args;fn.restype=restype
        self.flags=0x200|0x2000
        self.lib.SDL_SetHint(b'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS',b'1')
        if self.lib.SDL_InitSubSystem(self.flags)!=0:raise OSError('SDL no pudo abrir los mandos')
    def read(self):
        self.lib.SDL_PumpEvents();self.lib.SDL_GameControllerUpdate();now=time.monotonic()
        for index,pad in list(self.pads.items()):
            if not self.lib.SDL_GameControllerGetAttached(pad):self.lib.SDL_GameControllerClose(pad);del self.pads[index];self.sticks.pop(index,None)
        if now-self.enumerated>1:
            self.enumerated=now
            for index in range(self.lib.SDL_NumJoysticks()):
                instance=self.lib.SDL_JoystickGetDeviceInstanceID(index)
                if instance not in self.pads and self.lib.SDL_IsGameController(index):
                    pad=self.lib.SDL_GameControllerOpen(index)
                    if pad:self.pads[instance]=pad
        pressed=set()
        # Steam Input can expose both the physical Deck and its virtual gamepad.
        # Read the configured virtual device when it is present, avoiding echoes.
        virtual={key:pad for key,pad in self.pads.items() if b'steam virtual' in (self.lib.SDL_GameControllerName(pad) or b'').lower()}
        for key,pad in (virtual or self.pads).items():
            pressed.update(action for button,action in self.BUTTONS.items() if self.lib.SDL_GameControllerGetButton(pad,button))
            left,right=self.sticks.get(key,(None,None))
            left=stick_direction(self.lib.SDL_GameControllerGetAxis(pad,0),self.lib.SDL_GameControllerGetAxis(pad,1),left)
            right=stick_direction(self.lib.SDL_GameControllerGetAxis(pad,2),self.lib.SDL_GameControllerGetAxis(pad,3),right)
            self.sticks[key]=(left,right)
            if left:pressed.add(left)
            if right:pressed.add('scroll_'+right)
        return pressed
    def close(self):
        for pad in self.pads.values():self.lib.SDL_GameControllerClose(pad)
        self.pads.clear();self.sticks.clear();self.lib.SDL_QuitSubSystem(self.flags)

class Driver:
    def __init__(self,window):
        from gi.repository import GLib
        from .compositor_focus import GamescopeFocus
        self.window=window;self.sdl=SDL();self.focus=GamescopeFocus();self.repeat=Repeater();self.timer=GLib.timeout_add(25,self.poll)
    def poll(self):
        from gi.repository import Gtk
        if self.window.ui_closed:return False
        focused=self.focus.focused()
        active=next((w for w in Gtk.Window.list_toplevels() if w.get_visible() and w.get_accept_focus() and (w.is_active() or w.has_toplevel_focus())),None)
        own=active
        while own is not None and own is not self.window:own=own.get_transient_for()
        if own is not self.window:
            grab=Gtk.grab_get_current()
            anchor=grab.get_attach_widget() if isinstance(grab,Gtk.Menu) else None
            candidate=anchor.get_toplevel() if anchor else None;owner=candidate
            while owner is not None and owner is not self.window:owner=owner.get_transient_for()
            if owner is self.window:active=candidate;own=owner
        pressed=self.sdl.read()
        # Gamescope owns app focus. Its activation can remain correct while GTK's
        # is_active flags are cleared by an internal page/menu change.
        if focused is False:self.repeat.events(pressed);return True
        if focused is True and self.window.get_visible() and self.window.get_mapped() and own is not self.window:
            active=self.window;own=self.window
        if own is not self.window:self.repeat.events(pressed);return True
        self.window.prepare_controller_window(active)
        self.window.ensure_controller_focus(active)
        for event in self.repeat.events(pressed):self.window.controller_action(event,active)
        return True
    def close(self):
        from gi.repository import GLib
        if GLib.MainContext.default().find_source_by_id(self.timer):GLib.source_remove(self.timer)
        self.sdl.close();self.focus.close()
