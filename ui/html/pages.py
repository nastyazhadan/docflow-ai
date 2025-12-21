from __future__ import annotations

import json

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>DocFlow Login</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; max-width: 680px; }
    label { display: block; margin-top: 0.75rem; font-weight: 600; }
    input { width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
    button { margin-top: 1rem; padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }
    #error { margin-top: 1rem; color: #b00020; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>DocFlow — Login</h1>
  <p style="opacity: 0.8;">Test UI. Token is stored in an httpOnly cookie.</p>

  <form id="login-form">
    <label>
      tenant_slug
      <input type="text" id="tenant_slug" value="default" />
    </label>
    <label>
      tenant_name (for Register)
      <input type="text" id="tenant_name" value="Default" />
    </label>
    <label>
      email
      <input type="text" id="email" value="u@example.com" />
    </label>
    <label>
      password
      <input type="password" id="password" value="super-secret" />
    </label>
    <label>
      role (for Register)
      <select id="role" style="width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box;">
        <option value="editor" selected>editor (read + write)</option>
        <option value="viewer">viewer (read-only)</option>
      </select>
    </label>
    <button type="submit">Login</button>
    <button type="button" id="register" style="margin-left: 0.5rem;">Register</button>
  </form>

  <div id="error"></div>

  <script>
    const form = document.getElementById('login-form');
    const err = document.getElementById('error');
    const registerBtn = document.getElementById('register');

    function formatDetail(d) {
      if (d == null) return '';
      if (typeof d === 'string') return d;
      try { return JSON.stringify(d, null, 2); } catch (e) { return String(d); }
    }

    async function doAuth(path) {
      err.textContent = '';

      const tenant_slug = document.getElementById('tenant_slug').value.trim();
      const tenant_name = document.getElementById('tenant_name').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      const role = document.getElementById('role').value;

      try {
        let body = { tenant_slug, email, password };
        if (path === '/api/register') {
          body = { tenant_slug, tenant_name, email, password, role };
        }
        const resp = await fetch(path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });

        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          err.textContent = 'Error: ' + formatDetail(detail);
          return;
        }

        window.location.href = '/spaces';
      } catch (e2) {
        err.textContent = 'Request failed: ' + e2;
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await doAuth('/api/login');
    });

    registerBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      await doAuth('/api/register');
    });
  </script>
</body>
</html>
"""


SPACES_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>DocFlow Spaces</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; max-width: 900px; }
    .row { display: flex; gap: 1rem; align-items: end; flex-wrap: wrap; }
    label { display: block; margin-top: 0.75rem; font-weight: 600; }
    input { width: 320px; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
    button { margin-top: 1rem; padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }
    #error { margin-top: 1rem; color: #b00020; white-space: pre-wrap; }
    .space { padding: 0.75rem 0; border-bottom: 1px solid #eee; }
    .muted { opacity: 0.75; }
    a { color: #0b57d0; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>DocFlow — Spaces</h1>
  <div id="who" class="muted" style="margin-top: -0.5rem; margin-bottom: 1rem;"></div>
  <div style="margin-bottom: 1rem;">
    <a href="/sources">Manage Sources</a>
  </div>

  <div class="row" id="create-row">
    <div>
      <label>New space_id</label>
      <input id="space_id" value="demo-space" />
    </div>
    <div>
      <label>Name (optional)</label>
      <input id="name" value="Demo" />
    </div>
    <div>
      <button id="create">Create</button>
      <button id="logout" style="margin-left: 0.5rem;">Logout</button>
    </div>
  </div>

  <div id="error"></div>
  <h3 style="margin-top: 1.5rem;">Your spaces</h3>
  <div id="list" class="muted">Loading…</div>

  <script>
    const err = document.getElementById('error');
    const list = document.getElementById('list');
    const who = document.getElementById('who');
    const createRow = document.getElementById('create-row');

    function formatDetail(d) {
      if (d == null) return '';
      if (typeof d === 'string') return d;
      try { return JSON.stringify(d, null, 2); } catch (e) { return String(d); }
    }

    async function loadSpaces() {
      err.textContent = '';
      list.textContent = 'Loading…';
      const resp = await fetch('/api/spaces');
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        if (resp.status === 401) { window.location.href = '/login'; return; }
        const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
        err.textContent = 'Error: ' + formatDetail(detail);
        list.textContent = '';
        return;
      }
      const items = (data && data.items) || [];
      if (!items.length) {
        list.innerHTML = '<div class="muted">No spaces yet. Create one above.</div>';
        return;
      }
      list.innerHTML = items.map(s => (
        `<div class="space">
          <div><b>${s.space_id}</b> — ${s.name || ''}</div>
          <div class="muted">created_at=${s.created_at}</div>
          <div style="margin-top: 0.25rem;">
            <a href="/chat/${encodeURIComponent(s.space_id)}">Open chat</a>
            <a href="/sources?space_id=${encodeURIComponent(s.space_id)}" style="margin-left: 1rem;">Sources</a>
          </div>
        </div>`
      )).join('');
    }

    async function loadMe() {
      const resp = await fetch('/api/me');
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        if (resp.status === 401) { window.location.href = '/login'; return; }
        const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
        who.textContent = 'Error: ' + formatDetail(detail);
        return;
      }
      who.textContent = `tenant=${data.tenant_slug} • email=${data.email} • role=${data.role}`;
      if (data.role === 'viewer') {
        if (createRow) createRow.style.display = 'none';
      }
    }

    document.getElementById('create').addEventListener('click', async () => {
      err.textContent = '';
      const space_id = document.getElementById('space_id').value.trim();
      const name = document.getElementById('name').value.trim();
      if (!space_id) { err.textContent = 'space_id is required'; return; }
      const resp = await fetch('/api/spaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ space_id, name })
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
        err.textContent = 'Error: ' + formatDetail(detail);
        return;
      }
      await loadSpaces();
    });

    document.getElementById('logout').addEventListener('click', async () => {
      await fetch('/api/logout', { method: 'POST' });
      window.location.href = '/login';
    });

    loadMe();
    loadSpaces();
  </script>
</body>
</html>
"""


def chat_html(space_id: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>DocFlow Chat</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; max-width: 920px; }}
    label {{ display: block; margin-top: 0.75rem; font-weight: 600; }}
    input, textarea {{ width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }}
    button {{ margin-top: 1rem; padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }}
    #answer {{ margin-top: 1.5rem; padding: 1rem; border: 1px solid #ccc; background: #fafafa; white-space: pre-wrap; }}
    #sources {{ margin-top: 1rem; }}
    .source-item {{ margin-bottom: 0.5rem; padding: 0.5rem; border-bottom: 1px solid #eee; }}
    #error {{ margin-top: 1rem; color: #b00020; white-space: pre-wrap; }}
    #raw-json {{ margin-top: 1rem; display: none; white-space: pre; background: #111; color: #eee; padding: 1rem; overflow-x: auto; }}
    a {{ color: #0b57d0; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>DocFlow — Chat</h1>
  <div style="margin-bottom: 1rem;">
    <a href="/spaces">← back to spaces</a>
  </div>
  <div><b>space_id:</b> <span>{space_id}</span></div>

  <form id="chat-form">
    <label>
      Question
      <textarea id="question" rows="4">Кто такой капитан?</textarea>
    </label>

    <label>
      top_k
      <input type="number" id="top_k" value="3" min="1" max="20" />
    </label>

    <button type="submit">Ask</button>
  </form>

  <div id="error"></div>
  <div id="answer"></div>
  <div id="sources"></div>

  <label style="margin-top: 1rem; display: inline-flex; align-items: center; gap: 0.5rem;">
    <input type="checkbox" id="toggle-raw" /> Show raw JSON
  </label>
  <pre id="raw-json"></pre>

  <script>
    const space_id = {json.dumps(space_id)};
    const form = document.getElementById('chat-form');
    const answerEl = document.getElementById('answer');
    const sourcesEl = document.getElementById('sources');
    const errorEl = document.getElementById('error');
    const rawEl = document.getElementById('raw-json');
    const toggleRaw = document.getElementById('toggle-raw');

    function formatDetail(d) {{
      if (d == null) return '';
      if (typeof d === 'string') return d;
      try {{ return JSON.stringify(d, null, 2); }} catch (e) {{ return String(d); }}
    }}

    toggleRaw.addEventListener('change', () => {{
      rawEl.style.display = toggleRaw.checked ? 'block' : 'none';
    }});

    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      errorEl.textContent = '';
      answerEl.textContent = '';
      sourcesEl.textContent = '';
      rawEl.textContent = '';

      const question = document.getElementById('question').value.trim();
      const top_k = parseInt(document.getElementById('top_k').value || '3', 10);

      if (!question) {{
        errorEl.textContent = 'question is required';
        return;
      }}

      try {{
        const resp = await fetch('/api/chat/ask', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ space_id, query: question, top_k }})
        }});

        const data = await resp.json().catch(() => ({{}}));
        rawEl.textContent = JSON.stringify(data, null, 2);

        if (!resp.ok) {{
          if (resp.status === 401) {{ window.location.href = '/login'; return; }}
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          errorEl.textContent = 'Error: ' + formatDetail(detail);
          return;
        }}

        answerEl.textContent = data.answer || '';

        if (Array.isArray(data.sources)) {{
          const parts = data.sources.map((s) => {{
            const text = s.text || '';
            const score = typeof s.score === 'number' ? ` (score=${{s.score.toFixed(3)}})` : '';
            const meta = [];
            if (s.path) meta.push(`path=${{s.path}}`);
            if (s.title) meta.push(`title=${{s.title}}`);
            if (s.url) meta.push(`url=${{s.url}}`);
            const metaStr = meta.length ? ' [' + meta.join(', ') + ']' : '';
            return `<div class="source-item">${{text}}${{score}}${{metaStr}}</div>`;
          }});
          sourcesEl.innerHTML = '<h3>Sources</h3>' + parts.join('');
        }}

      }} catch (err) {{
        console.error(err);
        errorEl.textContent = 'Request failed: ' + err;
      }}
    }});
  </script>
</body>
</html>
"""


SOURCES_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>DocFlow Sources</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; max-width: 1000px; }
    .row { display: flex; gap: 1rem; align-items: end; flex-wrap: wrap; }
    label { display: block; margin-top: 0.75rem; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }
    button { margin-top: 1rem; padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }
    #error { margin-top: 1rem; color: #b00020; white-space: pre-wrap; }
    .source { padding: 1rem; margin-top: 1rem; border: 1px solid #ddd; border-radius: 4px; background: #fafafa; }
    .source-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .source-id { font-weight: 600; }
    .source-meta { font-size: 0.9em; color: #666; margin-top: 0.5rem; }
    .source-actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
    .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 3px; font-size: 0.85em; }
    .badge-enabled { background: #4caf50; color: white; }
    .badge-disabled { background: #999; color: white; }
    .badge-indexed { background: #2196f3; color: white; }
    .muted { opacity: 0.75; }
    a { color: #0b57d0; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .config-json { background: #f5f5f5; padding: 0.5rem; border-radius: 3px; font-family: monospace; font-size: 0.9em; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>DocFlow — Sources</h1>
  <div style="margin-bottom: 1rem;">
    <a href="/spaces">← back to spaces</a>
  </div>
  <div id="who" class="muted" style="margin-top: -0.5rem; margin-bottom: 1rem;"></div>

  <div class="row" id="create-row">
    <div style="flex: 1;">
      <label>Space ID</label>
      <select id="space_id" style="width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box;">
        <option value="">-- Select space --</option>
      </select>
    </div>
    <div style="flex: 1;">
      <label>Type</label>
      <select id="type" style="width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box;">
        <option value="http">HTTP</option>
        <option value="upload">Upload</option>
      </select>
    </div>
    <div style="flex: 2;">
      <label>Config (JSON)</label>
      <textarea id="config" rows="4" style="width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; font-family: monospace; font-size: 0.9em;" placeholder='{}'></textarea>
      <div id="config-hint" style="font-size: 0.85em; color: #666; margin-top: 0.5rem; padding: 0.5rem; background: #f5f5f5; border-radius: 3px;">
        <strong>Подсказка:</strong><br/>
        <span id="config-hint-text">Выберите тип источника для отображения примера конфигурации</span>
      </div>
    </div>
    <div>
      <button id="create">Create Source</button>
    </div>
  </div>

  <div id="error"></div>
  <div id="sources"></div>

  <script>
    function formatDetail(d) {
      if (d == null) return '';
      if (typeof d === 'string') return d;
      try { return JSON.stringify(d, null, 2); } catch (e) { return String(d); }
    }

    async function loadSpaces() {
      const resp = await fetch('/api/spaces');
      if (resp.status === 401) { window.location.href = '/login'; return; }
      const data = await resp.json().catch(() => ({}));
      if (resp.ok && data && data.items) {
        const spaceSelect = document.getElementById('space_id');
        spaceSelect.innerHTML = '<option value="">-- Select space --</option>';
        data.items.forEach(space => {
          const option = document.createElement('option');
          option.value = space.space_id;
          option.textContent = space.space_id + (space.name ? ` (${space.name})` : '');
          spaceSelect.appendChild(option);
        });
      }
    }

    async function loadMe() {
      const resp = await fetch('/api/me');
      if (resp.status === 401) { window.location.href = '/login'; return; }
      const data = await resp.json().catch(() => ({}));
      const who = document.getElementById('who');
      if (data && data.email) {
        who.textContent = `tenant=${data.tenant_slug} • email=${data.email} • role=${data.role}`;
        if (data.role === 'viewer') {
          const createRow = document.getElementById('create-row');
          if (createRow) createRow.style.display = 'none';
        }
      }
    }

    function updateConfigHint() {
      const type = document.getElementById('type').value;
      const hintText = document.getElementById('config-hint-text');
      if (type === 'http') {
        hintText.innerHTML = `
          <strong>HTTP источник:</strong> Укажите URL для скачивания данных.<br/>
          <strong>Пример:</strong> <code>{"url": "https://example.com"}</code><br/>
          <strong>Дополнительные параметры:</strong> <code>{"url": "https://api.example.com/data", "method": "GET", "headers": {"Authorization": "Bearer token"}}</code>
        `;
      } else if (type === 'upload') {
        hintText.innerHTML = `
          <strong>Upload источник:</strong> Конфигурация для загрузки файлов.<br/>
          <strong>Пример (пустой):</strong> <code>{}</code><br/>
          <strong>С параметрами:</strong> <code>{"path": "/data/uploads", "allowed_extensions": [".pdf", ".txt"]}</code>
        `;
      } else {
        hintText.textContent = 'Выберите тип источника для отображения примера конфигурации';
      }
    }

    async function loadSources() {
      const err = document.getElementById('error');
      const sourcesEl = document.getElementById('sources');
      err.textContent = '';
      sourcesEl.textContent = 'Loading...';

      try {
        const urlParams = new URLSearchParams(window.location.search);
        const spaceId = urlParams.get('space_id');
        const url = spaceId ? `/api/sources?space_id=${encodeURIComponent(spaceId)}` : '/api/sources';
        const resp = await fetch(url);
        if (resp.status === 401) { window.location.href = '/login'; return; }
        const data = await resp.json().catch(() => ({}));
        
        if (!resp.ok) {
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          err.textContent = 'Error: ' + formatDetail(detail);
          sourcesEl.textContent = '';
          return;
        }

        const items = data.items || [];
        if (items.length === 0) {
          sourcesEl.innerHTML = '<p class="muted">No sources found. Create one above.</p>';
          return;
        }

        sourcesEl.innerHTML = items.map(s => {
          const enabledClass = s.enabled ? 'badge-enabled' : 'badge-disabled';
          const indexedBadge = s.indexed_count !== null && s.indexed_count !== undefined 
            ? `<span class="badge badge-indexed">${s.indexed_count} indexed</span>` 
            : '';
          return `
            <div class="source">
              <div class="source-header">
                <div>
                  <span class="source-id">${s.id}</span>
                  <span class="badge ${enabledClass}">${s.enabled ? 'enabled' : 'disabled'}</span>
                  ${indexedBadge}
                </div>
              </div>
              <div class="source-meta">
                <div><b>Space:</b> ${s.space_id}</div>
                <div><b>Type:</b> ${s.type}</div>
                <div><b>Created:</b> ${new Date(s.created_at).toLocaleString()}</div>
              </div>
              <div class="config-json">${JSON.stringify(s.config, null, 2)}</div>
              <div class="source-actions">
                <button onclick="toggleSource('${s.id}', ${!s.enabled})">${s.enabled ? 'Disable' : 'Enable'}</button>
                <button onclick="deleteSource('${s.id}')" style="background: #f44336; color: white;">Delete</button>
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        err.textContent = 'Failed to load sources: ' + e;
        sourcesEl.textContent = '';
      }
    }

    async function toggleSource(sourceId, enabled) {
      const err = document.getElementById('error');
      err.textContent = '';
      try {
        const resp = await fetch(`/api/sources/${sourceId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        });
        if (resp.status === 401) { window.location.href = '/login'; return; }
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          err.textContent = 'Error: ' + formatDetail(detail);
          return;
        }
        await loadSources();
      } catch (e) {
        err.textContent = 'Failed to toggle source: ' + e;
      }
    }

    async function deleteSource(sourceId) {
      if (!confirm('Delete this source?')) return;
      const err = document.getElementById('error');
      err.textContent = '';
      try {
        const resp = await fetch(`/api/sources/${sourceId}`, { method: 'DELETE' });
        if (resp.status === 401) { window.location.href = '/login'; return; }
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          err.textContent = 'Error: ' + formatDetail(detail);
          return;
        }
        await loadSources();
      } catch (e) {
        err.textContent = 'Failed to delete source: ' + e;
      }
    }

    document.getElementById('type').addEventListener('change', updateConfigHint);
    updateConfigHint();

    document.getElementById('create').addEventListener('click', async () => {
      const err = document.getElementById('error');
      err.textContent = '';
      const space_id = document.getElementById('space_id').value.trim();
      const type = document.getElementById('type').value;
      const configText = document.getElementById('config').value.trim();
      
      if (!space_id) { err.textContent = 'Выберите space из списка'; return; }
      
      let config = {};
      if (configText) {
        try {
          config = JSON.parse(configText);
        } catch (e) {
          err.textContent = 'Invalid JSON in config: ' + e;
          return;
        }
      }

      try {
        const resp = await fetch('/api/sources', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ space_id, type, config, enabled: true })
        });
        if (resp.status === 401) { window.location.href = '/login'; return; }
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          const detail = (data && (data.detail ?? data.error ?? data)) || (resp.status + ' ' + resp.statusText);
          err.textContent = 'Error: ' + formatDetail(detail);
          return;
        }
        document.getElementById('space_id').value = '';
        document.getElementById('config').value = '';
        await loadSources();
      } catch (e) {
        err.textContent = 'Failed to create source: ' + e;
      }
    });

    loadMe();
    loadSpaces();
    loadSources();
    updateConfigHint();
  </script>
</body>
</html>
"""


