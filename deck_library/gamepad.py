"""Optional SDL2 controller polling. No window, video subsystem or exclusive input grab."""
import ctypes as C
import ctypes.util,time

class Repeater:
    def __init__(self):self.held=set();self.next={}
    def events(self,pressed,now=None):
        now=time.monotonic() if now is None else now;pressed=set(pressed);out=[]
        for key in sorted(pressed):
            if key not in self.held:out.append(key);self.next[key]=now+.35
            elif key in ('up','down','left','right') and now>=self.next[key]:out.append(key);self.next[key]=now+.11
        self.held=pressed;self.next={k:v for k,v in self.next.items() if k in pressed};return out

class SDL:
    BUTTONS={0:'activate',1:'back',2:'search',9:'previous_tab',10:'next_tab',11:'up',12:'down',13:'left',14:'right'}
    def __init__(self):
        name=ctypes.util.find_library('SDL2')
        if not name:raise OSError('SDL2 no está disponible')
        self.lib=C.CDLL(name);self.pads={};self.enumerated=0
        signatures={'SDL_InitSubSystem':([C.c_uint32],C.c_int),'SDL_QuitSubSystem':([C.c_uint32],None),'SDL_SetHint':([C.c_char_p,C.c_char_p],C.c_int),'SDL_NumJoysticks':([],C.c_int),'SDL_IsGameController':([C.c_int],C.c_int),'SDL_GameControllerOpen':([C.c_int],C.c_void_p),'SDL_GameControllerClose':([C.c_void_p],None),'SDL_GameControllerGetAttached':([C.c_void_p],C.c_int),'SDL_GameControllerGetButton':([C.c_void_p,C.c_int],C.c_uint8),'SDL_GameControllerGetAxis':([C.c_void_p,C.c_int],C.c_int16),'SDL_GameControllerUpdate':([],None),'SDL_PumpEvents':([],None)}
        for key,(args,restype) in signatures.items():fn=getattr(self.lib,key);fn.argtypes=args;fn.restype=restype
        self.flags=0x200|0x2000
        self.lib.SDL_SetHint(b'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS',b'1')
        if self.lib.SDL_InitSubSystem(self.flags)!=0:raise OSError('SDL no pudo abrir los mandos')
    def read(self):
        self.lib.SDL_PumpEvents();self.lib.SDL_GameControllerUpdate();now=time.monotonic()
        for index,pad in list(self.pads.items()):
            if not self.lib.SDL_GameControllerGetAttached(pad):self.lib.SDL_GameControllerClose(pad);del self.pads[index]
        if now-self.enumerated>1:
            self.enumerated=now
            for index in range(self.lib.SDL_NumJoysticks()):
                if index not in self.pads and self.lib.SDL_IsGameController(index):
                    pad=self.lib.SDL_GameControllerOpen(index)
                    if pad:self.pads[index]=pad
        pressed=set()
        for pad in self.pads.values():
            pressed.update(action for key,action in self.BUTTONS.items() if self.lib.SDL_GameControllerGetButton(pad,key))
            x,y=self.lib.SDL_GameControllerGetAxis(pad,0),self.lib.SDL_GameControllerGetAxis(pad,1)
            if abs(x)>15000 and abs(x)>abs(y):pressed.add('right' if x>0 else 'left')
            elif abs(y)>15000:pressed.add('down' if y>0 else 'up')
        return pressed
    def close(self):
        for pad in self.pads.values():self.lib.SDL_GameControllerClose(pad)
        self.pads.clear();self.lib.SDL_QuitSubSystem(self.flags)

class Driver:
    def __init__(self,window):
        from gi.repository import GLib
        self.window=window;self.sdl=SDL();self.repeat=Repeater();self.timer=GLib.timeout_add(25,self.poll)
    def poll(self):
        from gi.repository import Gtk
        if self.window.ui_closed:return False
        active=next((w for w in Gtk.Window.list_toplevels() if w.get_visible() and w.is_active()),None)
        own=active
        while own is not None and own is not self.window:own=own.get_transient_for()
        pressed=self.sdl.read()
        if own is not self.window:self.repeat.events(pressed);return True
        for event in self.repeat.events(pressed):self.window.controller_action(event,active)
        return True
    def close(self):
        from gi.repository import GLib
        if GLib.MainContext.default().find_source_by_id(self.timer):GLib.source_remove(self.timer)
        self.sdl.close()
