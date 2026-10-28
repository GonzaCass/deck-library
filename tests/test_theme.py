import importlib.util,pathlib,re,unittest

ROOT=pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('ui_theme',ROOT/'deck_library/ui_theme.py');theme=importlib.util.module_from_spec(spec);spec.loader.exec_module(theme)

def luminance(color):
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    channels=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
    return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]

def contrast(a,b):
    bright,dark=sorted((luminance(a),luminance(b)),reverse=True);return (bright+.05)/(dark+.05)

def tokens(name,scale='normal'):
    return dict(re.findall(r'@define-color (\w+) (#[0-9a-fA-F]{6})',theme.css(scale,name).decode()))

class ThemeTests(unittest.TestCase):
    def test_the_light_theme_has_a_counterpart_for_every_colour_of_the_black_one(self):
        used={c.lower() for c in re.findall(r'#[0-9a-fA-F]{6}',theme.TEMPLATE)}
        self.assertEqual(sorted(used-set(theme.LIGHT)),[]);self.assertEqual(sorted(set(theme.LIGHT)-used),[])
    def test_every_theme_and_scale_resolves_all_placeholders_and_keeps_font_sizes_in_proportion(self):
        for name in theme.THEMES:
            for scale in theme.SCALES:
                text=theme.css(scale,name).decode();self.assertNotRegex(text,r'@[A-Z_]+@');self.assertIn('@define-color accent_a',text)
        normal=int(re.search(r'label\.hero[^}]*font-size:(\d+)px',theme.css('normal').decode()).group(1));large=int(re.search(r'label\.hero[^}]*font-size:(\d+)px',theme.css('xlarge').decode()).group(1))
        self.assertGreater(large,normal)
    def test_an_unknown_theme_falls_back_to_black(self):
        self.assertEqual(theme.css('normal','nope'),theme.css('normal','dark'))
    def test_text_and_brand_colours_stay_readable_in_both_themes(self):
        for name in theme.THEMES:
            colors=tokens(name)
            for foreground,background,minimum in (('text','bg',7),('text','surface',7),('dim','bg',4.5),('dim','surface',4.5),('dim','raised',4.5),('accent','bg',4.5),('accent','surface',4.5),('accent_soft','bg',4.5),('accent_soft','surface',4.5),('on_accent','accent_a',4.5),('on_accent','accent_b',4.5),('on_accent','accent_a_hover',4.5),('on_accent','accent_b_hover',4.5),('focus_ring','bg',7)):
                self.assertGreaterEqual(contrast(colors[foreground],colors[background]),minimum,f'{name}: {foreground} on {background}')
    def test_coloured_tags_stay_readable_in_both_themes(self):
        for name in theme.THEMES:
            css=theme.css('normal',name).decode()
            for tone in ('green','blue','violet','yellow','orange','red'):
                match=re.search(r'label\.tag-%s,button label\.tag-%s \{ color:(#\w+); background:(#\w+)'%(tone,tone),css)
                self.assertGreaterEqual(contrast(match.group(1),match.group(2)),4.5,f'{name}: {tone}')
    def test_the_brand_gradient_matches_the_logo_blue_to_violet(self):
        for name in theme.THEMES:
            colors=tokens(name);blue,violet=colors['accent_a'],colors['accent_b']
            self.assertGreater(int(blue[5:7],16),int(blue[1:3],16));self.assertGreater(int(violet[1:3],16),0x40)
    def test_drawn_colours_follow_the_active_theme(self):
        try:
            theme.set_theme('light');light=theme.drawn('backdrop');theme.set_theme('dark');dark=theme.drawn('backdrop')
        finally:theme.set_theme('dark')
        self.assertGreater(sum(light),sum(dark))

if __name__=='__main__':unittest.main()
