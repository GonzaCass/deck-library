"""TodoJuegos-inspired surfaces and local typography, shared by the native interface."""
import ctypes,ctypes.util,pathlib

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

CSS=b'''
@define-color bg #08090b;
@define-color surface #121417;
@define-color raised #1c2025;
@define-color text #f1f3f5;
@define-color dim #b6bec9;
@define-color accent #f1a17d;
@define-color line #343b45;
window,dialog { background:@bg; color:@text; font-family:"Manrope ExtraLight","Noto Sans",Sans; font-size:16px; }
label { color:@text; }
label.meta,label.status,label.muted,label.subtitle { color:@dim; font-weight:400; }
label.meta,label.status { font-size:14px; }
label.library-count { font-size:15px; }
label.original-required { color:#f1ce90; font-size:14px; font-weight:700; }
label.hero,label.welcome-title,label.game-title,.inline-page-heading { font-family:"Space Grotesk Light","Noto Sans",Sans; font-size:28px; font-weight:700; letter-spacing:-0.4px; }
label.title,label.section-title { font-size:18px; font-weight:700; }
label.brand { font-family:"Space Grotesk Light",Sans; font-size:21px; font-weight:700; }
label.eyebrow,label.rail-heading { color:@dim; font-size:13px; font-weight:600; }
label.pill,label.platform-chip { color:@dim; font-size:13px; font-weight:600; }
label.platform-chip { background:@raised; border:1px solid @line; border-radius:6px; padding:3px 8px; }
.app-header { background:#040506; border-bottom:1px solid #292e36; padding:5px 12px; }
button { background:@surface; color:@text; border:1px solid @line; border-radius:9px; padding:7px 12px; min-height:24px; background-image:none; box-shadow:none; text-shadow:none; transition:background 150ms ease-out,border-color 150ms ease-out; }
button label { color:@text; font-size:15px; font-weight:600; }
button:hover { background:@raised; border-color:#66717e; }
button:active { background:#29323d; }
button:focus { outline:2px solid @accent; outline-offset:2px; }
button:disabled { opacity:0.42; }
button.primary,button.play,button.violet { background:@accent; color:#211109; border-color:@accent; }
button.primary label,button.play label,button.violet label { color:#211109; font-weight:800; }
button.primary:hover,button.play:hover,button.violet:hover { background:#ffc4a6; border-color:#ffc4a6; }
button.play { min-height:30px; }
button.flat,button.quiet,button.nav,button.game-menu,button.breadcrumb { background:transparent; border-color:transparent; }
button.quiet:hover,button.nav:hover,button.game-menu:hover { background:@raised; border-color:transparent; }
button.nav { padding:6px 10px; border-radius:8px; min-height:26px; }
button.nav label { color:#c4ccd6; font-size:15px; }
button.nav.active { background:#29323d; border-bottom:2px solid @accent; }
button.nav.active label { color:#ffffff; }
button.nav label.badge,button.nav.active label.badge { background:@accent; color:#211109; font-size:13px; font-weight:800; border-radius:5px; padding:2px 6px; min-width:14px; min-height:16px; }
button.steam { background:#243449; border-color:#405979; }
button.steam label { color:#c4ddff; }
button.steam-outline,button.steam-add { background:transparent; border-color:@line; }
button.steam-outline label,button.steam-add label { color:#c4ddff; }
button.violet-outline,button.game-section { background:@surface; border-color:@line; }
button.violet-outline label { color:#f4bd9f; }
button.amber { background:#30291d; border-color:#59472c; }
button.amber label { color:#f1ce90; }
button.cyan { background:#1c2c32; border-color:#354f59; }
button.cyan label { color:#b0dce5; }
button.danger { background:transparent; border-color:#6d4140; }
button.danger label { color:#ffb6ad; }
button.action { min-height:24px; padding:7px 12px; }
button.action.play,button.action.game-section { min-height:30px; }
button.breadcrumb { padding:2px 4px; min-height:24px; }
button.breadcrumb label { color:@dim; font-size:14px; }
button.game-menu { padding:4px 8px; min-height:24px; }
entry,combobox button,spinbutton { background:@surface; color:@text; border:1px solid @line; border-radius:8px; padding:6px 10px; min-height:26px; }
entry:focus { border-color:@accent; }
combobox button label { font-size:14px; }
list,viewport,scrolledwindow { background:transparent; }
list row { padding:6px; border-radius:10px; border:1px solid transparent; }
list row:hover { background:@surface; }
list row:selected,list row:focus,list row.game-focused { background:#29323d; border:2px solid @accent; outline:0; }
.card,.surface-panel,.preset-detail,.selection-bar { background:@surface; border:1px solid @line; border-radius:12px; padding:14px; }
.settings-row { padding:14px 4px; border-bottom:1px solid @line; }
.banner { background:@surface; border:1px solid @line; border-left:3px solid @accent; border-radius:9px; padding:8px 12px; }
.library-game { padding:0; border:2px solid transparent; border-radius:11px; transition:background 150ms ease-out,border-color 150ms ease-out; }
.library-game.game-focused { background:#20262d; border-color:@accent; }
.library-game.game-focused .cover-title { color:white; }
button.poster { padding:0; border:0; border-radius:10px; background:@surface; }
button.poster:hover,button.poster.selected { border-color:@accent; }
button.poster:focus { outline:2px solid @accent; outline-offset:0; }
.game-card-info { padding:8px 5px 7px; }
.cover-title { font-size:16px; font-weight:700; }
.game-card-info label.platform-caption { color:@dim; font-size:13px; }
.game-card-info label.card-state { color:#9bdfb8; font-size:13px; }
.page-toolbar { padding:4px 0 8px; }
.port-card { background:@surface; border:1px solid @line; border-radius:12px; padding:0; }
button.catalog-open { padding:0; background:transparent; border:0; border-radius:11px; }
button.catalog-open:hover { background:@raised; }
.port-card-content { padding:11px 12px; }
.port-card-content label.title { font-size:17px; font-weight:700; }
.port-card-actions { padding:0 12px 12px; }
.port-card label.os-badge { color:#c4ddff; font-size:13px; }
.port-card label.install-state { color:#9bdfb8; font-size:13px; }
.summary-card { padding:14px 16px; background:@surface; border:1px solid @line; border-radius:12px; }
.summary-card label.summary-count { font-family:"Space Grotesk Light",Sans; font-size:30px; font-weight:700; }
.summary-card label.meta { font-size:14px; }
button.summary-game { padding:0; background:@surface; border:1px solid @line; border-radius:12px; }
button.summary-game:hover { border-color:#66717e; background:@raised; }
button.summary-game label.title { font-size:17px; }
.section-row { padding:4px 0; }
.game-tabs { padding-bottom:6px; border-bottom:1px solid @line; }
button.game-section.active { background:#29323d; border-color:@accent; }
label.game-title { font-size:28px; }
.compact label.game-title { font-size:25px; }
button.hero-cover { padding:0; border:0; border-radius:10px; }
button.profile-card { background:@surface; border:1px solid @line; border-radius:11px; padding:14px; }
button.profile-card:hover { background:@raised; border-color:#79828d; }
button.profile-card.chosen { background:#25201e; border-color:@accent; }
button.profile-card label { font-weight:400; }
button.profile-card label.profile-title { color:@text; font-size:19px; font-weight:700; }
button.profile-card label.profile-spec,.violet-icon { color:#f1b99b; font-size:14px; font-weight:600; }
button.profile-card label.meta { font-size:14px; }
label.rating { color:#f1ce90; font-size:14px; }
.profile-feedback { padding:2px; color:@accent; }
.profile-feedback label { font-size:14px; }
.change-details { background:@surface; border:1px solid @line; border-radius:10px; }
button.disclosure { padding:6px; min-height:28px; background:transparent; border-color:transparent; }
button.disclosure label { color:#e4c1ae; font-size:16px; }
.apply-dock { background:@surface; border:1px solid @line; border-radius:11px; padding:10px 12px; }
label.dock-title { font-size:16px; font-weight:700; }
button.applied { background:#1d3529; border-color:#3a674d; }
button.applied label { color:#9bdfb8; }
button.applied:disabled { opacity:1; }
button.task { padding:10px 12px; border-radius:10px; }
button.task label.task-title { font-size:17px; font-weight:700; }
button.task label.meta { font-size:14px; font-weight:400; }
button.task.amber { background:#221e17; border-color:#4b402c; }
button.task.cyan { background:#152127; border-color:#2f454e; }
check { min-width:18px; min-height:18px; border:1px solid #79828d; border-radius:5px; background:@surface; }
check:checked { background:@accent; color:#211109; }
switch { background:@line; border-radius:12px; }
switch:checked { background:#9bdfb8; }
scrollbar { background:transparent; min-width:10px; min-height:10px; }
scrollbar slider { background:#616b78; border:2px solid @bg; border-radius:7px; }
scrollbar.vertical slider { min-width:6px; min-height:36px; }
scrollbar.horizontal slider { min-height:6px; min-width:36px; }
textview text { background:@surface; color:@text; }
progressbar trough { background:#29323d; min-height:5px; border-radius:5px; }
progressbar progress { background:@accent; border-radius:5px; }
.toast { background:#1c2025; border:1px solid #526c59; border-radius:12px; padding:12px 16px; }
label.toast-text { color:#d5f1df; font-size:17px; font-weight:600; }
.toast.error { border-color:#9e5a54; }
.toast.error label.toast-text { color:#ffb6ad; }
popover,menu { background:@surface; color:@text; border:1px solid @line; border-radius:10px; padding:5px; }
popover button,menuitem { padding:7px 10px; }
menuitem:hover,menuitem:selected,menuitem:selected label { background:#29323d; color:white; }
.controller-focus,button.controller-focus,button.action.controller-focus,button.action.play.controller-focus,button.task.controller-focus,button.profile-card.controller-focus,button.poster.controller-focus,entry.controller-focus,switch.controller-focus,scale.controller-focus { outline:2px solid white; outline-offset:2px; box-shadow:inset 0 0 0 1px @accent; }
combobox.controller-focus button { outline:2px solid white; outline-offset:-2px; background:#29323d; }
label.control-glyph { background:#1c2025; border:1px solid #616b78; border-radius:6px; padding:3px 7px; color:#f1f3f5; font-size:13px; font-weight:700; }
label.control-stick { border-radius:14px; min-width:16px; padding:3px 5px; }
label.control-caption { color:@dim; font-size:13px; }
.deck-density .card,.deck-density .surface-panel { padding:12px; }
.deck-density button.profile-card { padding:11px; }
.deck-density .app-header button { min-height:26px; }
.deck-density .app-header { padding:3px 8px; }
.deck-density .settings-row { padding:10px 2px; }
.deck-density label.hero { font-size:25px; }
.deck-density .inline-page-heading { font-size:23px; }
.community-profile-row { min-height:48px; padding:9px 12px; }
'''
