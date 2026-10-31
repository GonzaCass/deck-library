"""TodoJuegos-inspired surfaces and local typography, shared by the native interface."""
import ctypes,ctypes.util,pathlib,re

def load_fonts():
    # App fonts only: no system installation, network request or user font-cache change.
    try:
        fontconfig=ctypes.CDLL(ctypes.util.find_library('fontconfig'))
        fontconfig.FcConfigGetCurrent.restype=ctypes.c_void_p
        fontconfig.FcConfigAppFontAddFile.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
        config=fontconfig.FcConfigGetCurrent()
        for font in sorted((pathlib.Path(__file__).resolve().parent.parent/'assets/fonts').glob('*.woff2')):
            fontconfig.FcConfigAppFontAddFile(config,str(font).encode())
    except (OSError,AttributeError,TypeError):pass

TEMPLATE='''
@define-color bg #08090b;
@define-color surface #121417;
@define-color raised #1c2025;
@define-color text #f1f3f5;
@define-color dim #b6bec9;
@define-color accent @ACCENT@;
@define-color accent_soft @ACCENT_SOFT@;
@define-color accent_bg @ACCENT_BG@;
@define-color focus_ring @FOCUS_RING@;
@define-color accent_a @ACCENT_A@;
@define-color accent_b @ACCENT_B@;
@define-color accent_a_hover @ACCENT_A_HOVER@;
@define-color accent_b_hover @ACCENT_B_HOVER@;
@define-color on_accent @ON_ACCENT@;
@define-color line #343b45;
window,dialog { background:@bg; color:@text; font-family:"Manrope ExtraLight","Noto Sans",Sans; font-size:16px; }
label { color:@text; }
label.meta,label.status,label.muted,label.subtitle { color:@dim; font-weight:400; }
label.meta,label.status { font-size:16px; }
label.library-count { font-size:15px; }
label.original-required { color:#f1ce90; font-size:16px; font-weight:700; }
label.tag,button label.tag { font-size:15px; font-weight:600; border:1px solid #46515e; border-radius:6px; padding:2px 6px; color:#c8d0da; background:#20262e; }
flowbox.tag-row > flowboxchild { padding:0; }
label.tag-green,button label.tag-green { color:#a4e9be; background:#182e24; border-color:#365e48; }
label.tag-blue,button label.tag-blue { color:#b6d7ff; background:#1d2c41; border-color:#3b5475; }
label.tag-violet,button label.tag-violet { color:#dbcbff; background:#2a243b; border-color:#55476e; }
label.tag-yellow,button label.tag-yellow { color:#f5df9a; background:#302b1c; border-color:#645333; }
label.tag-orange,button label.tag-orange { color:#ffc199; background:#35271e; border-color:#735039; }
label.tag-red,button label.tag-red { color:#ffb8b2; background:#352225; border-color:#704147; }
label.compatibility-badge,button label.compatibility-badge { font-size:16px; font-weight:700; padding:4px 8px; }
label.hero,label.welcome-title,label.game-title,.inline-page-heading { font-family:"Space Grotesk Light","Noto Sans",Sans; font-size:28px; font-weight:700; letter-spacing:-0.4px; }
label.title,label.section-title { font-size:18px; font-weight:700; }
label.brand { font-family:"Space Grotesk Light",Sans; font-size:21px; font-weight:700; }
label.eyebrow,label.rail-heading { color:@dim; font-size:15px; font-weight:600; }
label.pill,label.platform-chip { color:@dim; font-size:15px; font-weight:600; }
label.platform-chip { background:@raised; border:1px solid @line; border-radius:6px; padding:3px 8px; }
.app-header { background:#040506; border-bottom:1px solid #292e36; padding:5px 12px; }
button { background:@surface; color:@text; border:1px solid @line; border-radius:9px; padding:7px 14px; min-height:32px; background-image:none; box-shadow:none; text-shadow:none; transition:background 150ms ease-out,border-color 150ms ease-out; }
button label { color:@text; font-size:15px; font-weight:600; }
button:hover { background:@raised; border-color:#66717e; }
button:active { background:#29323d; }
button:focus { outline:2px solid @accent; outline-offset:2px; }
button:disabled { opacity:0.42; }
button.primary,button.play,button.violet { background-color:@accent_b; background-image:linear-gradient(135deg,@accent_a,@accent_b); color:@on_accent; border-color:@accent_b; }
button.primary label,button.play label,button.violet label { color:@on_accent; font-weight:800; }
button.primary:hover,button.play:hover,button.violet:hover { background-color:@accent_b_hover; background-image:linear-gradient(135deg,@accent_a_hover,@accent_b_hover); border-color:@accent_b_hover; }
button.play { min-height:36px; }
button.flat,button.quiet,button.nav,button.game-menu,button.breadcrumb { background:transparent; border-color:transparent; }
button.quiet:hover,button.nav:hover,button.game-menu:hover { background:@raised; border-color:transparent; }
button.quiet.active { background:#29323d; border-bottom:2px solid @accent; }
button.nav { padding:7px 9px; border-radius:8px; min-height:30px; }
button.nav label { color:#c4ccd6; font-size:15px; }
button.nav.active { background:#29323d; border-bottom:2px solid @accent; }
button.nav.active label { color:#ffffff; }
button.nav label.badge,button.nav.active label.badge { background:@accent_b; color:@on_accent; font-size:15px; font-weight:800; border-radius:5px; padding:2px 6px; min-width:14px; min-height:16px; }
button.steam { background:#243449; border-color:#405979; }
button.steam label { color:#c4ddff; }
button.steam-outline,button.steam-add { background:transparent; border-color:@line; }
button.steam-outline label,button.steam-add label { color:#c4ddff; }
button.violet-outline,button.game-section { background:@surface; border-color:@line; }
button.violet-outline label { color:@accent_soft; }
button.amber { background:#30291d; border-color:#59472c; }
button.amber label { color:#f1ce90; }
button.cyan { background:#1c2c32; border-color:#354f59; }
button.cyan label { color:#b0dce5; }
button.danger { background:transparent; border-color:#6d4140; }
button.danger label { color:#ffb6ad; }
button.game-delete { background:#942e2e; border-color:#b74444; color:rgb(255,255,255); }
button.game-delete label { color:rgb(255,255,255); }
button.game-delete:hover { background:#aa3535; }
button.action { min-height:32px; padding:7px 14px; }
button.action.play,button.action.game-section { min-height:34px; }
button.breadcrumb { padding:4px 8px; min-height:32px; }
button.breadcrumb label { color:@dim; font-size:16px; }
button.game-menu { padding:7px 10px; min-height:32px; }
entry,combobox button,spinbutton { background:@surface; color:@text; border:1px solid @line; border-radius:8px; padding:7px 10px; min-height:32px; }
entry:focus { border-color:@accent; }
combobox button label { font-size:16px; }
list,viewport,scrolledwindow { background:transparent; }
list row { padding:6px; border-radius:10px; border:1px solid transparent; }
list row:hover { background:@surface; }
list row:selected,list row:focus,list row.game-focused { background:#29323d; border:2px solid @accent; outline:0; }
.card,.surface-panel,.preset-detail,.selection-bar { background:@surface; border:1px solid @line; border-radius:12px; padding:14px; }
.settings-row { padding:14px 4px; border-bottom:1px solid @line; }
.banner { background:@surface; border:1px solid @line; border-left:3px solid @accent; border-radius:9px; padding:8px 12px; }
.library-game { padding:0; border:2px solid transparent; border-radius:11px; transition:background 150ms ease-out,border-color 150ms ease-out; }
.library-game.game-focused { background:#20262d; border-color:@accent; }
.library-game.game-focused .cover-title { color:@text; }
button.poster { padding:0; border:0; border-radius:10px; background:@surface; }
button.poster:hover,button.poster.selected { border-color:@accent; }
button.poster:focus { outline:2px solid @accent; outline-offset:0; }
.game-card-info { padding:8px 5px 7px; }
.cover-title { font-size:16px; font-weight:700; }
.game-card-info label.platform-caption { color:@dim; font-size:15px; }
.game-card-info label.card-state { color:#9bdfb8; font-size:15px; }
.page-toolbar { padding:4px 0 8px; }
.port-card { background:@surface; border:1px solid @line; border-radius:12px; padding:0; }
button.catalog-open { padding:0; background:transparent; border:0; border-radius:11px; }
button.catalog-open:hover { background:@raised; }
.port-card-content { padding:11px 12px; }
.port-card-content label.title { font-size:17px; font-weight:700; }
.port-card-actions { padding:0 12px 12px; }
.port-card label.os-badge { color:#c4ddff; font-size:15px; }
.port-card label.install-state { color:#9bdfb8; font-size:15px; }
.summary-card { padding:14px 16px; background:@surface; border:1px solid @line; border-radius:12px; }
.summary-card label.summary-count { font-family:"Space Grotesk Light",Sans; font-size:30px; font-weight:700; }
.summary-card label.meta { font-size:16px; }
button.summary-game { padding:0; background:@surface; border:1px solid @line; border-radius:12px; }
button.summary-game:hover { border-color:#66717e; background:@raised; }
button.summary-game label.title { font-size:17px; }
.section-row { padding:4px 0; }
.game-tabs { padding-bottom:6px; border-bottom:1px solid @line; }
button.game-section.steam { background:#243449; border-color:#405979; }
button.game-section.amber { background:#30291d; border-color:#59472c; }
button.game-section.active { background:#29323d; border-color:@accent; }
label.game-title { font-size:28px; }
.compact label.game-title { font-size:25px; }
button.hero-cover { padding:0; border:0; border-radius:10px; }
button.profile-card { background:@surface; border:1px solid @line; border-radius:11px; padding:10px; }
button.profile-card:hover { background:@raised; border-color:#79828d; }
button.profile-card.chosen { background:@accent_bg; border-color:@accent; }
button.profile-card label { font-weight:400; }
button.profile-card label.profile-title { color:@text; font-size:18px; font-weight:700; }
button.profile-card label.profile-spec,.violet-icon { color:@accent_soft; font-size:16px; font-weight:600; }
button.profile-card label.meta { font-size:16px; }
label.rating { color:#f1ce90; font-size:16px; }
.profile-feedback { padding:2px; color:@accent; }
.profile-feedback label { font-size:16px; }
.change-details { background:@surface; border:1px solid @line; border-radius:10px; }
button.disclosure { padding:7px 8px; min-height:32px; background:transparent; border-color:transparent; }
button.disclosure label { color:@accent_soft; font-size:16px; }
.request-notice { background:@surface; border-left:4px solid @accent_b; padding:8px 14px; }
.apply-dock { background:@surface; border:1px solid @line; border-radius:11px; padding:10px 12px; }
label.dock-title { font-size:16px; font-weight:700; }
button.applied { background:#1d3529; border-color:#3a674d; }
button.applied label { color:#9bdfb8; }
button.applied:disabled { opacity:1; }
button.task { padding:10px 12px; border-radius:10px; }
button.task label.task-title { font-size:17px; font-weight:700; }
button.task label.meta { font-size:16px; font-weight:400; }
button.task.amber { background:#221e17; border-color:#4b402c; }
button.task.cyan { background:#152127; border-color:#2f454e; }
check { min-width:24px; min-height:24px; border:1px solid #79828d; border-radius:5px; background:@surface; }
check:checked { background:@accent_b; color:@on_accent; }
switch { background:@line; border-radius:12px; }
switch:checked { background:#9bdfb8; }
scrollbar { background:transparent; min-width:10px; min-height:10px; }
scrollbar slider { background:#616b78; border:2px solid @bg; border-radius:7px; }
scrollbar.vertical slider { min-width:6px; min-height:36px; }
scrollbar.horizontal slider { min-height:6px; min-width:36px; }
textview text { background:@surface; color:@text; }
.game-compatibility button { min-height:26px; padding:3px 8px; }
.game-compatibility .tag { padding:3px 8px; }
progressbar.conversion-progress text { color: @text; font-size:15px; }
progressbar.conversion-progress trough { min-height:8px; }
progressbar trough { background:#29323d; min-height:5px; border-radius:5px; }
progressbar progress { background-color:@accent_b; background-image:linear-gradient(90deg,@accent_a,@accent_b); border-radius:5px; }
.toast { background:#1c2025; border:1px solid #526c59; border-radius:12px; padding:12px 16px; }
label.toast-text { color:#d5f1df; font-size:17px; font-weight:600; }
.toast.error { border-color:#9e5a54; }
.toast.error label.toast-text { color:#ffb6ad; }
popover,menu { background:@surface; color:@text; border:1px solid @line; border-radius:10px; padding:5px; }
popover button,menuitem { padding:7px 10px; }
menuitem:hover,menuitem:selected,menuitem:selected label { background:#29323d; color:@text; }
.controller-focus,button.controller-focus,button.action.controller-focus,button.action.play.controller-focus,button.task.controller-focus,button.profile-card.controller-focus,button.poster.controller-focus,entry.controller-focus,switch.controller-focus,scale.controller-focus { outline:2px solid @focus_ring; outline-offset:2px; box-shadow:inset 0 0 0 1px @accent; }
combobox.controller-focus button { outline:2px solid @focus_ring; outline-offset:-2px; background:#29323d; }
label.control-glyph { background:#1c2025; border:1px solid #616b78; border-radius:6px; padding:3px 6px; color:#f1f3f5; font-size:15px; font-weight:700; }
label.control-stick { border-radius:14px; min-width:16px; padding:3px 5px; }
label.control-caption { color:@dim; font-size:15px; }
.deck-density .card,.deck-density .surface-panel { padding:12px; }
.deck-density button.profile-card { padding:10px; }
.deck-density .app-header button { min-height:30px; }
.deck-density .app-header { padding:4px 8px; }
.deck-density .settings-row { padding:10px 2px; }
.deck-density label.hero { font-size:25px; }
.deck-density .inline-page-heading { font-size:23px; }
.community-profile-row { min-height:48px; padding:9px 12px; }
'''

SCALES={'normal':1.0,'large':1.15,'xlarge':1.3}
THEMES=('dark','light')

# Brand colours come from the logo gradient (blue 4780cd to violet 6152b6). Text on the gradient is always white.
BRAND={
    'dark':{'ACCENT':'#8aa8f5','ACCENT_SOFT':'#b7c9fb','ACCENT_BG':'#1a2136','ACCENT_A':'#3f6fb8','ACCENT_B':'#5a49ad','ACCENT_A_HOVER':'#4373c1','ACCENT_B_HOVER':'#6e5cc6','ON_ACCENT':'#ffffff','FOCUS_RING':'#ffffff'},
    'light':{'ACCENT':'#3b5bc0','ACCENT_SOFT':'#34469a','ACCENT_BG':'#e3e9fb','ACCENT_A':'#3f6fb8','ACCENT_B':'#5a49ad','ACCENT_A_HOVER':'#3563aa','ACCENT_B_HOVER':'#4e3e9c','ON_ACCENT':'#ffffff','FOCUS_RING':'#161a20'},
}
# The stylesheet above is written for the black theme. The light theme swaps each colour for its counterpart.
LIGHT={
    '#942e2e':'#942e2e','#aa3535':'#aa3535','#b74444':'#b74444',
    '#08090b':'#f3f5f9','#121417':'#ffffff','#1c2025':'#e8ecf4','#f1f3f5':'#161a20','#b6bec9':'#4b5563','#343b45':'#c6cedb',
    '#29323d':'#dfe5f0','#66717e':'#8e9aab','#79828d':'#7b8696','#616b78':'#9aa5b5','#46515e':'#b5bfce','#c8d0da':'#3a4452','#20262e':'#e6ebf3',
    '#040506':'#eef1f7','#292e36':'#c6cedb','#c4ccd6':'#3f4958','#ffffff':'#0f1318','#20262d':'#e3e9f3',
    '#9bdfb8':'#1f7a46','#a4e9be':'#15663a','#182e24':'#dff4e7','#365e48':'#9bd1b0','#1d3529':'#dff4e7','#3a674d':'#9bd1b0',
    '#b6d7ff':'#1d4f91','#1d2c41':'#dde9fb','#3b5475':'#9db9e0','#c4ddff':'#1d4f91','#243449':'#dce8fa','#405979':'#9ab7e0',
    '#dbcbff':'#4b3a96','#2a243b':'#e8e2fa','#55476e':'#b8abdf',
    '#f5df9a':'#6b5200','#302b1c':'#faf0cc','#645333':'#dcc57a','#f1ce90':'#7a5a00','#30291d':'#fbf1d3','#59472c':'#dcc57a','#221e17':'#fbf3dc','#4b402c':'#dcc57a',
    '#ffc199':'#8a3d0b','#35271e':'#fde6d6','#735039':'#e3b08a',
    '#ffb8b2':'#8f1d17','#352225':'#fbe0de','#704147':'#e2a3a0','#ffb6ad':'#9a2a22','#6d4140':'#d99a96','#9e5a54':'#d6837c',
    '#1c2c32':'#dcf0f4','#354f59':'#9cc7d1','#b0dce5':'#1d5b6b','#152127':'#e0f1f5','#2f454e':'#a6cbd4',
    '#526c59':'#8cc3a2','#d5f1df':'#14532d',
}
# Colours painted with cairo, outside the stylesheet.
DRAWN={'dark':{'backdrop':(0.071,0.078,0.090),'image':(.11,.125,.145)},'light':{'backdrop':(0.925,0.941,0.969),'image':(.86,.89,.94)}}
ACTIVE='dark'

def set_theme(name):
    global ACTIVE
    ACTIVE=name if name in THEMES else 'dark'

def drawn(key):return DRAWN[ACTIVE][key]

def css(scale='normal',theme='dark'):
    """The stylesheet for a theme, with every font size multiplied by the chosen interface scale."""
    theme=theme if theme in THEMES else 'dark';text=TEMPLATE
    if theme=='light':text=re.sub(r'#[0-9a-fA-F]{6}',lambda m:LIGHT.get(m.group(0).lower(),m.group(0)),text)
    for key,value in BRAND[theme].items():text=text.replace('@'+key+'@',value)
    factor=SCALES.get(scale,1.0)
    if factor!=1.0:text=re.sub(r'font-size:(\d+)px',lambda m:'font-size:%dpx'%round(int(m.group(1))*factor),text)
    return text.encode()

CSS=css()

def brand_pixbuf(path,size,theme):
    """The logo scaled for the header. Its outline is white, so the light theme gets a dark copy of that outline."""
    from gi.repository import GdkPixbuf,GLib
    pixbuf=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),size,size,True)
    if theme!='light':return pixbuf
    pixbuf=pixbuf.copy() if pixbuf.get_has_alpha() else pixbuf.add_alpha(False,0,0,0)
    data=bytearray(pixbuf.get_pixels());stride=pixbuf.get_rowstride();channels=pixbuf.get_n_channels()
    for y in range(pixbuf.get_height()):
        for x in range(pixbuf.get_width()):
            i=y*stride+x*channels;r,g,b=data[i],data[i+1],data[i+2]
            # Blue/violet circle keeps its colour; light grey-white outline becomes the theme's text colour.
            if min(r,g,b)>150 and max(r,g,b)-min(r,g,b)<40:data[i],data[i+1],data[i+2]=0x2a,0x31,0x40
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(data)),GdkPixbuf.Colorspace.RGB,True,8,pixbuf.get_width(),pixbuf.get_height(),stride)
