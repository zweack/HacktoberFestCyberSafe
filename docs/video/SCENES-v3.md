# v3 scene list: changes from v2

v3 has the same voiceover, timings, scenes, focus-camera moves and soundtrack as v2 (see `SCENES-v2.md` and
`SCRIPT-v2.md`, both still valid). Only the look changed. Source: `film/src/v3/` (composition `FilmV3`).

- **Light mode.** Page `#F4F6F8` (cool off-white), white cards with a `#D5DCE3` hairline, near-black text `#0E1620`,
  grey secondary text `#4E5D6C`, light code cards (white, dark code, blue strings). Shadows are soft.
- **Focus camera on light:** everything outside the highlighted region gets a pale veil (`rgba(244,246,248,0.72)`) instead
  of a dark dim. Highlight outlines are 6 px, and the accents are deepened slightly so they hold on white: red `#D62839`,
  green `#1E9E50`, yellow `#E0A100`, blue `#2F6FDB`. On the dark drill screenshots the veil reads as a grey wash, and the
  outlined rows stay full-strength.
- **Typefaces from kittyleads.com** (from the site's CSS: `--font-bricolage`, `--font-geist`, `--font-newsreader`):
  Bricolage Grotesque for headings, Geist for body and captions, Geist Mono for code. All three are OFL fonts from Google
  Fonts, loaded locally from `film/public/fonts/*.woff2`. The site's third font, Newsreader (a serif), is not used.
- **End card:** "Team CyberSafe · Hack Day Pune 2026" in dark grey (the yellow was too faint on white); the repo URL is in blue.
