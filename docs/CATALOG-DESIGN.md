# Independent port catalog: source audit and proposed design

Research snapshot: 2026-10-30. This document is a design, not a replacement of the current runtime catalog.

## What the other projects actually do

| Project | Discovery and metadata | Releases and images | What Deck Library already reads |
| --- | --- | --- | --- |
| Quiver | Public first-party API at `https://api.quiverlauncher.com/api/v1`, with paginated apps, original games, project details and release status. A separate community repository holds editable JSON lists. | Its client reads project details and release history; release providers support GitHub and GitLab. Library artwork belongs to game/project records. A scheduled workflow generates platform metadata every six hours. | Apps, release status and original-game artwork from the API, plus the older community lists. The current adapter accepts GitHub projects only. |
| PortIntegration | A `PORTS_DATABASE` JSON literal inside `app.js`. A daily GitHub Actions job searches GitHub by topics and phrases, inspects READMEs/releases and updates suggestions/metadata. | GitHub REST requests, usually through a Cloudflare Worker, with browser caching. Local WebP covers, Wikipedia thumbnails and repository artwork as fallbacks. | JSON literals and the local cover manifest; JavaScript is never executed. |

PortIntegration's discovery has explicit filters: star thresholds, language checks, exclusions for forks, archived repositories, engines and non-games. Its search reads a limited number of results per query. These are discovery heuristics, not proof that a port is complete or runs on Steam Deck. Fork exclusion can hide a useful compatibility variant.

The live adapters returned 798 distinct GitHub project repositories from Quiver and 287 from PortIntegration, with 174 in common: 911 distinct repository links in the union. These counts include projects with different readiness levels; they are not counts of games installable or verified on Deck. Multiple repositories may implement the same game. Remote catalogs and counts change.

Sources inspected directly:

- [Quiver catalog client](https://github.com/tgeorgiadis/quiver-launcher/blob/main/Services/QuiverCatalogClient.cs)
- [Quiver release selection](https://github.com/tgeorgiadis/quiver-launcher/blob/main/lib/QuiverLauncher.Core/Services/CatalogReleaseSelection.cs)
- [Quiver community metadata workflow](https://github.com/tgeorgiadis/quiver-community-app-catalog/blob/main/.github/workflows/platform-index.yml)
- [PortIntegration database and browser metadata loading](https://github.com/Samuel-SSLabs/Port-Integration/blob/main/app.js)
- [PortIntegration discovery script](https://github.com/Samuel-SSLabs/Port-Integration/blob/main/scripts/discover-ports.js)
- [PortIntegration discovery schedule](https://github.com/Samuel-SSLabs/Port-Integration/blob/main/.github/workflows/auto-discover-ports.yml)

The audit reads public source and GET endpoints. Quiver identifies its API as its own service; it is not the GitHub API. Its launcher has an MIT license. No root license file was found for PortIntegration in this snapshot. The proposed implementation uses original code and links to upstream repositories; it does not copy either application's UI, source modules or image bundle.

## Proposed model

Keep separate identities for an original game, a port project, a release artifact and an installation recipe. Names and release dates must not be identity keys. Different ports/forks of one game appear as variants; a repository implementing multiple games can link to each original game.

An example record, with deliberately unresolved releases and checksums:

```json
{
  "schema_version": 2,
  "game": {
    "id": "switch-01007ef00011e000",
    "title": "The Legend of Zelda: Breath of the Wild",
    "original_platform": "Switch"
  },
  "project": {
    "id": "github:revivedx/savagewindrecomp",
    "provider": "github",
    "repository": "Revivedx/SavageWindRecomp",
    "name": "Savage Wind Recomp"
  },
  "recipe": {
    "id": "savagewind-linux-appimage",
    "os": "linux",
    "architecture": "x86_64",
    "package": "appimage",
    "runtime": {"kind": "native"},
    "originals": {
      "kind": "switch-dump",
      "title_ids": ["01007ef00011e000"],
      "minimum_update": "1.9.0",
      "accepts": ["nsp", "xci", "extracted-directory", "compiled-directory"]
    },
    "preparation": "switch-launcher"
  },
  "releases": [],
  "provenance": [
    {"source": "upstream", "url": "https://github.com/Revivedx/SavageWindRecomp"}
  ],
  "verification": {"status": "not-recorded", "evidence": []}
}
```

A resolved release adds its exact tag, upstream release ID/date, download URL, file size, checksum and platform/architecture. Choose the newest compatible artifact, not just the newest tag: a newer Windows-only release must not displace a working native Linux release. A Windows artifact can declare a Proton recipe and its tested version; it must not be presented as native Linux.

Recipes use an allowlist of preparation types implemented by Deck Library. Remote JSON cannot contain commands or scripts to execute automatically. Original-disc/title/revision checks, extraction and cleanup stay in those local adapters. This avoids treating an unreviewed catalog suggestion as an installer.

## Publication and updates

1. Maintain an editable Deck Library registry with stable identities, variants, original-data requirements and reviewed recipe IDs.
2. A scheduled GitHub Actions collector reads public source feeds and upstream GitHub/GitLab metadata. New discoveries go to a review queue/PR; it does not label them verified or make them automatically executable.
3. Resolve compatible release assets and produce a versioned static JSON snapshot. Keep provenance, first-seen time and upstream release time as different fields. Use conditional requests, rate-limit backoff and the last successful snapshot when a source fails.
4. Publish the snapshot on GitHub initially. The application downloads one small catalog, caches it and uses upstream download URLs directly. Ordinary users do not need a GitHub token for catalog browsing. A later server collector can perform the same work without changing the public format.
5. Keep compatibility reports separate: exact game revision, port tag, runtime/Proton, hardware, settings, test date and evidence. Ratings measure community feedback, not an invented compatibility percentage.

Discovery can combine existing feeds, curated known repositories and scoped GitHub searches. No public index is exhaustive. Search hits stay candidates until the recipe and required original data are understood. Unknown forks and small new projects should be reviewable rather than discarded solely for low star counts.

## Migration from the current app

- Preserve `catalog/ports.json` and the current live-source adapters as fallbacks.
- Add stable project/game identities to imported rows without changing existing library IDs or Steam AppIDs.
- Introduce the static snapshot reader, then move metadata refresh to the collector. Keep downloads, original-data wizards and existing local installations working throughout.
- Test unavailable feeds, missing/renamed repositories, GitLab projects, prereleases, Windows-only assets, older native releases, multi-game repositories and multiple variants of one game.

No new database, service deployment or runtime-source replacement was performed for this design.
