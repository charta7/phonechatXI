// Takes the README and release screenshots from a running bridge fed with made-up chat.
// Run tools/screenshots.py, not this file: it starts the bridge and writes the fake lines first.
// Needs Node and Playwright (npm i playwright, then npx playwright install chromium).
const { chromium } = require("playwright");

const [url, out] = process.argv.slice(2);
const W = 390, H = 844;   // an iPhone 13/14 screen in CSS pixels

async function page(browser, prefs) {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.addInitScript(pr => {
    try { localStorage.setItem("pcxi", JSON.stringify(Object.assign({ savedAt: Date.now() + 1e9, tipSeen: true }, pr))); } catch (e) {}
  }, prefs);
  await p.goto(url);
  await p.waitForSelector("#tab-chat .top");
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(800);
  return p;
}
async function shot(p, name) { await p.waitForTimeout(400); await p.screenshot({ path: out + "/" + name + ".png" }); console.log("  " + name + ".png"); }
async function tab(p, t, cs) { await p.click('#tabbar [data-tab="' + t + '"]' + (cs ? '[data-cs="' + cs + '"]' : "")); }

(async () => {
  const b = await chromium.launch();
  const base = { watch: "Charta", quickFilters: true, bazaar: true };
  for (const skin of ["classic", "midnight", "onyx", "yuna"]) {
    const p = await page(b, Object.assign({}, base, { skin }));
    await shot(p, "skin-" + skin);
    if (skin === "classic") {   // the feature shots lead with Classic
      await shot(p, "chat");
      await tab(p, "tells"); await p.click('[data-thread="Wren"]'); await shot(p, "tell-thread");
      await p.click("#scr-thread [data-back]"); await tab(p, "cmds", "emote"); await shot(p, "emotes");
      await tab(p, "cmds", "server"); await shot(p, "server");
      await tab(p, "alerts"); await shot(p, "ventures");
      await p.locator('[data-go="settings"]:visible').first().click(); await shot(p, "settings");
    }
    await p.context().close();
  }
  await b.close();
})().catch(e => { console.error("ERR", e.message); process.exit(1); });
