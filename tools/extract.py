#!/usr/bin/env python3
"""Extract Echoes of Yendor game data + sprites into the wiki's data/ and img/ folders.
Usage: extract.py <game_repo> <wiki_dir>"""
import os, re, sys, json, math
from PIL import Image

GAME, WIKI = sys.argv[1], sys.argv[2]
SRC = os.path.join(GAME, "core/src/main/java/com/shatteredpixel/shatteredpixeldungeon")
AST = os.path.join(GAME, "core/src/main/assets")
IMG = os.path.join(WIKI, "img")
DATA = os.path.join(WIKI, "data")
for d in ["items", "mobs", "skills", "ui", "metals"]:
    os.makedirs(os.path.join(IMG, d), exist_ok=True)
os.makedirs(DATA, exist_ok=True)

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)

# ---------- messages ----------
MSG = {}
for root, _, files in os.walk(os.path.join(AST, "messages")):
    for fn in files:
        if not fn.endswith(".properties"):
            continue
        for line in read(os.path.join(root, fn)).splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                MSG[k.strip()] = v.replace("\\n", "\n").replace("\\'", "'")

def clean(t):
    if t is None:
        return None
    t = re.sub(r"%\d+\$[sd]|%[sd]", "X", t)
    return t

# ---------- Assets constants ----------
ASSETS = {}
for m in re.finditer(r'public static final String (\w+)\s*=\s*"([^"]+)"', read(os.path.join(SRC, "Assets.java"))):
    ASSETS.setdefault(m.group(1), m.group(2))

# ---------- ItemSpriteSheet ----------
iss = strip_comments(read(os.path.join(SRC, "sprites/ItemSpriteSheet.java")))
CONST = {"WIDTH": 16}
def xy(x, y):
    return (x - 1) + 16 * (y - 1)
for m in re.finditer(r"static final int (\w+)\s*=\s*([^;]+);", iss.split("class Icons")[0]):
    name, expr = m.group(1), m.group(2).strip()
    if name in ("SIZE", "TX_WIDTH", "TX_HEIGHT", "WIDTH"):
        continue
    try:
        CONST[name] = int(eval(expr, {"xy": xy}, CONST))
    except Exception:
        pass

# Icons sub-class (8x8 overlays on item_icons.png)
ICON = {}
icons_src = iss.split("class Icons")[1] if "class Icons" in iss else ""
for m in re.finditer(r"static final int (\w+)\s*=\s*([^;]+);", icons_src):
    if m.group(1) in ("WIDTH", "SIZE"):
        continue
    try:
        ICON[m.group(1)] = int(eval(m.group(2).strip(), {"xy": xy}, ICON))
    except Exception:
        pass
for k in list(ICON):
    CONST.pop(k, None) if k in CONST and False else None
icon_sheet = Image.open(os.path.join(AST, "sprites/item_icons.png")).convert("RGBA")
def overlay(base, icon_idx):
    x, y = (icon_idx % 16) * 8, (icon_idx // 16) * 8
    ic = icon_sheet.crop((x, y, x + 8, y + 8)).resize((16, 16), Image.NEAREST)
    base = base.copy(); base.alpha_composite(ic, (0, 0)); return base
BASE_FOR = {"scrolls": "SCROLL_KAUNAN", "exotic-scrolls": "EXOTIC_KAUNAN", "potions": "POTION_CRIMSON",
            "exotic-potions": "EXOTIC_CRIMSON", "rings": "RING_GARNET"}

sheet16 = Image.open(os.path.join(AST, "sprites/items.png")).convert("RGBA")
sheet32 = Image.open(os.path.join(AST, "sprites/items_hd.png")).convert("RGBA")
_sheets = {}
def sheet_for(mat, hd):
    key = (mat, hd)
    if key not in _sheets:
        p = os.path.join(AST, "sprites/items%s%s.png" % ("_hd" if hd else "", "_" + mat if mat else ""))
        _sheets[key] = Image.open(p).convert("RGBA") if os.path.exists(p) else None
    return _sheets[key]

def item_icon(idx, mat=None):
    """32x32 icon for sprite index, HD if available."""
    s32 = sheet_for(mat, True)
    if s32 is not None:
        x, y = (idx % 16) * 32, (idx // 16) * 32
        c = s32.crop((x, y, x + 32, y + 32))
        if c.getbbox():
            return c
    s16 = sheet_for(mat, False) or sheet16
    x, y = (idx % 16) * 16, (idx // 16) * 16
    c = s16.crop((x, y, x + 16, y + 16))
    if not c.getbbox():
        return None
    return c.resize((32, 32), Image.NEAREST)

# ---------- java class index ----------
CLASSES = {}  # simple name -> dict
for root, _, files in os.walk(SRC):
    for fn in files:
        if fn.endswith(".java"):
            p = os.path.join(root, fn)
            CLASSES.setdefault(fn[:-5], []).append(p)

def class_info(p):
    s = read(p)
    sc = strip_comments(s)
    m = re.search(r"public\s+(abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", sc)
    if not m:
        return None
    return {"abstract": bool(m.group(1)), "name": m.group(2), "parent": m.group(3), "src": sc, "path": p}

def ancestors(name, depth=0):
    out = []
    while name and depth < 12:
        out.append(name)
        ps = CLASSES.get(name)
        if not ps:
            break
        ci = class_info(ps[0])
        name = ci["parent"] if ci else None
        depth += 1
    return out

# ---------- weapon stats ----------
ws = strip_comments(read(os.path.join(SRC, "items/weapon/WeaponStats.java")))
def wstats(kg, perk, thrown, fixed):
    r = kg / 1.2
    base = 9 if thrown else 6
    le = 0.4 if thrown else 0.6
    scale = r ** (le if r <= 1 else 0.9)
    avg = base * scale * perk
    mn = max(1, round_half_up(avg * 0.4))
    mx = max(mn + 1, round_half_up(2 * avg - mn))
    lmax = max(1, round_half_up(2 * scale * perk))
    d = fixed if fixed is not None else r ** (0.3 if thrown else 0.45)
    d = max(0.5, min(2, d))
    w = "Light" if kg < 1 else ("Medium" if kg <= 2 else "Heavy")
    return dict(kg=kg, min=mn, max=mx, lvlMin=1, lvlMax=lmax, delay=round(d, 2), weight=w)
def round_half_up(x):
    return int(math.floor(x + 0.5))
WSTATS = {}
for m in re.finditer(r"(melee|thrown)\((\w+)\.class,\s*([\d.]+)f,\s*([\d.]+)f(?:,\s*([\d.]+)f)?\)", ws):
    WSTATS[m.group(2)] = wstats(float(m.group(3)), float(m.group(4)), m.group(1) == "thrown",
                                float(m.group(5)) if m.group(5) else None)

# ---------- materials ----------
mat_src = strip_comments(read(os.path.join(SRC, "items/Material.java")))
MATS = []
for m in re.finditer(r"(\w+)\s*\(Kind\.(\w+),\s*([\d.]+)f,\s*(\d+),\s*([\d.]+)f,\s*(\d+),\s*(\d+)\)", mat_src):
    MATS.append(dict(id=m.group(1).lower(), kind=m.group(2).lower(), power=float(m.group(3)), hits=int(m.group(4)),
                     magicResist=float(m.group(5)), minDepth=int(m.group(6)), maxDepth=int(m.group(7)),
                     name=MSG.get("items.material." + m.group(1).lower(), m.group(1).lower())))
DMG = {"tin": 1.0, "copper": 1.4, "bronze": 2.0, "iron": 2.5, "steel": 2.8, "titanium": 3.0, "tungsten": 3.3, "obsidian": 4.0}
ARM = {"linen": 1.0, "hide": 1.0, "wool": 1.6, "boiled_leather": 1.6, "silk": 2.2, "wyvern_hide": 2.2, "spider_silk": 2.6, "dragonhide": 2.8}
# umbralite (obsidian) is the strongest metal: list it last
MATS = [m for m in MATS if m["id"] != "obsidian"][:7] and \
    [m for m in MATS if m["kind"] == "metal" and m["id"] != "obsidian"] + [m for m in MATS if m["id"] == "obsidian"] + \
    [m for m in MATS if m["kind"] != "metal"]
for mt in MATS:
    mt["damageMult"] = DMG.get(mt["id"])
    mt["armorMult"] = ARM.get(mt["id"], DMG.get(mt["id"]))
    mt["wearPerUse"] = round(100 / mt["hits"], 3)

# ---------- proficiency families ----------
prof = strip_comments(read(os.path.join(SRC, "actors/hero/Proficiency.java")))
FAMILY_OF = {}
for m in re.finditer(r"fam\(Family\.(\w+),([^;]+)\);", prof):
    for c in re.findall(r"(\w+)\.class", m.group(2)):
        FAMILY_OF[c] = m.group(1).lower()
PIERCE = {m.group(1).lower(): float(m.group(2)) for m in re.finditer(r"case (\w+):\s*return ([\d.]+)f;", prof.split("armorPierce")[1].split("rollGlancing")[0])}

# ---------- items ----------
CATS = [  # (path prefix under items/, category id, label)
    ("weapon/melee", "melee", "Melee Weapons"), ("weapon/missiles/darts", "darts", "Darts"),
    ("weapon/missiles", "thrown", "Thrown Weapons"), ("weapon/enchantments", "enchantments", "Enchantments"),
    ("weapon/curses", "curses", "Weapon Curses"), ("weapon", "melee", "Melee Weapons"),
    ("armor/glyphs", "glyphs", "Glyphs"), ("armor/curses", "curses", "Armor Curses"), ("armor", "armor", "Armor"),
    ("wands", "wands", "Wands"), ("rings", "rings", "Rings"), ("artifacts", "artifacts", "Artifacts"),
    ("trinkets", "trinkets", "Trinkets"), ("potions/exotic", "exotic-potions", "Exotic Potions"),
    ("potions/brews", "brews", "Brews & Elixirs"), ("potions/elixirs", "brews", "Brews & Elixirs"),
    ("potions", "potions", "Potions"), ("scrolls/exotic", "exotic-scrolls", "Exotic Scrolls"),
    ("scrolls", "scrolls", "Scrolls"), ("stones", "stones", "Runestones"), ("spells", "spells", "Spells"),
    ("food", "food", "Food"), ("bombs", "bombs", "Bombs"), ("bags", "bags", "Bags"),
    ("quest", "quest", "Quest Items"), ("keys", "misc", "Keys"), ("remains", "misc", "Remains"),
    ("journal", "misc", "Journal"), ("", "misc", "Miscellaneous"),
]
CAT_LABEL = {}
for _, cid, lab in CATS:
    CAT_LABEL.setdefault(cid, lab)
CAT_LABEL.update({"misc": "Miscellaneous", "curses": "Curses"})

items = []
seen_names = set()
item_root = os.path.join(SRC, "items")
for root, _, files in os.walk(item_root):
    rel = os.path.relpath(root, item_root).replace("\\", "/")
    rel = "" if rel == "." else rel
    for fn in sorted(files):
        if not fn.endswith(".java"):
            continue
        ci = class_info(os.path.join(root, fn))
        if not ci or ci["abstract"]:
            continue
        cname = ci["name"]
        key = "items." + (rel.replace("/", ".") + "." if rel else "") + cname.lower()
        name = MSG.get(key + ".name")
        if not name:
            continue
        if "%s" in name:
            name = name.replace("%s", "").strip()
        if "%" in name:
            continue
        desc = MSG.get(key + ".desc") or ""
        im = re.search(r"image\s*=\s*ItemSpriteSheet\.(\w+)\s*;", ci["src"])
        idx = None
        if im and im.group(1) in CONST:
            idx = CONST[im.group(1)]
        else:  # inherit
            for anc in ancestors(ci["parent"]):
                for p in CLASSES.get(anc, []):
                    m2 = re.search(r"image\s*=\s*ItemSpriteSheet\.(\w+)\s*;", strip_comments(read(p)))
                    if m2 and m2.group(1) in CONST:
                        idx = CONST[m2.group(1)]
                        break
                if idx is not None:
                    break
        mic = re.search(r"icon\s*=\s*ItemSpriteSheet\.Icons\.(\w+)\s*;", ci["src"])
        cat = next(c for pfx, c, _ in CATS if rel == pfx or rel.startswith(pfx + "/") or pfx == "")
        slug = re.sub(r"[^a-z0-9]+", "-", cname.lower()).strip("-")
        it = dict(id=slug, cls=cname, name=name, cat=cat, desc=clean(desc))
        for extra in ("stats_desc", "effect", "ability_name"):
            if key + "." + extra in MSG:
                it[extra] = clean(MSG[key + "." + extra])
        # enchant/glyph have no sprites
        if cat in BASE_FOR and mic and mic.group(1) in ICON:
            ic = overlay(item_icon(CONST[BASE_FOR[cat]]), ICON[mic.group(1)])
            ic.save(os.path.join(IMG, "items", slug + ".png"))
            it["img"] = "img/items/%s.png" % slug
        elif idx is not None and idx > 0:
            ic = item_icon(idx)
            if ic is not None:
                ic.save(os.path.join(IMG, "items", slug + ".png"))
                it["img"] = "img/items/%s.png" % slug
            it["sprite"] = idx
        if cname in WSTATS:
            it["stats"] = WSTATS[cname]
            fam = FAMILY_OF.get(cname)
            if not fam:
                for anc in ancestors(ci["parent"]):
                    if anc in FAMILY_OF:
                        fam = FAMILY_OF[anc]; break
            if cat == "thrown":
                fam = "ranged"
            it["family"] = fam
            if fam in PIERCE:
                it["pierce"] = PIERCE[fam]
            if "twoHanded" in ci["src"] or re.search(r"twoHanded\(\)\s*{\s*return true", ci["src"]):
                it["twoHanded"] = True
            # per-metal sprites
            if idx:
                vs = {}
                for mt in MATS:
                    if mt["kind"] != "metal":
                        continue
                    ic = item_icon(idx, mt["id"])
                    if ic is not None:
                        fp = "img/metals/%s_%s.png" % (slug, mt["id"])
                        ic.save(os.path.join(WIKI, fp))
                        vs[mt["id"]] = fp
                it["variants"] = vs
        if cat == "armor" and idx:
            vs = {}
            for mt in MATS:
                ic = item_icon(idx, mt["id"])
                if ic is not None and sheet_for(mt["id"], True) is not None:
                    fp = "img/metals/%s_%s.png" % (slug, mt["id"])
                    ic.save(os.path.join(WIKI, fp))
                    vs[mt["id"]] = fp
            it["variants"] = vs
        if (name, cat) in seen_names:
            continue
        seen_names.add((name, cat))
        items.append(it)

# ---------- mobs ----------
def frame_from_sprite(sprite_cls):
    ps = CLASSES.get(sprite_cls)
    if not ps:
        return None
    s = strip_comments(read(ps[0]))
    m = re.search(r"hdFilm\(\s*Assets\.Sprites\.(\w+)\s*,\s*(\d+)", s)
    fw = fh = None
    if m:
        asset, fw = m.group(1), int(m.group(2)); fh = fw
    else:
        m = re.search(r"texture\(\s*Assets\.Sprites\.(\w+)\s*\)", s)
        m2 = re.search(r"new TextureFilm\(\s*texture\s*,\s*(\d+)\s*,\s*(\d+)", s)
        if not m or not m2:
            # inherit from parent sprite
            ci = class_info(ps[0])
            return frame_from_sprite(ci["parent"]) if ci and ci["parent"] not in ("MobSprite", "CharSprite") else None
        asset, fw, fh = m.group(1), int(m2.group(1)), int(m2.group(2))
    path = ASSETS.get(asset)
    if not path:
        return None
    c = 0
    mc = re.search(r"int c\s*=\s*(\d+)\s*(?:\*\s*(\d+))?\s*;", s)
    if mc:
        c = int(mc.group(1)) * (int(mc.group(2)) if mc.group(2) else 1)
    mi = re.search(r"idle\.frames\(\s*\w+\s*,\s*(?:row\(\s*c\s*,\s*)?(?:c\s*\+\s*)?(\d+)", s)
    f = int(mi.group(1)) if mi else 0
    uses_c = bool(re.search(r"idle\.frames\(\s*\w+\s*,\s*(row\(\s*c|c\s*\+)", s))
    idx = f + (c if uses_c else 0)
    im = Image.open(os.path.join(AST, path)).convert("RGBA")
    cols = max(1, im.width // fw)
    x, y = (idx % cols) * fw, (idx // cols) * fh
    crop = im.crop((x, y, x + fw, y + fh))
    bb = crop.getbbox()
    if not bb:
        return None
    return crop

def num(rx, s):
    m = re.search(rx, s)
    return m.group(1) if m else None

mobs = []
mob_root = os.path.join(SRC, "actors/mobs")
for root, _, files in os.walk(mob_root):
    rel = os.path.relpath(root, mob_root).replace("\\", "/")
    rel = "" if rel == "." else rel
    for fn in sorted(files):
        ci = class_info(os.path.join(root, fn))
        if not ci or ci["abstract"]:
            continue
        cname = ci["name"]
        key = "actors.mobs." + (rel.replace("/", ".") + "." if rel else "") + cname.lower()
        name = MSG.get(key + ".name")
        if not name:
            continue
        s = ci["src"]
        sp = num(r"spriteClass\s*=\s*(\w+)\.class", s)
        # inherit stats/sprite from parent mob where missing
        chain = [s] + [strip_comments(read(CLASSES[a][0])) for a in ancestors(ci["parent"]) if a in CLASSES and a not in ("Mob", "Char", "NPC")]
        def find(rx):
            for src in chain:
                v = num(rx, src)
                if v:
                    return v
            return None
        sp = sp or find(r"spriteClass\s*=\s*(\w+)\.class")
        hp = find(r"HP\s*=\s*HT\s*=\s*(?:[^;?]*\?\s*\d+\s*:\s*)?(\d+)\s*;")
        dmg = None
        mdm = None
        for src in chain:
            mdm = re.search(r"damageRoll\(\)\s*\{[^}]*?NormalIntRange\(\s*(\d+)\s*,\s*(\d+)\s*\)", src, re.S)
            if mdm:
                break
        if mdm:
            dmg = [int(mdm.group(1)), int(mdm.group(2))]
        acc = None
        for src in chain:
            ma = re.search(r"attackSkill\(\s*Char \w+\s*\)\s*\{\s*return\s+(\d+)\s*;", src)
            if ma:
                acc = int(ma.group(1)); break
        arm = None
        for src in chain:
            mr = re.search(r"drRoll\(\)\s*\{[^}]*?NormalIntRange\(\s*(\d+)\s*,\s*(\d+)\s*\)", src, re.S)
            if mr:
                arm = [int(mr.group(1)), int(mr.group(2))]; break
        props = []
        for src in chain:
            props += re.findall(r"properties\.add\(\s*Property\.(\w+)", src)
        kind = "npc" if rel == "npcs" else ("boss" if "BOSS" in props else ("miniboss" if "MINIBOSS" in props else "enemy"))
        if rel == "npcs" and "NPC" not in "".join(ancestors(cname)) and cname not in ("Ghost", "Imp", "Wandmaker", "Blacksmith", "Shopkeeper", "Sheep", "RatKing", "ImpShopkeeper", "MirrorImage", "PrismaticImage"):
            pass
        slug = re.sub(r"[^a-z0-9]+", "-", cname.lower()).strip("-")
        mob = dict(id=slug, cls=cname, name=name, kind=kind, desc=clean(MSG.get(key + ".desc", "")),
                   hp=int(hp) if hp else None, damage=dmg, accuracy=acc, armor=arm,
                   evasion=int(find(r"defenseSkill\s*=\s*(\d+)\s*;") or 0) or None,
                   exp=int(find(r"EXP\s*=\s*(\d+)\s*;") or 1), maxLvl=int(find(r"maxLvl\s*=\s*(\d+)\s*;") or 0) or None,
                   props=sorted(set(props)), group=rel)
        if sp:
            fr = frame_from_sprite(sp)
            if fr is not None:
                bb = fr.getbbox()
                fr = fr.crop(bb)
                fr.save(os.path.join(IMG, "mobs", slug + ".png"))
                mob["img"] = "img/mobs/%s.png" % slug
                mob["imgSize"] = list(fr.size)
        mobs.append(mob)

# ---------- skills ----------
sk = strip_comments(read(os.path.join(SRC, "actors/hero/Skill.java")))
icons = Image.open(os.path.join(AST, "interfaces/skill_icons.png")).convert("RGBA")
skills = []
for i, m in enumerate(re.finditer(r"(\w+)\s*\(Family\.(\w+),\s*Kind\.(\w+),\s*(true|false)((?:,\s*\d+)*)\)", sk)):
    sid = m.group(1).lower()
    cds = [int(x) for x in re.findall(r"\d+", m.group(5))]
    x, y = (i % 5) * 18, (i // 5) * 18
    ic = icons.crop((x, y, x + 18, y + 18))
    fp = "img/skills/%s.png" % sid
    if ic.getbbox():
        ic.save(os.path.join(WIKI, fp))
    skills.append(dict(id=sid, family=m.group(2).lower(), kind=m.group(3).lower(), cooldowns=cds,
                       name=MSG.get("actors.hero.skill.%s.name" % sid, sid.replace("_", " ")),
                       desc=clean(MSG.get("actors.hero.skill.%s.desc" % sid, "")), img=fp if ic.getbbox() else None))

FAMILIES = [dict(id=f, name=MSG.get("actors.hero.proficiency." + f, f.title()), pierce=PIERCE.get(f, 0)) for f in
            ["daggers", "swords", "axes", "blunt", "polearms", "staves", "fist", "shields", "flexible", "ranged", "wands"]]

json.dump(dict(items=items, cats=CAT_LABEL, mobs=mobs, skills=skills, families=FAMILIES, materials=MATS),
          open(os.path.join(DATA, "game.json"), "w"), indent=1)
print("items", len(items), "with img", sum(1 for i in items if i.get("img")))
print("mobs", len(mobs), "with img", sum(1 for m in mobs if m.get("img")), "with hp", sum(1 for m in mobs if m["hp"]))
print("skills", len(skills))
from collections import Counter
print(Counter(i["cat"] for i in items))
print(Counter(m["kind"] for m in mobs))

# ================= part 2: spawn depths, heroes, UI art =================
ms = strip_comments(read(os.path.join(SRC, "actors/mobs/MobSpawner.java")))
rot = ms.split("standardMobRotation( int depth ){")[1].split("\n\t}")[0]
DEPTHS = {}
for block in re.split(r"(?=(?:case \d+:\s*)+)", rot):
    cases = [int(x) for x in re.findall(r"case (\d+):", block.split("return")[0])]
    for c in re.findall(r"(\w+)\.(?:class|random\(\))", block):
        for d in cases:
            DEPTHS.setdefault(c, set()).add(d)
BOSS_DEPTH = {"Goo": 5, "Tengu": 10, "DM300": 15, "DwarfKing": 20, "YogDzewa": 25}
for mob in mobs:
    ds = set()
    for a in ancestors(mob["cls"]):
        ds |= DEPTHS.get(a, set())
    if mob["cls"] in BOSS_DEPTH:
        ds.add(BOSS_DEPTH[mob["cls"]])
    mob["depths"] = sorted(ds)
REGIONS = [("sewers", "Sewers", 1, 5), ("prison", "Prison", 6, 10), ("caves", "Caves", 11, 15),
           ("city", "Dwarven City", 16, 20), ("halls", "Demon Halls", 21, 26)]
GROUP_REGION = {"Rat": "sewers", "Albino": "sewers", "Snake": "sewers", "Gnoll": "sewers", "Swarm": "sewers", "Crab": "sewers",
                "Slime": "sewers", "CausticSlime": "sewers", "FetidRat": "sewers", "GnollTrickster": "sewers", "GreatCrab": "sewers",
                "HermitCrab": "sewers", "GnollExile": "sewers", "Goo": "sewers",
                "Skeleton": "prison", "Thief": "prison", "Bandit": "prison", "DM100": "prison", "Guard": "prison",
                "Necromancer": "prison", "SpectralNecromancer": "prison", "Tengu": "prison", "NewbornElemental": "prison",
                "Bat": "caves", "Brute": "caves", "ArmoredBrute": "caves", "Shaman": "caves", "RedShaman": "caves",
                "BlueShaman": "caves", "PurpleShaman": "caves", "Spinner": "caves", "DM200": "caves", "DM201": "caves",
                "DM300": "caves", "Pylon": "caves", "GnollGeomancer": "caves", "GnollGuard": "caves", "GnollSapper": "caves",
                "CrystalGuardian": "caves", "CrystalSpire": "caves", "CrystalWisp": "caves", "FungalCore": "caves",
                "FungalSentry": "caves", "FungalSpinner": "caves",
                "Ghoul": "city", "Elemental": "city", "FireElemental": "city", "FrostElemental": "city", "ShockElemental": "city",
                "ChaosElemental": "city", "Warlock": "city", "Monk": "city", "Senior": "city", "Golem": "city", "DwarfKing": "city",
                "Succubus": "halls", "Eye": "halls", "Scorpio": "halls", "Acidic": "halls", "RipperDemon": "halls",
                "DemonSpawner": "halls", "YogDzewa": "halls", "YogFist": "halls", "Larva": "halls"}
for mob in mobs:
    r = None
    for a in ancestors(mob["cls"]):
        if a in GROUP_REGION:
            r = GROUP_REGION[a]; break
    if not r and mob["depths"]:
        d = min(mob["depths"])
        r = next(rid for rid, _, lo, hi in REGIONS if lo <= d <= hi)
    mob["region"] = r or ("npc" if mob["kind"] == "npc" else "other")

# content that is unreachable in Echoes of Yendor (Blacksmith mine and Dwarven Vault were removed)
REMOVED = {"CrystalGuardian", "CrystalSpire", "CrystalWisp", "FungalCore", "FungalSentry", "FungalSpinner",
           "GnollGeomancer", "GnollGuard", "GnollSapper", "VaultBossElemental", "VaultLaser", "VaultMirror",
           "VaultSentry", "VaultTokenDoor"}
mobs = [m for m in mobs if m["cls"] not in REMOVED]
SPECIAL = {"Mimic": "Hides as a chest in any region", "GoldenMimic": "Hides as a chest in any region",
           "CrystalMimic": "Hides as a chest in any region", "EbonyMimic": "Hides as a chest in any region",
           "Statue": "Guards weapon vaults", "ArmoredStatue": "Guards armor vaults", "Piranha": "Lurks in deep water",
           "PhantomPiranha": "Lurks in deep water", "Wraith": "Rises from disturbed graves", "TormentedSpirit": "Bound to a cursed grave",
           "Bee": "Released from a honeypot", "RotHeart": "Rotberry garden", "RotLasher": "Rotberry garden"}
for m in mobs:
    if m["cls"] in SPECIAL:
        m["where"] = SPECIAL[m["cls"]]

items = [i for i in items if i["cls"] not in ("VaultBeacon", "EscapeCrystal")]
# forging materials (one MaterialItem class in game, shown as four wiki entries with every material colour)
CAT_LABEL["materials"] = "Forging Materials"
for sid, const, kind, nkey, dkey in [("ingot", "INGOT", "metal", "ingot", "desc_ingot"), ("ore", "METAL_ORE", "metal", "ore", "desc_ore"),
                                     ("cloth-bolt", "CLOTH_BOLT", "cloth", "bolt", "desc_bolt"), ("leather", "LEATHER_PIECE", "leather", "leather", "desc_leather")]:
    idx = CONST[const]
    vs = {}
    for mt in MATS:
        if mt["kind"] != kind:
            continue
        ic = item_icon(idx, mt["id"])
        if ic is not None:
            fp = "img/metals/%s_%s.png" % (sid, mt["id"]); ic.save(os.path.join(WIKI, fp)); vs[mt["id"]] = fp
    base = item_icon(idx, "iron" if kind == "metal" else None)
    base.save(os.path.join(IMG, "items", sid + ".png"))
    nm = MSG["items.materialitem." + nkey].replace("%s", "").strip() or "leather"
    desc = MSG["items.materialitem." + dkey].replace("%s", "metal" if kind == "metal" else kind)
    if sid == "ingot":
        desc += "\n\n" + MSG.get("items.materialitem.desc_obsidian", "")
    items.append(dict(id=sid, cls="MaterialItem", name=nm, cat="materials", desc=desc, img="img/items/%s.png" % sid, variants=vs))

# armor stats (mirrors Armor.armorKg / baseBlock / levelBlock / weightPenalty)
ARMOR_T = {"ClothArmor": (3, "cloth", 1), "Gambeson": (5, "cloth", 1), "LeatherArmor": (6, "leather", 1),
           "StuddedLeather": (8, "leather", 1), "Brigandine": (10, "metal", 2), "MailArmor": (12, "metal", 2),
           "ScaleArmor": (15, "metal", 2), "HalfPlate": (19, "metal", 2), "PlateArmor": (25, "metal", 3)}
for it in items:
    if it["cls"] in ARMOR_T:
        kg, kind, lb = ARMOR_T[it["cls"]]
        pen = 0 if it["cls"] == "Gambeson" else (-0.05 if kind == "cloth" else (0 if kind == "leather" else kg / 80))
        it["armor"] = dict(kg=kg, kind=kind, baseBlock=round_half_up(1.6 * kg ** 0.6), levelBlock=lb, penalty=round(pen, 4))
        it["variants"] = {k: v for k, v in it.get("variants", {}).items()
                          if next(mt for mt in MATS if mt["id"] == k)["kind"] == kind}

# heroes
HERO_FRAMES = {"warrior": 72, "mage": 54, "rogue": 64, "huntress": 78, "duelist": 72, "cleric": 80}
heroes = []
os.makedirs(os.path.join(IMG, "heroes"), exist_ok=True)
for h, fr in HERO_FRAMES.items():
    im = Image.open(os.path.join(AST, "sprites/hero_hd_%s.png" % h)).convert("RGBA")
    row = 2  # a mid-tier armor row looks best
    c = im.crop((0, row * fr, fr, row * fr + fr))
    if not c.getbbox():
        c = im.crop((0, 0, fr, fr))
    c = c.crop(c.getbbox())
    c.save(os.path.join(IMG, "heroes", h + ".png"))
    k = "actors.hero.heroclass." + h
    subs = []
    for m in re.finditer(r"(\w+)\s*\(\s*HeroClass\." + h.upper(), ""):  # placeholder
        pass
    heroes.append(dict(id=h, name=MSG.get(k, h), desc=MSG.get(k + "_desc", ""), short=MSG.get(k + "_desc_short", ""),
                       unlock=MSG.get(k + "_unlock", ""), img="img/heroes/%s.png" % h))
# subclasses
hsc = strip_comments(read(os.path.join(SRC, "actors/hero/HeroSubClass.java")))
for m in re.finditer(r"(\w+)\s*\(\s*HeroIcon\.\w+\s*\)", hsc):
    sid = m.group(1).lower()
    if sid == "none":
        continue
    pass
hc = strip_comments(read(os.path.join(SRC, "actors/hero/HeroClass.java")))
for h in heroes:
    m = re.search(r"%s\s*\(\s*HeroSubClass\.(\w+)\s*,\s*HeroSubClass\.(\w+)" % h["id"].upper(), hc)
    h["subclasses"] = []
    if m:
        for s in m.groups():
            sk_ = "actors.hero.herosubclass." + s.lower()
            h["subclasses"].append(dict(id=s.lower(), name=MSG.get(sk_, s.lower()), desc=MSG.get(sk_ + "_desc", "")))

# UI art
ui = os.path.join(IMG, "ui")
cg = Image.open(os.path.join(AST, "interfaces/chrome_game.png")).convert("RGBA")
cm = Image.open(os.path.join(AST, "interfaces/chrome.png")).convert("RGBA")
for name, sheet, box in [("window", cg, (0, 0, 20, 20)), ("window_menu", cm, (0, 0, 20, 20)),
                         ("silver", cg, (86, 0, 108, 22)), ("toast", cg, (20, 0, 29, 9)), ("toast_tr", cg, (20, 9, 29, 18)),
                         ("btn_red", cg, (38, 0, 44, 6)), ("btn_grey", cg, (38, 6, 44, 12)), ("tag", cg, (22, 18, 38, 32)),
                         ("gem", cg, (0, 32, 32, 64)), ("scroll", cg, (32, 32, 64, 64)), ("tabset", cg, (64, 0, 84, 20)),
                         ("tab_on", cg, (65, 22, 73, 35)), ("tab_off", cg, (75, 22, 83, 35))]:
    sheet.crop(box).save(os.path.join(ui, name + ".png"))
import shutil
for f in ["title_logo.png", "eoy_icon.png", "arcs1.png", "arcs2.png", "title_logo_glow.png"]:
    shutil.copy(os.path.join(AST, "interfaces", f), os.path.join(ui, f))
shutil.copy(os.path.join(AST, "effects/fireball-short.png"), os.path.join(ui, "fireball.png"))  # title torches
# the title-screen background art (ui/TitleBackground.java), animated by site/js/title-bg.js
for f in ["echoes_bg", "echoes_fog", "echoes_glow"]:
    shutil.copy(os.path.join(AST, "splashes/title/%s.png" % f), os.path.join(ui, f.replace("echoes_", "title_") + ".png"))
os.makedirs(os.path.join(WIKI, "fonts"), exist_ok=True)
shutil.copy(os.path.join(AST, "fonts/pixel_font.ttf"), os.path.join(WIKI, "fonts/pixel_font.ttf"))
# floor tiles for background (first 16x16-ish floor tile of each region, HD sheets)
for rid, *_ in REGIONS:
    p = os.path.join(AST, "environment/floor_%s.png" % rid)
    if os.path.exists(p):
        shutil.copy(p, os.path.join(ui, "floor_%s.png" % rid))
# a few item icons for nav
json.dump(dict(items=items, cats=CAT_LABEL, mobs=mobs, skills=skills, families=FAMILIES, materials=MATS,
               heroes=heroes, regions=[dict(id=a, name=b, lo=c, hi=d) for a, b, c, d in REGIONS]),
          open(os.path.join(DATA, "game.json"), "w"), indent=1)
print("regions", Counter(m["region"] for m in mobs))
print("heroes", [(h["id"], [s["id"] for s in h["subclasses"]]) for h in heroes])
