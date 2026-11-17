// GPN KW round 6 apply engine (17 Nov 2026). Runs on https://my.prom.ua/robots.txt (light host page) in the owner's Chrome.
// Load: R6.load(payloadUrl, sha256hex). Payload: {order:[base ids], it:{id:{sku, new:{name,title,meta,kw,desc}{uk,ru}, old5832?:{name,kw}}}, vars:{vid:{old:{uk,ru},new:{uk,ru}}}}
// Old values for comparison: IndexedDB tsu_kw_r6_2026-11-17 / b / kw_read (5832 not there: compared with payload old5832 + word report).
(() => {
  const R6 = window.R6 = window.R6 || {};
  const L2 = ['uk', 'ru'];
  const DBN = 'tsu_backup_gpn_r6_2026-11-17';
  const sleep = ms => new Promise(r => { const w = new Worker(URL.createObjectURL(new Blob(['setTimeout(()=>postMessage(1),' + ms + ')']))); w.onmessage = () => { w.terminate(); r(); }; });
  const sha = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s == null ? '' : String(s))))].map(b => b.toString(16).padStart(2, '0')).join('');
  const txt = h => ((new DOMParser()).parseFromString(h || '', 'text/html').body.textContent || '').replace(/\s+/g, '');
  const kwn = s => (s || '').split(',').map(x => x.trim()).filter(Boolean).join(', ');
  const words = h => ((new DOMParser()).parseFromString(h || '', 'text/html').body.textContent || '').toLowerCase().replace(/[’ʼ]/g, "'").match(/[0-9a-zа-яіїєґёъыэ'\-.,\/]+/g) || [];
  const idb = (name, store) => new Promise((res, rej) => {
    const q = indexedDB.open(name);
    q.onupgradeneeded = () => { if (!q.result.objectStoreNames.contains(store)) q.result.createObjectStore(store); };
    q.onsuccess = () => { const db = q.result; if (db.objectStoreNames.contains(store)) return res(db); const v = db.version + 1; db.close(); const q2 = indexedDB.open(name, v); q2.onupgradeneeded = () => q2.result.createObjectStore(store); q2.onsuccess = () => res(q2.result); q2.onerror = () => rej(q2.error); };
    q.onerror = () => rej(q.error);
  });
  const get = async (name, k) => { const db = await idb(name, 'b'); const v = await new Promise(r => { const q = db.transaction('b', 'readonly').objectStore('b').get(k); q.onsuccess = () => r(q.result); q.onerror = () => r(undefined); }); db.close(); return v; };
  const put = async (k, v) => { const db = await idb(DBN, 'b'); await new Promise((r, j) => { const tx = db.transaction('b', 'readwrite'); tx.objectStore('b').put(v, k); tx.oncomplete = r; tx.onerror = () => j(tx.error); }); db.close(); };
  const ctx = async id => { const r = await fetch('/cms/product/v2/edit/' + id + '/context', { credentials: 'include' }); const j = await r.json(); return j; };
  const vlist = c => ((c.variation_data || {}).variations || []);
  const frame = src => { const f = document.createElement('iframe'); f.style.cssText = 'position:fixed;left:-5000px;top:0;width:1400px;height:1000px'; f.src = src; document.body.appendChild(f); R6.loads = (R6.loads || 0) + 1; return f; };
  const kill = f => { try { f.src = 'about:blank'; } catch (e) {} setTimeout(() => f.remove(), 300); };
  const PROT = ['sku', 'price', 'prices', 'quantity_in_stock', 'presence', 'discount', 'category', 'group', 'status', 'images', 'is_portal_visible'];
  const sortDeep = v => Array.isArray(v) ? v.map(sortDeep).sort((a, b) => { const x = JSON.stringify(a), y = JSON.stringify(b); return x < y ? -1 : x > y ? 1 : 0; }) : (v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sortDeep(v[k])])) : v);

  R6.load = async (url, hash) => {
    const t = await (await fetch(url, { cache: 'no-store' })).text(); const h = await sha(t);
    if (h !== hash) return ['MISMATCH', h.slice(0, 12), t.length];
    R6.P = JSON.parse(t); R6.kw = await get('tsu_kw_r6_2026-11-17', 'kw_read');
    R6.S = R6.S || { pass: {}, res: {}, vres: {}, rb: {} }; R6.loads = 0;
    await put('payload_url', url); await put('payload_sha', hash);
    return ['ok', R6.P.order.length, Object.keys(R6.P.vars).length, R6.kw ? Object.keys(R6.kw).length : 0];
  };

  // Read pass: live context vs kw_read (or old5832); snapshot to IndexedDB. Returns list of problems (empty = clean).
  R6.check = async id => {
    const it = R6.P.it[id], j = await ctx(id), c = j.context, k = R6.kw[id], bad = [], note = [];
    await put('snap_' + id, j);
    if (k) {
      for (const L of L2) {
        if ((c.name || {})[L] !== k.name[L]) bad.push('name ' + L);
        if (kwn((c.keywords || {})[L]) !== kwn((k.kw || {})[L])) bad.push('kw ' + L);
        if (txt((c.description || {})[L]) !== txt((k.desc || {})[L])) bad.push('desc ' + L);
      }
      if (!!c.seo.is_default !== !!k.seo.is_default) bad.push('seo default');
      const kv = {}; for (const v of k.vars || []) kv[String(v.id)] = v;
      const lv = vlist(c); if (lv.length !== (k.vars || []).length) bad.push('var count ' + lv.length + '/' + (k.vars || []).length);
      for (const v of lv) { const o = kv[String(v.id)]; if (!o) { bad.push('var new ' + v.id); continue; } if (o.name_v2.uk !== v.name_v2.uk || o.name_v2.ru !== v.name_v2.ru) bad.push('var name ' + v.id); }
      if (c.price != k.price) note.push('price ' + k.price + '>' + c.price);
      if (c.status !== k.status) note.push('status');
    } else if (it.old5832) {
      for (const L of L2) { if ((c.name || {})[L] !== it.old5832.name[L]) bad.push('name ' + L); if (kwn((c.keywords || {})[L]) !== kwn(it.old5832.kw[L])) bad.push('kw ' + L); }
      for (const L of L2) { const a = words(c.description[L]), b = new Map(); for (const w of words(it.new.desc[L])) b.set(w, (b.get(w) || 0) + 1); const gone = []; for (const w of a) { const n = b.get(w) || 0; if (n) b.set(w, n - 1); else gone.push(w); } note.push('gone ' + L + ' ' + gone.length + ': ' + gone.slice(0, 12).join(' ')); }
    } else bad.push('no old values');
    if (c.discount) note.push('discount ' + JSON.stringify(c.discount).slice(0, 60));
    for (const v of vlist(c)) { if (String(v.id) === String(id)) continue; const p = R6.P.vars[String(v.id)]; if (!p) bad.push('var not in payload ' + v.id); else if (p.old.uk !== v.name_v2.uk || p.old.ru !== v.name_v2.ru) bad.push('var old differs ' + v.id); }
    R6.S.pass[id] = { bad, note }; return { bad, note };
  };
  R6.checkAll = () => { R6.S.passDone = false; R6.S.passIdx = 0; (async () => { for (const id of R6.P.order) { try { await R6.check(id); } catch (e) { R6.S.pass[id] = { bad: ['err ' + e.message], note: [] }; } R6.S.passIdx++; await sleep(1500); } R6.S.passDone = true; await put('pass', R6.S.pass); })(); return 'pass started'; };
  R6.passSum = () => { const b = {}, n = {}; for (const id in R6.S.pass) { if (R6.S.pass[id].bad.length) b[id] = R6.S.pass[id].bad.slice(0, 3); if (R6.S.pass[id].note.length) n[id] = R6.S.pass[id].note.slice(0, 2); } return { done: R6.S.passDone, idx: R6.S.passIdx, clean: Object.keys(R6.S.pass).length - Object.keys(b).length, bad: b, notes: n }; };

  // Form save of the base listing: name, seo_title, seo_description, seo_is_default false, keywords, description.
  R6.saveBase = async (id, mode) => {
    const it = R6.P.it[id], snap = await get(DBN, 'snap_' + id), c = snap.context, u = { id, mode, status: null, abort: null };
    const f = frame('/cms/product/edit/' + id); let btn = null;
    for (let i = 0; i < 60; i++) { await sleep(1000); try { btn = f.contentDocument && f.contentDocument.querySelector('[data-qaid=save_position_btn]'); } catch (e) { btn = null; } if (btn && i >= 8) break; }
    if (!btn) { u.abort = 'no save button'; kill(f); return u; }
    const W = f.contentWindow; let done = false;
    const want = x => String(x && x.url || x).indexOf('/cms/product/v2/save/' + id) >= 0;
    const mod = s => {
      const b = JSON.parse(s), o = JSON.parse(s);
      for (const L of L2) {
        if (((b.name || {})[L] || '') !== (c.name[L] || '')) throw new Error('form name ' + L + ' differs from snapshot');
        if (typeof (b.keywords || {})[L] !== 'string' || kwn(b.keywords[L]) !== kwn(c.keywords[L])) throw new Error('form kw ' + L + ' differs');
        if (txt((b.description || {})[L]) !== txt(c.description[L])) throw new Error('form desc ' + L + ' differs');
      }
      if (!b.seo_title || !b.seo_description) throw new Error('no seo keys');
      u.note = 'isdef ' + b.seo_is_default + ', vars ' + (Array.isArray(b.variations) ? b.variations.length : typeof b.variations);
      b.name = Object.assign({}, b.name, it.new.name);
      b.seo_title = Object.assign({}, b.seo_title, it.new.title);
      b.seo_description = Object.assign({}, b.seo_description, it.new.meta);
      b.seo_is_default = false;
      b.keywords = Object.assign({}, b.keywords, it.new.kw);
      b.description = Object.assign({}, b.description, it.new.desc);
      const ch = Object.keys(b).filter(k => JSON.stringify(b[k]) !== JSON.stringify(o[k])); u.changed = ch.join(' ');
      const odd = ch.filter(k => ['name', 'seo_title', 'seo_description', 'seo_is_default', 'keywords', 'description'].indexOf(k) < 0);
      if (odd.length) throw new Error('unexpected keys ' + odd.join(' '));
      return JSON.stringify(b);
    };
    const onResp = t => { try { const r = JSON.parse(t); u.status = r.status; u.errors = r.errors ? JSON.stringify(r.errors).slice(0, 300) : null; } catch (e) { u.status = 'unparsed'; } done = true; };
    const of = W.fetch;
    W.fetch = async function (x, o) {
      if (!want(x) || !o || typeof o.body !== 'string') return of.apply(this, arguments);
      u.seen = 'fetch'; let nb; try { nb = mod(o.body); } catch (e) { u.abort = e.message; done = true; throw e; }
      if (mode === 'dry') { u.abort = 'dry'; done = true; throw new Error('tsu dry'); }
      const r = await of.call(this, x, Object.assign({}, o, { body: nb })); onResp(await r.clone().text()); return r;
    };
    const X = W.XMLHttpRequest.prototype, oo = X.open, os = X.send;
    X.open = function (m, x) { this.__u = x; return oo.apply(this, arguments); };
    X.send = function (body) {
      if (!want(this.__u) || typeof body !== 'string') return os.apply(this, arguments);
      u.seen = 'xhr'; let nb; try { nb = mod(body); } catch (e) { u.abort = e.message; done = true; return; }
      if (mode === 'dry') { u.abort = 'dry'; done = true; return; }
      this.addEventListener('loadend', () => onResp(this.responseText)); return os.call(this, nb);
    };
    btn.click();
    for (let i = 0; i < 40 && !done; i++) await sleep(1000);
    if (!done) u.abort = u.abort || 'no request seen';
    await sleep(1500); kill(f); return u;
  };

  // Variant popup save: UA = name_input_primary, RU = name_input_secondary; body name = RU, name_translation = UA.
  R6.saveVar = async (base, vid) => {
    const p = R6.P.vars[vid], s = { base, vid, ok: false, abort: null };
    const f = frame('/cms/product/edit/' + base + '?show_variation_popup_by_id=' + vid);
    const inp = t => t && (/^(INPUT|TEXTAREA)$/.test(t.tagName) ? t : t.querySelector('input,textarea'));
    let a = null, b = null, btn = null;
    for (let i = 0; i < 50; i++) { await sleep(1000); try { const pop = f.contentDocument && f.contentDocument.querySelector('[data-qaid=edit_variation_popup]'); if (pop) { a = inp(pop.querySelector('[data-qaid=name_input_primary]')); b = inp(pop.querySelector('[data-qaid=name_input_secondary]')); btn = pop.querySelector('[data-qaid=save_btn]'); } } catch (e) { a = null; } if (a && b && btn && i >= 3 && a.value) break; }
    if (!(a && b && btn)) { s.abort = 'popup not found'; kill(f); return s; }
    if (a.value !== p.old.uk || b.value !== p.old.ru) { s.abort = 'popup shows other names'; s.seen = a.value.slice(0, 60); kill(f); return s; }
    const W = f.contentWindow; let done = false;
    const setv = (el, v) => { const pr = el.tagName === 'TEXTAREA' ? W.HTMLTextAreaElement.prototype : W.HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(pr, 'value').set.call(el, v); for (const e of ['input', 'change']) el.dispatchEvent(new W.Event(e, { bubbles: true })); el.dispatchEvent(new W.FocusEvent('blur', { bubbles: true })); el.dispatchEvent(new W.FocusEvent('focusout', { bubbles: true })); };
    setv(a, p.new.uk); await sleep(300); setv(b, p.new.ru); await sleep(500);
    const want = x => String(x && x.url || x).indexOf('/cms/variation_api/add_or_update_variation') >= 0;
    const chk = body => { let g = null; if (typeof body === 'string') { if (body.trim()[0] === '{') { const o = JSON.parse(body); g = k => o[k]; } else { const q = new URLSearchParams(body); g = k => q.get(k); } } else if (body && typeof body.get === 'function') g = k => body.get(k); if (!g) throw new Error('variant body shape'); if (g('name') !== p.new.ru || g('name_translation') !== p.new.uk) throw new Error('variant body names not as planned'); };
    const fin = (st, t) => { s.http = st; let o = null; try { o = JSON.parse(t); } catch (e) {} s.status = o && o.status !== undefined ? String(o.status) : ''; s.resp = String(t).slice(0, 120); const er = o && o.errors && (Array.isArray(o.errors) ? o.errors.length : Object.keys(o.errors).length); s.ok = st === 200 && !er && !/err|fail/i.test(s.status); done = true; };
    const of = W.fetch;
    W.fetch = async function (x, o) { if (!want(x)) return of.apply(this, arguments); s.seen = 'fetch'; try { chk(o && o.body); } catch (e) { s.abort = e.message; done = true; throw e; } const r = await of.apply(this, arguments); fin(r.status, await r.clone().text()); return r; };
    const X = W.XMLHttpRequest.prototype, oo = X.open, os = X.send;
    X.open = function (m, x) { this.__u = x; return oo.apply(this, arguments); };
    X.send = function (body) { if (!want(this.__u)) return os.apply(this, arguments); s.seen = 'xhr'; try { chk(body); } catch (e) { s.abort = e.message; done = true; return; } this.addEventListener('loadend', () => fin(this.status, this.responseText)); return os.apply(this, arguments); };
    btn.click();
    for (let i = 0; i < 40 && !done; i++) await sleep(1000);
    if (!done) s.abort = 'no variant request seen';
    await sleep(1500); kill(f); return s;
  };

  // Read-back of one listing after its saves: new values + protected fields vs snapshot.
  R6.readBack = async id => {
    const it = R6.P.it[id], snap = (await get(DBN, 'snap_' + id)).context, c = (await ctx(id)).context, bad = [], note = [];
    for (const L of L2) {
      if (c.name[L] !== it.new.name[L]) bad.push('name ' + L);
      if (((c.seo.title || {})[L] || '') !== it.new.title[L]) bad.push('title ' + L);
      if (((c.seo.description || {})[L] || '') !== it.new.meta[L]) bad.push('meta ' + L);
      if (kwn(c.keywords[L]) !== kwn(it.new.kw[L])) bad.push('kw ' + L); else if (c.keywords[L] !== it.new.kw[L]) note.push('kw ' + L + ' list-equal');
      if (c.description[L] !== it.new.desc[L]) { if (txt(c.description[L]) === txt(it.new.desc[L])) note.push('desc ' + L + ' markup differs'); else bad.push('desc ' + L); }
    }
    if (c.seo.is_default !== false) bad.push('seo is_default ' + c.seo.is_default);
    for (const k of PROT) { const a = k === 'images' ? (snap.images || []).length : JSON.stringify(sortDeep(snap[k])), b = k === 'images' ? (c.images || []).length : JSON.stringify(sortDeep(c[k])); if (a !== b) bad.push('changed ' + k); }
    if (JSON.stringify(sortDeep(snap.product_attributes)) !== JSON.stringify(sortDeep(c.product_attributes))) note.push('attributes changed');
    for (const v of vlist(c)) { const p = R6.P.vars[String(v.id)]; const exp = String(v.id) === String(id) ? it.new.name : (p ? p.new : null); if (exp && (v.name_v2.uk !== exp.uk || v.name_v2.ru !== exp.ru)) bad.push('var ' + v.id); }
    R6.S.rb[id] = { bad, note }; await put('rb_' + id, { bad, note, attrsAfter: c.product_attributes }); return { bad, note };
  };

  // Background run. Per listing: form save, then its variant popups, then read-back. Stops: 2 failures, unclean pass, load cap (fresh tab).
  R6.run = (list, maxLoads) => {
    const cap = maxLoads || 36; R6.S.run = { list, idx: 0, fails: 0, done: false, stop: '', t0: Date.now() };
    (async () => {
      const R = R6.S.run;
      for (const id of list) {
        if (location.host !== 'my.prom.ua') { R.stop = 'host'; break; }
        const prev = (await get(DBN, 'res_' + id)) || { base: null, vars: {} };
        if (prev.complete) { R.idx++; continue; }
        const pass = R6.S.pass[id] || ((await get(DBN, 'pass')) || {})[id];
        if (!pass || pass.bad.length) { prev.skip = 'pass not clean'; await put('res_' + id, prev); R.idx++; continue; }
        const snap = (await get(DBN, 'snap_' + id)).context;
        const todo = vlist(snap).filter(v => String(v.id) !== String(id)).map(v => String(v.id)).filter(v => R6.P.vars[v] && !(prev.vars[v] && prev.vars[v].ok) && (R6.P.vars[v].new.uk !== R6.P.vars[v].old.uk || R6.P.vars[v].new.ru !== R6.P.vars[v].old.ru));
        if (R6.loads > 0 && R6.loads + (prev.base === 'success' ? 0 : 1) + todo.length > cap) { R.stop = 'fresh tab'; break; }
        if (prev.base !== 'success') {
          await sleep(2000); let u; try { u = await R6.saveBase(id, 'real'); } catch (e) { u = { abort: 'exc ' + e.message }; }
          R6.S.res[id] = u; prev.base = u.status; prev.baseInfo = { abort: u.abort, errors: u.errors, changed: u.changed, note: u.note };
          await put('res_' + id, prev);
          if (u.status !== 'success') { R.fails++; if (R.fails >= 2) { R.stop = '2 fails'; break; } R.idx++; continue; }
        }
        for (const vid of todo) {
          await sleep(2000); let s; try { s = await R6.saveVar(id, vid); } catch (e) { s = { abort: 'exc ' + e.message }; }
          R6.S.vres[vid] = s; prev.vars[vid] = { ok: !!s.ok, abort: s.abort || null, status: s.status || null }; await put('res_' + id, prev);
          if (!s.ok) { R.fails++; if (R.fails >= 2) { R.stop = '2 fails'; break; } }
        }
        if (R.stop) break;
        await sleep(2000); let rb; try { rb = await R6.readBack(id); } catch (e) { rb = { bad: ['rb err ' + e.message], note: [] }; }
        prev.rb = rb; prev.complete = !rb.bad.length; await put('res_' + id, prev);
        if (rb.bad.length) { R.stop = 'read-back ' + id + ': ' + rb.bad.slice(0, 3).join(', '); break; }
        R.idx++;
      }
      R.done = true; R.min = Math.round((Date.now() - R.t0) / 60000);
    })();
    return 'run started ' + list.length;
  };
  R6.status = async () => { const R = R6.S.run || {}; let comp = 0, vok = 0, vbad = []; for (const id of R6.P.order) { const r = await get(DBN, 'res_' + id); if (!r) continue; if (r.complete) comp++; for (const v in r.vars) r.vars[v].ok ? vok++ : vbad.push(v); } return { done: R.done, stop: R.stop, idx: R.idx, of: (R.list || []).length, loads: R6.loads, complete: comp, varsOk: vok, varsBad: vbad.slice(0, 5), min: R.min }; };

  // Digest of the saved values of every listing (compared with the same digest made locally from the payload).
  R6.digest = async ids => { const out = {}; for (const id of ids) { const c = (await ctx(id)).context; const parts = []; for (const L of L2) parts.push(c.name[L], (c.seo.title || {})[L] || '', (c.seo.description || {})[L] || '', kwn(c.keywords[L]), c.description[L]); for (const v of vlist(c).slice().sort((a, b) => a.id - b.id)) parts.push(String(v.id), v.name_v2.uk, v.name_v2.ru); out[id] = (await sha(parts.join('\u0001'))).slice(0, 12); await sleep(800); } return out; };
  R6.ver = 'r6-1';
})();
