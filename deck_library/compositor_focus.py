"""Read Gamescope's app focus, independently of GTK's X11 activation hints."""
import ctypes as C,ctypes.util,os


def steam_app_id(environment):
    for name in ('SteamAppId','SteamGameId'):
        try:value=int(environment.get(name,'0'))
        except (ValueError,TypeError):continue
        if value>0xffffffff:value>>=32
        if 0<value<=0xffffffff:return value
    return None


class GamescopeFocus:
    def __init__(self,environment=None):
        self.environment=dict(os.environ if environment is None else environment)
        self.app_id=steam_app_id(self.environment);self.lib=None;self.display=None;self.atom=0;self.attempted=False

    def connect(self):
        self.attempted=True
        name=ctypes.util.find_library('X11')
        if not name or not self.environment.get('DISPLAY'):return
        lib=C.CDLL(name)
        signatures={'XOpenDisplay':([C.c_char_p],C.c_void_p),'XCloseDisplay':([C.c_void_p],C.c_int),'XDefaultRootWindow':([C.c_void_p],C.c_ulong),'XInternAtom':([C.c_void_p,C.c_char_p,C.c_int],C.c_ulong),'XGetWindowProperty':([C.c_void_p,C.c_ulong,C.c_ulong,C.c_long,C.c_long,C.c_int,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ubyte))],C.c_int),'XFree':([C.c_void_p],C.c_int)}
        for key,(args,result) in signatures.items():getattr(lib,key).argtypes=args;getattr(lib,key).restype=result
        self.lib=lib;self.display=lib.XOpenDisplay(self.environment['DISPLAY'].encode())
        if self.display:self.atom=lib.XInternAtom(self.display,b'GAMESCOPE_FOCUSED_APP',True)

    def focused(self):
        """True/False with Gamescope; None on ordinary desktops or missing data."""
        if self.app_id is None:return None
        if not self.attempted:
            try:self.connect()
            except (OSError,AttributeError):self.close();return None
        if not self.display or not self.atom:return None
        kind=C.c_ulong();format_=C.c_int();count=C.c_ulong();remaining=C.c_ulong();data=C.POINTER(C.c_ubyte)()
        result=self.lib.XGetWindowProperty(self.display,self.lib.XDefaultRootWindow(self.display),self.atom,0,1,False,6,C.byref(kind),C.byref(format_),C.byref(count),C.byref(remaining),C.byref(data)) # XA_CARDINAL=6
        try:
            if result or kind.value!=6 or format_.value!=32 or count.value!=1 or not data:return None
            return (C.cast(data,C.POINTER(C.c_ulong))[0]&0xffffffff)==self.app_id
        finally:
            if data:self.lib.XFree(data)

    def close(self):
        if self.lib and self.display:self.lib.XCloseDisplay(self.display)
        self.display=None;self.atom=0
