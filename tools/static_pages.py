"""Builds the wiki's standalone pages (privacy policy, name/logo notice, unlisted source page).
Run: python3 tools/static_pages.py <game repo checkout>"""
import os, sys, markdown, json

GAME = sys.argv[1]
SITE = os.path.join(os.path.dirname(__file__), "..", "site")
SOURCE_DIR = "src-277sg332gs"   # unlisted: linked only from the game's About screen
# the zips are uploaded straight to the server in dl-files/src-277sg332gs/ (dl-files is a subdomain folder,
# which site deploys leave alone); versions.json links to them there

def page(title, body_html, depth=0, noindex=False):
    up = "../" * depth
    robots = '<meta name="robots" content="noindex, nofollow">\n' if noindex else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}<title>{title} – Echoes of Yendor</title>
<link rel="icon" href="{up}img/ui/eoy_icon.png">
<link rel="stylesheet" href="{up}css/style.css?v=7">
<style>.doc{{max-width:900px;margin:24px auto;padding:0 16px}} .doc section{{padding:24px 28px}} .doc table{{border-collapse:collapse}} .doc td,.doc th{{padding:6px 12px;border-bottom:1px solid #555;text-align:left}}</style>
</head>
<body>
<header class="top">
  <a href="{up}#/"><img class="logo px" src="{up}img/ui/eoy_icon.png" alt="Echoes of Yendor"></a>
  <div class="brand"><b>Echoes of Yendor</b><span>{title}</span></div>
</header>
<main class="doc"><section class="window">
{body_html}
</section></main>
</body>
</html>
"""

def md_file(path):
    return markdown.markdown(open(path, encoding="utf-8").read(), extensions=["tables"])

os.makedirs(os.path.join(SITE, SOURCE_DIR), exist_ok=True)
open(os.path.join(SITE, "privacy.html"), "w").write(page("Privacy Policy", md_file(os.path.join(GAME, "PRIVACY.md"))))
open(os.path.join(SITE, "trademarks.html"), "w").write(page("Name and Logo Notice", md_file(os.path.join(GAME, "TRADEMARKS.md"))))

# source page: one row per released version listed in versions.json
vers_path = os.path.join(SITE, SOURCE_DIR, "versions.json")
versions = json.load(open(vers_path)) if os.path.exists(vers_path) else []
rows = "".join(f'<tr><td>v{v["version"]}</td><td>{v["date"]}</td><td><a href="{v["file"]}">{v["file"].split("/")[-1]}</a></td></tr>' for v in versions) \
       or '<tr><td colspan="3">The first release\'s source will appear here when version 1.0.0 is published.</td></tr>'
body = f"""<h1>Source code</h1>
<p>Echoes of Yendor is free software: you can redistribute it and/or modify it under the terms of the
<a href="https://www.gnu.org/licenses/gpl-3.0.html">GNU General Public License v3</a>. It is a modification of
Shattered Pixel Dungeon by Evan Debenham, which is based on Pixel Dungeon by Watabou.</p>
<p>Below is the complete source code for each released version, including the files needed to build it.
Open the folder in Android Studio, or see <code>docs/getting-started-android.md</code> inside the download.</p>
<table><tr><th>Version</th><th>Released</th><th>Download</th></tr>{rows}</table>
<p>The Echoes of Yendor&trade; name and logo are not covered by the GPL: versions you publish must use a different
name and logo. See the <a href="../trademarks.html">name and logo notice</a>.</p>
"""
open(os.path.join(SITE, SOURCE_DIR, "index.html"), "w").write(page("Source code", body, depth=1, noindex=True))
if not os.path.exists(vers_path):
    json.dump([], open(vers_path, "w"))
print("pages written")
