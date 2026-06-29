"""Builds the interactive HTML dashboard (docs/index.html).

A single filterable list of opportunities. Each row leads with the funding
organization, shows the per-project award amount, and carries a deadline meter.
Filters (organization, keywords, days left, days since released) run client-side.
"""
import datetime

from jinja2 import Environment, BaseLoader, select_autoescape

WINDOW_DAYS = 90  # the deadline bar shows time remaining against this window


def _money(n):
    if not n:
        return None
    if n >= 1_000_000:
        return f"${n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"${round(n / 1_000)}K"
    return f"${n:,}"


def _award(ceiling, floor):
    if ceiling and floor and ceiling != floor:
        return f"{_money(floor)}–{_money(ceiling)}", "per award"
    if ceiling:
        return _money(ceiling), "max award"
    if floor:
        return _money(floor), "floor"
    return None, None


def _decorate(item, today, closing_soon_days, new_uids):
    close = item.get("close_date")
    opened = item.get("open_date")
    days_left = (close - today).days if close else None
    days_since = (today - opened).days if opened else None

    if days_left is None:
        urgency = "none"
    elif days_left <= 3:
        urgency = "urgent"
    elif days_left <= closing_soon_days:
        urgency = "soon"
    else:
        urgency = "ok"

    bar = 0.0 if days_left is None else max(0.0, min(1.0, days_left / WINDOW_DAYS))
    award_val, award_label = _award(item.get("award_ceiling"),
                                    item.get("award_floor"))
    matched = item.get("matched_keywords", []) or []

    d = dict(item)
    d.update(
        days_left=days_left,
        days_since=days_since,
        urgency=urgency,
        bar_pct=round(bar * 100),
        close_str=close.strftime("%b %-d, %Y") if close else None,
        is_new=item["uid"] in new_uids,
        award_val=award_val,
        award_label=award_label,
        matched_keywords=matched,
        kw_attr="|".join(matched),
        dl_attr=days_left if days_left is not None else -1,
        rel_attr=days_since if days_since is not None else -1,
        new_attr="1" if item["uid"] in new_uids else "0",
        released_str=(f"{days_since}d ago" if days_since is not None else None),
    )
    return d


def _sort_key(d):
    if d["days_left"] is None:
        # undated: after dated; newest-released first
        rel = d["days_since"] if d["days_since"] is not None else 10**6
        return (1, rel)
    return (0, d["days_left"])


def build(items, config, generated_at, new_uids):
    today = generated_at.date()
    closing_soon_days = config.get("closing_soon_days", 14)

    rows = sorted(
        (_decorate(it, today, closing_soon_days, new_uids) for it in items),
        key=_sort_key,
    )

    orgs = sorted({r["agency"] for r in rows if r["agency"]}, key=str.lower)
    kw_order = config.get("keywords", [])
    present = {k for r in rows for k in r["matched_keywords"]}
    kw_chips = [k for k in kw_order if k in present]

    soon = sum(1 for r in rows if r["urgency"] in ("urgent", "soon"))

    ctx = {
        "title": config.get("report", {}).get("title", "Energy R&D Funding"),
        "generated_at": generated_at,
        "date_long": generated_at.strftime("%A, %B %-d, %Y"),
        "time_str": generated_at.strftime("%-I:%M %p %Z").strip(),
        "total": len(rows),
        "new_count": sum(1 for r in rows if r["is_new"]),
        "soon_count": soon,
        "closing_soon_days": closing_soon_days,
        "rows": rows,
        "orgs": orgs,
        "kw_chips": kw_chips,
    }
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    return env.from_string(TEMPLATE).render(**ctx)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} — Morning Dispatch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --paper:#ECEEF1; --card:#FCFCFD; --ink:#14161B; --muted:#616A78;
    --line:#DCDFE5; --gold:#E0A11B; --blue:#1F49E0; --green:#1C7C4A;
    --ok:#5A6473; --soon:#B45309; --urgent:#B0201A;
    --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
    --disp:"Archivo",system-ui,sans-serif;
    --body:"Archivo",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
    font-family:var(--body); line-height:1.45; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:920px; margin:0 auto; padding:32px 20px 80px; }

  /* Masthead */
  .mast { border-bottom:3px solid var(--ink); padding-bottom:14px; }
  .kicker { font-family:var(--mono); font-size:11px; letter-spacing:.22em;
    text-transform:uppercase; color:var(--muted); display:flex; align-items:center;
    gap:8px; margin-bottom:10px; }
  .bolt { width:13px; height:13px; fill:var(--gold); flex:none; }
  h1 { font-family:var(--disp); font-weight:800; font-size:clamp(30px,7vw,52px);
    line-height:.96; letter-spacing:-.02em; text-transform:uppercase; margin:0; }
  h1 .accent { color:var(--gold); }
  .meta { font-family:var(--mono); font-size:12.5px; color:var(--muted);
    margin-top:12px; }
  .pills { display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }
  .pill { font-family:var(--mono); font-size:12px; padding:5px 11px;
    border:1px solid var(--line); border-radius:999px; background:var(--card);
    display:flex; gap:7px; align-items:center; }
  .pill b { font-weight:600; }
  .pill .dot { width:7px; height:7px; border-radius:50%; flex:none; }
  .dot.gold{background:var(--gold);} .dot.blue{background:var(--blue);} .dot.red{background:var(--urgent);}

  /* Filter bar */
  .filters { position:sticky; top:0; z-index:5; background:var(--paper);
    border-bottom:1px solid var(--line); padding:14px 0 12px; margin-top:18px; }
  .frow { display:flex; flex-wrap:wrap; gap:10px 14px; align-items:flex-end; }
  .field { display:flex; flex-direction:column; gap:5px; }
  .field label { font-family:var(--mono); font-size:10px; letter-spacing:.12em;
    text-transform:uppercase; color:var(--muted); }
  .field select { font-family:var(--mono); font-size:12.5px; color:var(--ink);
    background:var(--card); border:1px solid var(--line); border-radius:7px;
    padding:7px 9px; min-width:140px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
  .chip { font-family:var(--mono); font-size:11.5px; padding:5px 10px;
    border:1px solid var(--line); border-radius:999px; background:var(--card);
    color:var(--muted); cursor:pointer; }
  .chip.active { background:var(--ink); border-color:var(--ink); color:#fff; }
  .toolbar { display:flex; align-items:center; gap:14px; margin-top:11px;
    font-family:var(--mono); font-size:12px; color:var(--muted); flex-wrap:wrap; }
  .toolbar .newtog { display:flex; align-items:center; gap:6px; cursor:pointer; }
  .toolbar button { font-family:var(--mono); font-size:12px; color:var(--ink);
    background:none; border:1px solid var(--line); border-radius:7px;
    padding:6px 11px; cursor:pointer; }
  .toolbar button:hover { border-color:var(--ink); }
  .showing b { color:var(--ink); font-weight:600; }

  /* Opportunity row */
  .list { margin-top:6px; }
  .row { border-left:4px solid var(--rail,var(--ok)); padding:18px 0 16px 16px;
    border-bottom:1px solid var(--line); }
  .u-urgent{--rail:var(--urgent);} .u-soon{--rail:var(--soon);}
  .u-ok{--rail:var(--ok);} .u-none{--rail:#AEB4BE;}
  .tags { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:9px; }
  .tag { font-family:var(--mono); font-size:10.5px; letter-spacing:.08em;
    text-transform:uppercase; padding:3px 8px; border-radius:4px;
    border:1px solid var(--line); color:var(--muted); white-space:nowrap; }
  .tag.new { background:var(--blue); border-color:var(--blue); color:#fff; font-weight:600; }
  .org { font-family:var(--mono); font-size:12.5px; font-weight:600;
    letter-spacing:.03em; text-transform:uppercase; color:var(--ink);
    display:flex; align-items:center; gap:8px; margin-bottom:6px; }
  .org::before { content:""; width:7px; height:7px; background:var(--gold);
    border-radius:50%; flex:none; }
  a.t { font-family:var(--disp); font-weight:700; font-size:18px; color:var(--ink);
    text-decoration:none; line-height:1.25; display:inline-block; }
  a.t:hover { text-decoration:underline; text-decoration-color:var(--gold);
    text-underline-offset:3px; }
  .metarow { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px 16px;
    margin-top:10px; font-family:var(--mono); font-size:12px; color:var(--muted); }
  .deadline { color:var(--rail,var(--muted)); font-weight:600; }
  .award { color:var(--green); font-weight:600; }
  .award .lbl { color:var(--muted); font-weight:400; }
  .bartrack { height:3px; background:var(--line); border-radius:2px; overflow:hidden;
    margin-top:12px; max-width:420px; }
  .barfill { height:100%; background:var(--rail,var(--ok)); }

  .noresults { display:none; font-family:var(--mono); font-size:13px;
    color:var(--muted); padding:30px 0; }

  footer { margin-top:42px; padding-top:18px; border-top:3px solid var(--ink);
    font-family:var(--mono); font-size:11px; color:var(--muted);
    display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }
  footer a { color:var(--muted); }

  @media (max-width:560px) {
    .field select { min-width:0; width:100%; }
    .field { flex:1 1 45%; }
  }
</style>
</head>
<body>
<div class="wrap">

  <header class="mast">
    <div class="kicker">
      <svg class="bolt" viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2 4 14h6l-1 8 9-12h-6z"/></svg>
      Morning Dispatch · Auto-generated
    </div>
    <h1>Energy R&amp;D<br><span class="accent">Funding</span> Watch</h1>
    <div class="meta">{{ date_long }}{% if time_str %} · {{ time_str }}{% endif %}</div>
    <div class="pills">
      <span class="pill"><span class="dot gold"></span><b>{{ total }}</b> open</span>
      <span class="pill"><span class="dot blue"></span><b>{{ new_count }}</b> new</span>
      <span class="pill"><span class="dot red"></span><b>{{ soon_count }}</b> closing &le; {{ closing_soon_days }}d</span>
    </div>
  </header>

  <section class="filters">
    <div class="frow">
      <div class="field">
        <label for="f-org">Funding organization</label>
        <select id="f-org"><option value="">All organizations</option>
          {% for o in orgs %}<option value="{{ o }}">{{ o }}</option>{% endfor %}
        </select>
      </div>
      <div class="field">
        <label for="f-days">Days left</label>
        <select id="f-days"><option value="">Any</option>
          <option value="7">&le; 7 days</option>
          <option value="14">&le; 14 days</option>
          <option value="30">&le; 30 days</option>
          <option value="90">&le; 90 days</option>
        </select>
      </div>
      <div class="field">
        <label for="f-rel">Days since released</label>
        <select id="f-rel"><option value="">Any</option>
          <option value="1">Today</option>
          <option value="3">&le; 3 days</option>
          <option value="7">&le; 7 days</option>
          <option value="30">&le; 30 days</option>
        </select>
      </div>
    </div>
    {% if kw_chips %}
    <div class="chips" id="f-kw">
      {% for k in kw_chips %}<span class="chip" data-kw="{{ k }}">{{ k }}</span>{% endfor %}
    </div>
    {% endif %}
    <div class="toolbar">
      <label class="newtog"><input type="checkbox" id="f-new"> New only</label>
      <span class="showing"><b id="shown">{{ total }}</b> of {{ total }} shown</span>
      <button id="f-reset" type="button">Reset filters</button>
    </div>
  </section>

  <div class="list" id="list">
    {% for it in rows %}
    <article class="row u-{{ it.urgency }}"
      data-org="{{ it.agency }}" data-source="{{ it.source_key }}"
      data-new="{{ it.new_attr }}" data-daysleft="{{ it.dl_attr }}"
      data-released="{{ it.rel_attr }}" data-kw="{{ it.kw_attr }}">
      <div class="tags">
        {% if it.is_new %}<span class="tag new">New</span>{% endif %}
        <span class="tag">{{ it.source }}</span>
        {% if it.status %}<span class="tag">{{ it.status }}</span>{% endif %}
      </div>
      {% if it.agency %}<div class="org">{{ it.agency }}</div>{% endif %}
      {% if it.url %}<a class="t" href="{{ it.url }}" target="_blank" rel="noopener">{{ it.title }}</a>
      {% else %}<span class="t">{{ it.title }}</span>{% endif %}
      <div class="metarow">
        {% if it.close_str %}<span class="deadline">{{ it.days_left }} days left · closes {{ it.close_str }}</span>
        {% else %}<span>{{ "Rolling / no deadline" if it.source_key=="foundation" else "Forecasted" }}</span>{% endif %}
        {% if it.award_val %}<span class="award">{{ it.award_val }} <span class="lbl">{{ it.award_label }}</span></span>
        {% else %}<span class="lbl" style="color:var(--muted)">Award not listed</span>{% endif %}
        {% if it.released_str %}<span>released {{ it.released_str }}</span>{% endif %}
        {% if it.number %}<span>{{ it.number }}</span>{% endif %}
      </div>
      {% if it.days_left is not none %}
      <div class="bartrack"><div class="barfill" style="width:{{ it.bar_pct }}%"></div></div>
      {% endif %}
    </article>
    {% endfor %}
    <div class="noresults" id="noresults">No opportunities match these filters. Try widening them.</div>
  </div>

  <footer>
    <span>Built by your funding bot · {{ generated_at.strftime("%Y-%m-%d %H:%M %Z") }}</span>
    <span>Sources: <a href="https://grants.gov" target="_blank" rel="noopener">Grants.gov</a> + RSS</span>
  </footer>

</div>

<script>
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll(".row"));
  var orgSel = document.getElementById("f-org");
  var daysSel = document.getElementById("f-days");
  var relSel = document.getElementById("f-rel");
  var newChk = document.getElementById("f-new");
  var shown = document.getElementById("shown");
  var nores = document.getElementById("noresults");
  var kwBox = document.getElementById("f-kw");
  var activeKw = [];

  function apply() {
    var org = orgSel.value;
    var maxDays = daysSel.value === "" ? null : parseInt(daysSel.value, 10);
    var maxRel = relSel.value === "" ? null : parseInt(relSel.value, 10);
    var newOnly = newChk.checked;
    var count = 0;

    rows.forEach(function (r) {
      var ok = true;
      if (org && r.getAttribute("data-org") !== org) ok = false;
      if (ok && newOnly && r.getAttribute("data-new") !== "1") ok = false;

      if (ok && maxDays !== null) {
        var dl = parseInt(r.getAttribute("data-daysleft"), 10);
        if (dl < 0 || dl > maxDays) ok = false;   // undated excluded by a day filter
      }
      if (ok && maxRel !== null) {
        var rel = parseInt(r.getAttribute("data-released"), 10);
        if (rel < 0 || rel > maxRel) ok = false;
      }
      if (ok && activeKw.length) {
        var kws = (r.getAttribute("data-kw") || "").split("|");
        var hit = activeKw.some(function (k) { return kws.indexOf(k) !== -1; });
        if (!hit) ok = false;
      }
      r.style.display = ok ? "" : "none";
      if (ok) count++;
    });

    shown.textContent = count;
    nores.style.display = count === 0 ? "block" : "none";
  }

  orgSel.addEventListener("change", apply);
  daysSel.addEventListener("change", apply);
  relSel.addEventListener("change", apply);
  newChk.addEventListener("change", apply);

  if (kwBox) {
    kwBox.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip) return;
      var kw = chip.getAttribute("data-kw");
      var i = activeKw.indexOf(kw);
      if (i === -1) { activeKw.push(kw); chip.classList.add("active"); }
      else { activeKw.splice(i, 1); chip.classList.remove("active"); }
      apply();
    });
  }

  document.getElementById("f-reset").addEventListener("click", function () {
    orgSel.value = ""; daysSel.value = ""; relSel.value = ""; newChk.checked = false;
    activeKw = [];
    if (kwBox) Array.prototype.forEach.call(
      kwBox.querySelectorAll(".chip"), function (c) { c.classList.remove("active"); });
    apply();
  });
})();
</script>
</body>
</html>
"""
