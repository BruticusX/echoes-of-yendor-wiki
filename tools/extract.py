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
            if name.startswith("of "):  # "%s of obfuscation" -> "glyph of obfuscation" / "curse of ..."
                name = ("curse " if "curses" in rel else "glyph ") + name
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
        if cname == "Bag":
            idx = CONST["BACKPACK"]
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
           "VaultSentry", "VaultTokenDoor", "VaultShaman"}
mobs = [m for m in mobs if m["cls"] not in REMOVED]

# ================= the Bestiary is the master list of creatures =================
# (journal/Bestiary.java). Many creatures are inner classes (Shaman.RedShaman, YogFist.BurningFist, ...),
# so names, stats and sprites are resolved through a small Java class model.
def find_block(src, name):
    """(parent, body) of 'class <name>' inside src, by brace matching"""
    m = re.search(r"class\s+%s\b([^{]*)\{" % re.escape(name), src)
    if not m:
        return None, None
    pm = re.search(r"extends\s+([\w.]+)", m.group(1))
    i, depth = m.end(), 1
    while depth and i < len(src):
        depth += {"{": 1, "}": -1}.get(src[i], 0); i += 1
    return (pm.group(1) if pm else None), src[m.end():i - 1]

def strip_nested(body):
    """remove nested class bodies so the outer class's own fields are read, not its inner classes'"""
    out, i = [], 0
    for m in re.finditer(r"\bclass\s+\w+[^{;]*\{", body):
        if m.start() < i:
            continue
        out.append(body[i:m.start()]); j, depth = m.end(), 1
        while depth and j < len(body):
            depth += {"{": 1, "}": -1}.get(body[j], 0); j += 1
        i = j
    out.append(body[i:])
    return "".join(out)

JC = {}
def jclass(token, ctx_outer=None):
    """resolve 'Outer' or 'Outer.Inner(.Inner)' (or a bare inner name within ctx_outer) to
    {name, parent, body, key, outer, path}"""
    if token in JC:
        return JC[token]
    parts = token.split(".")
    if parts[0] not in CLASSES and ctx_outer:
        parts = ctx_outer.split(".")[:1] + parts
    if parts[0] not in CLASSES:
        return None
    path = CLASSES[parts[0]][0]
    src = strip_comments(read(path))
    parent, body = find_block(src, parts[0])
    for inner in parts[1:]:
        parent, body = find_block(body or "", inner)
    if body is None:
        return None
    rel = os.path.relpath(os.path.dirname(path), SRC).replace("\\", "/").replace("/", ".")
    key = rel + "." + "$".join(p.lower() for p in parts)
    info = dict(name=parts[-1], token=".".join(parts), parent=parent, body=strip_nested(body), key=key, outer=parts[0])
    JC[token] = info
    return info

def jchain(token):
    """the class and its ancestors, nearest first"""
    out, cur, ctx = [], jclass(token), token
    while cur and len(out) < 10:
        out.append(cur)
        if not cur["parent"] or cur["parent"] in ("Mob", "Char", "NPC", "Actor", "MobSprite", "CharSprite", "Object"):
            break
        nxt = jclass(cur["parent"], cur["token"])
        if not nxt and "." not in cur["parent"]:
            nxt = jclass(cur["outer"] + "." + cur["parent"])
        cur = nxt
    return out

def jmsg(chain, suffix):
    for c in chain:
        v = MSG.get(c["key"] + "." + suffix)
        if v:
            return v
    return None

def jfind(chain, rx, group=1):
    for c in chain:
        m = re.search(rx, c["body"], re.S)
        if m:
            return m if group is None else m.group(group)
    return None

def sprite_frame(token):
    ch = jchain(token)
    if not ch:
        return None
    m = jfind(ch, r"hdFilm\(\s*Assets\.Sprites\.(\w+)\s*,\s*(\d+)", None)
    if m:
        asset, fw = m.group(1), int(m.group(2)); fh = fw
    else:
        mt = jfind(ch, r"texture\(\s*Assets\.Sprites\.(\w+)\s*\)", None)
        mf = jfind(ch, r"new TextureFilm\(\s*texture\s*,\s*(\d+)\s*,\s*(\d+)", None)
        if not mt or not mf:
            return None
        asset, fw, fh = mt.group(1), int(mf.group(1)), int(mf.group(2))
    path = ASSETS.get(asset)
    if not path:
        return None
    c = 0
    cexpr = jfind(ch, r"int c\s*=\s*([^;]+);")
    if cexpr:
        off = jfind(ch, r"texOffset\(\)\s*\{\s*return\s+([^;]+);")
        e = cexpr.replace("texOffset()", "(%s)" % (off or "0")).replace("/", "//")
        try:
            c = int(eval(e, {}, {}))
        except Exception:
            c = 0
    mi = jfind(ch, r"idle\.frames\(\s*\w+\s*,\s*(row\(\s*c\s*,\s*|c\s*\+\s*)?(\d+)", None)
    f = int(mi.group(2)) if mi else 0
    idx = f + (c if mi and mi.group(1) else 0)
    im = Image.open(os.path.join(AST, path)).convert("RGBA")
    cols = max(1, im.width // fw)
    x, y = (idx % cols) * fw, (idx // cols) * fh
    crop = im.crop((x, y, x + fw, y + fh))
    if not crop.getbbox():
        crop = im.crop((0, 0, fw, fh))
    return crop.crop(crop.getbbox()) if crop.getbbox() else None

bsrc = strip_comments(read(os.path.join(SRC, "journal/Bestiary.java")))
BEST = {}
for cat, body in re.findall(r"(\w+)\.addEntities\((.*?)\);", bsrc, re.S):
    BEST[cat] = re.findall(r"([\w.]+)\.class", body)
REMOVED_TOK = lambda t: t.split(".")[-1] in REMOVED or t.startswith("Vault")

QUEST_REGION = {"FetidRat": "sewers", "GnollTrickster": "sewers", "GreatCrab": "sewers", "NewbornFireElemental": "prison",
                "RotLasher": "prison", "RotHeart": "prison"}
BOSS_REGION = {"Goo": "sewers", "Tengu": "prison", "Pylon": "caves", "DM300": "caves", "DwarfKing": "city"}
old_by_cls = {m["cls"]: m for m in mobs}
new_mobs, seen_tok = [], set()
for cat in ["BOSSES", "REGIONAL", "RARE", "QUEST", "UNIVERSAL", "NEUTRAL", "ALLY"]:
    for tok in BEST.get(cat, []):
        if REMOVED_TOK(tok) or tok in seen_tok:
            continue
        seen_tok.add(tok)
        ch = jchain(tok)
        if not ch:
            print("unresolved", tok); continue
        name = jmsg(ch, "name")
        if tok.startswith("WandOfWarding.Ward"):  # wards are named by tier; use the generic text
            sentry = tok.endswith("WardSentry")
            name = "ward sentry" if sentry else "ward"
            MSG[ch[0]["key"] + ".desc"] = MSG.get("items.wands.wandofwarding$ward.desc_generic_" + ("sentry" if sentry else "ward"), "")
        if not name:
            print("no name", tok); continue
        desc = jmsg(ch, "desc") or ""
        extra = MSG.get(ch[0]["key"] + ".spell_desc")
        if extra:
            desc += "\n\n" + extra
        cls = ch[0]["name"]
        # variants that share a name with their parent get the variant in brackets (e.g. gnoll shaman (red))
        label = name
        if tok == "DriedRose.GhostHero":
            label = name + " (Dried Rose)"
        elif tok.count(".") and ch[0]["key"] + ".name" not in MSG and not tok.startswith("WandOfWarding"):
            v = re.sub(r"(Shaman|Elemental|Fist)$", "", cls)
            label = "%s (%s)" % (name, re.sub(r"(?<!^)([A-Z])", r" \1", v).lower())
        hp = jfind(ch, r"HP\s*=\s*HT\s*=\s*(?:[^;?]*\?\s*\d+\s*:\s*)?(\d+)\s*;")
        dm = jfind(ch, r"damageRoll\(\)\s*\{[^}]*?NormalIntRange\(\s*(\d+)\s*,\s*(\d+)\s*\)", None)
        ac = jfind(ch, r"attackSkill\(\s*Char \w+\s*\)\s*\{\s*return\s+(\d+)\s*;")
        ar = jfind(ch, r"drRoll\(\)\s*\{[^}]*?NormalIntRange\(\s*(\d+)\s*,\s*(\d+)\s*\)", None)
        props = sorted(set(sum([re.findall(r"properties\.add\(\s*Property\.(\w+)", c["body"]) for c in ch], [])))
        kind = {"BOSSES": "boss", "NEUTRAL": "npc", "ALLY": "ally"}.get(cat, "enemy")
        if kind == "boss" and "BOSS" not in props:
            kind = "miniboss"
        if cat == "QUEST" and kind == "enemy":
            kind = "miniboss" if "MINIBOSS" in props else "enemy"
        if "MINIBOSS" in props and kind == "enemy":
            kind = "miniboss"
        slug = re.sub(r"[^a-z0-9]+", "-", tok.replace(".", "-").lower()).strip("-")
        if "." in tok and tok.split(".")[0] in ("Shaman", "Elemental", "YogFist", "YogDzewa"):
            slug = re.sub(r"[^a-z0-9]+", "-", cls.lower())
        depths = set()
        for c in ch:
            depths |= DEPTHS.get(c["name"], set())
        if cls in BOSS_DEPTH:
            depths.add(BOSS_DEPTH[cls])
        mob = dict(id=slug, cls=cls, token=tok, name=label, kind=kind, rare=(cat == "RARE"), desc=clean(desc),
                   hp=int(hp) if hp else None, damage=[int(dm.group(1)), int(dm.group(2))] if dm else None,
                   accuracy=int(ac) if ac else None, armor=[int(ar.group(1)), int(ar.group(2))] if ar else None,
                   evasion=int(jfind(ch, r"defenseSkill\s*=\s*(\d+)\s*;") or 0) or None,
                   exp=int(jfind(ch, r"EXP\s*=\s*(\d+)\s*;") or 1), maxLvl=int(jfind(ch, r"maxLvl\s*=\s*(\d+)\s*;") or 0) or None,
                   props=props, depths=sorted(depths))
        # region
        r = None
        if cat in ("UNIVERSAL",):
            r = "other"
        elif cat in ("NEUTRAL",):
            r = "npc"
        elif cat == "ALLY":
            r = "allies"
        elif cls in QUEST_REGION:
            r = QUEST_REGION[cls]
        elif cls in BOSS_REGION:
            r = BOSS_REGION[cls]
        else:
            for c in ch:
                if c["name"] in GROUP_REGION:
                    r = GROUP_REGION[c["name"]]; break
            if not r and mob["depths"]:
                d = min(mob["depths"])
                r = next(rid for rid, _, lo, hi in REGIONS if lo <= d <= hi)
            if not r and tok.startswith(("YogFist", "YogDzewa")):
                r = "halls"
        mob["region"] = r or "other"
        if cls == "Bee":
            mob["region"] = "other"
        sp = jfind(ch, r"spriteClass\s*=\s*([\w.]+)\.class")
        if sp:
            fr = sprite_frame(sp if "." in sp or sp in CLASSES else ch[0]["outer"] + "." + sp)
            if fr is not None:
                fr.save(os.path.join(IMG, "mobs", slug + ".png"))
                mob["img"] = "img/mobs/%s.png" % slug
        new_mobs.append(mob)
# mod-only NPCs that the bestiary doesn't list: the furnace and anvil
for extra in ("Furnace", "Anvil"):
    if extra in old_by_cls:
        m = old_by_cls[extra]; m["region"] = "npc"; m["kind"] = "npc"; new_mobs.append(m)
# drop stale images from the old pass
keep = {m["id"] for m in new_mobs}
for fn in os.listdir(os.path.join(IMG, "mobs")):
    if fn[:-4] not in keep:
        os.remove(os.path.join(IMG, "mobs", fn))
mobs = new_mobs
print("bestiary mobs", len(mobs), "no img", [m["token"] for m in mobs if not m.get("img")])

# creatures drawn from the HD hero sheets in code (StatueSprite, MirrorSprite, PrismaticSprite):
# first idle frame of an armor row, trimmed
def hero_frame(sheet, frame, row):
    im = Image.open(os.path.join(AST, "sprites", sheet)).convert("RGBA")
    c = im.crop((0, row * frame, frame, row * frame + frame))
    return c.crop(c.getbbox()) if c.getbbox() else None
def tint(img, r, g, b, amount):
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            pr, pg, pb, pa = px[x, y]
            if pa:
                px[x, y] = (int(pr + (r * 255 - pr) * amount), int(pg + (g * 255 - pg) * amount), int(pb + (b * 255 - pb) * amount), pa)
    return img
HERO_SPRITES = {
    "Statue": lambda: hero_frame("hero_hd_warrior_stone.png", 72, 0),        # StatueSprite default armor
    "ArmoredStatue": lambda: hero_frame("hero_hd_warrior_stone.png", 72, 3), # wears armor; mail is its fallback
    "MirrorImage": lambda: hero_frame("hero_hd_warrior.png", 72, 0),         # looks like the hero
    "PrismaticImage": lambda: tint(hero_frame("hero_hd_warrior.png", 72, 0), 0.55, 0.35, 1.0, 0.5),  # shifting tint
    "Guardian": lambda: tint(hero_frame("hero_hd_warrior_stone.png", 72, 0), 0, 0, 1, 0.2),           # GuardianSprite: blue-tinted statue
    "ShadowAlly": lambda: tint(hero_frame("hero_hd_rogue.png", 64, 0), 0.08, 0.06, 0.12, 0.75),      # a shadowy rogue
    "Ward": lambda: Image.open(os.path.join(AST, "sprites/wards.png")).convert("RGBA").crop((22, 0, 37, 16)),   # WardSprite tier 3
    "WardSentry": lambda: Image.open(os.path.join(AST, "sprites/wards.png")).convert("RGBA").crop((52, 0, 60, 15)),  # tier 6
    "LightAlly": lambda: tint(hero_frame("hero_hd_cleric.png", 80, 0), 1, 0.97, 0.8, 0.55),          # a hero made of light
}
for m in mobs:
    if m["cls"] in HERO_SPRITES and not m.get("img"):
        fr = HERO_SPRITES[m["cls"]]()
        if fr is not None:
            fr.save(os.path.join(IMG, "mobs", m["id"] + ".png"))
            m["img"] = "img/mobs/%s.png" % m["id"]; m["imgSize"] = list(fr.size)
SPECIAL = {"Mimic": "Hides as a chest in any region", "GoldenMimic": "Hides as a chest in any region",
           "CrystalMimic": "Hides as a chest in any region", "EbonyMimic": "Hides as a chest in any region",
           "Statue": "Guards weapon vaults", "ArmoredStatue": "Guards armor vaults", "Piranha": "Lurks in deep water",
           "PhantomPiranha": "Lurks in deep water", "Wraith": "Rises from disturbed graves", "TormentedSpirit": "Bound to a cursed grave",
           "Bee": "Released from a honeypot", "RotHeart": "Rotberry garden", "RotLasher": "Rotberry garden"}
for m in mobs:
    if m["cls"] in SPECIAL:
        m["where"] = SPECIAL[m["cls"]]

# not obtainable in Echoes of Yendor: vault/mine quest items, the Mage's staff (replaced by his tome,
# 0 drop chance) and Scrolls of Upgrade (replaced by the anvil; the class only remains as forge code)
_drop = ("VaultBeacon", "EscapeCrystal", "MagesStaff", "ScrollOfUpgrade")
for i in items:
    if i["cls"] in _drop and i.get("img") and os.path.exists(os.path.join(WIKI, i["img"])):
        os.remove(os.path.join(WIKI, i["img"]))
items = [i for i in items if i["cls"] not in _drop]
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


# ---------- enchantment / glyph / curse icons ----------
# These have no item sprite in the game: they show on gear as a pulsing glow (ItemSprite.Glowing, up to 60% tint)
# plus a painted aura (effects/ItemAura: ElementalVfx frames from effects/enchant_vfx.png; every curse uses smoke).
# The wiki icon is a longsword (weapon effects) or plate armor (armor effects) wearing that glow and aura.
from PIL import ImageFilter
aura_src = strip_comments(read(os.path.join(SRC, "effects/ItemAura.java")))
VFX_KIND = {"FIRE": 0, "FROST": 1, "LIGHTNING": 2, "POISON": 3, "SMOKE": 4, "GLINT": 5, "BLOOD": 6, "ARCANE": 7}
AURA = {}
for m in re.finditer(r"FACTORIES\.put\(\s*(?:[\w.]+\.)?(\w+)\.class\s*,\s*ElementalVfx\.factory\(ElementalVfx\.(\w+)", aura_src):
    AURA[m.group(1)] = VFX_KIND[m.group(2)]
vfx_sheet = Image.open(os.path.join(AST, "effects/enchant_vfx.png")).convert("RGBA")
def vfx(kind, frame=2):
    i = kind * 4 + frame
    return vfx_sheet.crop(((i % 4) * 48, (i // 4) * 48, (i % 4) * 48 + 48, (i // 4) * 48 + 48))
def effect_icon(base_idx, color, kind, spots, curse):
    base = item_icon(base_idx, "iron")
    if base is None:
        return None
    base = base.resize((64, 64), Image.NEAREST)
    r, g, b = (color >> 16) & 255, (color >> 8) & 255, color & 255
    # tint the item toward the glow colour (the game pulses between 0 and 60%)
    px = base.load(); amt = 0.42
    for y in range(64):
        for x in range(64):
            pr, pg, pb, pa = px[x, y]
            if pa:
                px[x, y] = (int(pr + (r - pr) * amt), int(pg + (g - pg) * amt), int(pb + (b - pb) * amt), pa)
    # soft halo in the glow colour behind it (curses: a dark violet-black haze)
    hc = (40, 10, 50) if curse else (r, g, b)
    sil = Image.new("RGBA", (64, 64), hc + (0,))
    sil.putalpha(base.split()[3].point(lambda a: 200 if a else 0))
    halo = sil.filter(ImageFilter.GaussianBlur(3.2))
    out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    out.alpha_composite(halo); out.alpha_composite(halo); out.alpha_composite(base)
    if kind is not None:
        for (cx, cy, size, frame) in spots:
            v = vfx(kind, frame).resize((size, size), Image.LANCZOS)
            out.alpha_composite(v, (int(cx - size / 2), int(cy - size / 2)))
    return out
SWORD_SPOTS = [(36, 28, 40, 2), (50, 13, 32, 1)]     # along the blade
ARMOR_SPOTS = [(22, 20, 36, 2), (44, 42, 32, 1)]     # on the chest and side
for it in items:
    if it["cat"] not in ("enchantments", "glyphs", "curses"):
        continue
    paths = [p_ for p_ in CLASSES.get(it["cls"], []) if re.search(r"[\\/](enchantments|glyphs|curses)[\\/]", p_)]
    src_ = strip_comments(read(paths[0])) if paths else ""
    mc = re.search(r"Glowing\(\s*0x([0-9A-Fa-f]{6})", src_)
    color = int(mc.group(1), 16) if mc else 0xFFFFFF
    armor = "/armor/" in (paths[0].replace("\\", "/") if paths else "")
    curse = it["cat"] == "curses"
    kind = VFX_KIND["SMOKE"] if curse else AURA.get(it["cls"])
    ic = effect_icon(CONST["ARMOR_PLATE"] if armor else CONST["LONGSWORD"], color, kind, ARMOR_SPOTS if armor else SWORD_SPOTS, curse)
    if ic is not None:
        ic.save(os.path.join(IMG, "items", it["id"] + ".png"))
        it["img"] = "img/items/%s.png" % it["id"]
        it["appliesTo"] = "armor" if armor else "weapon"

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
