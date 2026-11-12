import sys, pathlib
from playwright.sync_api import sync_playwright
R = pathlib.Path(__file__).parent; SH = R / "shots"; SH.mkdir(exist_ok=True)
URL = (R / "index.html").as_uri()
scheme = sys.argv[1] if len(sys.argv) > 1 else "dark"
res = []; errs = []
def ok(name, cond, info=""):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (" · " + str(info) if info and not cond else ""))

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 360, "height": 760}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme=scheme, locale="tr-TR")
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    try: cdp.send("Emulation.setSafeAreaInsetsOverride", {"insets": {"top": 40, "bottom": 24, "left": 0, "right": 0}})
    except Exception as e: print("inset n/a", e)
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(URL); pg.wait_for_selector(".row[data-item]", timeout=15000)
    db = lambda path: pg.evaluate("p=>window.__db.get(p)||null", path)
    items = lambda: pg.evaluate("()=>[...window.__db.entries()].filter(([k])=>k.startsWith('items/')).map(([k,v])=>({id:k.split('/')[1],...v}))")
    shot = lambda n: pg.screenshot(path=str(SH / f"{scheme}-veri-{n}.png"))
    W = lambda ms=250: pg.wait_for_timeout(ms)
    noov = lambda: pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth")
    under = lambda: pg.evaluate("()=>{const h=document.querySelector('header').getBoundingClientRect().bottom;const f=document.querySelector('#main').firstElementChild.getBoundingClientRect().top;return [h,f]}")

    ok("başlıkta Veriler düğmesi görünür", pg.is_visible("#dataBtn"))
    pg.click("#dataBtn"); W()
    hb, ct = under(); ok("Veriler sayfası başlığın altında", ct >= hb - 1, (hb, ct))
    ok("yatay taşma yok (ürünler)", noov())
    n_all = len(items()); ok("ürün listesi tam", pg.locator("[data-vedit]").count() == n_all, (pg.locator("[data-vedit]").count(), n_all))
    shot("01-urunler")

    # eksik bilgili filtre
    pg.click('[data-vmiss="1"]'); W()
    miss = [i for i in items() if not i.get("unit") or not i.get("location") or not i.get("category") or i.get("min") is None]
    ok("eksik bilgili filtresi", pg.locator("[data-vedit]").count() == len(miss), (pg.locator("[data-vedit]").count(), len(miss)))
    pg.click('[data-vmiss="0"]'); W()

    # arama
    pg.fill("#vq", "tortilla"); W()
    c = pg.locator("[data-vedit]").count(); ok("arama süzüyor", 0 < c < n_all, c)
    ok("arama sırasında odak korunuyor", pg.evaluate("()=>document.activeElement.id")=="vq")
    pg.fill("#vq", ""); W()

    # ürün düzenle
    first = pg.locator("[data-vedit]").first.get_attribute("data-vedit")
    pg.click(f'[data-vedit="{first}"]'); pg.wait_for_selector("#f-name")
    ok("düzenleme penceresinde stok butonları yok", pg.locator("#amt").count() == 0)
    qty0 = db("items/" + first).get("qty")
    pg.fill("#f-note", "veri testi notu"); pg.fill("#f-min", "3")
    shot("02-duzenle"); pg.click('[data-act="saveinfo"]'); W()
    d = db("items/" + first)
    ok("ürün bilgisi kaydedildi", d.get("note") == "veri testi notu" and d.get("min") == 3, d)
    ok("düzenleme stoğu değiştirmedi", d.get("qty") == qty0)

    # toplu düzenleme
    ids = [pg.locator("[data-vsel]").nth(i).get_attribute("data-vsel") for i in range(3)]
    for i in ids: pg.check(f'[data-vsel="{i}"]'); W(120)
    ok("toplu panel açıldı", pg.is_visible(".vbulk"))
    pg.select_option("#vbf", "location"); W(); pg.select_option("#vbv", "Kuru depo")
    shot("03-toplu"); pg.click('[data-act="vbulk"]'); W()
    ok("toplu yer ataması", all(db("items/" + i).get("location") == "Kuru depo" for i in ids), [db("items/" + i).get("location") for i in ids])
    ok("seçim temizlendi", not pg.is_visible(".vbulk"))

    # yerler: ekle, yeniden adlandır (ürünlere yansır), sırala, sil
    pg.click('[data-vsec="locations"]'); W()
    ok("yatay taşma yok (yerler)", noov())
    pg.fill("#vadd", "Arka depo"); pg.keyboard.press("Enter"); W()
    L = lambda: (db("settings/lists") or {}).get("locations", [])
    ok("yer eklendi (Enter)", "Arka depo" in L(), L())
    ok("eski listeler korunuyor", "Dondurucu" in L() and len((db("settings/lists") or {}).get("suppliers", [])) > 0)
    n_kuru = sum(1 for i in items() if i.get("location") == "Kuru depo")
    ix = L().index("Kuru depo")
    pg.click(f'[data-vren="{ix}"]'); W(); pg.fill("#vren", "Kuru Depo (raf)"); pg.click("[data-vrensave]"); W(400)
    ok("yer adı değişti", "Kuru Depo (raf)" in L() and "Kuru depo" not in L(), L())
    ok("ürünlere yansıdı", sum(1 for i in items() if i.get("location") == "Kuru Depo (raf)") == n_kuru and n_kuru > 0, n_kuru)
    last = len(L()) - 1
    pg.click(f'[data-vmv="-1"][data-vix="{last}"]'); W()
    ok("sıra değişti", L()[last - 1] == "Arka depo", L())
    shot("04-yerler")
    # kullanılan yeri sil -> ürünler yersiz kalır, sayımda görünür
    tgt = "Kuru Depo (raf)"; ix = L().index(tgt)
    pg.click(f'[data-vdel="{ix}"]'); W()
    ok("silme onayı istiyor", pg.is_visible(".vwarn") and tgt in L())
    shot("05-sil-onay")
    pg.click(f'[data-vdel="{ix}"]'); W(400)
    ok("yer silindi", tgt not in L())
    ok("ürünlerden yer kaldırıldı", not any(i.get("location") == tgt for i in items()) and sum(1 for i in items() if not i.get("location")) >= n_kuru)

    # kategoriler + birim yeniden adlandırma
    pg.click('[data-vsec="categories"]'); W()
    pg.fill("#vadd", "Tatlı"); pg.click('[data-vadd="categories"]'); W()
    ok("kategori eklendi", "Tatlı" in (db("settings/lists") or {}).get("categories", []))
    pg.fill("#vadd", "tatlı"); pg.click('[data-vadd="categories"]'); W()
    ok("aynısı ikinci kez eklenmez", (db("settings/lists") or {}).get("categories", []).count("Tatlı") == 1 and "tatlı" not in db("settings/lists")["categories"])
    pg.click('[data-vsec="items"]'); W()
    for i in ids: pg.check(f'[data-vsel="{i}"]'); W(120)
    pg.select_option("#vbf", "unit"); W(); pg.select_option("#vbv", "paket"); pg.click('[data-act="vbulk"]'); W()
    ok("toplu birim ataması", all(db("items/" + i).get("unit") == "paket" for i in ids))
    pg.click('[data-vsec="units"]'); W()
    U = lambda: (db("settings/lists") or {}).get("units", [])
    n_pk = sum(1 for i in items() if i.get("unit") == "paket")
    pg.click(f'[data-vren="{U().index("paket") if U() else 0}"]'); W(); pg.fill("#vren", "pk"); pg.keyboard.press("Enter"); W(400)
    ok("birim adı değişti + ürünler güncellendi", "pk" in U() and sum(1 for i in items() if i.get("unit") == "pk") == n_pk and n_pk > 0, n_pk)
    pg.click('[data-vsec="suppliers"]'); W()
    ok("tedarikçiler bölümü", pg.locator("[data-vdel]").count() >= 5)

    # diğer ekranlara yansıma
    pg.click('[data-tab="stok"]'); W()
    pg.click('[data-group="loc"]'); W()
    chips = pg.evaluate("()=>[...document.querySelectorAll('.chip[data-cat]')].map(c=>c.textContent)")
    ok("stokta yeni yer chip'i", "Arka depo" in chips and "Kuru Depo (raf)" not in chips, chips)
    pg.click('.tab[data-tab="sayim"]'); W()
    cl = pg.evaluate("()=>[...document.querySelectorAll('[data-cloc]')].map(c=>c.dataset.cloc)")
    ok("sayımda yeni yer + yeri belirtilmemiş", "Arka depo" in cl and "Yeri belirtilmemiş" in cl, cl)
    pg.click('.tab[data-tab="stok"]'); W()
    pg.click(".row[data-item]"); pg.wait_for_selector("#amt")
    pg.click("#sheetRoot details summary"); W()
    opts = pg.evaluate("()=>[...document.querySelectorAll('#f-loc option')].map(o=>o.textContent)")
    ok("ürün formunda yeni yer listesi", "Arka depo" in opts and "Kuru Depo (raf)" not in opts, opts)
    pg.keyboard.press("Escape"); W()
    pg.click('[data-act="lists"]'); W()
    ok("'Listeleri düzenle' Veriler'i açar", pg.is_visible('[data-vsec="locations"][aria-pressed="true"]'))

    # yeni ürün + silme Veriler'den
    pg.click('[data-vsec="items"]'); W(); pg.click('[data-act="vnew"]'); pg.wait_for_selector("#f-name")
    pg.fill("#f-name", "Veri Test Ürünü"); pg.select_option("#f-loc", "Arka depo"); pg.select_option("#f-cat", "Tatlı"); pg.click('[data-act="create"]'); W()
    nw = [i for i in items() if i.get("name") == "Veri Test Ürünü"]
    ok("Veriler'den ürün eklendi", len(nw) == 1 and nw[0].get("location") == "Arka depo" and nw[0].get("category") == "Tatlı", nw)
    pg.click(f'[data-vedit="{nw[0]["id"]}"]'); pg.wait_for_selector("#f-name")
    pg.click('[data-act="del"]'); W(); pg.click('[data-act="del"]'); W()
    ok("Veriler'den ürün silindi", db("items/" + nw[0]["id"]) is None)
    ok("hiç hata yok", not errs, errs)
    pg.evaluate("scrollTo(0,0)"); W()
    hb, ct = under(); ok("son durumda da başlık altında", ct >= hb - 1, (hb, ct))
    shot("06-son")
    b.close()
print(f"\n{sum(res)}/{len(res)} geçti")
