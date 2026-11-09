/* Echoes of Yendor wiki: a small hash-routed single page app over data/game.json */
(function () {
  "use strict";
  var D = null;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var main = $("#main"), nav = $("#nav");

  // ---------- helpers ----------
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var NO_CAPS = { a: 1, an: 1, and: 1, of: 1, by: 1, to: 1, the: 1, x: 1, "for": 1 };
  function title(s) {
    var out = String(s || "").split(/(\s+)/).map(function (w) {
      if (/^\s+$/.test(w) || NO_CAPS[w.toLowerCase().replace(/[:0-9]/g, "")]) return w;
      return w.charAt(0).toUpperCase() + w.slice(1);
    }).join("");
    return out.charAt(0).toUpperCase() + out.slice(1);
  }
  // game text: _x_ = highlight, \n = paragraph
  function fmt(t) {
    if (!t) return "";
    return esc(t).split(/\n\s*\n/).map(function (p) {
      return "<p>" + p.replace(/_([^_]+)_/g, '<span class="hl">$1</span>').replace(/\n/g, "<br>") + "</p>";
    }).join("");
  }
  function pct(f) { return Math.round(f * 1000) / 10 + "%"; }
  function rnd(x) { return Math.floor(x + 0.5); }
  function byId(list, id) { for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i]; return null; }
  function img(src, cls, alt) { return src ? '<img class="px ' + (cls || "") + '" src="' + src + '" alt="' + esc(alt || "") + '" loading="lazy">' : ""; }
  function crumbs(parts) {
    return '<div class="crumbs">' + parts.map(function (p) { return p[1] ? '<a href="' + p[1] + '">' + esc(p[0]) + "</a>" : esc(p[0]); }).join(" &rsaquo; ") + "</div>";
  }
  function win(html, cls) { return '<section class="window ' + (cls || "") + '">' + html + "</section>"; }
  function metalName(id) { var m = byId(D.materials, id); return m ? m.name : id; }

  var CAT_ORDER = ["melee", "thrown", "darts", "armor", "enchantments", "glyphs", "curses", "wands", "rings", "artifacts",
    "trinkets", "potions", "exotic-potions", "brews", "scrolls", "exotic-scrolls", "stones", "spells", "materials", "food", "bombs", "bags", "quest", "misc"];
  var FAMILY_ICON = { daggers: "dagger", swords: "sword", axes: "battleaxe", blunt: "mace", polearms: "spear", staves: "quarterstaff",
    fist: "gloves", shields: "roundshield", flexible: "whip", ranged: "spiritbow", wands: "magictome" };
  var REGION_ICON = { sewers: "rat", prison: "skeleton", caves: "bat", city: "ghoul", halls: "succubus", other: "mimic", npc: "shopkeeper", allies: "mirrorimage" };
  var MECH = [
    ["metals", "Metals & Materials", "ingot"],
    ["durability", "Durability & Repair", "repairkit"],
    ["forging", "Furnace & Anvil", "anvil"],
    ["proficiency", "Weapon Proficiency", "longsword"],
    ["skills", "Weapon Skills", "skills"],
    ["combat", "Combat & Armor", "roundshield"],
    ["enemies-rules", "Tougher Enemies & Elites", "brute"],
    ["changes", "What's New in Echoes", "amulet"]
  ];

  // ---------- Google Play button (settings in js/config.js) ----------
  var PLAY_ICON = '<svg class="play-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5v17a1 1 0 0 0 1.5.86l14-8.5a1 1 0 0 0 0-1.72l-14-8.5A1 1 0 0 0 6 3.5z" fill="#e9b949" stroke="#3a2408" stroke-width="1"/><path d="M7.6 5.6v6.2l9.6-0.1z" fill="#fff2b0" opacity=".55"/></svg>';
  function playButton(big) {
    var c = (window.EOY_CONFIG && window.EOY_CONFIG.playStore) || {};
    var live = c.published && c.url;
    var inner = PLAY_ICON + '<span class="play-txt"><small>' + (live ? "Get it on" : "Coming soon to") + "</small><b>Google Play</b></span>";
    return live
      ? '<a class="btn on play-btn' + (big ? " big" : "") + '" href="' + esc(c.url) + '" target="_blank" rel="noopener">' + inner + "</a>"
      : '<span class="btn play-btn soon' + (big ? " big" : "") + '" aria-disabled="true" title="Echoes of Yendor isn\'t on Google Play yet">' + inner + "</span>";
  }

  function itemImg(id) { var it = byId(D.items, id); return it && it.img; }
  function mobImg(id) { var m = byId(D.mobs, id); return m && m.img; }
  function iconFor(key) {
    return itemImg(key) || mobImg(key) || (key === "anvil" ? "img/mobs/anvil.png" : null) || (key === "skills" ? "img/skills/cleave.png" : null);
  }

  // ---------- nav ----------
  function buildNav() {
    var h = "<h4>Wiki</h4>";
    h += '<a href="#/">' + img("img/ui/eoy_icon.png") + "Home</a>";
    h += '<a href="#/heroes">' + img("img/heroes/warrior.png") + "Heroes</a>";
    h += "<h4>Items</h4>";
    CAT_ORDER.forEach(function (c) {
      var first = D.items.filter(function (i) { return i.cat === c && i.img; })[0];
      if (!D.cats[c]) return;
      h += '<a href="#/items/' + c + '">' + img(first && first.img) + esc(D.cats[c]) + "</a>";
    });
    h += "<h4>Enemies</h4>";
    D.regions.concat([{ id: "other", name: "Special" }, { id: "npc", name: "NPCs" }, { id: "allies", name: "Allies" }]).forEach(function (r) {
      h += '<a href="#/enemies/' + r.id + '">' + img(mobImg(REGION_ICON[r.id])) + esc(r.name) + "</a>";
    });
    h += "<h4>Mechanics</h4>";
    MECH.forEach(function (m) { h += '<a href="#/mechanics/' + m[0] + '">' + img(iconFor(m[2])) + esc(m[1]) + "</a>"; });
    nav.innerHTML = h;
  }
  function markNav() {
    var hash = location.hash || "#/";
    [].forEach.call(nav.querySelectorAll("a"), function (a) {
      var href = a.getAttribute("href");
      a.classList.toggle("on", href === hash || (href !== "#/" && hash.indexOf(href + "/") === 0));
    });
  }

  // ---------- pages ----------
  function pageHome() {
    var n = D.items.length, m = D.mobs.filter(function (x) { return x.kind !== "npc" && x.kind !== "ally"; }).length;
    var h = '<div class="hero-banner"><div class="logo-anim" id="logoAnim">' + img("img/ui/title_logo.png", "logo-img", "Echoes of Yendor") +
      '<canvas class="flame left"></canvas><canvas class="flame right"></canvas>' + img("img/ui/title_logo_glow.png", "logo-glow") + "</div></div>";
    h += '<div class="play-row">' + playButton(true) + "</div>";
    h += "<h1>Welcome to the Echoes of Yendor Wiki</h1>";
    h += "<p><span class=\"hl\">Echoes of Yendor</span> is a roguelike dungeon crawler built on Shattered Pixel Dungeon. Descend through five regions of the dungeon, forge your gear from the metals you find, master your weapons and claim the <a href=\"#/item/amulet\">Amulet of Yendor</a>.</p>";
    h += "<p>This wiki covers every hero, item, enemy and system in the game. Stats are pulled straight from the game's own data, so they match what you'll see when you play.</p>";
    h += '<div class="callouts">';
    [["#/heroes", "img/heroes/warrior.png", "Heroes", "Six heroes, their subclasses and starting gear"],
     ["#/items/melee", itemImg("longsword"), "Weapons", D.items.filter(function (i) { return i.stats && i.cat === "melee"; }).length + " melee weapons, every one in every metal"],
     ["#/items/armor", itemImg("platearmor"), "Armor", "Cloth, leather and metal armor"],
     ["#/enemies/sewers", mobImg("gnoll"), "Bestiary", m + " creatures across the dungeon"],
     ["#/mechanics/metals", itemImg("ingot"), "Metals", "From tin to rare umbralite"],
     ["#/mechanics/proficiency", itemImg("sword"), "Proficiency", "Train weapon families and unlock skills"],
     ["#/mechanics/forging", "img/mobs/anvil.png", "Furnace & Anvil", "Melt, reforge, enhance and repair"],
     ["#/mechanics/changes", itemImg("amulet"), "What's New", "Everything Echoes changes"]
    ].forEach(function (c) {
      h += '<a class="callout" href="' + c[0] + '">' + img(c[1]) + "<div><b>" + c[2] + "</b><small>" + c[3] + "</small></div></a>";
    });
    h += "</div>";
    h += '<p class="dim" style="margin-top:14px">' + n + " items &middot; " + m + " creatures &middot; " + D.skills.length + " weapon skills</p>";
    return win(h);
  }

  function pageHeroes() {
    var h = crumbs([["Home", "#/"], ["Heroes"]]) + "<h1>Heroes</h1><p>Each hero starts with their own gear and a starting weapon family already at proficiency level 1. Every hero can pick one of two subclasses later in the run.</p>";
    h += '<div class="hero-row">';
    D.heroes.forEach(function (x) {
      h += '<a class="hero-card" href="#/hero/' + x.id + '">' + img(x.img) + "<b>" + esc(title(x.name)) + '</b><small class="dim">' +
        x.subclasses.map(function (s) { return title(s.name); }).join(" &middot; ") + "</small></a>";
    });
    return win(h + "</div>");
  }

  function pageHero(id) {
    var x = byId(D.heroes, id);
    if (!x) return notFound();
    var h = crumbs([["Home", "#/"], ["Heroes", "#/heroes"], [title(x.name)]]);
    h += '<div class="infobox window silver"><div class="art">' + img(x.img, "hero") + "</div><h3>" + esc(title(x.name)) + '</h3><table class="kv">' +
      "<tr><th>Subclasses</th><td>" + x.subclasses.map(function (s) { return title(s.name); }).join(", ") + "</td></tr></table></div>";
    h += "<h1 class=\"cap\">" + esc(title(x.name)) + "</h1>" + fmt(x.desc);
    if (x.unlock) h += '<div class="note">' + fmt(x.unlock) + "</div>";
    h += "<h2>Subclasses</h2>";
    x.subclasses.forEach(function (s) { h += '<h3 class="cap">' + esc(title(s.name)) + "</h3>" + fmt(s.desc); });
    return win(h + '<div class="clear"></div>');
  }

  function itemTile(i) {
    return '<a class="tile" href="#/item/' + i.id + '">' + (i.img ? img(i.img) : '<div style="height:68px"></div>') + "<span>" + esc(title(i.name)) + "</span>" +
      (i.stats ? "<small>" + i.stats.min + "&ndash;" + i.stats.max + " dmg</small>" : "") + "</a>";
  }

  function pageItems() {
    var h = crumbs([["Home", "#/"], ["Items"]]) + "<h1>Items</h1>";
    CAT_ORDER.forEach(function (c) {
      var list = D.items.filter(function (i) { return i.cat === c; });
      if (!list.length) return;
      h += '<h2><a href="#/items/' + c + '">' + esc(D.cats[c]) + "</a> <small class=\"dim\">(" + list.length + ")</small></h2>";
      h += '<div class="grid">' + list.slice(0, 8).map(itemTile).join("") + "</div>";
    });
    return win(h);
  }

  function weaponTable(list, thrown) {
    var h = '<div class="scroll-x"><table class="data sortable"><thead><tr><th></th><th class="sort">Weapon</th><th class="sort">Family</th><th class="sort n">Weight</th><th class="sort n">Damage (tin)</th><th class="sort n">Per level</th><th class="sort n">Speed</th><th class="sort n">Armor pierce</th></tr></thead><tbody>';
    list.forEach(function (i) {
      var s = i.stats;
      h += "<tr><td>" + img(i.img) + '</td><td><a class="cap" href="#/item/' + i.id + '">' + esc(title(i.name)) + "</a>" + (i.twoHanded ? ' <span class="chip">2H</span>' : "") +
        '</td><td class="cap">' + esc(title(famName(i.family))) + '</td><td class="n" data-v="' + s.kg + '">' + s.kg + ' kg</td><td class="n" data-v="' + (s.min + s.max) + '">' + s.min + "&ndash;" + s.max +
        '</td><td class="n">+' + s.lvlMin + "/+" + s.lvlMax + '</td><td class="n" data-v="' + s.delay + '">' + speedText(s.delay) + '</td><td class="n" data-v="' + (i.pierce || 0) + '">' + pct(i.pierce || 0) + "</td></tr>";
    });
    return h + "</tbody></table></div>";
  }
  function speedText(d) { return d === 1 ? "Normal" : (d < 1 ? (Math.round(100 / d) / 100) + "&times; faster" : (Math.round(d * 100) / 100) + " turns"); }
  function famName(f) { var x = byId(D.families, f); return x ? x.name : (f || "-"); }

  function armorTable(list) {
    var h = '<div class="scroll-x"><table class="data sortable"><thead><tr><th></th><th class="sort">Armor</th><th class="sort">Made of</th><th class="sort n">Weight</th><th class="sort n">Block (base)</th><th class="sort n">Per level</th><th class="sort n">Evasion &amp; stealth</th></tr></thead><tbody>';
    list.forEach(function (i) {
      var a = i.armor;
      h += "<tr><td>" + img(i.img) + '</td><td><a class="cap" href="#/item/' + i.id + '">' + esc(title(i.name)) + '</a></td><td>' + title(a.kind) + '</td><td class="n" data-v="' + a.kg + '">' + a.kg + ' kg</td><td class="n" data-v="' + a.baseBlock + '">0&ndash;' + a.baseBlock +
        '</td><td class="n">+' + a.levelBlock + '</td><td class="n" data-v="' + (-a.penalty) + '">' + (a.penalty < 0 ? '<span class="pos">+' + pct(-a.penalty) + "</span>" : a.penalty > 0 ? '<span class="neg">&minus;' + pct(a.penalty) + "</span>" : "None") + "</td></tr>";
    });
    return h + "</tbody></table></div>";
  }

  function pageCat(c) {
    var list = D.items.filter(function (i) { return i.cat === c; });
    if (!list.length) return notFound();
    var h = crumbs([["Home", "#/"], ["Items", "#/items"], [D.cats[c]]]) + "<h1>" + esc(D.cats[c]) + "</h1>";
    var intro = {
      melee: "Every melee weapon can be made of any metal. The metal multiplies its damage, so a tungsten dagger can out-hit a tin greataxe. Damage below is for <a href=\"#/mechanics/metals\">tin</a>, the weakest metal. Speed and damage come from the weapon's real weight: light weapons attack faster, heavy weapons hit disproportionately hard.",
      thrown: "Thrown weapons are made of metals too, and they wear down and break with use. The metal multiplies their damage the same way it does for melee weapons.",
      armor: "Armor comes in cloth, leather and metal. Cloth and leather resist magic, metal blocks the most but its weight costs you evasion and stealth. The material multiplies the block value; see <a href=\"#/mechanics/metals\">Metals &amp; Materials</a>.",
      enchantments: "Enchantments add a power to a weapon. They have no sprite of their own: an enchanted weapon glows in the enchantment's colour, and many show painted elemental effects along the blade. The icons show each one on a longsword.",
      glyphs: "Glyphs are the armor equivalent of enchantments. Glyphed armor glows in the glyph's colour, often with a painted aura. The icons show each one on plate armor.",
      curses: "Curses have no sprite of their own: cursed gear glows black with curls of dark smoke, so every curse looks the same on a weapon or armor until you learn which one it is. Weapon curses are shown on a longsword, armor curses on plate armor.",
      scrolls: "Scrolls of Upgrade are gone in Echoes of Yendor. Gear is improved at the <a href=\"#/mechanics/forging\">anvil</a> instead, and three new scrolls were added: Mending, Focus and Smelting."
    }[c];
    if (intro) h += "<p>" + intro + "</p>";
    var withStats = list.filter(function (i) { return i.stats; });
    if ((c === "melee" || c === "thrown") && withStats.length) {
      h += weaponTable(withStats);
      var rest = list.filter(function (i) { return !i.stats; });
      if (rest.length) h += "<h2>Other</h2><div class=\"grid\">" + rest.map(itemTile).join("") + "</div>";
    } else if (c === "armor") {
      h += armorTable(list.filter(function (i) { return i.armor; }));
      h += "<h2>Class Armor</h2><div class=\"grid\">" + list.filter(function (i) { return !i.armor; }).map(itemTile).join("") + "</div>";
    } else if (!list.some(function (i) { return i.img; })) {
      h += list.map(function (i) { return '<h3 class="cap"><a href="#/item/' + i.id + '">' + esc(title(i.name)) + "</a></h3>" + fmt(i.desc); }).join("");
    } else {
      h += '<div class="grid">' + list.map(itemTile).join("") + "</div>";
    }
    return win(h);
  }

  function metalDamageTable(i) {
    var s = i.stats;
    var h = '<div class="scroll-x"><table class="data"><thead><tr><th></th><th>Metal</th><th class="n">+0</th><th class="n">+3</th><th class="n">+5</th><th class="n">Durability</th><th class="n">Found on floors</th></tr></thead><tbody>';
    D.metalsSorted.forEach(function (m) {
      function at(l) { var mn = Math.max(0, rnd((s.min + l * s.lvlMin) * m.damageMult)); var mx = Math.max(mn, rnd((s.max + l * s.lvlMax) * m.damageMult)); return mn + "&ndash;" + mx; }
      h += "<tr><td>" + img(i.variants && i.variants[m.id]) + '</td><td class="cap">' + esc(title(m.name)) + '</td><td class="n">' + at(0) + '</td><td class="n">' + at(3) + '</td><td class="n">' + at(5) + '</td><td class="n">' + m.hits + ' hits</td><td class="n">' + (m.id === "obsidian" ? "Rare" : m.minDepth + "&ndash;" + m.maxDepth) + "</td></tr>";
    });
    return h + "</tbody></table></div>";
  }
  function armorMatTable(i) {
    var a = i.armor;
    var h = '<div class="scroll-x"><table class="data"><thead><tr><th></th><th>Material</th><th class="n">Block +0</th><th class="n">Block +3</th><th class="n">Magic resist</th><th class="n">Durability</th></tr></thead><tbody>';
    D.materials.filter(function (m) { return m.kind === a.kind; }).forEach(function (m) {
      function at(l) { return "0&ndash;" + rnd((a.baseBlock + l * a.levelBlock) * m.armorMult); }
      h += "<tr><td>" + img(i.variants && i.variants[m.id]) + '</td><td class="cap">' + esc(title(m.name)) + '</td><td class="n">' + at(0) + '</td><td class="n">' + at(3) + '</td><td class="n">' + (m.magicResist ? pct(m.magicResist) : "&ndash;") + '</td><td class="n">' + m.hits + " hits</td></tr>";
    });
    return h + "</tbody></table></div>";
  }

  function pageItem(id) {
    var i = byId(D.items, id);
    if (!i) return notFound();
    var h = crumbs([["Home", "#/"], ["Items", "#/items"], [D.cats[i.cat], "#/items/" + i.cat], [title(i.name)]]);
    var kv = "<tr><th>Type</th><td>" + esc(D.cats[i.cat]) + "</td></tr>";
    if (i.stats) {
      kv += "<tr><th>Family</th><td><a class=\"cap\" href=\"#/mechanics/skills#" + i.family + "\">" + esc(title(famName(i.family))) + "</a></td></tr>";
      kv += "<tr><th>Weight</th><td>" + i.stats.kg + " kg (" + i.stats.weight + ")</td></tr>";
      kv += "<tr><th>Damage</th><td>" + i.stats.min + "&ndash;" + i.stats.max + " <span class=\"dim\">at tin</span></td></tr>";
      kv += "<tr><th>Per level</th><td>+" + i.stats.lvlMin + " min, +" + i.stats.lvlMax + " max</td></tr>";
      kv += "<tr><th>Speed</th><td>" + speedText(i.stats.delay) + "</td></tr>";
      if (i.pierce) kv += "<tr><th>Armor pierce</th><td>" + pct(i.pierce) + "</td></tr>";
      if (i.twoHanded) kv += "<tr><th>Hands</th><td>Two-handed</td></tr>";
    }
    if (i.armor) {
      kv += "<tr><th>Made of</th><td>" + title(i.armor.kind) + "</td></tr><tr><th>Weight</th><td>" + i.armor.kg + " kg</td></tr><tr><th>Block</th><td>0&ndash;" + i.armor.baseBlock + " <span class=\"dim\">base</span></td></tr>";
    }
    if (i.ability_name) kv += "<tr><th>Duelist ability</th><td>" + esc(title(i.ability_name)) + "</td></tr>";
    h += '<div class="infobox window silver"><div class="art">' + (i.img ? img(i.img, "small") : "") + "</div><h3>" + esc(title(i.name)) + '</h3><table class="kv">' + kv + "</table></div>";
    h += '<h1 class="cap">' + esc(title(i.name)) + "</h1>" + fmt(i.desc);
    if (i.stats_desc) h += fmt(i.stats_desc);
    if (i.variants && Object.keys(i.variants).length) {
      h += "<h2>Materials</h2><div class=\"variants\">";
      Object.keys(i.variants).forEach(function (k) {
        h += '<figure><div class="slot">' + img(i.variants[k]) + '</div><figcaption class="cap">' + esc(title(metalName(k))) + "</figcaption></figure>";
      });
      h += "</div>";
      if (i.stats) h += metalDamageTable(i);
      if (i.armor) h += armorMatTable(i);
    }
    var same = D.items.filter(function (x) { return x.cat === i.cat && x.id !== i.id; }).slice(0, 12);
    if (same.length) h += '<div class="clear"></div><h2>More ' + esc(D.cats[i.cat]) + '</h2><div class="grid">' + same.map(itemTile).join("") + "</div>";
    return win(h + '<div class="clear"></div>');
  }

  function mobTile(m) {
    return '<a class="tile" href="#/enemy/' + m.id + '">' + (m.img ? img(m.img) : '<div style="height:100px"></div>') + "<span>" + esc(title(m.name)) + "</span>" +
      (m.kind === "boss" ? '<small class="hl">Boss</small>' : m.kind === "miniboss" ? '<small class="hl">Mini-boss</small>' : m.rare ? '<small style="color:var(--gold)">Rare' + (m.hp ? " &middot; " + m.hp + " HP" : "") + "</small>" : m.hp ? "<small>" + m.hp + " HP</small>" : "") + "</a>";
  }
  function regionName(r) { var x = byId(D.regions, r); return x ? x.name : ({ npc: "NPCs", allies: "Allies" }[r] || "Special"); }

  function pageEnemies(r) {
    var list = D.mobs.filter(function (m) { return m.region === r; });
    if (!list.length) return notFound();
    var reg = byId(D.regions, r);
    var h = crumbs([["Home", "#/"], ["Enemies"], [regionName(r)]]) + "<h1>" + esc(regionName(r)) + "</h1>";
    if (reg) h += "<p class=\"dim\">Floors " + reg.lo + "&ndash;" + reg.hi + "</p>";
    if (r === "allies") h += "<p>Creatures that fight on your side: summoned by spells, wands, artifacts and hero abilities.</p>";
    if (r !== "npc" && r !== "allies") h += '<div class="note">Enemies are tougher than the numbers in their base stats: see <a href="#/mechanics/enemies-rules">Tougher Enemies &amp; Elites</a>.</div>';
    var order = { boss: 0, miniboss: 1, enemy: 2, npc: 3, ally: 4 };
    list.sort(function (a, b) { return (order[a.kind] - order[b.kind]) || ((a.depths[0] || 99) - (b.depths[0] || 99)) || a.name.localeCompare(b.name); });
    h += '<div class="grid mobs">' + list.map(mobTile).join("") + "</div>";
    var stat = list.filter(function (m) { return m.hp && m.kind !== "npc"; });
    list.forEach(function (m) { if (m.rare) m._rare = true; });
    if (stat.length) {
      h += '<h2>Stats</h2><div class="scroll-x"><table class="data sortable"><thead><tr><th></th><th class="sort">Name</th><th class="sort n">HP</th><th class="sort n">Damage</th><th class="sort n">Accuracy</th><th class="sort n">Evasion</th><th class="sort n">Armor</th><th class="sort n">XP</th><th class="sort n">Floors</th></tr></thead><tbody>';
      stat.forEach(function (m) {
        h += "<tr><td>" + img(m.img) + '</td><td><a class="cap" href="#/enemy/' + m.id + '">' + esc(title(m.name)) + '</a></td><td class="n">' + m.hp + '</td><td class="n" data-v="' + (m.damage ? m.damage[1] : 0) + '">' + (m.damage ? m.damage.join("&ndash;") : "&ndash;") + '</td><td class="n">' + (m.accuracy || "&ndash;") + '</td><td class="n">' + (m.evasion || 0) + '</td><td class="n" data-v="' + (m.armor ? m.armor[1] : 0) + '">' + (m.armor ? m.armor.join("&ndash;") : "0") + '</td><td class="n">' + m.exp + '</td><td class="n" data-v="' + (m.depths[0] || 0) + '">' + depthText(m.depths) + "</td></tr>";
      });
      h += "</tbody></table></div>";
    }
    return win(h);
  }
  function depthText(d) {
    if (!d || !d.length) return "&ndash;";
    var out = [], s = d[0], p = d[0];
    for (var i = 1; i <= d.length; i++) {
      if (d[i] === p + 1) { p = d[i]; continue; }
      out.push(s === p ? s : s + "&ndash;" + p); s = p = d[i];
    }
    return out.join(", ");
  }
  var PROP = { BOSS: "Boss", MINIBOSS: "Mini-boss", UNDEAD: "Undead", DEMONIC: "Demonic", INORGANIC: "Inorganic", FIERY: "Fiery", ICY: "Icy",
    ACIDIC: "Acidic", ELECTRIC: "Electric", LARGE: "Large", IMMOVABLE: "Immovable", MINIBOSS_: "", BLOB_IMMUNE: "Gas immune", ANIMAL: "Animal", STATIC: "Static" };

  function pageEnemy(id) {
    var m = byId(D.mobs, id);
    if (!m) return notFound();
    var h = crumbs([["Home", "#/"], ["Enemies"], [regionName(m.region), "#/enemies/" + m.region], [title(m.name)]]);
    var kv = "";
    if (m.hp) kv += "<tr><th>Health</th><td>" + m.hp + "</td></tr>";
    if (m.damage) kv += "<tr><th>Damage</th><td>" + m.damage.join("&ndash;") + "</td></tr>";
    if (m.accuracy) kv += "<tr><th>Accuracy</th><td>" + m.accuracy + "</td></tr>";
    if (m.evasion) kv += "<tr><th>Evasion</th><td>" + m.evasion + "</td></tr>";
    if (m.armor) kv += "<tr><th>Armor</th><td>" + m.armor.join("&ndash;") + "</td></tr>";
    if (m.kind !== "npc" && m.kind !== "ally") kv += "<tr><th>Experience</th><td>" + m.exp + "</td></tr>";
    if (m.maxLvl) kv += "<tr><th>XP until level</th><td>" + m.maxLvl + "</td></tr>";
    if (m.depths && m.depths.length) kv += "<tr><th>Floors</th><td>" + depthText(m.depths) + "</td></tr>";
    if (m.where) kv += "<tr><th>Found</th><td>" + esc(m.where) + "</td></tr>";
    var props = (m.props || []).map(function (p) { return PROP[p]; }).filter(Boolean);
    if (m.rare) props.unshift("Rare variant");
    h += '<div class="infobox window silver"><div class="art">' + img(m.img) + "</div><h3>" + esc(title(m.name)) + "</h3>" +
      (props.length ? '<div class="chips" style="justify-content:center;margin-bottom:6px">' + props.map(function (p) { return '<span class="chip' + (p === "Boss" || p === "Mini-boss" || p === "Rare variant" ? " gold" : "") + '">' + p + "</span>"; }).join("") + "</div>" : "") +
      '<table class="kv">' + kv + "</table></div>";
    h += '<h1 class="cap">' + esc(title(m.name)) + "</h1>" + fmt(m.desc);
    if (m.kind === "enemy" || m.kind === "miniboss") h += '<div class="note">Listed stats are the base values. In Echoes of Yendor, regular enemies get extra health and armor depending on the floor, and 1 in 25 can spawn as an <a href="#/mechanics/enemies-rules">elite</a>.</div>';
    var same = D.mobs.filter(function (x) { return x.region === m.region && x.id !== m.id; }).slice(0, 10);
    if (same.length) h += '<div class="clear"></div><h2>Also in ' + esc(regionName(m.region)) + '</h2><div class="grid mobs">' + same.map(mobTile).join("") + "</div>";
    return win(h + '<div class="clear"></div>');
  }

  // ---------- mechanics ----------
  var THRESH = [5, 12, 22, 38, 60, 90, 130, 190, 280, 400];
  function mech(id) {
    var page = MECH.filter(function (x) { return x[0] === id; })[0];
    if (!page) return notFound();
    var h = crumbs([["Home", "#/"], ["Mechanics"], [page[1]]]) + "<h1>" + page[1] + "</h1>";
    var metals = D.metalsSorted;
    switch (id) {
      case "metals":
        h += "<p>There are no strength requirements in Echoes of Yendor. Instead, every weapon and piece of armor is <span class=\"hl\">made of a material</span>. The material sets how hard it hits or how much it blocks, and how long it lasts before breaking.</p>";
        h += "<p>Gear you find is always made of the <span class=\"hl\">base material</span> of its kind (tin, linen or hide). Better materials come from <a href=\"#/mechanics/forging\">reforging at the anvil</a> with ingots, cloth or leather you collect. Deeper floors drop better materials.</p>";
        h += "<h2>Metals</h2><p>Metals are ordered by hardness. Weapons use the damage multiplier, metal armor uses the same multiplier for its block.</p>";
        h += matTable(metals, true);
        h += '<div class="note"><span class="hl">Umbralite</span> is the rarest metal. It only appears where Scrolls of Upgrade used to, and besides forging, each ingot can be <span class="hl">melded</span> into any upgradable item for a purple +1, up to +5. Reforging gear into umbralite costs three times the usual amount.</div>';
        h += "<h2>Cloth</h2><p>Light armor with strong magic resistance. Cloth armor also gives a small evasion bonus instead of a penalty.</p>" + matTable(D.materials.filter(function (m) { return m.kind === "cloth"; }));
        h += "<h2>Leather</h2><p>Between cloth and metal: some magic resistance and no evasion penalty. Whips are also made of leather.</p>" + matTable(D.materials.filter(function (m) { return m.kind === "leather"; }));
        h += "<p>Magic resistance reduces magic damage and shortens magical debuffs by that fraction.</p>";
        break;
      case "durability":
        h += "<p>All weapons and armor have <span class=\"hl\">durability</span>, shown as a percentage. Every use wears it down by an amount set by the material: weaker materials wear out faster.</p>";
        h += "<p class=\"formula\">wear per use = 100% &divide; material hits</p>";
        h += "<p>At <span class=\"neg\">0%</span> an item is <span class=\"neg\">broken</span>: a broken weapon or armor does nothing until it's repaired. Broken gear is never destroyed.</p>";
        h += "<h2>Repairing</h2><ul>" +
          "<li><a href=\"#/item/repairkit\">Repair kit</a>: restores 50% durability to one item, even a broken one.</li>" +
          "<li><a href=\"#/item/scrollofmending\">Scroll of Mending</a>: restores 50% durability to your equipped weapon and armor.</li>" +
          "<li><a href=\"#/mechanics/forging\">Anvil</a>: +50% durability for one unit of the item's own material.</li>" +
          "<li>The Warrior's <span class=\"hl\">Field Repairs</span> talent makes repair kits and anvil repairs restore 50% or 100% more.</li></ul>";
        h += "<h2>Lifespan by material</h2>" + '<div class="scroll-x"><table class="data"><thead><tr><th>Material</th><th class="n">Hits from 100% to 0%</th><th class="n">Wear per use</th></tr></thead><tbody>' +
          D.materials.map(function (m) { return '<tr><td class="cap">' + esc(title(m.name)) + '</td><td class="n">' + m.hits + '</td><td class="n">' + (Math.round(m.wearPerUse * 100) / 100) + "%</td></tr>"; }).join("") + "</tbody></table></div>";
        break;
      case "forging":
        h += '<p>A <span class="hl">furnace</span> ' + img("img/mobs/furnace.png", "", "furnace").replace("<img", '<img style="height:32px;vertical-align:middle"') + ' and an <span class="hl">anvil</span> ' + img("img/mobs/anvil.png", "", "anvil").replace("<img", '<img style="height:32px;vertical-align:middle"') + " stand next to each alchemy pot. Together they replace Scrolls of Upgrade.</p>";
        h += '<div class="scroll-x"><table class="data"><thead><tr><th>Action</th><th>Where</th><th>Cost</th><th>Result</th></tr></thead><tbody>' +
          "<tr><td class=\"hl\">Melt</td><td>Furnace</td><td>An unequipped weapon or armor</td><td>Half its forging cost (rounded up) in its material</td></tr>" +
          "<tr><td class=\"hl\">Smelt</td><td>Furnace</td><td>Ore</td><td>One ingot per ore</td></tr>" +
          "<tr><td class=\"hl\">Reforge</td><td>Anvil</td><td>Its forging cost in the new material (&times;3 for umbralite)</td><td>Changes the item to any material of its kind</td></tr>" +
          "<tr><td class=\"hl\">Enhance</td><td>Anvil</td><td>Its forging cost in its own material</td><td>+1 level</td></tr>" +
          "<tr><td class=\"hl\">Repair</td><td>Anvil</td><td>1 of its own material</td><td>+50% durability</td></tr>" +
          "<tr><td class=\"hl\">Meld</td><td>Anywhere</td><td>1 umbralite ingot</td><td>+1 umbralite level to any upgradable item (max +5)</td></tr>" +
          "</tbody></table></div>";
        h += "<h2>Forging cost</h2><ul><li>Light weapons: 2 &middot; medium: 3 &middot; heavy: 4</li><li>Thrown weapons: 1 per set</li><li>Cloth and leather armor: 2 &middot; mail: 3 &middot; scale: 4 &middot; plate: 5</li></ul>";
        h += "<h2>Materials</h2><p>Melting gives ingots (metal), cloth bolts or leather. Ore is mined or found and smelted into ingots. Elites drop ingots too. The <a href=\"#/item/forgesatchel\">forge satchel</a> holds up to 12 kinds of material, one slot each, no matter how many you carry.</p>";
        h += "<p>The <a href=\"#/item/scrollofsmelting\">Scroll of Smelting</a> melts one item anywhere, like a portable furnace.</p>";
        h += "<p><a href=\"#/item/potionofstrength\">Potions of Strength</a> no longer raise strength. Each one gives <span class=\"hl\">+10 max HP</span>.</p>";
        break;
      case "proficiency":
        h += "<p>Every weapon type belongs to a <span class=\"hl\">family</span>, and each family has its own <span class=\"hl\">proficiency</span> from 0 to 10. You raise it by defeating enemies with weapons from that family (tough enemies count for more). Proficiency is <span class=\"hl\">kept per hero across runs</span>.</p>";
        h += "<h2>What it does</h2><ul><li>Accuracy: &times;0.85 at level 0, up to &times;1.35 at level 10.</li><li>Damage: +2% per level.</li><li><span class=\"hl\">Glancing blows</span>: a miss can still land for 40% damage. The chance is 20% at level 0 plus 5% per level (70% at 10), and 10% less per tier of gear above what you've trained for.</li><li>Each level gives one <a href=\"#/mechanics/skills\">skill point</a>. Ultimates need level 8.</li></ul>";
        h += "<h2>Experience needed</h2>" + '<div class="scroll-x"><table class="data"><thead><tr><th>Level</th>' + THRESH.map(function (t, i) { return '<th class="n">' + (i + 1) + "</th>"; }).join("") + "</tr></thead><tbody><tr><td>Total XP</td>" + THRESH.map(function (t) { return '<td class="n">' + t + "</td>"; }).join("") + "</tr></tbody></table></div>";
        h += "<p class=\"dim\">About one XP per kill. The <a href=\"#/item/scrolloffocus\">Scroll of Focus</a> doubles proficiency gain for 300 turns, and the Duelist trains every family 25% faster.</p>";
        h += "<h2>Starting families</h2><ul><li>Warrior: Swords</li><li>Mage: Magic (his tome)</li><li>Rogue: Daggers</li><li>Huntress: Ranged and Fist</li><li>Duelist: Swords</li><li>Cleric: Blunt</li></ul>";
        h += "<h2>Families</h2>" + familyTable();
        break;
      case "skills":
        h += "<p>Each weapon family has <span class=\"hl\">2 active skills</span> and <span class=\"hl\">2 passive skills</span> with 3 ranks each, plus <span class=\"hl\">1 ultimate</span> (1 rank, needs proficiency 8). You get one skill point per proficiency level. Active skills run on cooldowns (in turns, shown per rank).</p>";
        h += '<div class="tabs">' + D.families.map(function (f) { return '<a class="btn" href="#/mechanics/skills#' + f.id + '">' + img(itemImg(FAMILY_ICON[f.id])).replace("<img", '<img style="width:20px;height:20px;vertical-align:middle"') + " " + esc(title(f.name)) + "</a>"; }).join("") + "</div>";
        D.families.forEach(function (f) {
          var sk = D.skills.filter(function (s) { return s.family === f.id; });
          sk.sort(function (a, b) { return (a.kind === "ultimate") - (b.kind === "ultimate"); });
          h += '<h2 id="' + f.id + '" class="cap">' + esc(title(f.name)) + "</h2><div class=\"skilltree\">";
          sk.forEach(function (s) {
            h += '<div class="skill ' + s.kind + '">' + img(s.img) + "<div><b>" + esc(title(s.name)) + '</b> <span class="chip' + (s.kind === "ultimate" ? " gold" : "") + '">' + title(s.kind) + "</span>" +
              (s.cooldowns.length ? ' <span class="dim">' + s.cooldowns.join(" / ") + " turns</span>" : "") + "<div>" + fmt(s.desc) + "</div></div></div>";
          });
          h += "</div>";
        });
        break;
      case "combat":
        h += "<h2>Weapon weight</h2><p>Each weapon type has a real-world weight that sets how fast it swings and how hard it hits. A 1.2 kg sword attacks once per turn; lighter weapons attack faster (up to twice per turn), heavier ones slower (up to 2 turns).</p>";
        h += '<p class="formula">turns per attack = (kg &divide; 1.2)<sup>0.45</sup><br>average damage at tin = 6 &times; (kg &divide; 1.2)<sup>0.6</sup> (up to a sword) or <sup>0.9</sup> (heavier)</p>';
        h += "<p>The metal then multiplies the damage. See the full list on <a href=\"#/items/melee\">Melee Weapons</a>.</p>";
        h += "<h2>Armor piercing</h2><p>Each family ignores part of the enemy's armor. Heavy and pointed weapons pierce the most. Some weapons go further: a stiletto leaves only 25% of armor, a halberd 60%, a khopesh 70%.</p>" + familyTable();
        h += "<h2>Shields &amp; off-hand</h2><p>Shields go in a separate <span class=\"hl\">off-hand slot</span> and block incoming attacks. Two-handed weapons can't be used with a shield. The Mage carries a scrying orb in his off hand that strengthens all his magic.</p>";
        h += "<h2>Armor weight</h2><p>Metal armor costs evasion and stealth equal to its weight &divide; 80 (plate armor: about &minus;31%), and heavy metal armor is noisy. Leather has no penalty and cloth gives +5% evasion. Cloth and leather resist magic.</p>";
        break;
      case "enemies-rules":
        h += "<h2>Tougher enemies</h2><ul><li>Early enemies have more health so they aren't one-shot: <span class=\"hl\">&times;1.5</span> on floors 1&ndash;5, <span class=\"hl\">&times;1.3</span> on 6&ndash;10, <span class=\"hl\">&times;1.15</span> on 11&ndash;15, then another &times;1.1 on top everywhere.</li>" +
          "<li>Enemies block <span class=\"hl\">25% more</span> damage.</li><li>Deeper enemies are better armored: about <span class=\"hl\">+2 armor</span> at floor 5, +4 at 10 and +8 at 20.</li><li>Bosses are unchanged.</li></ul>";
        h += '<h2>Elites</h2><p>About <span class="hl">1 in 25</span> regular enemies spawns as an <span style="color:var(--gold)">elite</span>, surrounded by a gold aura. Elites:</p><ul>' +
          "<li>Have 60% more health and are a little stronger.</li><li>Are <span class=\"hl\">not hostile until provoked</span>: they wander the floor and leave you alone.</li>" +
          "<li><span class=\"neg\">Parry the first attack</span> made against them and strike back at once. A khopesh hooks their guard aside and skips the parry.</li>" +
          "<li>Give <span class=\"hl\">double experience</span> and drop ingots.</li></ul><p>Bosses, mini-bosses and mimics are never elite.</p>";
        break;
      case "changes":
        h += "<p>Echoes of Yendor is a modification of Shattered Pixel Dungeon v4.0.2 by Evan Debenham, itself based on Pixel Dungeon by Watabou. Here's what changes:</p>";
        h += "<h2>Gear &amp; combat</h2><ul><li>No strength requirements. Gear is made of <a href=\"#/mechanics/metals\">metals</a> up to rare umbralite, and every metal works with every weapon type.</li><li>All gear has <a href=\"#/mechanics/durability\">durability</a>.</li><li>Melt gear at the <a href=\"#/mechanics/forging\">furnace</a>, repair and enhance at the anvil. Scrolls of Upgrade are gone; Potions of Strength give +10 max HP.</li><li><a href=\"#/mechanics/proficiency\">Weapon proficiency</a> and <a href=\"#/mechanics/skills\">weapon skills</a>, with glancing blows.</li><li>Shields in an off-hand slot; two-handed weapons.</li><li>Thrown weapons use metals and wear out.</li><li>New weapon and armor types, each with their own perks.</li></ul>";
        h += "<h2>Heroes</h2><ul><li>Reworked talents for every hero, with a new fourth tier.</li><li>The Mage uses a magic tome of spells with cooldowns, deciphered as he grows stronger.</li><li>The Duelist's talents are built around weapon skills.</li><li>Cleric prayers unlock as she levels.</li></ul>";
        h += "<h2>Items</h2><ul><li>New scrolls: <a href=\"#/item/scrollofmending\">Mending</a>, <a href=\"#/item/scrolloffocus\">Focus</a> and <a href=\"#/item/scrollofsmelting\">Smelting</a>.</li><li>New enchantments with painted elemental effects.</li><li>Chests show their contents so you choose what to take.</li></ul>";
        h += "<h2>The dungeon</h2><ul><li><a href=\"#/mechanics/enemies-rules\">Tougher enemies</a> and elites.</li><li>The Blacksmith quest is back to the classic version: mine dark gold from the Caves walls.</li><li>Mimics look exactly like the chest they imitate.</li></ul>";
        h += "<h2>Art &amp; sound</h2><ul><li>Every hero, creature and boss redrawn in high detail; heroes hold their weapons, shields and tomes.</li><li>High-resolution art for all items, and redrawn tiles for every region.</li><li>A new 31-track soundtrack.</li></ul>";
        break;
    }
    return win(h);
  }
  function matTable(list, metal) {
    var h = '<div class="scroll-x"><table class="data"><thead><tr><th></th><th>Material</th>' + (metal ? '<th class="n">Damage</th>' : "") + '<th class="n">Block</th><th class="n">Magic resist</th><th class="n">Durability</th><th class="n">Floors</th></tr></thead><tbody>';
    var demo = metal ? byId(D.items, "longsword") : byId(D.items, list[0].kind === "cloth" ? "clotharmor" : "leatherarmor");
    list.forEach(function (m) {
      h += "<tr><td>" + img(demo && demo.variants && demo.variants[m.id]) + '</td><td class="cap">' + esc(title(m.name)) + "</td>" + (metal ? '<td class="n">&times;' + m.damageMult + "</td>" : "") +
        '<td class="n">&times;' + m.armorMult + '</td><td class="n">' + (m.magicResist ? pct(m.magicResist) : "&ndash;") + '</td><td class="n">' + m.hits + ' hits</td><td class="n">' + (m.id === "obsidian" ? "Rare" : m.minDepth + "&ndash;" + m.maxDepth) + "</td></tr>";
    });
    return h + "</tbody></table></div>";
  }
  function familyTable() {
    var h = '<div class="scroll-x"><table class="data"><thead><tr><th></th><th>Family</th><th class="n">Armor pierce</th><th>Weapons</th></tr></thead><tbody>';
    D.families.forEach(function (f) {
      var ws = D.items.filter(function (i) { return i.family === f.id && i.cat === "melee"; });
      h += "<tr><td>" + img(itemImg(FAMILY_ICON[f.id])) + '</td><td class="cap"><a href="#/mechanics/skills#' + f.id + '">' + esc(title(f.name)) + '</a></td><td class="n">' + pct(f.pierce) + "</td><td>" +
        (f.id === "ranged" ? "Bows, crossbows and thrown weapons" : ws.map(function (w) { return '<a class="cap" href="#/item/' + w.id + '">' + esc(title(w.name)) + "</a>"; }).join(", ") || (f.id === "wands" ? "The Mage's tome and wands" : "")) + "</td></tr>";
    });
    return h + "</tbody></table></div>";
  }

  function notFound() { return win("<h1>Not found</h1><p>That page doesn't exist (yet). <a href=\"#/\">Back to the start</a>.</p>"); }

  // ---------- sorting ----------
  function enableSort() {
    [].forEach.call(main.querySelectorAll("table.sortable th.sort"), function (th) {
      th.addEventListener("click", function () {
        var table = th.closest("table"), idx = [].indexOf.call(th.parentNode.children, th), body = table.tBodies[0];
        var dir = th.dataset.dir === "asc" ? -1 : 1; th.dataset.dir = dir === 1 ? "asc" : "desc";
        var rows = [].slice.call(body.rows);
        rows.sort(function (a, b) {
          var x = a.cells[idx], y = b.cells[idx];
          var xv = x.dataset.v != null ? parseFloat(x.dataset.v) : parseFloat(x.textContent), yv = y.dataset.v != null ? parseFloat(y.dataset.v) : parseFloat(y.textContent);
          if (!isNaN(xv) && !isNaN(yv)) return (xv - yv) * dir;
          return x.textContent.localeCompare(y.textContent) * dir;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  }

  // ---------- router ----------
  function route() {
    var hash = location.hash.replace(/^#/, "") || "/";
    var anchor = null;
    var hi = hash.indexOf("#");
    if (hi > 0) { anchor = hash.slice(hi + 1); hash = hash.slice(0, hi); }
    var p = hash.split("/").filter(Boolean), html, name = "";
    if (!p.length) html = pageHome();
    else if (p[0] === "heroes") { html = pageHeroes(); name = "Heroes"; }
    else if (p[0] === "hero") { html = pageHero(p[1]); name = title(p[1]); }
    else if (p[0] === "items" && p[1]) { html = pageCat(p[1]); name = D.cats[p[1]]; }
    else if (p[0] === "items") { html = pageItems(); name = "Items"; }
    else if (p[0] === "item") { html = pageItem(p[1]); var it = byId(D.items, p[1]); name = it ? title(it.name) : ""; }
    else if (p[0] === "enemies") { html = pageEnemies(p[1] || "sewers"); name = regionName(p[1] || "sewers"); }
    else if (p[0] === "enemy") { html = pageEnemy(p[1]); var mb = byId(D.mobs, p[1]); name = mb ? title(mb.name) : ""; }
    else if (p[0] === "mechanics") { html = mech(p[1] || "metals"); var mm = MECH.filter(function (x) { return x[0] === p[1]; })[0]; name = mm ? mm[1] : ""; }
    else html = notFound();
    main.innerHTML = html;
    document.title = (name ? name + " - " : "") + "Echoes of Yendor Wiki";
    enableSort(); markNav();
    var la = document.getElementById("logoAnim");
    if (la && window.EOYLogo) window.EOYLogo.mount(la);
    nav.classList.remove("open");
    if (anchor) { var el = document.getElementById(anchor); if (el) { el.scrollIntoView(); return; } }
    window.scrollTo(0, 0);
  }

  // ---------- search ----------
  var INDEX = [];
  function buildIndex() {
    D.items.forEach(function (i) { INDEX.push({ n: i.name, h: "#/item/" + i.id, img: i.img, t: D.cats[i.cat] }); });
    D.mobs.forEach(function (m) { INDEX.push({ n: m.name, h: "#/enemy/" + m.id, img: m.img, t: { npc: "NPC", ally: "Ally", boss: "Boss", miniboss: "Mini-boss" }[m.kind] || "Enemy" }); });
    D.heroes.forEach(function (x) { INDEX.push({ n: x.name, h: "#/hero/" + x.id, img: x.img, t: "Hero" }); x.subclasses.forEach(function (s) { INDEX.push({ n: s.name, h: "#/hero/" + x.id, img: x.img, t: "Subclass" }); }); });
    D.skills.forEach(function (s) { INDEX.push({ n: s.name, h: "#/mechanics/skills#" + s.family, img: s.img, t: "Skill" }); });
    D.materials.forEach(function (m) { INDEX.push({ n: m.name, h: "#/mechanics/metals", img: null, t: "Material" }); });
    MECH.forEach(function (m) { INDEX.push({ n: m[1], h: "#/mechanics/" + m[0], img: iconFor(m[2]), t: "Mechanic" }); });
  }
  function setupSearch() {
    var input = $("#q"), box = $("#results"), sel = -1;
    function render() {
      var q = input.value.trim().toLowerCase();
      if (!q) { box.innerHTML = ""; box.classList.remove("window"); return; }
      var hits = INDEX.filter(function (e) { return e.n.toLowerCase().indexOf(q) >= 0; });
      hits.sort(function (a, b) { return (a.n.toLowerCase().indexOf(q) - b.n.toLowerCase().indexOf(q)) || a.n.length - b.n.length; });
      hits = hits.slice(0, 12); sel = -1;
      box.classList.toggle("window", hits.length > 0);
      box.innerHTML = hits.map(function (e) { return '<a href="' + e.h + '">' + (e.img ? img(e.img) : '<span style="width:32px"></span>') + '<span class="cap">' + esc(title(e.n)) + "</span><small>" + esc(e.t) + "</small></a>"; }).join("");
    }
    input.addEventListener("input", render);
    input.addEventListener("keydown", function (e) {
      var links = box.querySelectorAll("a");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, Math.min(links.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1))); [].forEach.call(links, function (a, i) { a.classList.toggle("sel", i === sel); }); }
      if (e.key === "Enter" && links.length) { location.hash = links[Math.max(0, sel)].getAttribute("href"); input.value = ""; render(); input.blur(); }
      if (e.key === "Escape") { input.value = ""; render(); }
    });
    box.addEventListener("click", function () { input.value = ""; render(); });
    document.addEventListener("click", function (e) { if (!e.target.closest(".search")) { box.innerHTML = ""; box.classList.remove("window"); } });
  }

  $("#menuBtn").addEventListener("click", function () { nav.classList.toggle("open"); });
  fetch("data/game.json").then(function (r) { return r.json(); }).then(function (data) {
    D = data;
    var pt = document.getElementById("playTop"); if (pt) pt.innerHTML = playButton(false);
    D.metalsSorted = D.materials.filter(function (m) { return m.kind === "metal"; }).sort(function (a, b) { return a.damageMult - b.damageMult; });
    buildNav(); buildIndex(); setupSearch(); route();
    window.addEventListener("hashchange", route);
  }).catch(function (e) { main.innerHTML = win("<h1>Couldn't load the wiki data</h1><p>" + esc(e) + "</p>"); });
})();
