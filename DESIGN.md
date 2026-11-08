# Deck Library design system

How Deck Library looks and why. The source of truth is `deck_library/ui_theme.py` (GTK CSS, both themes) and `deck_library/gui_widgets.py` (shared widgets). This file describes the rules those files follow, so new screens stay consistent. [DECK-INTERFACE.md](docs/DECK-INTERFACE.md) describes the screens themselves.

## Visual theme

A console-style launcher for a 1280×800 handheld screen, used with a controller or touch more often than a mouse. Dark charcoal surfaces, portrait game covers as the main imagery and a few solid action colours that mean the same thing on every screen. Decoration stays low: thin borders, no heavy shadows, short transitions that the Animations setting can turn off.

## Colour tokens

Dark is the reference theme. The light theme replaces each colour through the `LIGHT` map in `ui_theme.py`; filled buttons keep the same colours in both themes.

| Token | Dark | Light | Role |
| --- | --- | --- | --- |
| `bg` | `#08090b` | `#f3f5f9` | Window and page background |
| `surface` | `#121417` | `#ffffff` | Cards, inputs, default buttons |
| `raised` | `#1c2025` | `#e8ecf4` | Hover, selected list item, popovers |
| `line` | `#343b45` | `#c6cedb` | Borders and separators |
| `text` | `#f1f3f5` | `#161a20` | Body text |
| `dim` | `#b6bec9` | `#4b5563` | Secondary text: metadata, status, subtitles |
| `accent` | `#8aa8f5` | `#3b5bc0` | Links, focus outline, active tab line |
| `accent_a` → `accent_b` | `#3f6fb8` → `#5a49ad` | same | Brand gradient from the logo: progress bars |
| `on_accent` | `#ffffff` | `#ffffff` | Text on filled buttons |

Action colours, always white text on a solid fill: Play and Install green `#1c7845`, primary and search blue `#2e62b2`, profiles violet `#6152b6`, delete red `#942e2e`. Steam buttons use a dark blue tint (`#243449` with `#c4ddff` text), and other danger actions are outlined, with red text and no fill. Status tags (green, blue, violet, yellow, orange, red) pair a light text colour with a dark tinted background and a mid-tone border of the same hue.

Platform colours for covers without art are set in `Poster.draw_poster` in `gui_widgets.py`.

**Contrast rules.** Text needs 4.5:1 against its background and control borders need 3:1, in both themes. `tests/test_theme_contrast.py` checks every CSS rule that sets both a text colour and a solid background, body text on each surface, white text on every filled button, and the hover and checkbox borders. The lowest button today is white on `#228751` at 4.51:1, so nothing lighter than that should be used behind white text.

## Typography

- Body: Noto Sans (from the system), 16 px. Secondary text 15 px. Nothing smaller than 13 px, used only for platform chips on covers.
- Section titles: 18 px bold. Page and game titles: Space Grotesk Light at 28 px, bold.
- Filled-button labels: weight 800.
- The interface scale setting multiplies every font size by 1.0, 1.15 or 1.3 (`SCALES`). Layouts must keep working at 1.3.
- Space Grotesk ships in `assets/fonts` and is loaded only for this app, so titles look the same whatever SteamOS has installed.

## Components

- **Buttons:** 8 px radius, at least 32 px tall (36 px for Play), 7×14 px padding. Default buttons use `surface` with a `line` border. Filled ones use the classes `primary`, `play` or `violet`. `steam` is tinted and `danger` is outlined. Use one filled button per area; everything else stays default.
- **Focus:** a 2 px `accent` outline with a 2 px offset on every focusable control. It must stay visible, because controller users navigate by focus.
- **Choice lists:** `Dropdown` from `ui_components.py` (a button that opens a list of large rows), never `Gtk.ComboBoxText`. Rows are at least 32 px tall, so they work by touch, and they close on a single tap.
- **Covers:** `Poster` keeps a fixed 2:3 frame with 8 px corners. The cover fills the frame without side bands, and a cover without art gets the platform colour, a monogram and the title. Badges sit in the top corners and stack vertically instead of overlapping.
- **Tags:** 4 px radius, 15 px semi-bold, tinted by meaning (green for works, yellow for needs attention, red for problems).
- **Inline pages and dialogs:** `InlineDialog` keeps commands in the page header. Content gets a 14 px right margin, so cards never touch the edge.

## Layout and depth

- Spacing steps of 4 px: 4, 8, 12, 16 and 24 px are the common gaps.
- Corner radius: 8 px for controls and cards, 10–12 px for large panels, 4–6 px for small chips.
- Depth comes from the step between `bg`, `surface` and `raised`, plus a border, not from drop shadows.
- Everything must fit 1280×800 with the on-screen keyboard closed. Lists scroll and headers stay in place.

## Motion

All motion lives in `deck_library/motion.py` and turns off with the Animations setting.

- Tabs, sections, inline pages and dialogs fade in from the background over 210 ms (`motion.enter_page`). Pages switch at once and only their opacity animates. Gtk.Stack slide and crossfade transitions are avoided because Gamescope can show their snapshot half laid out.
- Disclosures slide open in 220 ms and their content fades in alongside.
- Card grids fade their first 12 new cards in with a 22 ms stagger.
- Hover and selection changes animate colour, background and border over 160–180 ms (CSS `transition`).
- Ease-out curves only. No motion longer than about 300 ms, and nothing loops except loaders.

## Do and don't

- Do add new colours to both themes: the dark value in the CSS and its light counterpart in `LIGHT`, and keep the contrast test passing.
- Do keep labels short and concrete, in Spanish with an English translation (`deck_library/i18n_en`).
- Do make every action reachable with the controller: a sensible focus order and nothing that needs a pointer.
- Don't use colour alone to carry meaning; pair it with a word or an icon.
- Don't hide a primary action behind hover, a long press or a menu that only a mouse can open.
- Don't add a second primary button next to Play or Install.

## Guide for code agents

When building or changing a GTK screen here:

1. Use the `label`, `button` and `wrap_row` helpers from `gui_widgets.py`, `Dropdown` from `ui_components.py` and the CSS classes above. Avoid inline colours.
2. Give new colours a token or a `LIGHT` counterpart, then run `tests/test_theme_contrast.py`.
3. Check the screen at 1280×800 and at interface scale 1.3 in both themes, using a GTK test in `tests/test_gui_deck.py` or a screenshot.
