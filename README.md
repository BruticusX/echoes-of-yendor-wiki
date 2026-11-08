# Echoes of Yendor Wiki

The game wiki for [Echoes of Yendor](https://github.com/BruticusX/echoes-of-yendor), styled after the in-game UI.

- `site/` is the whole website: plain static files (HTML, CSS, JS, images), no build step. Upload its contents to any web host.
- `site/data/game.json` and the sprites in `site/img/` are generated from the game's source by `tools/extract.py`, so stats match the game.

## Google Play button

The header and home page show a Google Play button. It says "Coming soon" until the game is published.
When it's live, open `site/js/config.js` and change `published: false` to `published: true`.
The link already points at the app ID `io.github.bruticusx.echoesofyendor`.

## Background music

The game's menu theme (`site/audio/`) loops in the background. Browsers only allow sound after a visitor
clicks or presses a key, so it starts then. The note button in the bottom-right corner turns it off or on,
and each visitor's choice is remembered in their browser. Volume is set at the top of `site/js/music.js`.

## Updating after game changes

```sh
git clone --depth 1 https://github.com/BruticusX/echoes-of-yendor game
rm -rf site/img/items site/img/mobs site/img/metals site/img/skills site/img/heroes site/data
python3 -I tools/extract.py game site
```

Hand-written pages (mechanics, home, changes) live in `site/js/app.js`.

## Preview locally

```sh
cd site && python3 -m http.server 8000
```
