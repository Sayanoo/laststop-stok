/* Test: in-memory Firestore (compat-like) + fake user + fake sample */
(function () {
  const data = new Map(); // path -> object
  const listeners = new Set();
  let seq = 0;
  const clone = o => JSON.parse(JSON.stringify(o));
  const strip = o => { const r = {}; for (const [k, v] of Object.entries(o)) if (v !== undefined) r[k] = v; return r; };
  window.__db = data;
  window.__writes = [];
  function notify(path) { const col = path.split('/').slice(0, -1).join('/'); queueMicrotask(() => listeners.forEach(fn => (!fn.col || fn.col === col || fn.col === path) && fn())); }
  function docSnap(path) {
    const d = data.get(path);
    return { id: path.split("/").pop(), exists: !!d, data: () => (d ? clone(d) : undefined), ref: docRef(path) };
  }
  function docRef(path) {
    return {
      id: path.split("/").pop(), path,
      async get() { return docSnap(path); },
      async set(v, o) { window.__writes.push(["set", path]); data.set(path, o && o.merge ? { ...(data.get(path) || {}), ...strip(v) } : strip(v)); notify(path); },
      async update(v) { if (!data.has(path)) throw { code: "not-found", message: "no doc " + path }; window.__writes.push(["update", path]); data.set(path, { ...data.get(path), ...strip(v) }); notify(path); },
      async delete() { window.__writes.push(["delete", path]); data.delete(path); notify(path); },
      onSnapshot(fn) { const l = () => fn(docSnap(path)); l.col = path; listeners.add(l); queueMicrotask(l); return () => listeners.delete(l); },
    };
  }
  function query(col, ord, lim) {
    const q = {
      orderBy: (f, dir) => query(col, [f, dir], lim),
      limit: n => query(col, ord, n),
      doc: id => docRef(col + "/" + (id || "auto" + (++seq))),
      async add(v) { const r = docRef(col + "/auto" + (++seq) + "_" + Date.now()); await r.set(v); return r; },
      onSnapshot(fn, err) {
        const l = () => {
          let ds = [...data.keys()].filter(k => k.startsWith(col + "/") && k.split("/").length === col.split("/").length + 1).map(docSnap);
          if (ord) ds.sort((a, b) => { const x = a.data()[ord[0]], y = b.data()[ord[0]]; return (x > y ? 1 : x < y ? -1 : 0) * (ord[1] === "desc" ? -1 : 1); });
          if (lim) ds = ds.slice(0, lim);
          fn({ docs: ds, metadata: { fromCache: false } });
        };
        l.col = col; listeners.add(l); queueMicrotask(l); return () => listeners.delete(l);
      },
    };
    return q;
  }
  const fs = { collection: p => query(p), doc: p => docRef(p) };
  for (const [id, d] of Object.entries(window.SEED || {})) data.set("items/" + id, d);

  const sample = async () => { throw { code: "x" } };
  sample.limits = async () => ({ images: { maxCount: 6, mediaTypes: ["image/jpeg", "image/png"] } });
  sample.json = async (prompt) => {
    await new Promise(r => setTimeout(r, 300));
    return { supplier: "Asel Food", date: "2026-11-11", total: 60000, vatSeparate: false,
      lines: [
        { text: "또띠아 12인치", qty: 2, unitPrice: 15000, amount: 30000, itemId: "tortilla-12-durum", stockQty: 2, stockUnit: "paket", stockPrice: 15000, confidence: 0.95, why: "isim" },
        { text: "할라피뇨 슬라이스", qty: 1, unitPrice: 30000, amount: 30000, itemId: "__new", stockQty: 1, stockUnit: "kutu", stockPrice: 30000, confidence: 0.6, why: "yeni" },
      ] };
  };
  const user = { id: async () => "Testçi", me: async () => ({ id: "Testçi" }), can: async () => true, isOwner: () => false, canEdit: () => true,
    profiles: async ids => Object.fromEntries(ids.map(i => [i, { name: i }])) };
  window.lsSwitchUser = () => {};
  window.claude = { use: async n => (n === "db" ? fs : n === "user" ? user : n === "sample" ? sample : null) };
  try { localStorage.setItem("ls-staff-name", "Testçi"); } catch (_) {}
})();
