"""Stick thresholds, held input and spatial game navigation."""
import unittest
from deck_library.gamepad import Repeater,stick_direction
from deck_library.navigation import neighbour

class NavigationTests(unittest.TestCase):
    def test_stick_dead_zone_and_hysteresis(self):
        self.assertIsNone(stick_direction(6000,0));self.assertIsNone(stick_direction(9000,0))
        self.assertEqual(stick_direction(11000,0),'right');self.assertEqual(stick_direction(7500,0,'right'),'right');self.assertIsNone(stick_direction(6000,0,'right'))
        self.assertEqual(stick_direction(-20000,0,'right'),'left');self.assertEqual(stick_direction(0,-20000),'up')
        self.assertEqual(stick_direction(20000,21000,'right'),'right');self.assertEqual(stick_direction(10000,24000,'right'),'down')
    def test_right_stick_repeats_but_activation_does_not(self):
        repeat=Repeater();self.assertEqual(repeat.events({'scroll_down','activate'},0),['activate','scroll_down']);self.assertEqual(repeat.events({'scroll_down','activate'},.4),['scroll_down'])
        self.assertEqual(repeat.events(set(),.5),[]);self.assertEqual(repeat.events({'activate'},.6),['activate'])
    def test_card_navigation_uses_rows_and_keeps_last_column(self):
        cards={'a':(0,0,160,240),'b':(190,0,160,240),'c':(380,0,160,240),'d':(0,280,160,240),'e':(190,280,160,240)}
        self.assertEqual(neighbour(cards,'a','right'),'b');self.assertEqual(neighbour(cards,'b','down'),'e');self.assertEqual(neighbour(cards,'c','down'),'e')
        self.assertIsNone(neighbour(cards,'c','right'));self.assertIsNone(neighbour(cards,'a','left'));self.assertIsNone(neighbour(cards,'a','up'))
        self.assertEqual(neighbour(cards,'e','up'),'b');self.assertEqual(neighbour(cards,None,'down'),'a')
    def test_list_navigation_and_platform_section_gaps(self):
        rows={'a':(0,0,400,80),'b':(0,100,400,80),'c':(0,350,400,80)}
        self.assertEqual(neighbour(rows,'b','down'),'c');self.assertEqual(neighbour(rows,'b','up'),'a');self.assertIsNone(neighbour(rows,'b','right'))

class MixedControlNavigationTests(unittest.TestCase):
    def test_vertical_movement_prefers_controls_in_the_same_column(self):
        from deck_library.navigation import control_neighbour
        controls={0:(300,100,140,46),1:(850,180,240,80),2:(280,260,250,220),3:(550,260,250,220)}
        self.assertEqual(control_neighbour(controls,0,'down'),2)
        self.assertEqual(control_neighbour(controls,2,'right'),3)
        self.assertEqual(control_neighbour(controls,2,'up'),0)

class CompositorFocusTests(unittest.TestCase):
    def test_steam_app_identity_accepts_shortcut_game_id_and_ignores_invalid_values(self):
        from deck_library.compositor_focus import steam_app_id
        self.assertEqual(steam_app_id({'SteamAppId':'3735928559'}),3735928559)
        self.assertEqual(steam_app_id({'SteamGameId':str((3735928559<<32)|0x02000000)}),3735928559)
        self.assertEqual(steam_app_id({'SteamAppId':'0','SteamGameId':'123'}),123)
        self.assertIsNone(steam_app_id({'SteamAppId':'invalid'}))

    def test_native_focus_property_matches_app_and_releases_x11_data(self):
        import ctypes as C
        from unittest.mock import Mock
        from deck_library.compositor_focus import GamescopeFocus
        reader=GamescopeFocus({'SteamAppId':'123'});reader.attempted=True;reader.display=1;reader.atom=2;reader.lib=Mock();reader.lib.XDefaultRootWindow.return_value=3
        value=C.c_ulong(123)
        def read(*args):
            C.cast(args[7],C.POINTER(C.c_ulong))[0]=6;C.cast(args[8],C.POINTER(C.c_int))[0]=32;C.cast(args[9],C.POINTER(C.c_ulong))[0]=1
            C.cast(args[11],C.POINTER(C.POINTER(C.c_ubyte)))[0]=C.cast(C.pointer(value),C.POINTER(C.c_ubyte));return 0
        reader.lib.XGetWindowProperty.side_effect=read
        self.assertTrue(reader.focused());value.value=769;self.assertFalse(reader.focused());self.assertEqual(reader.lib.XFree.call_count,2)
        reader.lib.XGetWindowProperty.return_value=1;reader.lib.XGetWindowProperty.side_effect=None;self.assertIsNone(reader.focused())
        reader.close();reader.lib.XCloseDisplay.assert_called_once_with(1)

    def test_ordinary_desktop_needs_no_gamescope_connection(self):
        from unittest.mock import patch
        from deck_library.compositor_focus import GamescopeFocus
        with patch('ctypes.CDLL',side_effect=AssertionError('unexpected X11 connection')):
            self.assertIsNone(GamescopeFocus({}).focused())
