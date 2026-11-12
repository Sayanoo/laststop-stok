import os, sys, json, pathlib
from playwright.sync_api import sync_playwright
R = pathlib.Path(__file__).parent; SH = R / "shots"; SH.mkdir(exist_ok=True)
URL = (R / "index.html").as_uri()
scheme = sys.argv[1] if len(sys.argv) > 1 else "dark"
res = []; errs = []
def ok(name, cond, info=""):
    res.append((name, bool(cond), info)); print(("PASS " if cond else "FAIL ") + name + (" · " + str(info) if info and not cond else ""))

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 384, "height": 820}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=scheme, locale="tr-TR")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(URL); pg.wait_for_selector(".row[data-item]", timeout=15000)
    db = lambda path: pg.evaluate("p=>window.__db.get(p)||null", path)
    coll = lambda c: pg.evaluate("c=>[...window.__db.entries()].filter(([k])=>k.startsWith(c+'/')).map(([k,v])=>({id:k.split('/')[1],...v}))", c)
    shot = lambda n: pg.screenshot(path=str(SH / f"{scheme}-{n}.png"))
    tab = lambda t: (pg.click(f'.tab[data-tab="{t}"]'), pg.wait_for_timeout(200))
    toast = lambda: pg.evaluate("()=>[...document.querySelectorAll('.toast')].map(t=>t.textContent).join(' | ')")

    # --- layout ---
    shot("01-stok")
    hh = pg.evaluate("()=>document.querySelector('header').getBoundingClientRect().height")
    ok("header kompakt (<150px)", hh < 150, hh)
    ok("yatay taşma yok", pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"), pg.evaluate("()=>[document.documentElement.scrollWidth,innerWidth]"))
    ok("h1 tek satır", pg.evaluate("()=>document.querySelector('h1').getBoundingClientRect().height<50"))
    ok("fab stokta görünür", pg.is_visible("#fab"))
    for t in ["cikis", "sayim", "siparis", "hareket"]:
        tab(t); ok(f"fab {t} sekmesinde gizli", not pg.is_visible("#fab"))
        ok(f"{t}: yatay taşma yok", pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth"))
    tab("stok")

    # --- ürün ekle ---
    pg.click("#fab"); pg.wait_for_selector("#f-name")
    pg.fill("#f-name", "Test Jalapeno"); pg.fill("#f-ko", "할라피뇨")
    pg.select_option("#f-sup", "Asel Food"); pg.select_option("#f-unit", "kutu")
    if pg.is_visible("#f-qty"): pg.fill("#f-qty", "5")
    if pg.is_visible("#f-min"): pg.fill("#f-min", "2")
    if pg.is_visible("#f-price"): pg.fill("#f-price", "12000")
    shot("02-yeni-urun"); pg.click('[data-act="create"]'); pg.wait_for_timeout(300)
    new = [x for x in coll("items") if x.get("name") == "Test Jalapeno"]
    ok("ürün eklendi", len(new) == 1, new); nid = new[0]["id"] if new else None
    ok("ürün alanları doğru", new and new[0].get("supplier") == "Asel Food" and new[0].get("unit") == "kutu" and new[0].get("qty") == 5, new and {k: new[0].get(k) for k in ["supplier", "unit", "qty", "min", "price"]})

    # --- arama ---
    pg.fill("#q", "jalap"); pg.wait_for_timeout(200)
    ok("arama buluyor", pg.locator(f'.row[data-item="{nid}"]').count() == 1)
    pg.fill("#q", "할라"); pg.wait_for_timeout(200)
    ok("korece arama", pg.locator(f'.row[data-item="{nid}"]').count() == 1)

    # --- mal girişi ---
    pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt")
    pg.click('[data-kind="in"]'); pg.fill("#amt", "3"); shot("03-mal-giris"); pg.click('[data-act="move"]'); pg.wait_for_timeout(300)
    ok("mal girişi 5+3=8", db("items/" + nid)["qty"] == 8, db("items/" + nid)["qty"])
    ok("hareket kaydı (in)", any(m.get("kind") == "in" and m.get("itemId") == nid and m.get("by") == "Testçi" for m in coll("moves")))
    # --- stoktan düş (sheet) ---
    pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt")
    pg.click('[data-kind="out"]'); pg.fill("#amt", "2"); pg.click('[data-act="move"]'); pg.wait_for_timeout(300)
    ok("kullanıldı 8-2=6", db("items/" + nid)["qty"] == 6, db("items/" + nid)["qty"])
    # --- zayi ---
    pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt")
    pg.click('[data-kind="waste"]'); pg.fill("#amt", "1"); pg.click('[data-act="move"]'); pg.wait_for_timeout(300)
    ok("zayi 6-1=5", db("items/" + nid)["qty"] == 5, db("items/" + nid)["qty"])
    ok("zayi hareketi", any(m.get("kind") == "waste" for m in coll("moves")))
    # --- fazla düşme engeli ---
    pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt")
    pg.click('[data-kind="out"]'); pg.fill("#amt", "99"); pg.click('[data-act="move"]'); pg.wait_for_timeout(300)
    q = db("items/" + nid)["qty"]; ok("stoktan fazlası düşmez (eksiye inmez)", q >= 0, q); print("   (99 düşülünce kalan:", q, ")")
    if pg.is_visible("#amt"): pg.click('[data-act="close"]') if pg.locator('[data-act="close"]').count() else pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    pg.fill("#q", ""); pg.wait_for_timeout(100)
    pg.evaluate("id=>window.__db.set('items/'+id,{...window.__db.get('items/'+id),qty:5})", nid)

    # --- ayarları düzenle ---
    pg.fill("#q", "jalap"); pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt")
    pg.click("details summary"); pg.fill("#f-min", "4"); pg.select_option("#f-sup", "Green Mart"); pg.click('[data-act="saveinfo"]'); pg.wait_for_timeout(300)
    d = db("items/" + nid); ok("ayar kaydı (min, tedarikçi)", d.get("min") == 4 and d.get("supplier") == "Green Mart", {k: d.get(k) for k in ["min", "supplier"]})
    pg.fill("#q", ""); pg.wait_for_timeout(100)

    # --- tedarikçi/birim listesi (Veriler) ---
    pg.click('[data-act="lists"]'); pg.wait_for_selector("#vadd")
    pg.click('[data-vsec="units"]'); pg.wait_for_timeout(150)
    pg.fill("#vadd", "tepsi"); pg.click('[data-vadd="units"]'); pg.wait_for_timeout(200)
    ok("birim eklendi", "tepsi" in (db("settings/lists") or {}).get("units", []))
    pg.click('[data-vsec="suppliers"]'); pg.wait_for_timeout(150)
    pg.fill("#vadd", "Hal Pazarı"); pg.click('[data-vadd="suppliers"]'); pg.wait_for_timeout(200)
    ok("tedarikçi eklendi", "Hal Pazarı" in (db("settings/lists") or {}).get("suppliers", []))
    shot("04-listeler")
    pg.click('[data-vsec="units"]'); pg.wait_for_timeout(150)
    ix = db("settings/lists")["units"].index("tepsi")
    pg.click(f'[data-vdel="{ix}"]'); pg.wait_for_timeout(150); pg.click(f'[data-vdel="{ix}"]'); pg.wait_for_timeout(200)
    ok("birim kaldırıldı", "tepsi" not in db("settings/lists").get("units", []))
    tab("stok")

    # --- çıkış sekmesi ---
    tab("cikis"); shot("05-cikis")
    pg.fill("#outq", "jalap"); pg.wait_for_timeout(200)
    before = db("items/" + nid)["qty"]
    pg.click(f'[data-out="{nid}"]'); pg.wait_for_timeout(300)
    ok("−1 düştü", db("items/" + nid)["qty"] == before - 1, (before, db("items/" + nid)["qty"]))
    ok("geri al butonu", pg.locator("#undoBtn").count() == 1)
    if pg.locator("#undoBtn").count(): pg.click("#undoBtn"); pg.wait_for_timeout(300)
    ok("geri al çalıştı", db("items/" + nid)["qty"] == before, db("items/" + nid)["qty"])
    sayilmamis = [x["id"] for x in coll("items") if x.get("qty") is None][0]
    pg.fill("#outq", ""); pg.wait_for_timeout(100)
    ok("sayılmamış üründe −1 kapalı", pg.locator(f'[data-out="{sayilmamis}"]').first.is_disabled() if pg.locator(f'[data-out="{sayilmamis}"]').count() else True)

    # --- sayım ---
    tab("sayim"); shot("06-sayim")
    loc = db("items/" + nid).get("location") or "Yeri belirtilmemiş"
    if pg.locator(f'[data-cloc="{loc}"]').count(): pg.click(f'[data-cloc="{loc}"]'); pg.wait_for_timeout(200)
    cur = db("items/" + nid)["qty"]
    pg.fill(f'[data-cnt="{nid}"]', str(cur - 2)); pg.locator(f'[data-cnt="{nid}"]').dispatch_event("change"); pg.wait_for_timeout(100)
    # unit for an uncounted item without unit
    others = [x for x in coll("items") if x.get("qty") is None and not x.get("unit") and (x.get("location") or "Yeri belirtilmemiş") == loc]
    oid = others[0]["id"] if others else None
    if oid:
        pg.select_option(f'[data-cunit="{oid}"]', "koli"); pg.fill(f'[data-cnt="{oid}"]', "3"); pg.locator(f'[data-cnt="{oid}"]').dispatch_event("change")
    shot("07-sayim-dolu")
    pg.click('[data-act="savecount"]'); pg.wait_for_timeout(500)
    ok("sayım stoğu güncelledi", db("items/" + nid)["qty"] == cur - 2, db("items/" + nid)["qty"])
    ok("sayım kişi+saat", db("items/" + nid).get("countedBy") == "Testçi" and db("items/" + nid).get("countedAt"))
    if oid: ok("sayımda birim kaydı", db("items/" + oid).get("unit") == "koli" and db("items/" + oid).get("qty") == 3, db("items/" + oid))
    cs = coll("counts"); ok("sayım geçmişi kaydı", len(cs) == 1 and cs[0].get("by") == "Testçi", cs)
    shot("08-sayim-rapor")
    rep = pg.inner_text("#sheetRoot"); ok("rapor kişi adı içeriyor", "Testçi" in rep, rep[:200])
    pg.click('[data-act="close"]'); pg.wait_for_timeout(200)
    ok("geçmiş sayımlar listesi", pg.locator("[data-countid]").count() >= 1)
    # ✓ Doğru
    pg.click(f'[data-cok="{nid}"]'); pg.wait_for_timeout(100); pg.click('[data-act="savecount"]'); pg.wait_for_timeout(400)
    ok("✓ Doğru ile sayım (değişmez)", db("items/" + nid)["qty"] == cur - 2)
    if pg.locator('[data-act="close"]').count(): pg.click('[data-act="close"]')

    # --- sipariş ---
    tab("siparis"); shot("09-siparis-bos")
    pg.fill("#ordq", "tortilla"); pg.wait_for_timeout(200)
    shot("10-siparis-ara")
    hits = pg.locator("[data-oadd]")
    ok("siparişte arama sonuç veriyor", hits.count() >= 1)
    first = hits.first.get_attribute("data-oadd"); hits.first.click(); pg.wait_for_timeout(300)
    ok("siparişe eklendi (db)", db("orderLines/" + first) is not None)
    pg.fill("#ordq", ""); pg.wait_for_timeout(100)
    pg.fill("#ordq", "jalap"); pg.wait_for_timeout(200); pg.click(f'[data-oadd="{nid}"]'); pg.wait_for_timeout(300)
    pg.fill("#ordq", ""); pg.wait_for_timeout(200)
    inp = pg.locator(f'[data-ord="{first}"]'); inp.fill("4"); inp.dispatch_event("change"); pg.wait_for_timeout(300)
    ok("sipariş miktarı kaydedildi", db("orderLines/" + first)["qty"] == 4, db("orderLines/" + first))
    shot("11-siparis-liste")
    ok("rozet sayısı", pg.inner_text("#ordBadge") != "0")
    # copy
    pg.evaluate("()=>{window.__copied=null;navigator.clipboard.writeText=t=>{window.__copied=t;return Promise.resolve()}}")
    sup_first = db("items/" + first).get("supplier") or "Tedarikçi belirtilmemiş"
    pg.click(f'[data-copy="{sup_first}"]'); pg.wait_for_timeout(200)
    cp = pg.evaluate("()=>window.__copied") or pg.evaluate("()=>document.querySelector('textarea.copy')?.value"); print("   COPY:", repr(cp), sup_first); ok("kopyala metni", cp and ": 4" in cp, cp)
    # remove
    pg.click(f'[data-odel="{nid}"]'); pg.wait_for_timeout(300)
    ok("siparişten çıkarıldı", db("orderLines/" + nid) is None)
    # received
    q0 = db("items/" + first).get("qty") or 0
    pg.click(f'[data-orecv="{sup_first}"]'); pg.wait_for_timeout(150)
    ok("geldi: onay ister", "Emin" in pg.inner_text(f'[data-orecv="{sup_first}"]'))
    pg.click(f'[data-orecv="{sup_first}"]'); pg.wait_for_timeout(500)
    ok("geldi → stoğa eklendi", (db("items/" + first).get("qty") or 0) == q0 + 4, (q0, db("items/" + first).get("qty")))
    ok("geldi → listeden düştü", db("orderLines/" + first) is None)
    shot("12-siparis-geldi")

    # --- fiş ---
    t0 = db("items/tortilla-12-durum").get("qty") or 0
    pg.set_input_files("#rcptIn", files=[{"name": "fis.jpg", "mimeType": "image/jpeg", "buffer": b"\xff\xd8\xff\xe0fake"}])
    pg.wait_for_timeout(2500); shot("13-fis")
    ok("fiş: eşleşen ürün stoğa eklendi", (db("items/tortilla-12-durum").get("qty") or 0) == t0 + 2, (t0, db("items/tortilla-12-durum").get("qty")))
    ok("fiş kaydı", len(coll("receipts")) == 1)
    if pg.locator('[data-act="close"]').count(): pg.click('[data-act="close"]'); pg.wait_for_timeout(200)

    # --- hareket ---
    tab("hareket"); shot("14-hareket")
    ok("hareket listesi dolu", pg.locator(".log-item").count() >= 5, pg.locator(".log-item").count())
    ok("hareketlerde kişi adı", "Testçi" in pg.inner_text("#main"))

    # --- sil ---
    tab("stok"); pg.fill("#q", "jalap"); pg.wait_for_timeout(200)
    pg.click(f'.row[data-item="{nid}"]'); pg.wait_for_selector("#amt"); pg.click("details summary")
    pg.click('[data-act="del"]'); pg.wait_for_timeout(150); pg.click('[data-act="del"]'); pg.wait_for_timeout(300)
    ok("ürün silindi", db("items/" + nid) is None)
    pg.fill("#q", ""); pg.wait_for_timeout(200)

    # --- barkod elle ---
    pg.click("#scanBtn"); pg.wait_for_timeout(200)
    if pg.locator("#bcman").count():
        pg.fill("#bcman", "8801234567890"); pg.click('[data-act="bcsearch"]'); pg.wait_for_timeout(200); shot("15-barkod")
        ok("barkod bulunamadı ekranı", pg.locator("#pickq").count() == 1 or "bulunamadı" in pg.inner_text("#sheetRoot").lower())
        if pg.locator("#pickq").count():
            pg.fill("#pickq", "sprite"); pg.wait_for_timeout(200)
            lk = pg.locator("[data-link]").first; lid = lk.get_attribute("data-link"); lk.click(); pg.wait_for_timeout(300)
            ok("barkod ürüne bağlandı", any(x.get("code") == "8801234567890" for x in db("items/" + lid).get("barcodes", [])))
            if pg.locator('[data-act="close"]').count(): pg.click('[data-act="close"]'); pg.wait_for_timeout(200)
            pg.click("#scanBtn"); pg.wait_for_timeout(200); pg.fill("#bcman", "8801234567890"); pg.click('[data-act="bcsearch"]'); pg.wait_for_timeout(300)
            ok("okutunca ürün açılıyor", pg.locator("#amt").count() == 1)
    shot("16-son")
    b.close()

fails = [r for r in res if not r[1]]
print(f"\n{len(res)-len(fails)}/{len(res)} geçti"); print("HATALAR:", errs[:10] if errs else "yok")
