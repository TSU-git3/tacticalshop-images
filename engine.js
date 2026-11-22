// TSU first-photo cards upload engine, 22 Nov 2026 (owner OK 22 Nov ~01:36 UK on the 411 overview; placement answer 22 Nov ~15:20 UK:
// «Keep plain, drop last photo»). Runs in a my.prom.ua tab (owner's Chrome). Boot: fetch this file by commit, check SHA-256, (0,eval)(src).
// Payload P = {raw, order: [ids], L: {id: [expected_first_image_id, 'rep'|'ins', card_sha256]}}.
//   rep = first photo is an old card -> replaced by the new card; ins = card goes first, old photos keep their order; over 10 -> last dropped.
// Per listing: context -> snapshot (IndexedDB snap_<id>) -> check first image -> card from raw.githubusercontent (SHA-256) -> upload_image
//   (multipart images[]) -> product form save in a frame with only `images` changed (quantity 0 -> null) -> read-back: images = planned,
//   whole-context diff (allowed: images, main_image_id, date_modified, urls, variation main_image*; soft: discount, specs, presence, quantity).
// Frames live inside a container frame that is replaced every F.CMAX loads (instead of a fresh tab). State in IndexedDB F.DB.
(() => {
const F = window.F = window.F || {};
F.DB = 'tsu_first_photos_2026-11-22'; F.CMAX = 25;
F.sleep = ms => new Promise(r => { const w = new Worker(URL.createObjectURL(new Blob(['setTimeout(()=>postMessage(1),' + ms + ')']))); w.onmessage = () => { w.terminate(); r(); }; });
F.J = { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }, credentials: 'include' };
F.csrf = () => decodeURIComponent((document.cookie.match(/(?:^|; )csrf_token=([^;]+)/) || [])[1] || '');
F.hex = async buf => [...new Uint8Array(await crypto.subtle.digest('SHA-256', buf))].map(x => x.toString(16).padStart(2, '0')).join('');
F.ctx = async id => { const r = await fetch('/cms/product/v2/edit/' + id + '/context', F.J); if (r.status !== 200) throw new Error('ctx ' + id + ' http ' + r.status); const j = await r.json(); if (!j.context) throw new Error('ctx ' + id + ' no context'); return j.context; };
F.ids = a => (a || []).map(x => String(x && typeof x === 'object' ? x.id : x));
F.db = () => new Promise((r, j) => { const q = indexedDB.open(F.DB, 1); q.onupgradeneeded = () => q.result.createObjectStore('kv'); q.onsuccess = () => r(q.result); q.onerror = () => j(q.error); });
F.put = async (k, v) => { const d = await F.db(); await new Promise((r, j) => { const t = d.transaction('kv', 'readwrite'); t.objectStore('kv').put(v, k); t.oncomplete = r; t.onerror = () => j(t.error); }); d.close(); };
F.get = async k => { const d = await F.db(); const v = await new Promise(r => { const q = d.transaction('kv').objectStore('kv').get(k); q.onsuccess = () => r(q.result); }); d.close(); return v; };
F.persist = () => F.put('state', JSON.stringify({ done: F.done, log: F.log, up: F.up, skipped: F.skipped, soft: F.softLog }));
F.init = async P => { F.P = P; await F.put('payload', JSON.stringify(P)); return F.restore(); };
F.restore = async () => { if (!F.P) F.P = JSON.parse(await F.get('payload')); const s = JSON.parse((await F.get('state')) || '{}'); F.done = s.done || {}; F.log = s.log || {}; F.up = s.up || {}; F.skipped = s.skipped || {}; F.softLog = s.soft || []; return 'ready ' + F.P.order.length + ' listings, done ' + Object.keys(F.done).length + ', uploaded ' + Object.keys(F.up).length; };
F.flat = (o, p = '', out = {}) => { if (o && typeof o === 'object') { const ks = Object.keys(o); if (!ks.length) out[p] = JSON.stringify(o); for (const k of ks) F.flat(o[k], p ? p + '.' + k : k, out); } else out[p] = JSON.stringify(o); return out; };
F.allow = /^(images|main_image_id|date_modified|urls|variation_data\.variations\.\d+\.(main_image|main_image_id|main_image_url|image|images))(\.|$)/;
F.soft = /(^|\.)(discount|discount_active|specs|quantity_in_stock|presence|presence_sure|presence_title|qty|disabled_for_presence_sure|is_moderated|is_moderated_category)(\.|$)/;   // category moderation flag is Prom's category data (22 Nov)
// empty string <-> null counts as unchanged (the form sends gtin / mpn "" back as null, 22 Nov);
// a description that differs only in images.prom.ua addresses (Prom stores an embedded picture under a new address on save) is soft
F.nimg = v => String(v).replace(/https?:\/\/images\.prom\.ua\/[^"'\s)\\]+/g, 'IMG');
F.diff = (a, b) => { const A = F.flat(a), B = F.flat(b); const hard = [], soft = []; const nul = v => v === undefined || v === 'null' || v === '""'; for (const k of new Set([...Object.keys(A), ...Object.keys(B)])) { if (A[k] === B[k] || F.allow.test(k) || (nul(A[k]) && nul(B[k]))) continue; if (/(^|\.)description(_text)?\.(uk|ru)$/.test(k) && F.nimg(A[k]) === F.nimg(B[k])) { soft.push(k + '~imgurl'); continue; } (F.soft.test(k) ? soft : hard).push(k); } return { hard, soft }; };
// attribute order inside a variation row can change on save (same values, 22 Nov on 3256114571) -> compare sorted by name
F.norm = c => { const x = JSON.parse(JSON.stringify(c)); for (const v of ((x.variation_data || {}).variations || [])) if (Array.isArray(v.attrs)) v.attrs.sort((p, q) => String(p.name).localeCompare(String(q.name))); return x; };
F.diffRaw = F.diff; F.diff = (a, b) => F.diffRaw(F.norm(a), F.norm(b));
F.varImgs = c => JSON.stringify(((c.variation_data || {}).variations || []).filter(v => String(v.id) !== String(c.id)).map(v => [v.id, F.ids(v.images)]));
F.plan = (old, nid, mode) => [String(nid)].concat(mode === 'rep' ? old.slice(1) : old).slice(0, 10);
F.card = async id => {
  if (F.up[id]) return F.up[id];
  const r = await fetch(F.P.raw + 'p' + id + '.jpg', { cache: 'no-store', credentials: 'omit' }); if (r.status !== 200) throw new Error('card http ' + r.status);
  const buf = await r.arrayBuffer(); if ((await F.hex(buf)) !== F.P.L[id][2]) throw new Error('card sha mismatch');
  const fd = new FormData(); fd.append('images[]', new File([buf], 'p' + id + '.jpg', { type: 'image/jpeg' }));
  const u = await fetch(F.cur.urls.upload_image, { method: 'POST', body: fd, credentials: 'include', headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': F.csrf() } });
  let j = null; try { j = await u.json(); } catch (x) { } const nid = j && j[0] && j[0].id; if (!nid) throw new Error('upload http ' + u.status + ' ' + JSON.stringify(j).slice(0, 80));
  F.up[id] = String(nid); await F.persist(); return F.up[id];
};
F.container = async () => {   // about:blank container (a /robots.txt container is text/plain: the form never rendered inside it, 22 Nov)
  if (F.box && F.boxLoads < F.CMAX) return F.box.contentDocument;
  if (F.box) { try { F.box.src = 'about:blank'; } catch (x) { } F.box.remove(); F.box = null; await F.sleep(1500); }
  const b = document.createElement('iframe'); b.style.cssText = 'position:fixed;left:-6000px;top:0;width:1500px;height:1100px'; b.src = 'about:blank'; document.body.appendChild(b);
  await F.sleep(500); F.box = b; F.boxLoads = 0; F.boxes = (F.boxes || 0) + 1; return b.contentDocument;
};
// The form fills an empty own SEO title with the default text on save (22 Nov, test 1) -> send the snapshot's own SEO values back.
F.keepSeo = b => { const sn = F.snapNow; if (!sn || !sn.seo) throw new Error('no snapshot for seo'); const t = sn.seo.title || {}, d = sn.seo.description || {}; if ('seo_title' in b) b.seo_title = Object.assign({}, b.seo_title, { uk: t.uk || '', ru: t.ru || '' }); if ('seo_description' in b) b.seo_description = Object.assign({}, b.seo_description, { uk: d.uk || '', ru: d.ru || '' }); if ('seo_is_default' in b) b.seo_is_default = sn.seo.is_default;
  const k = sn.keywords; if ('keywords' in b && k) b.keywords = Object.assign({}, b.keywords, { uk: k.uk || '', ru: k.ru || '' });   // the form copies RU phrases into an empty UA field (22 Nov)
  return b; };
F.hook = (W, want, onBody, st) => {
  const of = W.fetch;
  W.fetch = async function (u, o) {
    if (want(u) && o && o.body != null) {
      st.seen = 'fetch'; const body = onBody(String(o.body)); if (body === null) { st.aborted = 1; st.fin = 1; throw new Error('tsu abort'); }
      const r = await of.call(this, u, Object.assign({}, o, { body })); const t = await r.clone().text(); st.http = r.status; st.resp = t.slice(0, 300); try { st.status = JSON.parse(t).status; } catch (x) { } st.fin = 1; return r;
    }
    return of.apply(this, arguments);
  };
  const X = W.XMLHttpRequest.prototype, oo = X.open, os = X.send;
  X.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
  X.send = function (b) {
    if (want(this.__u) && b != null) {
      st.seen = 'xhr'; const body = onBody(String(b)); if (body === null) { st.aborted = 1; st.fin = 1; return; }
      this.addEventListener('loadend', () => { st.http = this.status; st.resp = String(this.responseText).slice(0, 300); try { st.status = JSON.parse(this.responseText).status; } catch (x) { } st.fin = 1; });
      return os.call(this, body);
    }
    return os.apply(this, arguments);
  };
};
F.save = async (id, oldIds, newIds) => {
  const st = { id }; const D = await F.container(); const fr = D.createElement('iframe'); fr.style.cssText = 'width:1400px;height:1000px'; fr.src = '/cms/product/edit/' + id; D.body.appendChild(fr); F.boxLoads++; F.loads = (F.loads || 0) + 1;
  try {
    let btn = null; for (let i = 0; i < 60; i++) { await F.sleep(1000); try { btn = fr.contentDocument && fr.contentDocument.querySelector('[data-qaid=save_position_btn]'); } catch (x) { } if (btn && i >= 4) break; }
    if (!btn) { st.err = 'no save button'; return st; }
    F.hook(fr.contentWindow, u => String(u).includes('/cms/product/v2/save/' + id), s => {
      try { const b = JSON.parse(s); if (JSON.stringify(F.ids(b.images)) !== JSON.stringify(oldIds)) { st.err = 'body images != context'; return null; }
        b.images = newIds.map(Number); if (b.quantity_in_stock === 0) { b.quantity_in_stock = null; st.q0 = 1; } F.keepSeo(b); return JSON.stringify(b); } catch (x) { st.err = 'modify ' + x.message; return null; } }, st);
    btn.click();
    for (let i = 0; i < 40 && !st.fin; i++) await F.sleep(1000);
    if (!st.seen) st.err = st.err || 'no save request seen';
    return st;
  } finally { try { fr.src = 'about:blank'; } catch (x) { } fr.remove(); }
};
F.one = async id => {
  const [first, mode] = F.P.L[id]; const c = await F.ctx(id); F.cur = c; F.snapNow = c; const old = F.ids(c.images); const lg = F.log[id] = F.log[id] || {};
  if (F.up[id] && old[0] === F.up[id]) { lg.note = 'already first'; return 'ok'; }
  if (old[0] !== String(first)) { F.skipped[id] = 'first is ' + old[0] + ' not ' + first; return 'skip'; }
  // Prom fills an empty language side of phrases / packaging text on ANY save (server side: RU phrases copied into UA, RU packaging
  // machine-translated from UA; a 2nd save with the side empty does not undo it; 22 Nov on 2565312895, 1800305449) -> skip, owner decides
  const os = ['keywords', 'packaging', 'description'].filter(f => { const o = c[f] || {}; return (!String(o.uk || '').trim()) !== (!String(o.ru || '').trim()); });
  if (os.length) { F.skipped[id] = 'one language empty in ' + os.join('+') + ' (a save makes Prom fill it)'; return 'skip'; }
  if (!lg.old) { lg.old = old; await F.put('snap_' + id, JSON.stringify(c)); }
  const nid = await F.card(id); const neu = F.plan(old, nid, mode); lg.new = neu; lg.drop = old.filter(x => !neu.includes(x));
  await F.sleep(1500);
  const st = await F.save(id, old, neu); Object.assign(lg, { http: st.http, status: st.status, err: st.err, q0: st.q0 });
  if (st.status === 'error' && /дублировать|дублювати/.test(st.resp || '')) { F.skipped[id] = 'attr duplicates variant'; return 'skip'; }
  if (st.err || st.status !== 'success') { lg.resp = (st.resp || '').slice(0, 160); return 'stop'; }
  await F.sleep(2000);
  const snap = JSON.parse(await F.get('snap_' + id)); const c2 = await F.ctx(id); const d = F.diff(snap, c2);
  lg.ok = JSON.stringify(F.ids(c2.images)) === JSON.stringify(neu) && !d.hard.length && F.varImgs(snap) === F.varImgs(c2);
  if (d.soft.length) F.softLog.push(id + ':' + d.soft.slice(0, 4).join('|'));
  if (!lg.ok) { lg.hard = d.hard.slice(0, 8); lg.imgs = F.ids(c2.images).slice(0, 3); return 'stop'; }
  return 'ok';
};
F.run = async (ids, limit) => {
  F.state = { running: true, stop: null, at: null, fin: 0, t0: Date.now() };
  try {
    for (const id of ids) {
      if (F.done[id] || F.skipped[id]) continue;
      if (limit && F.state.fin >= limit) break;
      if (F.halt) { F.state.stop = 'halted by hand'; break; }
      F.state.at = id; let r = await F.one(id); const lg0 = F.log[id] || {};
      if (r === 'stop' && lg0.status === 'error' && /"errors"/.test(lg0.resp || '')) { F.skipped[id] = 'Prom refused (nothing saved): ' + lg0.resp.slice(0, 120); r = 'skip'; }   // validation refusal, e.g. empty UA description
      await F.persist();
      if (r === 'stop') { F.state.stop = 'stop at ' + id + ': ' + JSON.stringify(F.log[id]).slice(0, 300); break; }
      if (r === 'ok') { F.done[id] = 1; F.state.fin++; await F.persist(); }
      await F.sleep(2000);
    }
  } catch (x) { F.state.stop = 'error at ' + F.state.at + ': ' + x.message; await F.persist(); }
  F.state.running = false; F.state.t1 = Date.now();
};
F.st = () => JSON.stringify({ run: F.state && F.state.running, at: F.state && F.state.at, stop: F.state && F.state.stop, done: Object.keys(F.done || {}).length + '/' + ((F.P && F.P.order.length) || 0), fin: F.state && F.state.fin, skipped: Object.entries(F.skipped || {}).map(e => e.join('=')).join('; ').slice(0, 300), soft: (F.softLog || []).length, boxes: F.boxes, loads: F.loads, min: F.state ? Math.round(((F.state.t1 || Date.now()) - F.state.t0) / 60000) : 0 });
return 'engine ready';
})();
