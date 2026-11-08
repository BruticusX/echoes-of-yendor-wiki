#!/usr/bin/env python3
"""Pack the whole site into one self-contained HTML file (images, font and data inlined), for previews.
Usage: bundle_preview.py <site_dir> <out.html>"""
import base64, json, os, re, sys

site, out = sys.argv[1], sys.argv[2]

def uri(path):
    p = os.path.join(site, path)
    ext = os.path.splitext(p)[1].lower()
    mime = {".png": "image/png", ".ttf": "font/ttf", ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
    with open(p, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())

html = open(os.path.join(site, "index.html"), encoding="utf-8").read()
css = open(os.path.join(site, "css/style.css"), encoding="utf-8").read()
js = open(os.path.join(site, "js/app.js"), encoding="utf-8").read()
bgjs = open(os.path.join(site, "js/title-bg.js"), encoding="utf-8").read()
bgjs += "\n" + open(os.path.join(site, "js/title-logo.js"), encoding="utf-8").read()
data = json.load(open(os.path.join(site, "data/game.json"), encoding="utf-8"))

# every image path the site uses
paths = set()
for root, _, files in os.walk(os.path.join(site, "img")):
    for fn in files:
        paths.add(os.path.relpath(os.path.join(root, fn), site).replace("\\", "/"))
images = {p: uri(p) for p in sorted(paths)}

css = re.sub(r'url\("\.\./([^"]+)"\)', lambda m: 'url("%s")' % uri(m.group(1)), css)
# the app builds <img src> from paths: resolve them through a lookup table
shim = "window.__IMG=%s;window.__DATA=%s;" % (json.dumps(images), json.dumps(data))
js = js.replace('fetch("data/game.json").then(function (r) { return r.json(); })', "Promise.resolve(window.__DATA)")
js = js.replace("function img(src, cls, alt) { return src ? '<img class=\"px ' + (cls || \"\") + '\" src=\"' + src + '\"",
                "function img(src, cls, alt) { return src ? '<img class=\"px ' + (cls || \"\") + '\" src=\"' + (window.__IMG[src] || src) + '\"")
html = re.sub(r'<link rel="preload"[^>]*>\n', "", html)
html = html.replace('<link rel="stylesheet" href="css/style.css">', "<style>" + css + "</style>")
html = html.replace('<script src="js/title-bg.js"></script>\n', "").replace('<script src="js/title-logo.js"></script>\n', "")
html = html.replace('<script src="js/app.js"></script>', "<script>" + shim + "</script><script>" + bgjs + "</script><script>" + js + "</script>")
for p in ("img/ui/eoy_icon.png",):
    html = html.replace('src="%s"' % p, 'src="%s"' % images[p]).replace('href="%s"' % p, 'href="%s"' % images[p])
open(out, "w", encoding="utf-8").write(html)
print("wrote", out, round(os.path.getsize(out) / 1e6, 2), "MB")
