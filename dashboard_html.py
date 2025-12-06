"""
HTML template generator for the Bandcamp release dashboard.
This module isolates the large HTML/JS/CSS document so the main logic in
dashboard.py remains focused on data normalization and file I/O.
"""

from __future__ import annotations

import html
import json


def render_dashboard_html(*, title: str, data_json: str, embed_proxy_url: str | None = None) -> str:
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
      gap: 8px;
    }}
.filter-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: var(--radius);
    }}
    .filter-item input {{
      accent-color: var(--accent);
    }}
    .filter-count {{
      margin-left: auto;
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
      padding: 10px 12px;
      text-align: left;
      border-bottom: 1px solid var(--border);
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
    tr.data-row:hover {{
      background: rgba(82, 208, 255, 0.02);
    }}
    tr.expanded {{
      background: rgba(82, 208, 255, 0.08);
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
      <div class="filter-title">Filter by Label/Page</div>
      <div id="label-filters" class="filter-list"></div>
    </aside>
    <main>
      <header>
        <div class="header-bar">
          <h1>{escaped_title}</h1>
          <div style="display:flex; gap:8px;">
            <button id="theme-toggle" class="button">Light mode</button>
            <button id="stop-all" class="button">Reset players</button>
          </div>
        </div>
      </header>
      <div class="table-wrapper">
        <table aria-label="Bandcamp releases">
          <thead>
            <tr>
              <th style="width:16px;"></th>
              <th data-sort="page_name">Label/Page <span class="sort-indicator"></span></th>
              <th data-sort="artist">Artist <span class="sort-indicator"></span></th>
              <th data-sort="title">Title <span class="sort-indicator"></span></th>
              <th data-sort="date" style="width:130px;">Date <span class="sort-indicator"></span></th>
            </tr>
          </thead>
          <tbody id="release-rows"></tbody>
        </table>
        <div id="empty-state" class="empty-state" style="display: none;">No releases match the current filter.</div>
      </div>
    </main>
  </div>
  <script id="release-data" type="application/json">{data_json}</script>
  <script>
    const EMBED_PROXY_URL = {proxy_literal};
  </script>
  <script>
    const releases = JSON.parse(document.getElementById("release-data").textContent);
    const state = {{
      sortKey: "date",
      direction: "desc",
      activeLabels: new Set(),
    }};
    const THEME_KEY = "bc_dashboard_theme";
    const themeToggleBtn = document.getElementById("theme-toggle");
    function applyTheme(theme) {{
      const isLight = theme === "light";
      document.body.classList.toggle("theme-light", isLight);
      if (themeToggleBtn) {{
        themeToggleBtn.textContent = isLight ? "Dark mode" : "Light mode";
      }}
      localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    }}
    const savedTheme = localStorage.getItem(THEME_KEY) || "light";
    applyTheme(savedTheme);
    if (themeToggleBtn) {{
      themeToggleBtn.addEventListener("click", () => {{
        const next = document.body.classList.contains("theme-light") ? "dark" : "light";
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
      if (release.embed_url) return release.embed_url;
      if (!release.url) return null;

      const tryDirect = async () => {{
        const response = await fetch(release.url, {{ method: "GET" }});
        const text = await response.text();
        const meta = parseEmbedMeta(text);
        if (!meta) return null;
        const embedUrl = buildEmbedUrl(meta.item_id, meta.item_type === "track");
        release.embed_url = embedUrl;
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

      if (state.activeLabels.size === 0) {{
        labels.forEach(label => state.activeLabels.add(label));
      }}

      labels.forEach(label => {{
        const wrapper = document.createElement("label");
        wrapper.className = "filter-item";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = state.activeLabels.has(label);
        checkbox.addEventListener("change", () => {{
          if (checkbox.checked) {{
            state.activeLabels.add(label);
          }} else {{
            state.activeLabels.delete(label);
          }}
          renderTable();
        }});
        const text = document.createElement("span");
        text.textContent = label;
        const count = document.createElement("span");
        count.className = "filter-count";
        count.textContent = `(${{counts[label]}})`;
        wrapper.appendChild(checkbox);
        wrapper.appendChild(text);
        wrapper.appendChild(count);
        container.appendChild(wrapper);
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

    function stopAllPlayers() {{
      document.querySelectorAll("[data-embed-target]").forEach(target => {{
        const iframe = target.querySelector("iframe");
        if (iframe) {{
          iframe.remove();
          target.innerHTML = '<div class="detail-meta">Player stopped. Expand to reload.</div>';
        }}
      }});
      closeOpenDetailRows();
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
      return tr;
    }}

    function renderTable() {{
      const tbody = document.getElementById("release-rows");
      tbody.innerHTML = "";
      closeOpenDetailRows();

      const filtered = releases.filter(r => {{
        if (state.activeLabels.size === 0) return true;
        if (!r.page_name) return true;
        return state.activeLabels.has(r.page_name);
      }});

      const sorted = sortData(filtered);
      document.getElementById("empty-state").style.display = sorted.length ? "none" : "block";

      sorted.forEach(release => {{
        const tr = document.createElement("tr");
        tr.className = "data-row";
        tr.dataset.page = release.page_name || "";
        tr.tabIndex = 0;
        tr.innerHTML = `
          <td style="width:16px;"><span class="row-dot"></span></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.page_name || "Unknown"}}</a></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.artist || "—"}}</a></td>
          <td><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">${{release.title || "—"}}</a></td>
          <td>${{formatDate(release.date)}}</td>
        `;

        tr.addEventListener("click", () => {{
          tr.focus();
          const existingDetail = tr.nextElementSibling;
          const hasDetail = existingDetail && existingDetail.classList.contains("detail-row");
          const wasVisible = hasDetail && existingDetail.style.display !== "none";

          // If already visible, toggle closed.
          if (wasVisible) {{
            closeOpenDetailRows();
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

          const embedTarget = detail.querySelector("[data-embed-target]");
          const dot = tr.querySelector(".row-dot");
          if (dot) dot.classList.add("read");
          ensureEmbed(release).then(embedUrl => {{
              if (!embedUrl) {{
                embedTarget.innerHTML = `<div class="detail-meta">No embed available. Is the app still running? <br><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">Open on Bandcamp</a>.</div>`;
                return;
              }}
            const height = release.is_track ? 320 : 480;
            embedTarget.innerHTML = `<iframe title="Bandcamp player" style="border:0; width:100%; height:${{height}}px;" src="${{embedUrl}}" seamless></iframe>`;
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
          if (evt.key === "ArrowDown" || evt.key === "ArrowUp") {{
            evt.preventDefault();
            const rows = Array.from(document.querySelectorAll("tr.data-row"));
            const idx = rows.indexOf(tr);
            const nextIdx = evt.key === "ArrowDown" ? idx + 1 : idx - 1;
            if (nextIdx >= 0 && nextIdx < rows.length) {{
              rows[nextIdx].focus();
              rows[nextIdx].dispatchEvent(new Event("click"));
            }}
          }}
        }});

        const dot = tr.querySelector(".row-dot");
        if (dot) {{
          dot.addEventListener("click", (evt) => {{
            evt.stopPropagation();
            dot.classList.toggle("read");
          }});
        }}

        // Hover-based preload with debounce (0.2s)
        let hoverTimer;
        tr.addEventListener("mouseenter", () => {{
          hoverTimer = setTimeout(() => ensureEmbed(release), 200);
        }});
        tr.addEventListener("mouseleave", () => {{
          if (hoverTimer) {{
            clearTimeout(hoverTimer);
            hoverTimer = null;
          }}
        }});

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
    const stopAllBtn = document.getElementById("stop-all");
    if (stopAllBtn) {{
      stopAllBtn.addEventListener("click", evt => {{
        evt.stopPropagation();
        stopAllPlayers();
      }});
    }}
    renderTable();
  </script>
</body>
</html>
"""
