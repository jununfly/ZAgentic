# Why this fixture exists

It is a synthetic repository, not a copy of a real one. Nothing here is quoted
from another project; the layout is assembled to concentrate the conventions
that a wiki-style handbook actually uses and that this repository does not:

| ZAgentic | here | why it matters |
|---|---|---|
| `docs/` tree at the root | **no `docs/` at all** | discovery cannot fall back to `docs/README.md` or `docs/**/*-map.md`; only the root `docs-map:` pointer can find the map |
| map at `docs/README.md` | `handbook/map.md` | the map is a page among pages, not the directory index |
| `docs/architecture/<page>.md` | `handbook/architecture/subsystems/<page>.md` | architecture pages are nested a level deeper and share the directory with non-architecture content |
| front matter only | `spec/10-overview.md`, `handbook/notes/…` | numeric prefixes and date-stamped notes are ordinary wiki habits |
| `ta-` everywhere | `ta-` / `pa-` / `ba-` mixed | the prefix is a kind marker, not a house style |

`handbook/architecture/drafts/ta-checkout-v2.md` is loaded on purpose: an
unstable name that the map does not link. It is the negative control — the
naming rule must stay silent until the map actually claims the page
(`ExternalLayoutTest` maps it and asserts the diagnostic appears).

A real third-party copy would add bulk and licensing questions without adding a
case this fixture does not already cover: every difference above is a discovery
or scoping decision, not content.
