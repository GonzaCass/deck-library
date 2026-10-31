# Windows components, Proton and community fixes

Open a Windows game and choose **Compatibility and fixes**. Its game page shows Proton beside a component status. These controls are inside the main window and work with the app's controller navigation.

## Component status

Deck Library reads the executable's PE headers and import tables without running game code. It identifies known Visual C++ 2005/2008/2010/2012/2013/2015–2022 runtimes, additional DirectX compiler/helper DLLs, XACT, XInput and legacy PhysX loaders. A header with no recognized components stays **not reviewed**. An unreadable executable does not become a successful check.

**Components present** means the imported DLLs were found in the game directory or its prefix with the executable's architecture. It is not a gameplay test. DLLs already provided by Proton also count as present. Dynamic and transitive dependencies can be missed; PE imports do not fully describe a game's requirements. Base DirectX 9/11/12 translation is managed by Proton, not replaced by installing a complete DirectX bundle.

If a Steam entry points at a launcher or folder, **Choose executable** selects the file to inspect without changing its Steam shortcut. Prototype 2, Splinter Cell: Conviction and Blacklist are also discovered from their installed Steam manifests. Multiple executable choices require selection rather than guessing which renderer the player uses.

## Preparing missing components

The component page lists the detected requirements and selects missing ones. **Prepare components** reviews the selection and installs in that game's prefix. Managed Windows games opened from Deck Library go through this page before launch when imports are missing; **Try the game** skips that check for one attempt.

- Managed ports use their existing persistent per-port prefix. Standalone EXEs use their existing per-entry prefix. Project 2099 follows its selected runtime prefix.
- Steam-owned games use their AppID's existing prefix and the selected Steam Proton build. Launch once through Steam first. Ambiguous prefixes are not modified.
- A managed prefix can be initialized with the selected Proton before preparation. If that already supplies the components, additional installers are skipped.
- Winetricks **20260125** is downloaded from its upstream tag and checked against a pinned SHA-256. A Protontricks Flatpak provides its execution tools when needed; Wine and the prefix come from the selected Proton/game. Only fixed, recognized Winetricks verbs are accepted.
- **Cancel** stops the current preparation process. Changes already made inside the prefix can remain; review the component status before retrying.
- The registry and Winetricks log are backed up before changes. This is **not a full-prefix backup or a complete rollback of installed DLLs**. Partial failure is reported and retains the backup.
- Preparation checks both the Winetricks installation log and the imported DLL files afterward. It does not mark gameplay as verified.

Game files and saves are not deliberately deleted or replaced by this flow. Installing redistributables modifies the selected prefix. Close the game before preparation.

## Proton recommendations

For managed games, **Automatic** prefers an already installed Proton version from a shipped, user-confirmed game profile. An explicit per-game choice takes precedence. When no matching recommendation is installed, Automatic retains its existing fallback behavior.

A **Use recommended Proton** action appears when a shipped, user-confirmed profile identifies a Proton version for this game. It uses an already installed build and the existing per-game selector. A missing build is reported rather than silently substituting another version. Community profile text does not automatically execute commands or change the runtime.

Managed launchers use the stored choice both from Deck Library and their Steam shortcut. Steam-owned/direct Steam compatibility remains controlled in Steam Properties. This release does not install new Proton distributions or claim a universally best version for every game.

## Community fix links

The initial resource list includes:

- [Prototype2Fix author's page](https://www.nexusmods.com/prototype2/mods/42).
- [Conviction FusionFix author instructions](https://github.com/ThirteenAG/WidescreenFixesPack/blob/master/.github/docs/scc.md), including Proton DLL overrides, plus its Linux issue reports.
- [Blacklist FusionFix author instructions](https://github.com/ThirteenAG/WidescreenFixesPack/blob/master/.github/docs/scb.md).
- Each game's ProtonDB reports.

These are external resources, not bundled mod installers or Deck verification badges. No patch archive is copied into those games automatically. A future package recipe needs its supported game versions, exact download, checksum, target files, overrides, backup behavior and testing evidence. The existing GTA IV and Shattered Dimensions actions remain available for their reviewed recipes.

## Validation

Automated tests cover bounded PE inspection, architecture checks, game-specific prefix selection, failed preparation, resource matching and the inline controller flow. A real isolated prefix test initialized Proton 11.0, removed a test compiler DLL, installed D3DCompiler 47 with the pinned Winetricks script through Protontricks Flatpak, and verified the resulting DLL and installation log. The synthetic executable was inspected only; no game binary was launched.

This validates that execution path, not every redistributable/Proton combination. Prototype 2, Conviction and Blacklist gameplay and their external patches were not tested by this change.
