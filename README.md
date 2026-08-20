# Circle of the Fish

**<https://circle-of-fish.github.io/>**

Source for the website of **Circle of the Fish** (복어회), a collective of junior
South Korean scholars of International Relations working to globalize IR by
recovering the ontologies through which East Asia — and the many worlds beyond
it — have understood the international.

The site is published in **English, Korean (한국어), Chinese (中文), and Japanese
(日本語)**.

## Building

The site is a small static generator: content lives in `data/*.json`, layout in
`templates/*.html.j2`, and `build.py` renders every page in every language into
the repository root, which is what GitHub Pages serves.

```bash
pip install jinja2
python build.py                      # write the site
python build.py --serve --port 8000  # build, then preview at localhost:8000
python build.py --serve --no-build   # preview what is already built
```

Output sits beside the source, so a build only ever deletes files a previous
build wrote (`generated_paths()` in `build.py` is the authoritative list).

## Editing content

Routine updates — adding a publication, logging a seminar, correcting an
affiliation — go through the editor at **`/admin/`**, which commits to
`data/*.json` and lets the `Rebuild site` workflow regenerate the pages. It
needs a fine-grained GitHub token with `Contents: Read and write` on this
repository; `NOTES.md` has the setup steps.

Everything a normal update touches is in `data/`:

| file | what it holds |
| --- | --- |
| `site.json` | site title, navigation, the fish parable, aims, contact, footer |
| `research.json` | theoretical and methodological orientation, the two research modules |
| `members.json` | member cards |
| `publications.json` | publications, grouped by theme, with summaries and full-text links |
| `seminars.json` | the seminar archive |
| `resources.json` | reading list, scholarly network, archives and tools |

Translatable strings are written as language bundles:

```json
{ "en": "Members", "ko": "구성원", "zh": "成员", "ja": "メンバー" }
```

A missing language falls back to English, so a partial translation still builds.
A plain string is used unchanged in all four languages — which is what
bibliographic data should be: **author names, titles, and journal names stay in
their original language everywhere.** Only summaries, blurbs, and interface text
are translated.

Two conventions worth knowing before editing the JSON by hand:

- list keys are named `entries`, never `items` (`items` collides with the dict
  method of the same name in the template language);
- templates run with undefined variables as errors, so optional per-record
  fields are read with `.get(...)`. Adding a new optional field means touching
  the template too.

## Layout

```
build.py                     static site generator
data/                        content (JSON, four languages)
templates/                   Jinja2 templates
assets/                      style.css, fish-circle.svg, favicon.svg — copied to the root
_build/                      one-off importers and the sand-circle generator
research/                    the research dossier the publication list was built from
*.html, ko/, zh/, ja/, …     build output — do not edit by hand
```

## The motif

The background figure is not decoration. The male white-spotted pufferfish
(*Torquigener albomaculatus*) ploughs a roughly two-metre geometric circle into
the seabed — radial ridges, an inner ring, a finely combed centre, shell
fragments laid along the spokes. `_build/make_fish_circle.py` draws that
geometry as an SVG. It is the group's answer to Kautilya: the fish, asked, turn
out to build things.
