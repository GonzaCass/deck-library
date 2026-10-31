# Savage Wind: Steam Deck configuration record

Port: [Savage Wind Recomp](https://github.com/Revivedx/SavageWindRecomp), Linux AppImage **v0.3.0-alpha.3**, with the user's own Switch game updated to **1.9.0**.

On 2026-10-30 a user confirmed good image quality and approximately **45–50 FPS** during gameplay with the settings below, except that the frame-rate target was still 90. After that report, **only the target was lowered to 60 FPS**. This is a subjective gameplay report, not a frametime benchmark or a claim of locked 60 FPS. No exact post-cap gameplay measurement has been recorded.

The default native configuration is `$XDG_DATA_HOME/savagewind/savagewind.ini`, normally `~/.local/share/savagewind/savagewind.ini`. A selected compiled-data directory can change that location. Close the game and back up the file before editing. Merge these options into the existing file; keep controls, audio, language and other unlisted options.

```ini
fullscreen = 1
window_size = 1280x800
frame_rate = 60
vsync = fast
upscaler = off
antialias = off
anisotropy = game
sharpening = 30
shadow_resolution = high
wide_view = 1
field_of_view = 100
async_shaders = 0
precompile_shaders = 1
```

These are the settings actually saved after the user's test. An earlier quality proposal used SMAA, 16× anisotropy and console shadows; those values do not describe the later confirmed configuration and must not be exported as though they did.

This record is a manual configuration guide. It does not add an automatic Savage Wind preset adapter or mark another version of the port as verified.
