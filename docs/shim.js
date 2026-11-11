/* Last Stop Stok — Firebase köprüsü.
   Sayfa kodu `window.claude.use("db"|"user"|"sample")` çağırır; burada bunları Firebase ile karşılıyoruz:
   db → Firestore (compat), user → dükkan girişi + seçilen isim, sample → Gemini (Firebase AI Logic). */
(function () {
  const cfg = window.FIREBASE_CONFIG;
  const SHOP_EMAIL = window.SHOP_EMAIL;
  firebase.initializeApp(cfg);
  const fs = firebase.firestore();
  fs.settings({ ignoreUndefinedProperties: true, merge: true });
  try { fs.enablePersistence({ synchronizeTabs: true }).catch(() => {}); } catch (_) {}
  const auth = firebase.auth();
  const ls = { get: k => { try { return localStorage.getItem(k) } catch (_) { return null } },
               set: (k, v) => { try { localStorage.setItem(k, v) } catch (_) {} },
               del: k => { try { localStorage.removeItem(k) } catch (_) {} } };

  let resolveReady; const ready = new Promise(r => (resolveReady = r));
  const nameKey = "ls-staff-name";

  function gate(needPass) {
    let el = document.getElementById("loginGate");
    if (!el) { el = document.createElement("div"); el.id = "loginGate"; document.body.appendChild(el); }
    const name = ls.get(nameKey) || "";
    el.innerHTML = `<form class="lg-card" autocomplete="on">
      <img class="lg-logo" src="logo.png" alt="">
      <h2>Last Stop Stok</h2>
      <p>${needPass ? "Dükkan şifresi ile giriş yapın. Bu telefonda bir kez yeterli." : "Bu telefonu kim kullanıyor?"}</p>
      <label>Adınız<input id="lgName" required maxlength="30" value="${name.replace(/"/g, "&quot;")}" placeholder="ör. Ahmet" autocomplete="nickname"></label>
      ${needPass ? `<label>Dükkan şifresi<input id="lgPass" type="password" required autocomplete="current-password"></label>` : ""}
      <button class="btn" type="submit">Giriş</button><div class="lg-err" id="lgErr"></div></form>`;
    el.hidden = false;
    el.querySelector("form").onsubmit = async e => {
      e.preventDefault();
      const n = el.querySelector("#lgName").value.trim(); if (!n) return;
      const btn = el.querySelector("button"); btn.disabled = true; el.querySelector("#lgErr").textContent = "";
      try {
        if (needPass) await auth.signInWithEmailAndPassword(SHOP_EMAIL, el.querySelector("#lgPass").value);
        ls.set(nameKey, n);
        try { await fs.doc("staff/" + n).set({ name: n, lastSeen: new Date().toISOString() }, { merge: true }); } catch (_) {}
        el.hidden = true; resolveReady(n);
      } catch (err) {
        btn.disabled = false;
        el.querySelector("#lgErr").textContent = /password|credential/i.test(err.code || "") ? "Şifre yanlış." : "Giriş olmadı: " + (err.message || err);
      }
    };
  }

  auth.onAuthStateChanged(u => {
    if (!u) return gate(true);
    const n = ls.get(nameKey);
    if (n) resolveReady(n); else gate(false);
  });

  window.lsSwitchUser = () => { ls.del(nameKey); location.reload(); };
  window.lsLogout = async () => { ls.del(nameKey); await auth.signOut(); location.reload(); };

  /* ---- Gemini ile fiş okuma ---- */
  async function shrink(file) {
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, 2000 / Math.max(bmp.width, bmp.height));
    const c = document.createElement("canvas"); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
    const url = c.toDataURL("image/jpeg", 0.85);
    return { inlineData: { mimeType: "image/jpeg", data: url.split(",")[1] } };
  }
  let modelP = null;
  function model() {
    return modelP ||= (async () => {
      const V = "12.19.0";
      const { initializeApp } = await import(`https://www.gstatic.com/firebasejs/${V}/firebase-app.js`);
      const { getAI, getGenerativeModel, GoogleAIBackend } = await import(`https://www.gstatic.com/firebasejs/${V}/firebase-ai.js`);
      const app = initializeApp(cfg, "ai");
      const ai = getAI(app, { backend: new GoogleAIBackend() });
      return getGenerativeModel(ai, { model: "gemini-2.5-flash", generationConfig: { responseMimeType: "application/json", temperature: 0.1 } });
    })();
  }
  const sample = async () => { throw { code: "unsupported", message: "Sadece JSON desteklenir" }; };
  sample.limits = async () => ({ images: { maxCount: 6, mediaTypes: ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"] } });
  sample.json = async (prompt, opts = {}) => {
    try {
      const m = await model();
      const parts = [String(prompt)];
      for (const f of opts.images || []) parts.push(await shrink(f));
      if (opts.signal?.aborted) throw { code: "aborted", message: "İptal edildi" };
      opts.onText && opts.onText({ text: "…", delta: "…" });
      const r = await m.generateContent(parts);
      const t = r.response.text().trim().replace(/^```(?:json)?\s*|\s*```$/g, "");
      try { return JSON.parse(t); } catch (_) { throw { code: "invalid_json", message: "Fiş okunamadı, tekrar deneyin", text: t }; }
    } catch (e) {
      if (e && e.code) throw e;
      const msg = String(e?.message || e);
      throw { code: /quota|429|exhaust/i.test(msg) ? "rate_limited" : "error", message: /quota|429|exhaust/i.test(msg) ? "Günlük ücretsiz fiş okuma sınırı doldu, biraz sonra deneyin." : msg };
    }
  };

  const userCap = {
    id: async () => ready,
    me: async () => ({ id: await ready, name: await ready }),
    can: async () => true,
    isOwner: () => false, canEdit: () => true,
    profiles: async ids => Object.fromEntries(ids.map(id => [id, { name: OLD_IDS[id] || id }])),
  };
  const OLD_IDS = window.OLD_IDS || {};

  window.claude = {
    use: async name => {
      if (name === "db") { await ready; return fs; }
      if (name === "user") { await ready; return userCap; }
      if (name === "sample") { await ready; return sample; }
      return null;
    },
  };
})();
