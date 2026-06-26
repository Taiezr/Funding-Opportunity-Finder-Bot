"""Builds the HTML dashboard (docs/index.html).

Design: a "morning dispatch" for energy R&D funding. The signature element is
the deadline meter on each row — a colored rail + days-left chip + a thin bar
of time remaining — because a closing date is the thing you most need to catch.
"""
import datetime

from jinja2 import Environment, BaseLoader, select_autoescape

WINDOW_DAYS = 90  # the deadline bar shows time remaining against this window


def _decorate(item, today, closing_soon_days, new_uids):
    """Add display fields (days_left, urgency, formatted dates, is_new)."""
    close = item.get("close_date")
    days_left = (close - today).days if close else None

    if days_left is None:
        urgency = "none"
    elif days_left <= 3:
        urgency = "urgent"
    elif days_left <= closing_soon_days:
        urgency = "soon"
    else:
        urgency = "ok"

    if days_left is None:
        bar = 0.0
    else:
        bar = max(0.0, min(1.0, days_left / WINDOW_DAYS))

    item = dict(item)
    item["days_left"] = days_left
    item["urgency"] = urgency
    item["bar_pct"] = round(bar * 100)
    item["close_str"] = close.strftime("%b %-d, %Y") if close else None
    item["open_str"] = (
        item["open_date"].strftime("%b %-d, %Y") if item.get("open_date") else None
    )
    item["is_new"] = item["uid"] in new_uids
    return item


def _sort_key(item):
    # Items with a deadline first (soonest first); undated ones after.
    if item["days_left"] is None:
        return (1, 0)
    return (0, item["days_left"])


def build(items, config, generated_at, new_uids):
    today = generated_at.date()
    closing_soon_days = config.get("closing_soon_days", 14)

    decorated = [
        _decorate(it, today, closing_soon_days, new_uids) for it in items
    ]

    federal = sorted(
        [d for d in decorated if d["source_key"] == "federal"], key=_sort_key
    )
    foundation = sorted(
        [d for d in decorated if d["source_key"] == "foundation"], key=_sort_key
    )
    new_items = sorted([d for d in decorated if d["is_new"]], key=_sort_key)
    closing_soon = [
        d for d in decorated if d["urgency"] in ("urgent", "soon")
    ]

    ctx = {
        "title": config.get("report", {}).get("title", "Energy R&D Funding"),
        "generated_at": generated_at,
        "date_long": generated_at.strftime("%A, %B %-d, %Y"),
        "time_str": generated_at.strftime("%-I:%M %p %Z").strip(),
        "total": len(decorated),
        "new_count": len(new_items),
        "soon_count": len(closing_soon),
        "new_items": new_items,
        "federal": federal,
        "foundation": foundation,
        "closing_soon_days": closing_soon_days,
        "year": generated_at.year,
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
    --line:#DCDFE5; --gold:#E0A11B; --blue:#1F49E0;
    --ok:#5A6473; --soon:#B45309; --urgent:#B0201A;
    --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
    --disp:"Archivo",system-ui,sans-serif;
    --body:"Archivo",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; background:var(--paper); color:var(--ink);
    font-family:var(--body); line-height:1.45;
    -webkit-font-smoothing:antialiased;
  }
  .wrap { max-width:880px; margin:0 auto; padding:32px 20px 80px; }

  /* ── Masthead ───────────────────────────────────────── */
  .mast { border-bottom:3px solid var(--ink); padding-bottom:14px; }
  .kicker {
    font-family:var(--mono); font-size:11px; letter-spacing:.22em;
    text-transform:uppercase; color:var(--muted); display:flex;
    align-items:center; gap:8px; margin-bottom:10px;
  }
  .bolt { width:13px; height:13px; fill:var(--gold); flex:none; }
  h1 {
    font-family:var(--disp); font-weight:800; font-size:clamp(30px,7vw,52px);
    line-height:.96; letter-spacing:-.02em; text-transform:uppercase; margin:0;
  }
  h1 .accent { color:var(--gold); }
  .meta {
    font-family:var(--mono); font-size:12.5px; color:var(--muted);
    margin-top:12px; display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center;
  }
  .pills { display:flex; gap:8px; flex-wrap:wrap; margin-top:14px; }
  .pill {
    font-family:var(--mono); font-size:12px; padding:5px 11px; border:1px solid var(--line);
    border-radius:999px; background:var(--card); display:flex; gap:7px; align-items:center;
  }
  .pill b { font-weight:600; }
  .pill .dot { width:7px; height:7px; border-radius:50%; flex:none; }
  .dot.gold{background:var(--gold);} .dot.blue{background:var(--blue);} .dot.red{background:var(--urgent);}

  /* ── Section headers ────────────────────────────────── */
  .section { margin-top:40px; }
  .shead {
    display:flex; align-items:baseline; justify-content:space-between;
    border-bottom:1px solid var(--line); padding-bottom:8px; margin-bottom:4px;
  }
  .shead h2 {
    font-family:var(--mono); font-weight:600; font-size:13px; letter-spacing:.14em;
    text-transform:uppercase; margin:0;
  }
  .shead .count { font-family:var(--mono); font-size:12px; color:var(--muted); }

  /* ── Opportunity row ───────────────────────────────── */
  .row {
    display:grid; grid-template-columns:96px 1fr; gap:16px;
    padding:18px 0; border-bottom:1px solid var(--line);
  }
  .meter { position:relative; padding-left:14px; }
  .meter::before {
    content:""; position:absolute; left:0; top:2px; bottom:2px; width:4px;
    border-radius:2px; background:var(--rail,var(--ok));
  }
  .days {
    font-family:var(--mono); font-weight:600; font-size:20px; line-height:1;
    color:var(--rail,var(--ink));
  }
  .days small { display:block; font-weight:400; font-size:10px; letter-spacing:.12em;
    text-transform:uppercase; color:var(--muted); margin-top:5px; }
  .bartrack { margin-top:9px; height:3px; background:var(--line); border-radius:2px; overflow:hidden; }
  .barfill { height:100%; background:var(--rail,var(--ok)); }

  .u-urgent { --rail:var(--urgent); } .u-soon { --rail:var(--soon); }
  .u-ok { --rail:var(--ok); } .u-none { --rail:#AEB4BE; }

  .body-col { min-width:0; }
  .tags { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:7px; }
  .tag {
    font-family:var(--mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase;
    padding:3px 8px; border-radius:4px; border:1px solid var(--line); color:var(--muted);
    white-space:nowrap;
  }
  .tag.new { background:var(--blue); border-color:var(--blue); color:#fff; font-weight:600; }
  .row a.t {
    font-family:var(--disp); font-weight:700; font-size:17px; color:var(--ink);
    text-decoration:none; line-height:1.25; display:inline-block;
  }
  .row a.t:hover { text-decoration:underline; text-decoration-color:var(--gold);
    text-underline-offset:3px; }
  .sub { font-family:var(--mono); font-size:12px; color:var(--muted); margin-top:6px;
    display:flex; flex-wrap:wrap; gap:4px 12px; }
  .sub .deadline { color:var(--rail,var(--muted)); font-weight:500; }

  .empty {
    font-family:var(--mono); font-size:13px; color:var(--muted);
    padding:18px 0; border-bottom:1px solid var(--line);
  }

  footer {
    margin-top:48px; padding-top:18px; border-top:3px solid var(--ink);
    font-family:var(--mono); font-size:11px; color:var(--muted);
    display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px;
  }
  footer a { color:var(--muted); }

  @media (max-width:520px) {
    .row { grid-template-columns:74px 1fr; gap:12px; }
    .days { font-size:17px; }
  }
  @media (prefers-reduced-motion:no-preference) {
    .row { transition:none; }
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

  {% macro row(it) %}
  <div class="row">
    <div class="meter u-{{ it.urgency }}">
      {% if it.days_left is not none %}
        <div class="days">{{ it.days_left }}<small>days left</small></div>
        <div class="bartrack"><div class="barfill" style="width:{{ it.bar_pct }}%"></div></div>
      {% else %}
        <div class="days" style="font-size:13px">{{ "Rolling" if it.source_key=="foundation" else "Forecast" }}</div>
      {% endif %}
    </div>
    <div class="body-col">
      <div class="tags">
        {% if it.is_new %}<span class="tag new">New</span>{% endif %}
        <span class="tag">{{ it.source }}</span>
        {% if it.status %}<span class="tag">{{ it.status }}</span>{% endif %}
      </div>
      {% if it.url %}<a class="t" href="{{ it.url }}" target="_blank" rel="noopener">{{ it.title }}</a>
      {% else %}<span class="t">{{ it.title }}</span>{% endif %}
      <div class="sub">
        {% if it.agency %}<span>{{ it.agency }}</span>{% endif %}
        {% if it.number %}<span>{{ it.number }}</span>{% endif %}
        {% if it.close_str %}<span class="deadline u-{{ it.urgency }}">Closes {{ it.close_str }}</span>{% endif %}
      </div>
    </div>
  </div>
  {% endmacro %}

  {% if new_items %}
  <section class="section">
    <div class="shead"><h2>New since last report</h2><span class="count">{{ new_items|length }}</span></div>
    {% for it in new_items %}{{ row(it) }}{% endfor %}
  </section>
  {% endif %}

  <section class="section">
    <div class="shead"><h2>Federal · Grants.gov</h2><span class="count">{{ federal|length }}</span></div>
    {% for it in federal %}{{ row(it) }}{% else %}<div class="empty">No federal opportunities matched today.</div>{% endfor %}
  </section>

  <section class="section">
    <div class="shead"><h2>Foundations</h2><span class="count">{{ foundation|length }}</span></div>
    {% for it in foundation %}{{ row(it) }}{% else %}<div class="empty">No foundation opportunities matched today. Add feeds in config.yaml.</div>{% endfor %}
  </section>

  <footer>
    <span>Built by your funding bot · {{ generated_at.strftime("%Y-%m-%d %H:%M %Z") }}</span>
    <span>Sources: <a href="https://grants.gov" target="_blank" rel="noopener">Grants.gov</a> + RSS</span>
  </footer>

</div>
</body>
</html>
"""
