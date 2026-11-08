"""Both themes keep readable text (WCAG 4.5:1) and visible control borders (3:1)."""
import re,unittest
from deck_library import ui_theme

def luminance(value):
    value=value.lstrip('#');channels=[int(value[i:i+2],16)/255 for i in (0,2,4)]
    linear=[c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4 for c in channels]
    return 0.2126*linear[0]+0.7152*linear[1]+0.0722*linear[2]

def ratio(a,b):
    high,low=sorted((luminance(a),luminance(b)),reverse=True);return (high+0.05)/(low+0.05)

def resolved(theme):
    css=ui_theme.css(theme=theme).decode()
    names=dict(re.findall(r'@define-color\s+(\w+)\s+(#[0-9a-fA-F]{6})\s*;',css))
    return re.sub(r'@(\w+)',lambda m:names.get(m[1],m[0]),css),names

class ThemeContrastTests(unittest.TestCase):
    def test_rules_with_text_and_a_solid_background_are_readable(self):
        for theme in ui_theme.THEMES:
            css,_=resolved(theme);checked=0
            for selector,body in re.findall(r'([^{}]+)\{([^{}]*)\}',css):
                fg=re.search(r'(?<![-\w])color:\s*(#[0-9a-fA-F]{6})',body);bg=re.search(r'background(?:-color)?:\s*(#[0-9a-fA-F]{6})\s*;',body)
                if fg and bg:
                    checked+=1
                    with self.subTest(theme=theme,selector=' '.join(selector.split())[:80]):self.assertGreaterEqual(ratio(fg[1],bg[1]),4.5)
            self.assertGreater(checked,10)
    def test_body_text_is_readable_on_every_page_surface(self):
        for theme in ui_theme.THEMES:
            _,names=resolved(theme)
            for text in ('text','dim'):
                for surface in ('bg','surface','raised'):
                    with self.subTest(theme=theme,text=text,surface=surface):self.assertGreaterEqual(ratio(names[text],names[surface]),4.5)
    def test_filled_buttons_keep_white_text_readable(self):
        for theme in ui_theme.THEMES:
            brand=ui_theme.BRAND[theme]
            for fill in ('ACCENT_A','ACCENT_B','ACCENT_A_HOVER','ACCENT_B_HOVER'):
                with self.subTest(theme=theme,fill=fill):self.assertGreaterEqual(ratio(brand['ON_ACCENT'],brand[fill]),4.5)
        for fill in ('#1c7845','#228751','#2e62b2','#3972c4','#942e2e','#aa3535','#b74444','#6152b6','#7161c7'):
            with self.subTest(fill=fill):self.assertGreaterEqual(ratio('#ffffff',fill),4.5)
    def test_hover_and_checkbox_borders_stay_visible(self):
        for theme in ui_theme.THEMES:
            _,names=resolved(theme)
            for border in ('#66717e','#79828d'):
                shown=ui_theme.LIGHT.get(border,border) if theme=='light' else border
                for surface in ('surface','raised'):
                    with self.subTest(theme=theme,border=border,surface=surface):self.assertGreaterEqual(ratio(shown,names[surface]),3.0)

if __name__=='__main__':unittest.main()
