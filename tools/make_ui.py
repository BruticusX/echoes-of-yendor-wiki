#!/usr/bin/env python3
"""Generate the wiki's high-resolution UI frames as SVG 9-slice images (used with CSS border-image).
Style: the game's dark iron window chrome, upscaled, with gold embroidery: a satin-stitched gold band,
running stitches and filigree corners set with the amulet's purple gem.
Every edge is periodic within its slice, so border-image-repeat: round tiles it seamlessly.
Usage: make_ui.py <out_dir>"""
import os, sys

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

GOLD_DEFS = """
<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fff2b0"/><stop offset=".35" stop-color="#f0c24a"/>
  <stop offset=".7" stop-color="#b9822a"/><stop offset="1" stop-color="#7a4f17"/>
</linearGradient>
<linearGradient id="goldH" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#fff2b0"/><stop offset=".35" stop-color="#f0c24a"/>
  <stop offset=".7" stop-color="#b9822a"/><stop offset="1" stop-color="#7a4f17"/>
</linearGradient>
<radialGradient id="gem" cx=".35" cy=".3" r=".8">
  <stop offset="0" stop-color="#f1d6ff"/><stop offset=".3" stop-color="#b26cf0"/>
  <stop offset=".75" stop-color="#5a1f98"/><stop offset="1" stop-color="#2a0b4a"/>
</radialGradient>
<radialGradient id="gemRed" cx=".35" cy=".3" r=".8">
  <stop offset="0" stop-color="#ffd6cc"/><stop offset=".3" stop-color="#f05a4a"/>
  <stop offset=".75" stop-color="#981f1f"/><stop offset="1" stop-color="#4a0b0b"/>
</radialGradient>
"""

def svg(w, h, body, defs=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" shape-rendering="geometricPrecision">'
            "<defs>%s%s</defs>%s</svg>") % (w, h, w, h, GOLD_DEFS, defs, body)

def corner_ornament(cx, cy, rot, s=1.0, gem="gem"):
    """gold filigree flourish with a cabochon gem, centred on (cx, cy), rotated to face into the corner"""
    g = ('<g transform="translate(%g %g) rotate(%g) scale(%g)">' % (cx, cy, rot, s))
    # two curling tendrils running along the edges
    g += ('<path d="M2 -1 C 9 -1, 13 -6, 19 -4 C 23 -3, 23 2, 19 2 C 16 2, 16 -1, 18 -1" fill="none" stroke="#3a2408" stroke-width="3.2" stroke-linecap="round"/>'
          '<path d="M-1 2 C -1 9, -6 13, -4 19 C -3 23, 2 23, 2 19 C 2 16, -1 16, -1 18" fill="none" stroke="#3a2408" stroke-width="3.2" stroke-linecap="round"/>'
          '<path d="M2 -1 C 9 -1, 13 -6, 19 -4 C 23 -3, 23 2, 19 2 C 16 2, 16 -1, 18 -1" fill="none" stroke="url(#gold)" stroke-width="1.8" stroke-linecap="round"/>'
          '<path d="M-1 2 C -1 9, -6 13, -4 19 C -3 23, 2 23, 2 19 C 2 16, -1 16, -1 18" fill="none" stroke="url(#gold)" stroke-width="1.8" stroke-linecap="round"/>')
    # small leaves
    g += ('<path d="M9 -2 q3 -5 7 -4 q-2 4 -7 4z" fill="url(#gold)" stroke="#3a2408" stroke-width=".6"/>'
          '<path d="M-2 9 q-5 3 -4 7 q4 -2 4 -7z" fill="url(#gold)" stroke="#3a2408" stroke-width=".6"/>')
    # diamond setting + gem
    g += ('<path d="M0 -8 L8 0 L0 8 L-8 0Z" fill="#2a1a06" />'
          '<path d="M0 -7 L7 0 L0 7 L-7 0Z" fill="url(#gold)" stroke="#5a3a0c" stroke-width=".8"/>'
          '<circle r="3.6" fill="url(#%s)" stroke="#2a1a06" stroke-width=".8"/>'
          '<circle cx="-1.2" cy="-1.3" r="1" fill="#fff" opacity=".75"/>' % gem)
    return g + "</g>"

def window(name, size=108, cut=36, interior="#363330", frame_a="#4b4239", frame_b="#231e1a", gem="gem"):
    """main window: iron rim, gold piping, satin-stitched band, gold inner piping, filigree corners"""
    S, C = size, cut
    b = []
    b.append('<rect width="%d" height="%d" rx="7" fill="#0f0d0b"/>' % (S, S))
    b.append('<rect x="1.5" y="1.5" width="%g" height="%g" rx="6" fill="%s"/>' % (S - 3, S - 3, frame_a))
    b.append('<rect x="2.5" y="2.5" width="%g" height="%g" rx="5" fill="none" stroke="#fff" stroke-opacity=".08"/>' % (S - 5, S - 5))
    # outer gold piping
    b.append('<rect x="5.5" y="5.5" width="%g" height="%g" rx="3.5" fill="none" stroke="#2a1a06" stroke-width="3"/>' % (S - 11, S - 11))
    b.append('<rect x="5.5" y="5.5" width="%g" height="%g" rx="3.5" fill="none" stroke="url(#gold)" stroke-width="1.6"/>' % (S - 11, S - 11))
    # embroidered band (dark velvet) between the pipings
    b.append('<rect x="8" y="8" width="%g" height="%g" rx="2" fill="#241a22"/>' % (S - 16, S - 16))
    b.append('<rect x="17" y="17" width="%g" height="%g" fill="%s"/>' % (S - 34, S - 34, interior))
    # satin stitches: short diagonal gold strokes every 4px along each edge (period 4 divides the slice)
    st = []
    for x in range(12, S - 12, 4):  # top and bottom
        st.append('<path d="M%g 9.6 l2.6 5.8" />' % (x + .7))
        st.append('<path d="M%g %g l2.6 -5.8" />' % (x + .7, S - 9.6))
    for y in range(12, S - 12, 4):  # left and right
        st.append('<path d="M9.6 %g l5.8 2.6" />' % (y + .7))
        st.append('<path d="M%g %g l-5.8 2.6" />' % (S - 9.6, y + .7))
    b.append('<g stroke="#5a3a0c" stroke-width="2.2" stroke-linecap="round">%s</g>' % "".join(st))
    b.append('<g stroke="#e9b949" stroke-width="1.3" stroke-linecap="round">%s</g>' % "".join(st))
    # inner gold piping and a thin dark shadow on the interior
    b.append('<rect x="16.5" y="16.5" width="%g" height="%g" fill="none" stroke="#2a1a06" stroke-width="2.4"/>' % (S - 33, S - 33))
    b.append('<rect x="16.5" y="16.5" width="%g" height="%g" fill="none" stroke="url(#gold)" stroke-width="1.1"/>' % (S - 33, S - 33))
    b.append('<path d="M18 %g V18 H%g" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="2"/>' % (S - 18, S - 18))
    # corners
    for cx, cy, rot in [(11, 11, 0), (S - 11, 11, 90), (S - 11, S - 11, 180), (11, S - 11, 270)]:
        b.append(corner_ornament(cx, cy, rot, 1.0, gem))
    defs = ('<linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/>'
            '<stop offset="1" stop-color="%s"/></linearGradient>' % (frame_a, frame_b))
    open(os.path.join(OUT, name + ".svg"), "w").write(svg(S, S, "".join(b), defs))

def button(name, fill_a, fill_b, size=48, cut=16):
    """velvet button with a gold cord edge, a gold running stitch and tiny gold studs in the corners"""
    S, C = size, cut
    b = []
    b.append('<rect width="%d" height="%d" rx="6" fill="#0f0b0a"/>' % (S, S))
    b.append('<rect x="1.5" y="1.5" width="%g" height="%g" rx="5" fill="url(#cord)"/>' % (S - 3, S - 3))
    b.append('<rect x="3.5" y="3.5" width="%g" height="%g" rx="3.5" fill="url(#velvet)"/>' % (S - 7, S - 7))
    # soft highlight along the top
    b.append('<rect x="4" y="4" width="%g" height="6" rx="3" fill="#fff" opacity=".07"/>' % (S - 8))
    # running stitch: 3px dashes every 5px... use period 4 for even tiling: 2.4 long, 1.6 gap
    st = []
    for x in range(12, S - 12, 4):
        st.append('<path d="M%g 7 h2.4"/><path d="M%g %g h2.4"/>' % (x + .8, x + .8, S - 7))
    for y in range(12, S - 12, 4):
        st.append('<path d="M7 %g v2.4"/><path d="M%g %g v2.4"/>' % (y + .8, S - 7, y + .8))
    b.append('<g stroke="#3a2408" stroke-width="2" stroke-linecap="round">%s</g>' % "".join(st))
    b.append('<g stroke="#f0c24a" stroke-width="1.15" stroke-linecap="round">%s</g>' % "".join(st))
    for cx, cy in [(7.5, 7.5), (S - 7.5, 7.5), (S - 7.5, S - 7.5), (7.5, S - 7.5)]:
        b.append('<path d="M%g %g l2.6 2.6 l-2.6 2.6 l-2.6 -2.6z" fill="url(#gold)" stroke="#3a2408" stroke-width=".6"/>' % (cx, cy - 2.6))
    defs = ('<linearGradient id="velvet" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
            '<linearGradient id="cord" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9a0"/><stop offset=".45" stop-color="#d6a03a"/>'
            '<stop offset="1" stop-color="#6e4512"/></linearGradient>' % (fill_a, fill_b))
    open(os.path.join(OUT, name + ".svg"), "w").write(svg(S, S, "".join(b), defs))

def field(name, size=48, cut=14):
    """sunken text field / slot: dark well with a fine gold rim"""
    S = size
    b = ('<rect width="%d" height="%d" rx="5" fill="#0d0b09"/>'
         '<rect x="1.5" y="1.5" width="%g" height="%g" rx="4" fill="none" stroke="#c89436" stroke-width="1.2"/>'
         '<rect x="3" y="3" width="%g" height="%g" rx="3" fill="#1c1916"/>'
         '<path d="M4 %g V4 H%g" fill="none" stroke="#000" stroke-opacity=".6" stroke-width="2"/>') % (S, S, S - 3, S - 3, S - 6, S - 6, S - 4, S - 4)
    open(os.path.join(OUT, name + ".svg"), "w").write(svg(S, S, b))

def slot(name, size=48, gold=False):
    """inventory slot: bevelled stone square, optionally with a gold rim (hover)"""
    S = size
    rim = '<rect x="1" y="1" width="%g" height="%g" rx="3" fill="none" stroke="#e9b949" stroke-width="1.6"/>' % (S - 2, S - 2) if gold else ""
    b = ('<rect width="%d" height="%d" rx="4" fill="#141210"/>'
         '<rect x="2" y="2" width="%g" height="%g" rx="3" fill="#2a2724"/>'
         '<path d="M3 %g V3 H%g" fill="none" stroke="#4a4640" stroke-width="1.6"/>'
         '<path d="M3 %g H%g V3" fill="none" stroke="#181614" stroke-width="1.6"/>%s') % (S, S, S - 4, S - 4, S - 3, S - 3, S - 3, S - 3, rim)
    open(os.path.join(OUT, name + ".svg"), "w").write(svg(S, S, b))

window("window", frame_a="#3a332d")                                             # main panels
window("window_silver", interior="#3b3a3e", frame_a="#676970", gem="gemRed")  # info boxes
button("btn", "#4a2333", "#2a1019")                           # default button: burgundy velvet
button("btn_on", "#5c3a12", "#2e1c08")                        # active: golden-brown velvet
field("field")
slot("slot")
slot("slot_hover", gold=True)
print("wrote", sorted(os.listdir(OUT)))
