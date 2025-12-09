"""
HTML template generator for the Bandcamp release dashboard.
This module isolates the large HTML/JS/CSS document so the main logic in
dashboard.py remains focused on data normalization and file I/O.
"""

from __future__ import annotations

import html
import json


def render_dashboard_html(*, title: str, data_json: str, embed_proxy_url: str | None = None, default_theme: str | None = None) -> str:
    """
    Build the full dashboard HTML document.
    """
    escaped_title = html.escape(title)
    proxy_literal = json.dumps(embed_proxy_url)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    :root {{
      --bg: #0f1116;
      --surface: #181b22;
      --panel: #0b0d11;
      --accent: #52d0ff;
      --text: #f4f6fb;
      --muted: #a8b0c2;
      --border: #222735;
      --shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      --radius: 10px;
      --row-bg: #181b22;
      --row-unseen-bg: #1f2430;
    }}
    .theme-light {{
      --bg: #f5f7fb;
      --surface: #ffffff;
      --panel: #f1f3f7;
      --accent: #1f7aff;
      --text: #0a0f1a;
      --muted: #5a6375;
      --border: #d9e2ef;
      --shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
      --row-bg: #f6f7fb;
      --row-unseen-bg: #e8ecf4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at 20% 20%, rgba(82, 208, 255, 0.08), transparent 25%),
                  radial-gradient(circle at 80% 0%, rgba(255, 105, 180, 0.08), transparent 20%),
                  var(--bg);
      color: var(--text);
      font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
      display: flex;
    }}
    body.theme-light {{
      background: radial-gradient(circle at 20% 20%, rgba(31, 122, 255, 0.08), transparent 25%),
                  radial-gradient(circle at 80% 0%, rgba(255, 171, 64, 0.1), transparent 25%),
                  var(--bg);
    }}
    a.link {{
      color: var(--text);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: color 0.12s ease, border-color 0.12s ease;
    }}
    a.link:hover {{
      color: var(--accent);
      border-color: rgba(82, 208, 255, 0.6);
    }}
    header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--header-bg);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 20;
    }}
    .button {{
      padding: 8px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      cursor: pointer;
      transition: all 0.12s ease;
      font-weight: 600;
      letter-spacing: 0.2px;
    }}
    .button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }}
    h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: 0.3px;
    }}
    .row-dot {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--muted);
      opacity: 0.7;
      cursor: pointer;
      transition: opacity 0.12s ease;
    }}
    .row-dot.read {{
      opacity: 0;
    }}
    .cached-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border-radius: 999px;
      background: rgba(82, 208, 255, 0.14);
      color: var(--accent);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      margin-left: 6px;
      border: 1px solid rgba(82, 208, 255, 0.25);
      white-space: nowrap;
    }}
    .header-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 0;
      width: 100%;
    }}
    aside {{
      background: var(--panel);
      border-right: 1px solid var(--border);
      padding: 20px;
      position: sticky;
      top: 0;
      align-self: start;
      height: 100vh;
      overflow-y: auto;
    }}
    .filter-title {{
      font-size: 14px;
      letter-spacing: 0.5px;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .filter-list {{
      display: grid;
      gap: 4px;
    }}
    .filter-item {{
      display: grid;
      grid-template-columns: auto auto 1fr auto;
      align-items: center;
      gap: 6px;
      padding: 2px 0;
      background: none;
      border: none;
      border-radius: 0;
      line-height: 1.05;
      font-size: 13px;
    }}
    .filter-checkbox {{
      width: 16px;
      height: 16px;
      cursor: pointer;
    }}
    .filter-checkbox.show {{
      accent-color: var(--accent);
    }}
    .filter-checkbox.show-only {{
      accent-color: #ff6b6b;
    }}
    .filter-checkbox:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .filter-item.show-only-active .filter-checkbox.show {{
      opacity: 0.5;
    }}
    .filter-count {{
      margin-left: auto;
      justify-self: end;
      color: var(--muted);
      font-size: 12px;
    }}
    main {{
      padding: 0 16px 32px 16px;
    }}
    .table-wrapper {{
      margin-top: 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    thead {{
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    th, td {{
      padding: 6px 8px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      line-height: 1.05;
    }}
    th {{
      user-select: none;
      cursor: pointer;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.6px;
      color: var(--muted);
      position: sticky;
      top: 0;
      background: var(--panel);
      z-index: 6;
    }}
    th .sort-indicator {{
      position: absolute;
      right: 10px;
      opacity: 0.7;
      font-size: 10px;
    }}
    tr.data-row {{
      transition: background 0.15s ease;
      background: var(--row-bg);
    }}
    tr.data-row.unseen {{
      background: var(--row-unseen-bg);
    }}
    tr.data-row:hover {{
      background: rgba(82, 208, 255, 0.02);
    }}
    tr.expanded {{
      background: var(--row-bg);
    }}
    .pill {{
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(82, 208, 255, 0.12);
      color: var(--text);
      border: 1px solid rgba(82, 208, 255, 0.25);
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .pill small {{
      color: var(--muted);
      font-weight: 600;
      letter-spacing: 0.3px;
    }}
    .detail-row td {{
      padding: 0;
      border: none;
      background: var(--surface);
    }}
    .detail-card {{
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      background: var(--surface);
    }}
    .detail-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .detail-meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    .settings-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.45);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 50;
    }}
    .settings-panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      min-width: 280px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 12px;
    }}
    .settings-panel h2 {{
      margin: 0;
      font-size: 16px;
    }}
    .settings-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .embed-wrapper {{
      width: 100%;
      max-width: 550px;
      border-radius: var(--radius);
      overflow: hidden;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .empty-state {{
      padding: 30px;
      text-align: center;
      color: var(--muted);
    }}
    @media (max-width: 900px) {{
      body {{ display: block; }}
      .layout {{ grid-template-columns: 1fr; }}
      aside {{
        position: static;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--border);
      }}
      header {{ position: static; }}
      .detail-card {{ padding: 12px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <div class="filter-title">Filter by date</div>
      <div style="margin-bottom: 12px;">
        <label style="display:flex; align-items:center; gap:6px; font-size:13px;">
          <input type="checkbox" id="date-filter-toggle" />
          <span>Filter by date range</span>
        </label>
        <div style="display:grid; gap:6px; margin-top:6px; padding-left:4px;">
          <label style="display:flex; align-items:center; gap:6px; font-size:13px;">
            <span style="min-width:38px;">From:</span>
            <input type="text" id="date-filter-from" placeholder="YYYY-MM-DD" style="width:120px;" />
          </label>
          <label style="display:flex; align-items:center; gap:6px; font-size:13px;">
            <span style="min-width:38px;">To:</span>
            <input type="text" id="date-filter-to" placeholder="YYYY-MM-DD" style="width:120px;" />
          </label>
        </div>
      </div>
      <div class="filter-title">Filter by Label/Page</div>
      <div id="label-filters" class="filter-list"></div>
    </aside>
    <main>
      <header>
        <div class="header-bar">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <h1>{escaped_title}</h1>
            <div class="detail-meta" id="date-range"></div>
          </div>
          <div style="display:flex; gap:8px;">
            <label style="display:flex; align-items:center; gap:4px; font-size:12px;">
              <input type="checkbox" id="hide-viewed-toggle" />
              <span>Hide already seen releases</span>
            </label>
            <button id="mark-seen" class="button" style="padding:6px 10px; font-size:12px;">Mark all as seen</button>
            <button id="mark-unseen" class="button" style="padding:6px 10px; font-size:12px;">Mark all as unseen</button>
            <button id="settings-btn" class="button">Settings</button>
          </div>
        </div>
      </header>
      <div class="table-wrapper">
        <table aria-label="Bandcamp releases">
          <thead>
            <tr>
              <th style="width:24px;"></th>
              <th data-sort="page_name" style="min-width:100px; max-width:180px;">Label/Page <span class="sort-indicator"></span></th>
              <th data-sort="artist" style="min-width:120px; max-width:180px;">Artist <span class="sort-indicator"></span></th>
              <th data-sort="title" style="min-width:280px; max-width:560px;">Title <span class="sort-indicator"></span></th>
              <th data-sort="date" style="width:120px; min-width:120px; max-width:120px;">Date <span class="sort-indicator"></span></th>
            </tr>
          </thead>
          <tbody id="release-rows"></tbody>
        </table>
        <div id="empty-state" class="empty-state" style="display: none;">No releases match the current filter.</div>
      </div>
    </main>
  </div>
  <div id="settings-backdrop" class="settings-backdrop">
    <div class="settings-panel">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <h2>Settings</h2>
        <button id="settings-close" class="button">Close</button>
      </div>
      <div class="settings-row" style="padding-left:4px; color: var(--muted); font-size: 13px;">
        Clear cache:
      </div>
      <div class="settings-row" style="padding-left:12px;">
        <input type="checkbox" id="reset-clear-cache" checked />
        <label for="reset-clear-cache">Clear cache</label>
      </div>
      <div class="settings-row" style="padding-left:12px;">
        <input type="checkbox" id="reset-clear-viewed" checked />
        <label for="reset-clear-viewed">Clear read/unread state</label>
      </div>
      <button id="settings-reset" class="button">Reset</button>
      <div style="height:8px;"></div>
      <div class="settings-row">
        <input type="checkbox" id="theme-toggle" />
        <label for="theme-toggle">Dark mode</label>
      </div>
      <div class="settings-row">
        <input type="checkbox" id="show-cached-toggle" checked />
        <label for="show-cached-toggle">Show cached badges</label>
      </div>
    </div>
  </div>
  <script id="release-data" type="application/json">{data_json}</script>
  <script>
    const EMBED_PROXY_URL = {proxy_literal};
  </script>
  <script>
    const releases = JSON.parse(document.getElementById("release-data").textContent);
    const releaseMap = new Map();
    releases.forEach(r => releaseMap.set(releaseKey(r), r));
    const VIEWED_KEY = "bc_viewed_releases_v1";
    const API_ROOT = EMBED_PROXY_URL ? EMBED_PROXY_URL.replace(/\/embed-meta.*$/, "") : null;
    const DEFAULT_THEME = {json.dumps(default_theme or "light")};
    function releaseKey(release) {{
      return release.url || [release.page_name, release.artist, release.title, release.date].filter(Boolean).join("|");
    }}
    function renderDateRangeLabel() {{
      const el = document.getElementById("date-range");
      if (!el || !releases.length) return;
      const dates = releases
        .map(r => r.date)
        .filter(Boolean)
        .map(d => new Date(d))
        .filter(d => !isNaN(d.getTime()))
        .sort((a, b) => a - b);
      if (!dates.length) {{
        el.textContent = "";
        return;
      }}
      const fmt = d => {{
        const y = d.getFullYear();
        const m = `${{d.getMonth() + 1}}`.padStart(2, "0");
        const day = `${{d.getDate()}}`.padStart(2, "0");
        return `${{y}}-${{m}}-${{day}}`;
      }};
      const first = dates[0];
      const last = dates[dates.length - 1];
      el.textContent = `Date range: ${{fmt(first)}} to ${{fmt(last)}}`;
    }}
    async function loadViewedSet() {{
      if (API_ROOT) {{
        try {{
          const resp = await fetch(`${{API_ROOT}}/viewed-state`);
          if (resp.ok) {{
            const data = await resp.json();
            if (data && Array.isArray(data.viewed)) {{
              return new Set(data.viewed);
            }}
          }}
        }} catch (err) {{
          console.warn("Failed to load viewed state from API; falling back to localStorage", err);
        }}
      }}
      try {{
        const raw = localStorage.getItem(VIEWED_KEY);
        if (!raw) return new Set();
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? new Set(parsed) : new Set();
      }} catch (err) {{
        return new Set();
      }}
    }}
    function persistViewedLocal(set) {{
      try {{
        localStorage.setItem(VIEWED_KEY, JSON.stringify(Array.from(set)));
      }} catch (err) {{}}
    }}
    async function persistViewedRemote(url, isRead) {{
      if (!API_ROOT || !url) return;
      try {{
        await fetch(`${{API_ROOT}}/viewed-state`, {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{url, read: isRead}}),
        }});
      }} catch (err) {{
        console.warn("Failed to persist viewed state to API", err);
      }}
    }}
    function setViewed(release, isRead) {{
      const key = releaseKey(release);
      if (!key) return;
      if (isRead) {{
        state.viewed.add(key);
      }} else {{
        state.viewed.delete(key);
      }}
      persistViewedLocal(state.viewed);
      persistViewedRemote(release.url || key, isRead);
    }}
    const state = {{
      sortKey: "date",
      direction: "desc",
      showLabels: new Set(),
      showOnlyLabels: new Set(),
      viewed: new Set(),
      hideViewed: false,
      hideViewedSnapshot: new Set(),
      expandedKey: null,
      dateFilterEnabled: false,
      dateFilterFrom: "",
      dateFilterTo: "",
      showCachedBadges: true,
    }};
    const THEME_KEY = "bc_dashboard_theme";
    const themeToggleBtn = document.getElementById("theme-toggle");
    function applyTheme(theme) {{
      const isLight = theme === "light";
      document.body.classList.toggle("theme-light", isLight);
      if (themeToggleBtn) {{
        themeToggleBtn.checked = !isLight;
      }}
      localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    }}
    const savedTheme = localStorage.getItem(THEME_KEY) || DEFAULT_THEME || "light";
    applyTheme(savedTheme);
    if (themeToggleBtn) {{
      themeToggleBtn.checked = savedTheme !== "light";
      themeToggleBtn.addEventListener("change", () => {{
        const next = themeToggleBtn.checked ? "dark" : "light";
        applyTheme(next);
      }});
    }}

    function formatDate(value) {{
      if (!value) return "";
      const parsed = new Date(value);
      if (isNaN(parsed.getTime())) return value;
      const y = parsed.getFullYear();
      const m = `${{parsed.getMonth() + 1}}`.padStart(2, "0");
      const d = `${{parsed.getDate()}}`.padStart(2, "0");
      return `${{y}}-${{m}}-${{d}}`;
    }}

    function pageUrlFor(release) {{
      const url = release.url || "";
      if (!url) return "#";
      if (url.includes("/album/")) return url.split("/album/")[0];
      if (url.includes("/track/")) return url.split("/track/")[0];
      return url;
    }}

    function buildEmbedUrl(id, isTrack) {{
      if (!id) return null;
      const kind = isTrack ? "track" : "album";
      return `https://bandcamp.com/EmbeddedPlayer/${{kind}}=${{id}}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/`;
    }}

    function parseEmbedMeta(htmlText) {{
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, "text/html");
      const meta = doc.querySelector('meta[name="bc-page-properties"]');
      if (!meta || !meta.content) return null;
      try {{
        return JSON.parse(meta.content);
      }} catch (err) {{
        try {{
          return eval(`(${{meta.content}})`);
        }} catch (e) {{
          return null;
        }}
      }}
    }}

    async function ensureEmbed(release) {{
      if (release.embed_url) {{
        return release.embed_url;
      }}
      if (!release.url) return null;

      const tryDirect = async () => {{
        const response = await fetch(release.url, {{ method: "GET" }});
        const text = await response.text();
        const meta = parseEmbedMeta(text);
        if (!meta) return null;
        const embedUrl = buildEmbedUrl(meta.item_id, meta.item_type === "track");
        release.embed_url = embedUrl;
        if (meta.item_id) release.release_id = meta.item_id;
        release.is_track = meta.item_type === "track";
        return embedUrl;
      }};

      try {{
        if (EMBED_PROXY_URL) {{
          try {{
            const response = await fetch(`${{EMBED_PROXY_URL}}?url=${{encodeURIComponent(release.url)}}`);
            if (!response.ok) throw new Error(`Proxy fetch failed: ${{response.status}}`);
            const data = await response.json();
            const embedUrl = data.embed_url || buildEmbedUrl(data.release_id, data.is_track);
            release.embed_url = embedUrl;
            if (data.release_id) release.release_id = data.release_id;
            if (typeof data.is_track === "boolean") {{
              release.is_track = data.is_track;
            }}
            if (embedUrl) return embedUrl;
          }} catch (proxyErr) {{
            console.warn("Proxy embed fetch failed, falling back to direct fetch", proxyErr);
          }}
        }}
        return await tryDirect();
      }} catch (err) {{
        console.warn("Failed to fetch embed info", err);
        return null;
      }}
    }}

    function renderFilters() {{
      const counts = releases.reduce((acc, r) => {{
        if (!r.page_name) return acc;
        acc[r.page_name] = (acc[r.page_name] || 0) + 1;
        return acc;
      }}, {{}});
      const labels = Object.keys(counts)
        .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
      const container = document.getElementById("label-filters");
      container.innerHTML = "";

      if (labels.length === 0) {{
        container.innerHTML = "<div class='detail-meta'>No label/page data available.</div>";
        return;
      }}

      if (state.showLabels.size === 0) {{
        labels.forEach(label => state.showLabels.add(label));
      }}

      const showOnlyMode = state.showOnlyLabels.size > 0;

      labels.forEach(label => {{
        const wrapper = document.createElement("div");
        wrapper.className = "filter-item";
        if (showOnlyMode) wrapper.classList.add("show-only-active");

        const showCheckbox = document.createElement("input");
        showCheckbox.type = "checkbox";
        showCheckbox.className = "filter-checkbox show";
        showCheckbox.dataset.filterRole = "show";
        showCheckbox.checked = state.showLabels.has(label);
        showCheckbox.disabled = showOnlyMode;
        showCheckbox.addEventListener("change", () => {{
          if (showCheckbox.checked) {{
            state.showLabels.add(label);
          }} else {{
            state.showLabels.delete(label);
          }}
          renderTable();
        }});

        const showOnlyCheckbox = document.createElement("input");
        showOnlyCheckbox.type = "checkbox";
        showOnlyCheckbox.className = "filter-checkbox show-only";
        showOnlyCheckbox.dataset.filterRole = "show-only";
        showOnlyCheckbox.checked = state.showOnlyLabels.has(label);
        showOnlyCheckbox.addEventListener("change", () => {{
          if (showOnlyCheckbox.checked) {{
            state.showOnlyLabels.add(label);
          }} else {{
            state.showOnlyLabels.delete(label);
          }}
          syncShowCheckboxAvailability();
          renderTable();
        }});

        const text = document.createElement("span");
        text.textContent = label;
        const count = document.createElement("span");
        count.className = "filter-count";
        count.textContent = `(${{counts[label]}})`;
        wrapper.appendChild(showCheckbox);
        wrapper.appendChild(showOnlyCheckbox);
        wrapper.appendChild(text);
        wrapper.appendChild(count);
        container.appendChild(wrapper);
      }});

      syncShowCheckboxAvailability();
    }}

    function syncShowCheckboxAvailability() {{
      const disableShow = state.showOnlyLabels.size > 0;
      document.querySelectorAll("#label-filters .filter-item").forEach(item => {{
        const show = item.querySelector('input[data-filter-role="show"]');
        if (show) {{
          show.disabled = disableShow;
        }}
        item.classList.toggle("show-only-active", disableShow);
      }});
    }}

    function sortData(items) {{
      const {{sortKey, direction}} = state;
      const dir = direction === "asc" ? 1 : -1;
      return items.slice().sort((a, b) => {{
        if (sortKey === "date") {{
          const da = new Date(a.date);
          const db = new Date(b.date);
          const aTime = isNaN(da) ? 0 : da.getTime();
          const bTime = isNaN(db) ? 0 : db.getTime();
          return (aTime - bTime) * dir;
        }}
        const av = (a[sortKey] || "").toLowerCase();
        const bv = (b[sortKey] || "").toLowerCase();
        if (av === bv) return 0;
        return av > bv ? dir : -dir;
      }});
    }}

    function closeOpenDetailRows() {{
      document.querySelectorAll(".detail-row").forEach(node => {{
        const iframe = node.querySelector("iframe");
        if (iframe) iframe.remove();
        node.remove();
      }});
      document.querySelectorAll("tr.data-row").forEach(row => row.classList.remove("expanded"));
    }}

    function attachRowActions(row, release) {{
      // no-op; buttons removed
    }}

    function createDetailRow(release) {{
      const tr = document.createElement("tr");
      tr.className = "detail-row";
      const td = document.createElement("td");
      td.colSpan = 5;

      td.innerHTML = `
        <div class="detail-card">
          <div class="embed-wrapper" data-embed-target>
            <div class="detail-meta">Loading player…</div>
          </div>
        </div>`;
      tr.appendChild(td);
      td.addEventListener("click", (evt) => {{
        // Ignore clicks directly on the iframe
        if (evt.target.tagName.toLowerCase() === "iframe") return;
        // Focus the parent data row without toggling collapse
        const dataRow = tr.previousElementSibling;
        if (dataRow && dataRow.classList.contains("data-row")) {{
          dataRow.focus();
        }}
      }});
      return tr;
    }}

    function renderTable() {{
      const tbody = document.getElementById("release-rows");
      tbody.innerHTML = "";
      closeOpenDetailRows();

      const filtered = releases.filter(r => {{
        const useShowOnly = state.showOnlyLabels.size > 0;
        const activeSet = useShowOnly ? state.showOnlyLabels : state.showLabels;
        if (activeSet.size === 0) return true;
        if (!r.page_name) return true;
        if (!activeSet.has(r.page_name)) return false;
        if (state.dateFilterEnabled) {{
          if (state.dateFilterFrom) {{
            const fromTs = Date.parse(state.dateFilterFrom);
            const rowTs = Date.parse(r.date);
            if (!isNaN(fromTs) && !isNaN(rowTs) && rowTs < fromTs) return false;
          }}
          if (state.dateFilterTo) {{
            const toTs = Date.parse(state.dateFilterTo);
            const rowTs = Date.parse(r.date);
            if (!isNaN(toTs) && !isNaN(rowTs) && rowTs > toTs) return false;
          }}
        }}
        if (state.hideViewed && state.hideViewedSnapshot.size > 0) {{
          const key = releaseKey(r);
          if (state.expandedKey && key === state.expandedKey) return true;
          return !state.hideViewedSnapshot.has(key);
        }}
        return true;
      }});

      const sorted = sortData(filtered);
      document.getElementById("empty-state").style.display = sorted.length ? "none" : "block";

      sorted.forEach(release => {{
        const tr = document.createElement("tr");
        tr.className = "data-row";
        tr.dataset.key = releaseKey(release);
        tr.dataset.page = release.page_name || "";
        tr.tabIndex = 0;
        tr.innerHTML = `
          <td style="width:24px;"><span class="row-dot"></span></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.page_name || "Unknown"}}</a></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.artist || "—"}}</a></td>
          <td><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">${{release.title || "—"}}</a>${{state.showCachedBadges && release.embed_url ? ' <span class="cached-badge">cached</span>' : ''}}</td>
          <td>${{formatDate(release.date)}}</td>
        `;
        const existingRead = state.viewed.has(releaseKey(release));
        const initialDot = tr.querySelector(".row-dot");
        if (initialDot) initialDot.classList.toggle("read", existingRead);
        tr.classList.toggle("unseen", !existingRead);

        tr.addEventListener("click", () => {{
          tr.focus();
          const existingDetail = tr.nextElementSibling;
          const hasDetail = existingDetail && existingDetail.classList.contains("detail-row");
          const wasVisible = hasDetail && existingDetail.style.display !== "none";

          // If already visible, toggle closed.
          if (wasVisible) {{
            closeOpenDetailRows();
            state.expandedKey = null;
            return;
          }}

          // Hide others
          closeOpenDetailRows();

          let detail = existingDetail;
          if (!hasDetail) {{
            detail = createDetailRow(release);
            tr.after(detail);
          }} else {{
            // ensure adjacency and show
            tr.after(detail);
            detail.style.display = "";
          }}
          tr.classList.add("expanded");
          state.expandedKey = releaseKey(release);

          const embedTarget = detail.querySelector("[data-embed-target]");
          const dot = tr.querySelector(".row-dot");
          if (dot) dot.classList.add("read");
          tr.classList.remove("unseen");
          const cachedUrl = releaseKey(release);
          if (cachedUrl) {{
            state.viewed.add(cachedUrl);
          }}
          setViewed(release, true);
          ensureEmbed(release).then(embedUrl => {{
              if (!embedUrl) {{
                embedTarget.innerHTML = `<div class="detail-meta">No embed available. Is the app still running? <br><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">Open on Bandcamp</a>.</div>`;
                return;
              }}
            const height = release.is_track ? 320 : 480;
            embedTarget.innerHTML = `<iframe title="Bandcamp player" style="border:0; width:100%; height:${{height}}px;" src="${{embedUrl}}" seamless></iframe>`;
            const titleCell = tr.children[3];
            if (titleCell && embedUrl && state.showCachedBadges && !titleCell.querySelector(".cached-badge")) {{
              titleCell.insertAdjacentHTML("beforeend", ' <span class="cached-badge">cached</span>');
            }}
          }});
        }});

        tr.addEventListener("keydown", (evt) => {{
          if (evt.key === "Escape") {{
            evt.preventDefault();
            closeOpenDetailRows();
            return;
          }}
          if (evt.key === " " || evt.key === "Spacebar" || evt.key === "Space") {{
            evt.preventDefault();
            tr.click();
            return;
          }}
          if (evt.key === "Enter") {{
            evt.preventDefault();
            tr.click();
            return;
          }}
          if (evt.key === "ArrowDown" || evt.key === "ArrowUp") {{
            evt.preventDefault();
            const rows = Array.from(document.querySelectorAll("tr.data-row"));
            const idx = rows.indexOf(tr);
            const nextIdx = evt.key === "ArrowDown" ? idx + 1 : idx - 1;
            if (nextIdx >= 0 && nextIdx < rows.length) {{
              rows[nextIdx].focus();
            }}
            return;
          }}
          if (evt.key.toLowerCase() === "u") {{
            evt.preventDefault();
            const markerCell = tr.querySelector("td:first-child");
            if (markerCell) {{
              const dot = markerCell.querySelector(".row-dot");
              if (dot) dot.classList.toggle("read", false);
              else {{
                const newDot = document.createElement("span");
                newDot.className = "row-dot";
                markerCell.appendChild(newDot);
              }}
              setViewed(release, false);
            }}
          }}
        }});

        const markerCell = tr.querySelector("td:first-child");
        if (markerCell) {{
          markerCell.addEventListener("click", (evt) => {{
            evt.stopPropagation();
            const dot = markerCell.querySelector(".row-dot");
            if (dot) {{
              const willBeRead = !dot.classList.contains("read");
              dot.classList.toggle("read");
              tr.classList.toggle("unseen", !willBeRead);
              setViewed(release, willBeRead);
            }}
          }});
        }}

        // Hover/focus-based preload with debounce (0.2s)
        let preloadTimer;
        const schedulePreload = () => {{
          preloadTimer = setTimeout(() => ensureEmbed(release), 200);
        }};
        const cancelPreload = () => {{
          if (preloadTimer) {{
            clearTimeout(preloadTimer);
            preloadTimer = null;
          }}
        }};
        tr.addEventListener("mouseenter", schedulePreload);
        tr.addEventListener("mouseleave", cancelPreload);
        tr.addEventListener("focus", schedulePreload);
        tr.addEventListener("blur", cancelPreload);

        attachRowActions(tr, release);
        tbody.appendChild(tr);
      }});
      refreshSortIndicators();
    }}

    function refreshSortIndicators() {{
      document.querySelectorAll("th[data-sort]").forEach(th => {{
        const indicator = th.querySelector(".sort-indicator");
        const key = th.dataset.sort;
        if (state.sortKey === key) {{
          indicator.textContent = state.direction === "asc" ? "▲" : "▼";
          th.style.color = "var(--text)";
        }} else {{
          indicator.textContent = "";
          th.style.color = "var(--muted)";
        }}
      }});
    }}

    function attachHeaderSorting() {{
      document.querySelectorAll("th[data-sort]").forEach(th => {{
        th.addEventListener("click", () => {{
          const key = th.dataset.sort;
          if (state.sortKey === key) {{
            state.direction = state.direction === "asc" ? "desc" : "asc";
          }} else {{
            state.sortKey = key;
            state.direction = key === "date" ? "desc" : "asc";
          }}
          renderTable();
        }});
      }});
    }}

    renderFilters();
    attachHeaderSorting();
    const settingsBackdrop = document.getElementById("settings-backdrop");
    const settingsBtn = document.getElementById("settings-btn");
    const settingsClose = document.getElementById("settings-close");
    const settingsReset = document.getElementById("settings-reset");
    const resetClearCache = document.getElementById("reset-clear-cache");
    const resetClearViewed = document.getElementById("reset-clear-viewed");
    const hideViewedToggle = document.getElementById("hide-viewed-toggle");
    const markSeenBtn = document.getElementById("mark-seen");
    const markUnseenBtn = document.getElementById("mark-unseen");
    const dateFilterToggle = document.getElementById("date-filter-toggle");
    const dateFilterFrom = document.getElementById("date-filter-from");
    const dateFilterTo = document.getElementById("date-filter-to");
    const showCachedToggle = document.getElementById("show-cached-toggle");

    function toggleSettings(open) {{
      if (!settingsBackdrop) return;
      settingsBackdrop.style.display = open ? "flex" : "none";
    }}
    if (settingsBtn) settingsBtn.addEventListener("click", () => toggleSettings(true));
    if (settingsClose) settingsClose.addEventListener("click", () => toggleSettings(false));
    if (settingsBackdrop) settingsBackdrop.addEventListener("click", (e) => {{
      if (e.target === settingsBackdrop) toggleSettings(false);
    }});

    async function performReset() {{
      const clearCache = resetClearCache ? !!resetClearCache.checked : false;
      const clearViewed = resetClearViewed ? !!resetClearViewed.checked : false;
      if (!clearCache && !clearViewed) {{
        toggleSettings(false);
        return;
      }}
      let hadError = false;
      if (API_ROOT) {{
        try {{
          const resp = await fetch(`${{API_ROOT}}/reset-caches`, {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{clear_cache: clearCache, clear_viewed: clearViewed}}),
          }});
          if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
        }} catch (err) {{
          console.warn("Failed to reset via API", err);
          hadError = true;
        }}
      }} else {{
        hadError = true; // cannot clear disk cache without API
      }}
      if (clearViewed) {{
        state.viewed = new Set();
        persistViewedLocal(state.viewed);
        renderTable();
      }}
      if (clearCache) {{
        releases.forEach(r => {{
          delete r.embed_url;
          delete r.release_id;
          delete r.is_track;
        }});
        renderTable();
      }}
      toggleSettings(false);
      if (hadError && clearCache) {{
        alert("Could not clear disk cache (proxy not reachable). Run the app/proxy and try again.");
      }}
    }}
    if (settingsReset) settingsReset.addEventListener("click", performReset);

    function applyHideViewed(checked) {{
      const expandedRow = document.querySelector("tr.data-row.expanded");
      if (expandedRow && expandedRow.dataset.key) {{
        state.expandedKey = expandedRow.dataset.key;
      }}
      state.hideViewed = checked;
      if (checked) {{
        state.hideViewedSnapshot = new Set(state.viewed);
      }} else {{
        state.hideViewedSnapshot = new Set();
      }}
      renderTable();
    }}
    if (hideViewedToggle) {{
      hideViewedToggle.addEventListener("change", () => applyHideViewed(hideViewedToggle.checked));
    }}

    function markVisibleRows(seen) {{
      const rows = Array.from(document.querySelectorAll("#release-rows tr.data-row"));
      rows.forEach(row => {{
        const key = row.dataset.key;
        const release = key ? releaseMap.get(key) : null;
        if (!release) return;
        setViewed(release, seen);
        const dot = row.querySelector(".row-dot");
        if (dot) {{
          dot.classList.toggle("read", seen);
        }}
        row.classList.toggle("unseen", !seen);
      }});
      if (state.hideViewed) {{
        state.hideViewedSnapshot = new Set(state.viewed);
      }}
      renderTable();
    }}
    if (markSeenBtn) markSeenBtn.addEventListener("click", () => markVisibleRows(true));
    if (markUnseenBtn) markUnseenBtn.addEventListener("click", () => markVisibleRows(false));

    if (showCachedToggle) {{
      showCachedToggle.checked = state.showCachedBadges;
      showCachedToggle.addEventListener("change", () => {{
        state.showCachedBadges = !!showCachedToggle.checked;
        renderTable();
      }});
    }}

    function onDateFilterChange() {{
      state.dateFilterEnabled = !!(dateFilterToggle && dateFilterToggle.checked);
      state.dateFilterFrom = (dateFilterFrom?.value || "").trim();
      state.dateFilterTo = (dateFilterTo?.value || "").trim();
      renderTable();
    }}
    if (dateFilterToggle) dateFilterToggle.addEventListener("change", onDateFilterChange);
    if (dateFilterFrom) dateFilterFrom.addEventListener("input", onDateFilterChange);
    if (dateFilterTo) dateFilterTo.addEventListener("input", onDateFilterChange);

    // Render after viewed state loads to keep persisted read dots and show date range
    loadViewedSet().then(set => {{
      state.viewed = set;
      renderDateRangeLabel();
      renderTable();
    }}).catch(() => {{
      renderDateRangeLabel();
      renderTable();
    }});
  </script>
</body>
</html>
"""
