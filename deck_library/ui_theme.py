"""Console surfaces and local typography, shared by the native interface."""
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
@define-color ambience @AMBIENCE@;
window,dialog { background:@bg; color:@text; font-family:"Noto Sans",Sans; font-size:16px; }
label { color:@text; }
label.meta,label.status,label.muted,label.subtitle { color:@dim; font-weight:400; }
label.meta,label.status { font-size:16px; }
label.library-count { font-size:15px; }
label.original-required { color:#f1ce90; font-size:16px; font-weight:700; }
label.tag,button label.tag { font-size:15px; font-weight:600; border:1px solid #46515e; border-radius:4px; padding:2px 6px; color:#c8d0da; background:#20262e; }
flowbox.tag-row > flowboxchild { padding:0; }
label.tag-green,button label.tag-green { color:#a4e9be; background:#182e24; border-color:#365e48; }
label.tag-blue,button label.tag-blue { color:#b6d7ff; background:#1d2c41; border-color:#3b5475; }
label.tag-violet,button label.tag-violet { color:#dbcbff; background:#2a243b; border-color:#55476e; }
label.tag-yellow,button label.tag-yellow { color:#f5df9a; background:#302b1c; border-color:#645333; }
label.tag-orange,button label.tag-orange { color:#ffc199; background:#35271e; border-color:#735039; }
label.tag-red,button label.tag-red { color:#ffb8b2; background:#352225; border-color:#704147; }
.plat-tag { border:1px solid #46515e; border-radius:6px; padding:3px 8px; background:alpha(#121417,.88); }
.plat-tag label,.plat-tag drawingarea { font-size:13px; font-weight:700; color:#f1f3f5; }
.plat-tag-green { border-color:#365e48; background:alpha(#182e24,.92); }
.plat-tag-green label,.plat-tag-green drawingarea { color:#a4e9be; }
.plat-tag-blue { border-color:#3b5475; background:alpha(#1d2c41,.92); }
.plat-tag-blue label,.plat-tag-blue drawingarea { color:#b6d7ff; }
.plat-tag-violet { border-color:#55476e; background:alpha(#2a243b,.92); }
.plat-tag-violet label,.plat-tag-violet drawingarea { color:#dbcbff; }
.plat-tag-yellow { border-color:#645333; background:alpha(#302b1c,.92); }
.plat-tag-yellow label,.plat-tag-yellow drawingarea { color:#f5df9a; }
.plat-tag-red { border-color:#704147; background:alpha(#352225,.92); }
.plat-tag-red label,.plat-tag-red drawingarea { color:#ffb8b2; }
label.compatibility-badge,button label.compatibility-badge { font-size:16px; font-weight:700; padding:4px 8px; }
label.hero,label.welcome-title,label.game-title,.inline-page-heading { font-family:"Space Grotesk Light","Noto Sans",Sans; font-size:28px; font-weight:700; letter-spacing:-0.4px; }
label.title,label.section-title { font-size:18px; font-weight:700; }
label.brand { font-family:"Space Grotesk Light",Sans; font-size:21px; font-weight:700; }
label.eyebrow,label.rail-heading { color:@dim; font-size:15px; font-weight:600; }
label.pill,label.platform-chip { color:@dim; font-size:15px; font-weight:600; }
label.platform-chip { background:@raised; border:1px solid @line; border-radius:4px; padding:3px 8px; }
.app-header { background:#040506; border-bottom:1px solid #292e36; padding:5px 12px; }
button { background:@surface; color:@text; border:1px solid @line; border-radius:8px; padding:7px 14px; min-height:32px; background-image:none; box-shadow:none; text-shadow:none; transition:background 180ms ease-out,border-color 180ms ease-out; }
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
button.nav { padding:7px 9px; border-radius:6px; min-height:30px; }
button.nav label { color:#c4ccd6; font-size:15px; }
button.nav.active { background:#29323d; border-bottom:2px solid @accent; }
button.nav.active label { color:#ffffff; }
button.nav label.badge,button.nav.active label.badge { background:@accent_b; color:@on_accent; font-size:15px; font-weight:800; border-radius:4px; padding:2px 6px; min-width:14px; min-height:16px; }
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
list row { padding:6px; border-radius:8px; border:1px solid transparent; }
list row:hover { background:@surface; }
list row:selected,list row:focus,list row.game-focused { background:#29323d; border:2px solid @accent; outline:0; }
.card,.surface-panel,.preset-detail,.selection-bar { background:@surface; border:1px solid @line; border-radius:10px; padding:14px; }
.settings-row { padding:14px 4px; border-bottom:1px solid @line; }
.banner { background:@surface; border:1px solid @line; border-left:3px solid @accent; border-radius:8px; padding:8px 12px; }
.library-game { padding:0; border:2px solid transparent; border-radius:10px; transition:background 180ms ease-out,border-color 180ms ease-out; }
.library-game.game-focused { background:#20262d; border-color:@accent; }
.library-game.game-focused .cover-title { color:@text; }
button.poster { padding:0; border:0; border-radius:8px; background:@surface; }
button.poster:hover,button.poster.selected { border-color:@accent; }
button.poster:focus { outline:2px solid @accent; outline-offset:0; }
.game-card-info { padding:8px 5px 7px; }
.cover-title { font-size:16px; font-weight:700; }
.game-card-info label.platform-caption { color:@dim; font-size:15px; }
.game-card-info label.card-state { color:#9bdfb8; font-size:15px; }
.page-toolbar { padding:4px 0 8px; }
.port-card { background:@surface; border:1px solid @line; border-radius:10px; padding:0; }
button.catalog-open { padding:0; background:transparent; border:0; border-radius:8px; }
button.catalog-open:hover { background:@raised; }
.port-card-content { padding:8px 9px; }
.port-card-content label.title { font-size:17px; font-weight:700; }
.port-card-actions { padding:0 12px 12px; }
.port-card label.os-badge { color:#c4ddff; font-size:15px; }
.port-card label.install-state { color:#9bdfb8; font-size:15px; }
.summary-card { padding:14px 16px; background:@surface; border:1px solid @line; border-radius:10px; }
.summary-card label.summary-count { font-family:"Space Grotesk Light",Sans; font-size:30px; font-weight:700; }
.summary-card label.meta { font-size:16px; }
button.summary-game { padding:0; background:@surface; border:1px solid @line; border-radius:8px; }
button.summary-game:hover { border-color:#66717e; background:@raised; }
button.summary-game label.title { font-size:17px; }
.section-row { padding:4px 0; }
.game-tabs { padding-bottom:6px; border-bottom:1px solid @line; }
button.game-section.steam { background:#243449; border-color:#405979; }
button.game-section.amber { background:#30291d; border-color:#59472c; }
button.game-section.active { background:#29323d; border-color:@accent; }
label.game-title { font-size:28px; }
.compact label.game-title { font-size:25px; }
button.hero-cover { padding:0; border:0; border-radius:8px; }
button.profile-card { background:@surface; border:1px solid @line; border-radius:8px; padding:10px; }
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
.apply-dock { background:@surface; border:1px solid @line; border-radius:8px; padding:10px 12px; }
label.dock-title { font-size:16px; font-weight:700; }
button.applied { background:#1d3529; border-color:#3a674d; }
button.applied label { color:#9bdfb8; }
button.applied:disabled { opacity:1; }
button.task { padding:10px 12px; border-radius:8px; }
button.task label.task-title { font-size:17px; font-weight:700; }
button.task label.meta { font-size:16px; font-weight:400; }
button.task.amber { background:#221e17; border-color:#4b402c; }
button.task.cyan { background:#152127; border-color:#2f454e; }
check { min-width:24px; min-height:24px; border:1px solid #79828d; border-radius:4px; background:@surface; }
check:checked { background:@accent_b; color:@on_accent; }
switch { background:@line; border-radius:12px; }
switch:checked { background:#9bdfb8; }
scrollbar { background:transparent; min-width:0; min-height:0; opacity:0; }
scrollbar slider { background:transparent; border:0; border-radius:0; min-width:0; min-height:0; opacity:0; }
scrollbar.vertical slider { min-width:0; min-height:0; opacity:0; }
scrollbar.horizontal slider { min-height:0; min-width:0; opacity:0; }
textview text { background:@surface; color:@text; }
.game-compatibility button { min-height:26px; padding:3px 8px; }
.game-compatibility .tag { padding:3px 8px; }
progressbar.conversion-progress text { color: @text; font-size:15px; }
progressbar.conversion-progress trough { min-height:8px; }
progressbar trough { background:#29323d; min-height:5px; border-radius:5px; }
progressbar progress { background-color:@accent_b; background-image:linear-gradient(90deg,@accent_a,@accent_b); border-radius:5px; }
.toast { background:#1c2025; border:1px solid #526c59; border-radius:8px; padding:12px 16px; }
label.toast-text { color:#d5f1df; font-size:17px; font-weight:600; }
.toast.error { border-color:#9e5a54; }
.toast.error label.toast-text { color:#ffb6ad; }
popover,menu { background:@surface; color:@text; border:1px solid @line; border-radius:10px; padding:5px; }
popover button,menuitem { padding:7px 10px; }
menuitem:hover,menuitem:selected,menuitem:selected label { background:#29323d; color:@text; }
.controller-focus,button.controller-focus,entry.controller-focus,switch.controller-focus,scale.controller-focus,expander.controller-focus,expander:focus { outline:2px solid @focus_ring; outline-offset:2px; box-shadow:none; }
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

/* Console shell: quiet surfaces, understated navigation and artwork as the hierarchy. */
.app-header { background:@bg; border-bottom:0; padding:6px 14px; }
.deck-density .app-header { padding:6px 14px; }
.deck-density .app-header button.console-round { min-height:20px; min-width:20px; padding:8px; }
button.nav { border-radius:6px; padding:7px 10px; min-height:30px; }
button.nav.active { background:transparent; border:1px solid transparent; border-bottom:2px solid @text; }
button.nav.active label { color:@text; }
button.nav.active label.badge { color:@on_accent; }
button.search-pill { border-radius:18px; padding:7px 16px; min-height:30px; background:@text; color:@bg; border:1px solid @text; }
button.search-pill label,button.search-pill drawingarea { color:@bg; font-weight:800; }
button.search-pill:hover { background:@dim; border-color:@dim; }
.port-hero-centered { padding:2px 12px 4px; }
button.port-install-cta,.port-workspace button.port-install-cta { min-width:180px; min-height:38px; padding:6px 24px; border-radius:10px; background:@text; color:@bg; border:1px solid @text; }
button.port-install-cta label,.port-workspace button.port-install-cta label { color:@bg; font-size:16px; font-weight:800; }
button.port-install-cta:hover,.port-workspace button.port-install-cta:hover { background:@dim; border-color:@dim; }
button.console-round { min-width:24px; min-height:24px; padding:12px; border-radius:8px; background:@raised; border:1px solid transparent; }
button.console-round:hover,button.console-round.active { background:@accent_bg; border-color:@accent; }
.shell-menu button.nav { border-radius:6px; }
button.shell-menu label.badge { background:@accent_b; color:@on_accent; font-size:15px; font-weight:800; border-radius:4px; padding:2px 6px; }
label.console-title { font-family:"Noto Sans",Sans; font-size:48px; font-weight:800; letter-spacing:-1px; }
.deck-density label.console-title { font-size:46px; }
label.console-eyebrow { color:@accent_soft; font-size:14px; font-weight:700; letter-spacing:1.4px; }
.console-home .tag { border:0; border-radius:8px; padding:5px 12px; font-size:13px; }
button.console-play,button.action.play { color:@bg; border-radius:8px; min-height:34px; padding:10px 24px; background-image:none; background:@text; border:1px solid @text; }
button.console-play drawingarea,button.action.play drawingarea { color:@bg; }
button.console-play label,button.action.play label { color:@bg; font-size:19px; font-weight:800; }
button.console-play:hover,button.action.play:hover { background-image:none; background:@dim; border-color:@dim; }
button.console-play { min-width:110px; }
button.console-card { padding:3px; border:2px solid transparent; border-radius:8px; background:transparent; }
button.console-card.featured { border-color:@dim; }
button.console-card:hover,button.console-card:focus,button.console-card.controller-focus { border-color:@text; outline:0; box-shadow:0 0 0 1px @text; }
button.console-all { border:2px dashed @line; border-radius:8px; background:transparent; }
button.console-all:hover { background:@surface; border-color:@dim; }
.console-utility { padding-top:8px; border-top:1px solid alpha(@line,.45); }
.summary-card { padding:6px 12px; background:@surface; border:1px solid alpha(@line,.65); border-radius:8px; }
.summary-card label.summary-count { font-family:"Noto Sans",Sans; font-size:16px; font-weight:800; }
.summary-card label.meta { font-size:14px; }
button.console-secondary { background:@raised; border:1px solid alpha(@line,.8); min-height:34px; padding:10px 18px; border-radius:8px; }
button.console-secondary:hover { background:@surface; border-color:@dim; }
.library-game { border-radius:10px; padding:3px; }
.library-game.game-focused { background:transparent; border-color:@text; }
button.poster { border-radius:8px; background:transparent; }
.game-card-info { padding:8px 6px; }
.game-card-info label.platform-caption { font-size:13px; }
.card,.surface-panel,.preset-detail,.port-card { border-radius:10px; }
button.profile-card { border-radius:8px; }
.game-tabs { border-bottom:0; }
button.game-section { border-radius:8px; }
label.control-glyph { border-radius:20px; min-width:17px; min-height:17px; padding:3px; }
.hint-activate label.control-glyph { background:#9bdfb8; border-color:#9bdfb8; color:#08090b; }
.hint-options label.control-glyph { background:#f5df9a; border-color:#f5df9a; color:#08090b; }
.hint-search label.control-glyph { background:#b6d7ff; border-color:#b6d7ff; color:#08090b; }
.hint-back label.control-glyph { background:#ffb8b2; border-color:#ffb8b2; color:#08090b; }
.account-hero { padding:22px 32px; min-width:420px; }
button.logout-cta { background:#352225; border:1px solid #704147; min-height:38px; padding:10px 22px; border-radius:10px; }
button.logout-cta label,button.logout-cta drawingarea { color:#ffb8b2; font-weight:700; }
button.logout-cta:hover { background:#942e2e; border-color:#b74444; }
button.logout-cta:hover label,button.logout-cta:hover drawingarea { color:#ffffff; }

/* Shared controls follow the home screen's neutral hierarchy. */
* { outline-color:@focus_ring; }
button { border-radius:8px; background:@raised; border-color:transparent; padding:8px 16px; }
button:hover { background:@surface; border-color:@dim; }
button:focus { outline:2px solid @focus_ring; outline-offset:2px; }
button.primary,button.play,button.violet { background-image:none; background:@text; color:@bg; border-color:@text; }
button.primary label,button.play label,button.violet label,
button.primary drawingarea,button.play drawingarea,button.violet drawingarea { color:@bg; }
button.primary:hover,button.play:hover,button.violet:hover { background-image:none; background:@dim; border-color:@dim; }
button.steam,button.steam-outline,button.steam-add,button.violet-outline,button.cyan,button.amber,
button.task.cyan,button.task.amber,button.game-section.steam,button.game-section.amber {
    background:@raised; color:@text; border-color:transparent;
}
button.steam label,button.steam-outline label,button.steam-add label,button.violet-outline label,
button.cyan label,button.amber label { color:@text; }
button.steam:hover,button.cyan:hover,button.amber:hover,button.violet-outline:hover { background:@surface; border-color:@dim; }
button.action { padding:8px 16px; }
button.quiet,button.flat,button.game-menu,button.breadcrumb { background:transparent; border-color:transparent; }
button.quiet:hover,button.game-menu:hover,button.breadcrumb:hover { background:@raised; }
button.danger,button.game-delete { background:transparent; border-color:transparent; color:#ffb6ad; }
button.danger label,button.game-delete label { color:#ffb6ad; }
button.danger:hover,button.game-delete:hover { background:#352225; border-color:#704147; }
button.game-section { border:1px solid transparent; background:@raised; padding:8px 18px; }
button.game-section.active,button.quiet.active { background:@text; color:@bg; border:1px solid @text; }
button.game-section.active label,button.game-section.active drawingarea,button.quiet.active label { color:@bg; }
button.nav.quiet.active { background:transparent; color:@text; border:1px solid transparent; border-bottom:2px solid @text; }
button.nav.quiet.active label,button.nav.quiet.active drawingarea { color:@text; }
button.danger.logout-cta { background:#352225; border:1px solid #704147; min-height:34px; padding:10px 22px; border-radius:8px; }
button.danger.logout-cta label,button.danger.logout-cta drawingarea { color:#ffb8b2; font-weight:700; }
button.danger.logout-cta:hover { background:#942e2e; border-color:#b74444; }
button.danger.logout-cta:hover label,button.danger.logout-cta:hover drawingarea { color:#ffffff; }
button.profile-card { background:@surface; border:1px solid @line; border-radius:8px; padding:14px; }
button.profile-card.chosen { background:@raised; border-color:@text; }
.deck-density button.profile-card { padding:12px; }
.apply-dock { background:transparent; border:0; border-bottom:1px solid @line; border-radius:0; padding:10px 0 16px; }
.game-workspace .apply-dock { padding:4px 0 8px; }
.game-workspace .apply-dock button.action,button.game-section-back,.game-tabs button.action { min-height:30px; padding:6px 16px; }
.game-workspace .apply-dock button.play { min-height:34px; }
.card,.surface-panel,.preset-detail,.change-details { background:alpha(@surface,.55); border:1px solid alpha(@line,.28); border-radius:12px; }
.port-card { background:@surface; border-color:alpha(@line,.55); border-radius:12px; }
.console-page { background-image:linear-gradient(145deg,alpha(@ambience,.38),alpha(@bg,0) 42%); }
label.hero,label.welcome-title,.inline-page-heading { font-family:"Noto Sans",Sans; font-size:34px; font-weight:800; letter-spacing:-.7px; }
.deck-density label.hero,.deck-density .inline-page-heading { font-size:30px; }
.page-heading { padding:4px 2px; }
entry,combobox button,spinbutton { border-radius:8px; border-color:alpha(@line,.8); background:@surface; padding:8px 14px; }
entry { padding:5px 12px; }
.appearance-field combobox button { padding:5px 12px; }
spinbutton { padding:0; min-height:0; }
spinbutton entry { border:0; background:transparent; padding:5px 10px; min-height:32px; }
spinbutton button { border:0; border-radius:0; padding:5px 10px; min-width:24px; min-height:32px; }
.manual-options .card { padding:10px; }
entry:focus,combobox:focus button { border-color:@text; }
combobox { outline:0; }
combobox:focus button { outline:2px solid @focus_ring; outline-offset:1px; }
check { border-radius:4px; }
switch { border:1px solid @line; border-radius:20px; }
switch slider { background:@text; border-radius:20px; min-width:22px; min-height:22px; }
switch:checked { background:@ambience; }
.settings-row { padding:8px 4px; }
button.preference-row { background:@surface; border:1px solid alpha(@line,.5); border-radius:8px; padding:10px 14px; }
button.preference-row:hover { background:@raised; border-color:@dim; }
button.preference-row label.preference-title { font-size:16px; font-weight:700; }
button.preference-row label.meta { font-size:14px; font-weight:400; color:@dim; }
button.preference-row label.preference-action { font-size:14px; font-weight:600; color:@dim; }
.preference-icon { background:@raised; border-radius:8px; padding:8px; }
.appearance-group { background:@surface; border:1px solid alpha(@line,.5); border-radius:10px; padding:12px; }
.appearance-field { padding:4px 0; }
label.tag,button label.tag,label.platform-chip { border-radius:4px; }
expander { background:@surface; border:1px solid alpha(@line,.6); border-radius:8px; padding:10px 14px; }
expander:hover { background:@raised; border-color:@dim; }
expander:focus,expander.controller-focus { outline:2px solid @focus_ring; outline-offset:2px; background:@raised; border-color:@text; }
button.steam-pending-btn { padding:6px 10px; border-radius:6px; background:#243449; border:1px solid #405979; }
button.steam-pending-btn:hover { background:@raised; border-color:@dim; }
button.steam-pending-btn label.badge { background:@accent_b; color:@on_accent; font-size:13px; font-weight:800; border-radius:4px; padding:1px 5px; }
popover,menu { background:@surface; border-radius:10px; padding:8px; }
popover button,menuitem { border-radius:8px; padding:8px 14px; }
.banner,.toast { background:@raised; border:1px solid @line; border-radius:14px; padding:10px 16px; box-shadow:0 8px 24px rgba(0,0,0,.6); }
.console-home button.console-play { background:@text; color:@bg; border-color:@text; min-height:34px; padding:10px 24px; }
.console-home button.console-play:hover { background:@dim; border-color:@dim; }
.console-home button.console-round { background:@raised; border-color:transparent; min-width:24px; min-height:24px; padding:12px; }
.app-header button.console-round { background:@raised; border-color:transparent; }

/* Local tabs sit below the page heading and keep their selected state distinct from focus. */
.game-workspace label.game-title { font-size:24px; }
label.metadata-line { font-size:14px; font-weight:500; color:@dim; }
.game-workspace button.action,.game-workspace .apply-dock button.action,
.game-workspace .game-actions button,.port-workspace button { min-height:30px; padding:6px 12px; font-size:15px; }
.game-workspace button.action label,.game-workspace .game-actions button label { font-size:15px; }
.game-workspace .game-actions button.play { background:@text; border-color:@text; color:@bg; }
.game-workspace .game-actions button.play:hover { background:@dim; border-color:@dim; }
.game-workspace .game-actions button.play label,.game-workspace .game-actions button.play drawingarea { color:@bg; }
.game-workspace .apply-dock button.play { background:@accent_a; border-color:@accent_a; color:@on_accent; }
.game-workspace .apply-dock button.play:hover { background:@accent_a_hover; border-color:@accent_a_hover; }
.game-workspace .apply-dock button.play label,.game-workspace .apply-dock button.play drawingarea { color:@on_accent; }
.game-workspace .game-actions button.steam { background:@raised; border-color:@line; }
.game-workspace .game-actions button.game-menu { background:@raised; border-color:@line; }
.game-workspace .card,.port-workspace .card { padding:12px; }
.game-workspace .card button.action { background:@raised; border-color:@line; }
.game-workspace .card label.meta,.port-workspace label.meta { font-size:14px; }
.port-workspace .inline-page-heading { font-size:26px; }
.game-options-popover { padding:6px; }
.game-options-popover button.game-option { padding:6px 8px; min-height:30px; }
.game-options-popover button.game-option label { font-size:15px; font-weight:500; }
.game-options-popover button.game-option:hover { background:@raised; }
.subtab-bar { border-bottom:1px solid @line; padding-bottom:0; }
.game-metadata label.tag { font-size:13px; padding:2px 6px; }
button.section-tab { background:transparent; border:0; border-bottom:2px solid transparent; border-radius:0; padding:6px 12px; min-height:32px; box-shadow:none; }
button.section-tab label { color:@dim; font-weight:600; }
button.section-tab:hover { background:alpha(@raised,.55); }
button.section-tab.active { background:transparent; border-bottom-color:@text; }
button.section-tab.active label { color:@text; }
/* Semantic actions keep their colour in both themes and in compact workspaces. */
button.primary,button.search-pill {
    background-image:none; background:#2e62b2; border-color:#2e62b2; color:@on_accent;
}
button.primary:hover,button.search-pill:hover { background:#3972c4; border-color:#3972c4; }
button.primary label,button.primary drawingarea,button.search-pill label,button.search-pill drawingarea { color:@on_accent; }
button.play,button.action.play,button.console-play,button.port-install-cta,
.console-home button.console-play,.port-workspace button.port-install-cta,
.game-workspace .game-actions button.play,.game-workspace .apply-dock button.play {
    background-image:none; background:#1c7845; border-color:#1c7845; color:@on_accent;
}
button.play:hover,button.action.play:hover,button.console-play:hover,button.port-install-cta:hover,
.console-home button.console-play:hover,.port-workspace button.port-install-cta:hover,
.game-workspace .game-actions button.play:hover,.game-workspace .apply-dock button.play:hover {
    background:#228751; border-color:#228751;
}
button.play label,button.play drawingarea,button.action.play label,button.action.play drawingarea,
button.console-play label,button.console-play drawingarea,button.port-install-cta label,
.port-workspace button.port-install-cta label,
.console-home button.console-play label,.console-home button.console-play drawingarea,
.game-workspace .game-actions button.play label,.game-workspace .game-actions button.play drawingarea,
.game-workspace .apply-dock button.play label,.game-workspace .apply-dock button.play drawingarea { color:@on_accent; }
button.violet { background:#6152b6; border-color:#6152b6; color:@on_accent; }
button.violet:hover { background:#7161c7; border-color:#7161c7; }
button.violet label,button.violet drawingarea { color:@on_accent; }
/* GTK outlines are rectangular. Shadows follow each control's border radius
   without changing its size or flattening pill-shaped buttons. */
button:focus,button.controller-focus,button.poster:focus,button.poster.controller-focus,
button.console-card:focus,button.console-card.controller-focus,
combobox:focus button,combobox.controller-focus button,
entry.controller-focus,switch.controller-focus {
    outline:0; box-shadow:0 0 0 2px @focus_ring;
}
button.disclosure { border-radius:8px; }
/* Mouse clicks keep the selected state but do not leave a keyboard focus frame. */
.pointer-input button:focus,.pointer-input button.controller-focus,.pointer-input button.poster:focus,
.pointer-input entry.controller-focus,.pointer-input switch.controller-focus,.pointer-input scale.controller-focus,
.pointer-input combobox.controller-focus button,.pointer-input combobox:focus button,.pointer-input expander:focus {
    outline:0; box-shadow:none;
}
'''

SCALES={'normal':1.0,'large':1.15,'xlarge':1.3}
THEMES=('dark','light')

# Brand colours come from the logo gradient (blue 4780cd to violet 6152b6). Text on the gradient is always white.
BRAND={
    'dark':{'ACCENT':'#8aa8f5','ACCENT_SOFT':'#b7c9fb','ACCENT_BG':'#1a2136','ACCENT_A':'#3f6fb8','ACCENT_B':'#5a49ad','ACCENT_A_HOVER':'#4373c1','ACCENT_B_HOVER':'#6e5cc6','ON_ACCENT':'#ffffff','FOCUS_RING':'#ffffff','AMBIENCE':'#123c35'},
    'light':{'ACCENT':'#3b5bc0','ACCENT_SOFT':'#34469a','ACCENT_BG':'#e3e9fb','ACCENT_A':'#3f6fb8','ACCENT_B':'#5a49ad','ACCENT_A_HOVER':'#3563aa','ACCENT_B_HOVER':'#4e3e9c','ON_ACCENT':'#ffffff','FOCUS_RING':'#161a20','AMBIENCE':'#d8ece7'},
}
# The stylesheet above is written for the black theme. The light theme swaps each colour for its counterpart.
LIGHT={
    # Filled actions use the same accessible white-on-colour palette in both themes.
    '#1c7845':'#1c7845','#228751':'#228751','#2e62b2':'#2e62b2','#3972c4':'#3972c4','#6152b6':'#6152b6','#7161c7':'#7161c7',
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
DRAWN={'dark':{'backdrop':(0.071,0.078,0.090),'image':(.11,.125,.145),'canvas':(.031,.035,.043),'console':(.13,.39,.34)},'light':{'backdrop':(0.925,0.941,0.969),'image':(.86,.89,.94),'canvas':(.953,.961,.976),'console':(.60,.81,.75)}}
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
