# Game feeds

The game downloads these files from this repository (raw files on `main`):

- `news.xml` – posts on the in-game News screen (newest first).
- `updates.json` – in-game update notices. Same shape as a GitHub releases list: an array of objects with
  `name` (version name), `html_url` (where to update, e.g. the Google Play page), `prerelease` (true/false)
  and `body`, which must contain `Internal version number: <versionCode>` and a short description above a
  line containing `---`. Leave it as `[]` when there is nothing to announce; Google Play delivers the updates.
