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
