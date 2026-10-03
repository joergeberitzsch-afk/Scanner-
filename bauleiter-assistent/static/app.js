/* Bauleiter-Assistent – Oberfläche (ohne Build-Schritt, ohne externe Abhängigkeiten außer pdf.js) */
"use strict";

const inhalt = document.getElementById("inhalt");
const zustand = { einstellungen: {}, info: {}, ungespeichert: false, maengelFilter: { status: "nicht_erledigt" } };

const STATUS = { offen: "offen", in_arbeit: "in Arbeit", erledigt: "erledigt" };
const WETTER = ["sonnig", "heiter", "bewölkt", "bedeckt", "Nebel", "Regen", "Schauer", "Gewitter", "Schnee", "Frost", "Sturm"];
const WOCHENTAGE = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];

if (window.pdfjsLib) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.js";
}

/* ---------------------------------------------------------------- Hilfen */

function esc(wert) {
  return String(wert ?? "").replace(/[&<>"']/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[z]));
}

function heute() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function datumDE(iso) {
  if (!iso) return "";
  const [j, m, t] = iso.split("-");
  return `${t}.${m}.${j}`;
}

function wochentag(iso) {
  const [j, m, t] = iso.split("-").map(Number);
  return WOCHENTAGE[new Date(j, m - 1, t).getDay()];
}

function groesse(bytes) {
  if (bytes > 1e6) return (bytes / 1e6).toFixed(1).replace(".", ",") + " MB";
  return Math.max(1, Math.round(bytes / 1e3)) + " kB";
}

async function api(methode, url, daten) {
  const optionen = { method: methode, headers: {} };
  if (daten !== undefined) {
    optionen.headers["Content-Type"] = "application/json";
    optionen.body = JSON.stringify(daten);
  }
  let antwort;
  try {
    antwort = await fetch(url, optionen);
  } catch (e) {
    throw new Error("Keine Verbindung zum Server – läuft der Bauleiter-Assistent noch?");
  }
  const text = await antwort.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch (e) { /* kein JSON */ }
  if (!antwort.ok) throw new Error((json && json.fehler) || `Fehler ${antwort.status}`);
  return json;
}

async function hochladen(url, datei, parameter = {}) {
  const maxMb = zustand.info.max_upload_mb;
  if (maxMb && datei.size > maxMb * 1e6) throw new Error(`${datei.name}: Datei zu groß (max. ${maxMb} MB)`);
  const q = new URLSearchParams({ dateiname: datei.name, ...parameter });
  for (const [k, v] of [...q.entries()]) if (v === "" || v == null) q.delete(k);
  let antwort;
  try {
    antwort = await fetch(`${url}?${q}`, { method: "POST", body: datei, headers: { "Content-Type": datei.type || "application/octet-stream" } });
  } catch (e) {
    throw new Error("Keine Verbindung zum Server");
  }
  const json = await antwort.json().catch(() => null);
  if (!antwort.ok) throw new Error(`${datei.name}: ${(json && json.fehler) || "Fehler " + antwort.status}`);
  return json;
}

async function mehrereHochladen(url, dateien, parameter, statusEl) {
  const ergebnisse = [];
  const fehler = [];
  let i = 0;
  for (const datei of dateien) {
    i += 1;
    if (statusEl) statusEl.textContent = `Lade hoch: ${i} von ${dateien.length} (${datei.name}) …`;
    try {
      ergebnisse.push(await hochladen(url, datei, parameter));
    } catch (e) {
      fehler.push(e.message);
    }
  }
  if (statusEl) statusEl.textContent = "";
  if (fehler.length) meldung(fehler.join("\n"), "fehler");
  else if (ergebnisse.length) meldung(`${ergebnisse.length} Datei(en) hochgeladen`);
  return ergebnisse;
}

let meldungTimer;
function meldung(text, art = "ok") {
  const el = document.getElementById("meldung");
  el.textContent = text;
  el.className = "meldung " + art;
  el.hidden = false;
  clearTimeout(meldungTimer);
  meldungTimer = setTimeout(() => { el.hidden = true; }, art === "fehler" ? 9000 : 3000);
}

function $(sel, wurzel = document) { return wurzel.querySelector(sel); }
function $$(sel, wurzel = document) { return [...wurzel.querySelectorAll(sel)]; }

function optionen(liste, gewaehlt, leerText) {
  const opts = leerText !== undefined ? [`<option value="">${esc(leerText)}</option>`] : [];
  for (const [wert, text] of liste) {
    opts.push(`<option value="${esc(wert)}"${String(wert) === String(gewaehlt ?? "") ? " selected" : ""}>${esc(text)}</option>`);
  }
  return opts.join("");
}

function gewerkeListe() {
  return (zustand.einstellungen.gewerke || "").split(",").map((g) => g.trim()).filter(Boolean);
}

function datalistFuellen(id, werte) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = [...new Set(werte.filter(Boolean))].sort((a, b) => a.localeCompare(b, "de")).map((w) => `<option value="${esc(w)}">`).join("");
}

function fehlerAnzeigen(e) {
  console.error(e);
  meldung(e.message || String(e), "fehler");
}

/* ---------------------------------------------------------------- Router */

const ansichten = {
  uebersicht: ansichtUebersicht,
  plaene: ansichtPlaene,
  fotos: ansichtFotos,
  maengel: ansichtMaengel,
  tagebuch: ansichtTagebuch,
  einstellungen: ansichtEinstellungen,
};

let letzterHash = location.hash;

function routeLesen() {
  const roh = location.hash.replace(/^#\/?/, "");
  const [pfad, query = ""] = roh.split("?");
  const teile = pfad.split("/").filter(Boolean);
  return { bereich: teile[0] || "uebersicht", param: teile[1], query: new URLSearchParams(query) };
}

async function navigieren() {
  if (zustand.ungespeichert && location.hash !== letzterHash) {
    if (!confirm("Es gibt ungespeicherte Änderungen. Trotzdem verlassen?")) {
      history.replaceState(null, "", letzterHash || "#/uebersicht");
      return;
    }
  }
  zustand.ungespeichert = false;
  letzterHash = location.hash;
  const { bereich, param, query } = routeLesen();
  const ansicht = ansichten[bereich] || ansichtUebersicht;
  $$("#navigation a").forEach((a) => a.classList.toggle("aktiv", a.dataset.bereich === bereich));
  if (ansichtAufraeumen) { ansichtAufraeumen(); ansichtAufraeumen = null; }
  try {
    await ansicht(param, query);
  } catch (e) {
    inhalt.innerHTML = `<div class="karte fehlerkarte"><h2>Fehler</h2><p>${esc(e.message)}</p></div>`;
    console.error(e);
  }
}

let ansichtAufraeumen = null;

window.addEventListener("hashchange", navigieren);
window.addEventListener("beforeunload", (e) => {
  if (zustand.ungespeichert) { e.preventDefault(); e.returnValue = ""; }
});

async function start() {
  try {
    const [info, einstellungen] = await Promise.all([api("GET", "/api/info"), api("GET", "/api/einstellungen")]);
    zustand.info = info;
    einstellungenUebernehmen(einstellungen);
    $("#version-badge").textContent = /test/i.test(info.version) ? `Testversion ${info.version.replace(/-test$/i, "")}` : `Version ${info.version}`;
  } catch (e) {
    fehlerAnzeigen(e);
  }
  navigieren();
}

function einstellungenUebernehmen(werte) {
  zustand.einstellungen = werte;
  const name = [werte.projekt_nr, werte.projekt_name].filter(Boolean).join(" · ");
  $("#projekt-name").textContent = name;
  document.title = name ? `${name} – Bauleiter-Assistent` : "Bauleiter-Assistent";
  datalistFuellen("gewerke", gewerkeListe());
}

/* ---------------------------------------------------------------- Übersicht */

async function ansichtUebersicht() {
  const d = await api("GET", "/api/uebersicht");
  const projektFehlt = !zustand.einstellungen.projekt_name;
  inhalt.innerHTML = `
    ${projektFehlt ? `<div class="karte hinweis">Noch kein Projekt eingetragen. <a href="#/einstellungen">Jetzt in den Einstellungen erfassen</a> – die Angaben erscheinen im Kopf von Mängelliste und Bautagebuch.</div>` : ""}
    <div class="kacheln">
      <a class="kachel" href="#/plaene"><span class="zahl">${d.plaene}</span><span>Pläne</span></a>
      <a class="kachel" href="#/fotos"><span class="zahl">${d.fotos}</span><span>Fotos</span></a>
      <a class="kachel ${d.maengel_ueberfaellig ? "warnung" : ""}" href="#/maengel"><span class="zahl">${d.maengel_offen}</span>
        <span>offene Mängel${d.maengel_ueberfaellig ? `, <strong>${d.maengel_ueberfaellig} überfällig</strong>` : ""}</span></a>
      <a class="kachel ${d.tagebuch_heute ? "" : "offen"}" href="#/tagebuch/${d.heute}"><span class="zahl">${d.tagebuch_eintraege}</span>
        <span>Bautagebuch – ${d.tagebuch_heute ? "heute erfasst" : "heute noch offen"}</span></a>
    </div>
    <div class="spalten">
      <section class="karte">
        <h2>Fällige Mängel <small>(überfällig oder in den nächsten 7 Tagen)</small></h2>
        ${d.faellige_maengel.length ? `<table class="tabelle"><thead><tr><th>Nr.</th><th>Mangel</th><th>Gewerk / Firma</th><th>Frist</th></tr></thead><tbody>
          ${d.faellige_maengel.map((m) => `<tr class="klickbar" data-mangel="${m.id}"><td>${m.nr}</td><td>${esc(m.titel)}</td>
            <td>${esc(m.gewerk)}<br><small>${esc(m.firma)}</small></td><td class="${m.ueberfaellig ? "ueberfaellig" : ""}">${datumDE(m.frist)}</td></tr>`).join("")}
          </tbody></table>` : `<p class="leer">Keine fälligen Mängel.</p>`}
      </section>
      <section class="karte">
        <h2>Neueste Fotos</h2>
        ${d.neueste_fotos.length ? `<div class="mini-raster">${d.neueste_fotos.map((f) => `<a href="#/fotos?datum=${f.datum}" title="${esc(datumDE(f.datum) + " " + f.notiz)}"><img loading="lazy" src="/datei/foto/${f.id}" alt=""></a>`).join("")}</div>`
          : `<p class="leer">Noch keine Fotos. <a href="#/fotos">Fotos hochladen</a></p>`}
      </section>
    </div>`;
  $$("[data-mangel]", inhalt).forEach((tr) => tr.addEventListener("click", async () => {
    mangelDialog(await api("GET", `/api/maengel/${tr.dataset.mangel}`), ansichtUebersicht);
  }));
}

/* ---------------------------------------------------------------- Pläne */

async function ansichtPlaene(param, query) {
  if (param) return ansichtPlan(Number(param), query);
  const plaene = await api("GET", "/api/plaene");
  inhalt.innerHTML = `
    <div class="werkzeugleiste">
      <h1>Pläne</h1>
      <label class="knopf primaer">Pläne hochladen<input type="file" id="plan-upload" accept=".pdf,.png,.jpg,.jpeg" multiple hidden></label>
      <span id="upload-status" class="status"></span>
    </div>
    <p class="hilfe">PDF, PNG oder JPG. Das Geschoss wird aus dem Dateinamen erkannt (z. B. <code>A_GR_OG5_ST3_NB.pdf</code> → OG5) und kann geändert werden.</p>
    ${plaene.length ? `<table class="tabelle">
      <thead><tr><th style="width:7rem">Geschoss</th><th>Bezeichnung</th><th>Datei</th><th>Markierungen</th><th></th></tr></thead>
      <tbody>${plaene.map((p) => `<tr data-id="${p.id}">
        <td><input class="eingabe-geschoss" list="geschosse" value="${esc(p.geschoss)}" data-feld="geschoss" aria-label="Geschoss"></td>
        <td><input value="${esc(p.bezeichnung)}" data-feld="bezeichnung" aria-label="Bezeichnung"></td>
        <td><small>${esc(p.dateiname)}<br>${groesse(p.groesse)}</small></td>
        <td><small>${p.anzahl_fotos} Fotos, ${p.anzahl_maengel} Mängel</small></td>
        <td class="aktionen"><a class="knopf primaer" href="#/plaene/${p.id}">Öffnen</a>
          <a class="knopf" href="/datei/plan/${p.id}" target="_blank" rel="noopener">Original</a>
          <button class="knopf gefahr" data-loeschen>Löschen</button></td></tr>`).join("")}</tbody></table>`
      : `<div class="karte leer">Noch keine Pläne vorhanden.</div>`}`;

  $("#plan-upload").addEventListener("change", async (ev) => {
    await mehrereHochladen("/api/plaene", [...ev.target.files], {}, $("#upload-status"));
    ansichtPlaene();
  });
  $$("tr[data-id] input", inhalt).forEach((inp) => inp.addEventListener("change", async () => {
    try {
      await api("PATCH", `/api/plaene/${inp.closest("tr").dataset.id}`, { [inp.dataset.feld]: inp.value });
      meldung("Gespeichert");
      if (inp.dataset.feld === "geschoss") ansichtPlaene();
    } catch (e) { fehlerAnzeigen(e); }
  }));
  $$("[data-loeschen]", inhalt).forEach((b) => b.addEventListener("click", async () => {
    const tr = b.closest("tr");
    if (!confirm("Plan löschen? Markierungen von Fotos und Mängeln auf diesem Plan werden entfernt.")) return;
    try { await api("DELETE", `/api/plaene/${tr.dataset.id}`); ansichtPlaene(); } catch (e) { fehlerAnzeigen(e); }
  }));
}

async function ansichtPlan(planId, query) {
  const [plan, alleFotos, alleMaengel] = await Promise.all([
    api("GET", "/api/plaene").then((l) => l.find((p) => p.id === planId)),
    api("GET", "/api/fotos"),
    api("GET", "/api/maengel"),
  ]);
  if (!plan) throw new Error("Plan nicht gefunden");
  const istPdf = /\.pdf$/i.test(plan.datei);
  const fotoNamen = (f) => `${datumDE(f.datum)} – ${f.notiz || f.dateiname}`;

  inhalt.innerHTML = `
    <div class="werkzeugleiste">
      <a class="knopf" href="#/plaene">← Pläne</a>
      <h1>${esc(plan.geschoss ? plan.geschoss + " · " : "")}${esc(plan.bezeichnung)}</h1>
      <span class="abstand"></span>
      <button class="knopf" data-zoom="-1" title="Verkleinern">−</button>
      <button class="knopf" data-zoom="0" title="Auf Breite einpassen">Einpassen</button>
      <button class="knopf" data-zoom="1" title="Vergrößern">+</button>
      <a class="knopf" href="/datei/plan/${plan.id}" target="_blank" rel="noopener">Original öffnen</a>
    </div>
    <div class="plan-layout">
      <aside class="plan-seite karte">
        <h2>Markierung setzen</h2>
        <select id="ziel">
          <option value="">– auswählen –</option>
          <option value="neu-mangel">＋ Neuer Mangel an dieser Stelle</option>
          <optgroup label="Mängel">${alleMaengel.map((m) => `<option value="mangel-${m.id}">M${m.nr} ${esc(m.titel)}${m.plan_id === plan.id && m.x != null ? " ✓" : ""}</option>`).join("")}</optgroup>
          <optgroup label="Fotos">${alleFotos.map((f) => `<option value="foto-${f.id}">${esc(fotoNamen(f))}${f.plan_id === plan.id && f.x != null ? " ✓" : ""}</option>`).join("")}</optgroup>
        </select>
        <p class="hilfe" id="ziel-hilfe">Eintrag wählen, dann auf die Stelle im Plan klicken. ✓ = auf diesem Plan bereits markiert (wird verschoben).</p>
        <div class="legende"><span class="punkt foto"></span> Foto <span class="punkt mangel"></span> Mangel offen <span class="punkt mangel erledigt"></span> erledigt</div>
        <h2>Auf diesem Plan</h2>
        <div id="markierungsliste" class="markierungsliste"></div>
      </aside>
      <div class="plan-rahmen" id="plan-rahmen">
        <div class="plan-buehne" id="plan-buehne">
          <div class="plan-ebene" id="plan-ebene"></div>
          <div class="plan-markierungen" id="plan-markierungen"></div>
          <div class="plan-popup" id="plan-popup" hidden></div>
        </div>
        <p class="leer" id="plan-laden">Plan wird geladen …</p>
      </div>
    </div>`;

  const rahmen = $("#plan-rahmen");
  const buehne = $("#plan-buehne");
  const ebene = $("#plan-ebene");
  const markEl = $("#plan-markierungen");
  const popup = $("#plan-popup");
  const zielSelect = $("#ziel");
  let zoom = 1;
  let seitenVerhaeltnis = 1.414; // Höhe / Breite
  let renderer = null;
  let markierbar = true;

  if (query.get("markiere")) zielSelect.value = query.get("markiere");
  const zielAktualisieren = () => buehne.classList.toggle("markiermodus", !!zielSelect.value && markierbar);
  zielSelect.addEventListener("change", zielAktualisieren);

  // ---- Darstellung
  if (istPdf && window.pdfjsLib) {
    try {
      const pdf = await pdfjsLib.getDocument({ url: `/datei/plan/${plan.id}` }).promise;
      const seite = await pdf.getPage(1);
      const vp1 = seite.getViewport({ scale: 1 });
      seitenVerhaeltnis = vp1.height / vp1.width;
      const canvas = document.createElement("canvas");
      ebene.appendChild(canvas);
      let aufgabe = null;
      renderer = async (breite) => {
        if (aufgabe) { aufgabe.cancel(); }
        const dpr = window.devicePixelRatio || 1;
        let skala = (breite * dpr) / vp1.width;
        const maxPixel = 16e6; // Grenze für Canvas-Größe in Browsern
        if (vp1.width * vp1.height * skala * skala > maxPixel) skala = Math.sqrt(maxPixel / (vp1.width * vp1.height));
        const vp = seite.getViewport({ scale: skala });
        const neu = document.createElement("canvas");
        neu.width = Math.floor(vp.width);
        neu.height = Math.floor(vp.height);
        aufgabe = seite.render({ canvasContext: neu.getContext("2d"), viewport: vp });
        try {
          await aufgabe.promise;
          ebene.replaceChildren(neu);
        } catch (e) {
          if (e && e.name !== "RenderingCancelledException") throw e;
        }
      };
      if (pdf.numPages > 1) $("#ziel-hilfe").insertAdjacentHTML("afterend", `<p class="hilfe">Hinweis: Der Plan hat ${pdf.numPages} Seiten – angezeigt und markiert wird Seite 1.</p>`);
    } catch (e) {
      console.error(e);
      renderer = null;
    }
  } else if (!istPdf) {
    const img = new Image();
    img.src = `/datei/plan/${plan.id}`;
    img.alt = plan.bezeichnung;
    await new Promise((ok) => { img.onload = ok; img.onerror = ok; });
    seitenVerhaeltnis = img.naturalWidth ? img.naturalHeight / img.naturalWidth : 1;
    ebene.appendChild(img);
    renderer = async () => {};
  }

  if (!renderer) {
    // Rückfall: PDF im Browser-Viewer, Markieren nicht möglich
    markierbar = false;
    rahmen.innerHTML = `<div class="karte hinweis">Die Planvorschau konnte nicht geladen werden. Markierungen sind daher nicht möglich.
      <a href="/datei/plan/${plan.id}" target="_blank" rel="noopener">Plan im Browser öffnen</a></div>
      <iframe class="plan-iframe" src="/datei/plan/${plan.id}"></iframe>`;
    zielSelect.disabled = true;
  }

  let renderTimer;
  const layout = () => {
    if (!markierbar) return;
    const breite = Math.max(200, (rahmen.clientWidth - 2) * zoom);
    buehne.style.width = `${breite}px`;
    buehne.style.height = `${breite * seitenVerhaeltnis}px`;
    clearTimeout(renderTimer);
    renderTimer = setTimeout(() => renderer(breite).catch(fehlerAnzeigen), 120);
  };

  if (markierbar) {
    $("#plan-laden").remove();
    layout();
    const beobachter = new ResizeObserver(() => { if (zoom === 1) layout(); });
    beobachter.observe(rahmen);
    ansichtAufraeumen = () => beobachter.disconnect();
  }

  $$("[data-zoom]").forEach((b) => b.addEventListener("click", () => {
    const schritt = Number(b.dataset.zoom);
    zoom = schritt === 0 ? 1 : Math.min(8, Math.max(0.5, zoom * (schritt > 0 ? 1.5 : 1 / 1.5)));
    layout();
  }));

  // ---- Markierungen
  async function markierungenLaden() {
    const m = await api("GET", `/api/plaene/${plan.id}/markierungen`);
    markEl.innerHTML = [
      ...m.maengel.map((x) => `<button class="marke mangel ${x.status === "erledigt" ? "erledigt" : ""}" style="left:${x.x * 100}%;top:${x.y * 100}%"
        data-art="mangel" data-id="${x.id}" title="M${x.nr} ${esc(x.titel)}">M${x.nr}</button>`),
      ...m.fotos.map((x) => `<button class="marke foto" style="left:${x.x * 100}%;top:${x.y * 100}%"
        data-art="foto" data-id="${x.id}" title="${esc(fotoNamen(x))}">F</button>`),
    ].join("");
    $("#markierungsliste").innerHTML = (m.maengel.length + m.fotos.length) ? [
      ...m.maengel.map((x) => `<button class="liste-eintrag" data-art="mangel" data-id="${x.id}"><span class="punkt mangel ${x.status === "erledigt" ? "erledigt" : ""}"></span>M${x.nr} ${esc(x.titel)}</button>`),
      ...m.fotos.map((x) => `<button class="liste-eintrag" data-art="foto" data-id="${x.id}"><span class="punkt foto"></span>${esc(fotoNamen(x))}</button>`),
    ].join("") : `<p class="leer">Noch keine Markierungen.</p>`;
    $$("[data-art]", markEl).concat($$("#markierungsliste [data-art]")).forEach((b) => b.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const daten = (b.dataset.art === "mangel" ? m.maengel : m.fotos).find((x) => x.id === Number(b.dataset.id));
      popupZeigen(b.dataset.art, daten);
    }));
  }

  function popupZeigen(art, d) {
    popup.hidden = false;
    popup.style.left = `${Math.min(d.x * 100, 70)}%`;
    popup.style.top = `${d.y * 100}%`;
    popup.innerHTML = art === "foto"
      ? `<img src="/datei/foto/${d.id}" alt=""><div><strong>${datumDE(d.datum)}</strong> ${esc(d.notiz)}</div>`
      : `<div><strong>M${d.nr}</strong> ${esc(d.titel)}</div><div><small>${esc(STATUS[d.status] || d.status)}${d.frist ? " · Frist " + datumDE(d.frist) : ""}${d.gewerk ? " · " + esc(d.gewerk) : ""}</small></div>`;
    popup.insertAdjacentHTML("beforeend", `<div class="popup-knoepfe">
        ${art === "mangel" ? `<button class="knopf" data-p="bearbeiten">Bearbeiten</button>` : `<a class="knopf" href="/datei/foto/${d.id}" target="_blank" rel="noopener">Groß</a>`}
        <button class="knopf" data-p="verschieben">Verschieben</button>
        <button class="knopf gefahr" data-p="entfernen">Entfernen</button>
        <button class="knopf" data-p="zu">×</button></div>`);
    popup.querySelector("[data-p=zu]").onclick = (ev) => { ev.stopPropagation(); popup.hidden = true; };
    popup.querySelector("[data-p=verschieben]").onclick = (ev) => {
      ev.stopPropagation(); popup.hidden = true; zielSelect.value = `${art}-${d.id}`; zielAktualisieren();
      meldung("Jetzt die neue Position im Plan anklicken");
    };
    popup.querySelector("[data-p=entfernen]").onclick = async (ev) => {
      ev.stopPropagation();
      try {
        await api("PATCH", `/api/${art === "foto" ? "fotos" : "maengel"}/${d.id}`, { plan_id: null });
        popup.hidden = true; markierungenLaden();
      } catch (e) { fehlerAnzeigen(e); }
    };
    const bearbeiten = popup.querySelector("[data-p=bearbeiten]");
    if (bearbeiten) bearbeiten.onclick = async (ev) => {
      ev.stopPropagation(); popup.hidden = true;
      mangelDialog(await api("GET", `/api/maengel/${d.id}`), markierungenLaden);
    };
    popup.onclick = (ev) => ev.stopPropagation();
  }

  buehne.addEventListener("click", async (ev) => {
    if (!popup.hidden) { popup.hidden = true; return; }
    const ziel = zielSelect.value;
    if (!ziel || !markierbar) return;
    const r = buehne.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width));
    const y = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height));
    const pos = { plan_id: plan.id, x: Math.round(x * 10000) / 10000, y: Math.round(y * 10000) / 10000 };
    try {
      if (ziel === "neu-mangel") {
        mangelDialog({ geschoss: plan.geschoss, status: "offen", ...pos }, () => { markierungenLaden(); });
      } else {
        const [art, id] = ziel.split("-");
        await api("PATCH", `/api/${art === "foto" ? "fotos" : "maengel"}/${id}`, pos);
        const opt = zielSelect.selectedOptions[0];
        if (opt && !opt.textContent.endsWith(" ✓")) opt.textContent += " ✓";
        meldung("Markierung gesetzt");
        await markierungenLaden();
      }
      zielSelect.value = "";
      zielAktualisieren();
    } catch (e) { fehlerAnzeigen(e); }
  });

  zielAktualisieren();
  await markierungenLaden();
}

/* ---------------------------------------------------------------- Fotos */

async function ansichtFotos(param, query) {
  const filter = { von: query.get("von") || "", bis: query.get("bis") || "", datum: query.get("datum") || "", geschoss: query.get("geschoss") || "" };
  const [fotos, plaene, maengel] = await Promise.all([
    api("GET", "/api/fotos?" + new URLSearchParams(Object.entries(filter).filter(([, v]) => v))),
    api("GET", "/api/plaene"),
    api("GET", "/api/maengel"),
  ]);
  const planName = (id) => { const p = plaene.find((x) => x.id === id); return p ? `${p.geschoss ? p.geschoss + " · " : ""}${p.bezeichnung}` : ""; };
  const planOptionen = plaene.map((p) => [p.id, planName(p.id)]);
  // Vorauswahl: markierter Plan, sonst Plan mit gleichem Geschoss, sonst der einzige Plan
  const vorschlagPlan = (f) => f.plan_id || (plaene.find((p) => p.geschoss && p.geschoss === f.geschoss) || {}).id || (plaene.length === 1 ? plaene[0].id : "");
  const mangelOptionen = maengel.map((m) => [m.id, `M${m.nr} ${m.titel}`]);

  const gruppen = new Map();
  for (const f of fotos) { if (!gruppen.has(f.datum)) gruppen.set(f.datum, []); gruppen.get(f.datum).push(f); }

  inhalt.innerHTML = `
    <div class="werkzeugleiste">
      <h1>Fotos</h1>
      <label class="knopf primaer">Fotos hochladen<input type="file" id="foto-upload" accept="image/jpeg,image/png,image/webp,image/gif" multiple hidden></label>
      <label class="feld-inline">Datum <input type="date" id="upload-datum" title="leer = aus Dateiname, sonst heute"></label>
      <label class="feld-inline">Geschoss <input id="upload-geschoss" list="geschosse" size="5"></label>
      <span id="upload-status" class="status"></span>
    </div>
    <p class="hilfe">Ohne Datumsangabe wird das Aufnahmedatum aus dem Dateinamen gelesen (z. B. <code>20260912_090810.jpg</code>), sonst das heutige Datum verwendet.</p>
    <form class="filterleiste" id="foto-filter">
      <label>Tag <input type="date" name="datum" value="${esc(filter.datum)}"></label>
      <label>von <input type="date" name="von" value="${esc(filter.von)}"></label>
      <label>bis <input type="date" name="bis" value="${esc(filter.bis)}"></label>
      <label>Geschoss <input name="geschoss" list="geschosse" size="5" value="${esc(filter.geschoss)}"></label>
      <button class="knopf">Filtern</button>
      <a class="knopf" href="#/fotos">Zurücksetzen</a>
      <span class="status">${fotos.length} Fotos</span>
    </form>
    ${fotos.length ? [...gruppen].map(([datum, liste]) => `
      <h2 class="tag-kopf">${wochentag(datum)}, ${datumDE(datum)} <small>${liste.length} Fotos</small>
        <a class="knopf klein" href="#/tagebuch/${datum}">Bautagebuch</a></h2>
      <div class="foto-raster">${liste.map((f) => `
        <article class="foto-karte" data-id="${f.id}">
          <a href="/datei/foto/${f.id}" target="_blank" rel="noopener"><img loading="lazy" src="/datei/foto/${f.id}" alt="${esc(f.dateiname)}"></a>
          <textarea data-feld="notiz" rows="2" placeholder="Notiz …">${esc(f.notiz)}</textarea>
          <div class="zeile">
            <input type="date" data-feld="datum" value="${esc(f.datum)}" aria-label="Datum">
            <input data-feld="geschoss" list="geschosse" value="${esc(f.geschoss)}" placeholder="Geschoss" aria-label="Geschoss">
          </div>
          <select data-feld="mangel_id" aria-label="Mangel">${optionen(mangelOptionen, f.mangel_id, "– kein Mangel –")}</select>
          <div class="zeile">
            <select data-plan aria-label="Plan">${optionen(planOptionen, vorschlagPlan(f), "– Plan –")}</select>
            <button class="knopf" data-markieren title="Auf dem Plan markieren">${f.x != null ? "Verschieben" : "Markieren"}</button>
          </div>
          <div class="zeile fuss"><small>${f.x != null ? "📍 " + esc(planName(f.plan_id)) : esc(f.dateiname)}</small>
            <button class="knopf gefahr klein" data-loeschen>Löschen</button></div>
        </article>`).join("")}</div>`).join("")
    : `<div class="karte leer">Keine Fotos${Object.values(filter).some(Boolean) ? " für diese Auswahl" : ""}.</div>`}`;

  $("#foto-upload").addEventListener("change", async (ev) => {
    await mehrereHochladen("/api/fotos", [...ev.target.files], { datum: $("#upload-datum").value, geschoss: $("#upload-geschoss").value }, $("#upload-status"));
    ansichtFotos(param, query);
  });
  $("#foto-filter").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const q = new URLSearchParams([...new FormData(ev.target)].filter(([, v]) => v));
    location.hash = "#/fotos" + (q.toString() ? "?" + q : "");
  });
  $$(".foto-karte [data-feld]", inhalt).forEach((el) => el.addEventListener("change", async () => {
    const id = el.closest(".foto-karte").dataset.id;
    try { await api("PATCH", `/api/fotos/${id}`, { [el.dataset.feld]: el.value || null }); meldung("Gespeichert"); } catch (e) { fehlerAnzeigen(e); }
  }));
  $$("[data-markieren]", inhalt).forEach((b) => b.addEventListener("click", () => {
    const karte = b.closest(".foto-karte");
    const planId = $("[data-plan]", karte).value;
    if (!planId) { meldung("Bitte zuerst einen Plan auswählen", "fehler"); return; }
    location.hash = `#/plaene/${planId}?markiere=foto-${karte.dataset.id}`;
  }));
  $$("[data-loeschen]", inhalt).forEach((b) => b.addEventListener("click", async () => {
    if (!confirm("Foto endgültig löschen?")) return;
    try { await api("DELETE", `/api/fotos/${b.closest(".foto-karte").dataset.id}`); ansichtFotos(param, query); } catch (e) { fehlerAnzeigen(e); }
  }));
}

/* ---------------------------------------------------------------- Mängel */

async function ansichtMaengel() {
  const f = zustand.maengelFilter;
  const [maengel, alle] = await Promise.all([
    api("GET", "/api/maengel?" + new URLSearchParams(Object.entries(f).filter(([, v]) => v))),
    api("GET", "/api/maengel"),
  ]);
  const werte = (feld) => [...new Set(alle.map((m) => m[feld]).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de"));
  datalistFuellen("firmen", werte("firma"));
  const druckQuery = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();

  inhalt.innerHTML = `
    <div class="werkzeugleiste">
      <h1>Mängel</h1>
      <button class="knopf primaer" id="neu">＋ Neuer Mangel</button>
      <a class="knopf" href="/druck/maengel?${esc(druckQuery)}" target="_blank" rel="noopener">Druckansicht / PDF</a>
    </div>
    <form class="filterleiste" id="filter">
      <label>Status <select name="status">${optionen([["nicht_erledigt", "nicht erledigt"], ["offen", "offen"], ["in_arbeit", "in Arbeit"], ["erledigt", "erledigt"]], f.status, "alle")}</select></label>
      <label>Gewerk <select name="gewerk">${optionen(werte("gewerk").map((w) => [w, w]), f.gewerk, "alle")}</select></label>
      <label>Geschoss <select name="geschoss">${optionen(werte("geschoss").map((w) => [w, w]), f.geschoss, "alle")}</select></label>
      <label>Firma <select name="firma">${optionen(werte("firma").map((w) => [w, w]), f.firma, "alle")}</select></label>
      <label>Suche <input name="q" value="${esc(f.q || "")}" placeholder="Text …"></label>
      <label class="check"><input type="checkbox" name="ueberfaellig" value="1" ${f.ueberfaellig ? "checked" : ""}> nur überfällige</label>
      <span class="status">${maengel.length} von ${alle.length}</span>
    </form>
    ${maengel.length ? `<table class="tabelle maengel">
      <thead><tr><th>Nr.</th><th>Mangel</th><th>Ort</th><th>Gewerk / Firma</th><th>Frist</th><th>Status</th><th></th></tr></thead>
      <tbody>${maengel.map((m) => `<tr data-id="${m.id}" class="${m.status === "erledigt" ? "erledigt" : ""}">
        <td>${m.nr}</td>
        <td><strong>${esc(m.titel)}</strong>${m.beschreibung ? `<br><small>${esc(m.beschreibung.slice(0, 140))}${m.beschreibung.length > 140 ? " …" : ""}</small>` : ""}</td>
        <td>${esc([m.geschoss, m.ort].filter(Boolean).join(" / "))}${m.plan_id && m.x != null ? `<br><a href="#/plaene/${m.plan_id}" title="Auf Plan anzeigen">📍 Plan</a>` : ""}</td>
        <td>${esc(m.gewerk)}<br><small>${esc(m.firma)}</small></td>
        <td class="${m.ueberfaellig ? "ueberfaellig" : ""}">${datumDE(m.frist)}</td>
        <td><select data-status aria-label="Status">${optionen(Object.entries(STATUS), m.status)}</select></td>
        <td class="aktionen">${m.anzahl_fotos ? `<small>📷 ${m.anzahl_fotos}</small>` : ""}<button class="knopf" data-bearbeiten>Bearbeiten</button></td>
      </tr>`).join("")}</tbody></table>`
    : `<div class="karte leer">Keine Mängel${alle.length ? " für diese Auswahl" : " erfasst"}.</div>`}`;

  $("#neu").addEventListener("click", () => mangelDialog({ status: "offen" }, ansichtMaengel));
  const filterForm = $("#filter");
  const filterAnwenden = () => {
    const daten = new FormData(filterForm);
    zustand.maengelFilter = Object.fromEntries([...daten].filter(([, v]) => v));
    ansichtMaengel();
  };
  $$("select, input[type=checkbox]", filterForm).forEach((el) => el.addEventListener("change", filterAnwenden));
  filterForm.addEventListener("submit", (ev) => { ev.preventDefault(); filterAnwenden(); });
  $$("[data-status]", inhalt).forEach((s) => s.addEventListener("change", async () => {
    try { await api("PATCH", `/api/maengel/${s.closest("tr").dataset.id}`, { status: s.value }); meldung("Status geändert"); ansichtMaengel(); } catch (e) { fehlerAnzeigen(e); }
  }));
  $$("[data-bearbeiten]", inhalt).forEach((b) => b.addEventListener("click", async () => {
    mangelDialog(await api("GET", `/api/maengel/${b.closest("tr").dataset.id}`), ansichtMaengel);
  }));
}

async function mangelDialog(mangel, nachSpeichern) {
  const dialog = $("#dialog");
  const istNeu = !mangel.id;
  const [plaene, fotos, alle] = await Promise.all([
    api("GET", "/api/plaene"),
    istNeu ? Promise.resolve([]) : api("GET", `/api/fotos?mangel_id=${mangel.id}`),
    api("GET", "/api/maengel"),
  ]);
  datalistFuellen("firmen", alle.map((m) => m.firma));
  const planOptionen = plaene.map((p) => [p.id, `${p.geschoss ? p.geschoss + " · " : ""}${p.bezeichnung}`]);

  $("#dialog-inhalt").innerHTML = `
    <div class="dialog-kopf"><h2>${istNeu ? "Neuer Mangel" : `Mangel M${mangel.nr}`}</h2><button type="button" class="knopf" data-schliessen title="Schließen">×</button></div>
    <div class="formular">
      <label class="breit">Kurzbeschreibung *<input name="titel" required maxlength="300" value="${esc(mangel.titel || "")}"></label>
      <label class="breit">Beschreibung<textarea name="beschreibung" rows="3">${esc(mangel.beschreibung || "")}</textarea></label>
      <label>Geschoss<input name="geschoss" list="geschosse" value="${esc(mangel.geschoss || "")}"></label>
      <label>Ort / Raum<input name="ort" value="${esc(mangel.ort || "")}"></label>
      <label>Gewerk<input name="gewerk" list="gewerke" value="${esc(mangel.gewerk || "")}"></label>
      <label>Firma<input name="firma" list="firmen" value="${esc(mangel.firma || "")}"></label>
      <label>Frist<input type="date" name="frist" value="${esc(mangel.frist || "")}"></label>
      <label>Status<select name="status">${optionen(Object.entries(STATUS), mangel.status || "offen")}</select></label>
      <label class="breit">Plan<span class="zeile"><select name="plan_id">${optionen(planOptionen, mangel.plan_id, "– kein Plan –")}</select>
        ${istNeu ? "" : `<button type="button" class="knopf" id="auf-plan">${mangel.x != null ? "Markierung verschieben" : "Auf Plan markieren"}</button>`}</span>
        <small>${mangel.x != null ? "📍 auf dem Plan markiert" : "noch nicht auf einem Plan markiert"}</small></label>
    </div>
    ${istNeu ? `<p class="hilfe">Fotos können nach dem Speichern ergänzt werden.</p>` : `
      <h3>Fotos</h3>
      <div class="mini-raster" id="mangel-fotos">${fotos.map((f) => `<figure><a href="/datei/foto/${f.id}" target="_blank" rel="noopener"><img src="/datei/foto/${f.id}" alt=""></a>
        <button type="button" class="knopf klein" data-loesen="${f.id}" title="Foto vom Mangel lösen">lösen</button></figure>`).join("") || `<p class="leer">Keine Fotos.</p>`}</div>
      <label class="knopf">Foto hinzufügen<input type="file" id="mangel-foto" accept="image/jpeg,image/png,image/webp,image/gif" multiple hidden></label>
      <span class="status" id="mangel-upload-status"></span>`}
    <div class="dialog-fuss">
      ${istNeu ? "" : `<button type="button" class="knopf gefahr" id="mangel-loeschen">Löschen</button>`}
      <span class="abstand"></span>
      <button type="button" class="knopf" data-schliessen>Abbrechen</button>
      <button class="knopf primaer" value="speichern">Speichern</button>
    </div>`;

  const form = $("#dialog-form");
  const wertLesen = () => {
    const d = Object.fromEntries(new FormData(form));
    const planGeaendert = String(d.plan_id || "") !== String(mangel.plan_id || "");
    if (!d.plan_id) { d.plan_id = null; }
    else if (planGeaendert) { d.x = null; d.y = null; } // Plan gewechselt: Markierung neu setzen
    else { d.x = mangel.x ?? null; d.y = mangel.y ?? null; }
    return d;
  };
  const speichern = async () => {
    const d = wertLesen();
    return istNeu ? api("POST", "/api/maengel", d) : api("PATCH", `/api/maengel/${mangel.id}`, d);
  };

  $$("[data-schliessen]", dialog).forEach((b) => b.onclick = () => dialog.close());
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    try {
      const ergebnis = await speichern();
      meldung(istNeu ? `Mangel M${ergebnis.nr} angelegt` : "Gespeichert");
      dialog.close();
      if (nachSpeichern) await nachSpeichern(ergebnis);
    } catch (e) { fehlerAnzeigen(e); }
  };

  const aufPlan = $("#auf-plan");
  if (aufPlan) aufPlan.onclick = async () => {
    const planId = form.elements.plan_id.value;
    if (!planId) { meldung("Bitte zuerst einen Plan auswählen", "fehler"); return; }
    try {
      await speichern();
      dialog.close();
      location.hash = `#/plaene/${planId}?markiere=mangel-${mangel.id}`;
    } catch (e) { fehlerAnzeigen(e); }
  };

  const fotoInput = $("#mangel-foto");
  if (fotoInput) fotoInput.onchange = async () => {
    await mehrereHochladen("/api/fotos", [...fotoInput.files], { mangel_id: mangel.id, geschoss: form.elements.geschoss.value }, $("#mangel-upload-status"));
    mangelDialog({ ...mangel, ...wertLesen(), id: mangel.id, nr: mangel.nr }, nachSpeichern);
  };
  $$("[data-loesen]", dialog).forEach((b) => b.onclick = async () => {
    try { await api("PATCH", `/api/fotos/${b.dataset.loesen}`, { mangel_id: null }); b.closest("figure").remove(); } catch (e) { fehlerAnzeigen(e); }
  });
  const loeschen = $("#mangel-loeschen");
  if (loeschen) loeschen.onclick = async () => {
    if (!confirm(`Mangel M${mangel.nr} löschen? Zugeordnete Fotos bleiben erhalten.`)) return;
    try { await api("DELETE", `/api/maengel/${mangel.id}`); dialog.close(); meldung("Gelöscht"); if (nachSpeichern) nachSpeichern(); } catch (e) { fehlerAnzeigen(e); }
  };

  if (!dialog.open) dialog.showModal();
  form.elements.titel.focus();
}

/* ---------------------------------------------------------------- Bautagebuch */

async function ansichtTagebuch(datum) {
  const liste = await api("GET", "/api/tagebuch");
  inhalt.innerHTML = `
    <div class="werkzeugleiste">
      <h1>Bautagebuch</h1>
      <form id="tag-oeffnen" class="zeile">
        <input type="date" name="datum" value="${esc(datum || heute())}" required>
        <button class="knopf primaer">Tag öffnen / anlegen</button>
      </form>
    </div>
    <div class="tagebuch-layout">
      <aside class="karte tageliste">
        <h2>Einträge <small>(${liste.length})</small></h2>
        ${liste.length ? liste.map((t) => `<a class="tag-eintrag ${t.datum === datum ? "aktiv" : ""}" href="#/tagebuch/${t.datum}">
          <strong>${wochentag(t.datum)}, ${datumDE(t.datum)}</strong>
          <small>${esc(t.wetter || "")}${t.personal_summe ? ` · ${t.personal_summe} AK` : ""}${t.anzahl_fotos ? ` · 📷 ${t.anzahl_fotos}` : ""}</small></a>`).join("")
          : `<p class="leer">Noch keine Einträge.</p>`}
      </aside>
      <section id="tag-editor" class="karte">${datum ? "" : `<p class="leer">Tag links auswählen oder oben ein Datum öffnen.</p>`}</section>
    </div>`;
  $("#tag-oeffnen").addEventListener("submit", (ev) => {
    ev.preventDefault();
    location.hash = `#/tagebuch/${new FormData(ev.target).get("datum")}`;
  });
  if (datum) await tagEditor(datum, liste);
}

async function tagEditor(datum, liste) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(datum)) throw new Error("Ungültiges Datum");
  const editor = $("#tag-editor");
  let eintrag = null;
  try { eintrag = await api("GET", `/api/tagebuch/${datum}`); } catch (e) { if (!/Kein Eintrag/.test(e.message)) throw e; }
  const neu = !eintrag;
  const t = eintrag || { wetter: "", temperatur: "", arbeitszeit: "07:00 – 16:00", personal: [], leistungen: "", behinderungen: "", vorkommnisse: "", anordnungen: "", besucher: "" };
  const fotos = await api("GET", `/api/fotos?datum=${datum}`);

  editor.innerHTML = `
    <div class="dialog-kopf"><h2>${wochentag(datum)}, ${datumDE(datum)} ${neu ? `<span class="badge neu">neu</span>` : ""}</h2>
      <span class="abstand"></span>
      ${neu ? "" : `<a class="knopf" href="/druck/tagebuch/${datum}" target="_blank" rel="noopener">Druckansicht / PDF</a>`}
    </div>
    <form id="tag-form" class="formular">
      <label>Wetter<input name="wetter" list="wetter-liste" value="${esc(t.wetter)}"></label>
      <label>Temperatur<input name="temperatur" value="${esc(t.temperatur)}" placeholder="z. B. 8 – 14 °C"></label>
      <label class="breit">Arbeitszeit<input name="arbeitszeit" value="${esc(t.arbeitszeit)}"></label>
      <fieldset class="breit personal">
        <legend>Personal auf der Baustelle</legend>
        <table class="tabelle kompakt"><thead><tr><th>Firma</th><th>Gewerk</th><th style="width:6rem">Anzahl</th><th></th></tr></thead>
          <tbody id="personal-zeilen"></tbody>
          <tfoot><tr><th colspan="2">Summe</th><th id="personal-summe">0</th><th></th></tr></tfoot></table>
        <div class="zeile"><button type="button" class="knopf" id="personal-plus">＋ Zeile</button>
          <button type="button" class="knopf" id="personal-vortag">Vom letzten Eintrag übernehmen</button></div>
      </fieldset>
      <label class="breit">Ausgeführte Leistungen<textarea name="leistungen" rows="5">${esc(t.leistungen)}</textarea></label>
      <label class="breit">Behinderungen / Erschwernisse<textarea name="behinderungen" rows="2">${esc(t.behinderungen)}</textarea></label>
      <label class="breit">Besondere Vorkommnisse<textarea name="vorkommnisse" rows="2">${esc(t.vorkommnisse)}</textarea></label>
      <label class="breit">Anordnungen / Vereinbarungen<textarea name="anordnungen" rows="2">${esc(t.anordnungen)}</textarea></label>
      <label class="breit">Besucher / Besprechungen<textarea name="besucher" rows="2">${esc(t.besucher)}</textarea></label>
      <datalist id="wetter-liste">${WETTER.map((w) => `<option value="${w}">`).join("")}</datalist>
      <div class="breit dialog-fuss">
        ${neu ? "" : `<button type="button" class="knopf gefahr" id="tag-loeschen">Eintrag löschen</button>`}
        <span class="abstand"></span>
        <button class="knopf primaer">Speichern</button>
      </div>
    </form>
    <h3>Fotos vom ${datumDE(datum)} <small>(${fotos.length})</small></h3>
    <div class="mini-raster">${fotos.map((f) => `<a href="/datei/foto/${f.id}" target="_blank" rel="noopener" title="${esc(f.notiz)}"><img loading="lazy" src="/datei/foto/${f.id}" alt=""></a>`).join("") || `<p class="leer">Keine Fotos an diesem Tag.</p>`}</div>
    <div class="zeile"><label class="knopf">Fotos für diesen Tag hochladen<input type="file" id="tag-fotos" accept="image/jpeg,image/png,image/webp,image/gif" multiple hidden></label>
      <a class="knopf" href="#/fotos?datum=${datum}">Fotos bearbeiten</a><span class="status" id="tag-upload-status"></span></div>`;

  const form = $("#tag-form");
  const tbody = $("#personal-zeilen");
  const zeileHinzu = (p = {}) => {
    tbody.insertAdjacentHTML("beforeend", `<tr>
      <td><input data-p="firma" list="firmen" value="${esc(p.firma || "")}" aria-label="Firma"></td>
      <td><input data-p="gewerk" list="gewerke" value="${esc(p.gewerk || "")}" aria-label="Gewerk"></td>
      <td><input data-p="anzahl" type="number" min="0" step="1" value="${esc(p.anzahl ?? "")}" aria-label="Anzahl"></td>
      <td><button type="button" class="knopf klein" data-weg title="Zeile entfernen">×</button></td></tr>`);
  };
  const summe = () => { $("#personal-summe").textContent = $$("[data-p=anzahl]", tbody).reduce((s, i) => s + (parseInt(i.value, 10) || 0), 0); };
  (t.personal.length ? t.personal : [{}]).forEach(zeileHinzu);
  summe();
  const personalLesen = () => $$("tr", tbody).map((tr) => ({
    firma: $("[data-p=firma]", tr).value, gewerk: $("[data-p=gewerk]", tr).value, anzahl: parseInt($("[data-p=anzahl]", tr).value, 10) || 0,
  })).filter((p) => p.firma || p.gewerk || p.anzahl);

  tbody.addEventListener("click", (ev) => { if (ev.target.matches("[data-weg]")) { ev.target.closest("tr").remove(); summe(); zustand.ungespeichert = true; } });
  form.addEventListener("input", () => { zustand.ungespeichert = true; summe(); });
  $("#personal-plus").onclick = () => zeileHinzu();
  $("#personal-vortag").onclick = async () => {
    const frueher = liste.find((x) => x.datum < datum);
    if (!frueher) { meldung("Kein früherer Eintrag vorhanden", "fehler"); return; }
    try {
      const v = await api("GET", `/api/tagebuch/${frueher.datum}`);
      if (!v.personal.length) { meldung(`Am ${datumDE(frueher.datum)} wurde kein Personal erfasst`, "fehler"); return; }
      tbody.innerHTML = "";
      v.personal.forEach(zeileHinzu);
      summe();
      zustand.ungespeichert = true;
      meldung(`Personal vom ${datumDE(frueher.datum)} übernommen – bitte prüfen`);
    } catch (e) { fehlerAnzeigen(e); }
  };

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const daten = Object.fromEntries(new FormData(form));
    daten.personal = personalLesen();
    try {
      await api("PUT", `/api/tagebuch/${datum}`, daten);
      zustand.ungespeichert = false;
      meldung("Bautagebuch gespeichert");
      ansichtTagebuch(datum);
    } catch (e) { fehlerAnzeigen(e); }
  });

  const loeschen = $("#tag-loeschen");
  if (loeschen) loeschen.onclick = async () => {
    if (!confirm(`Eintrag vom ${datumDE(datum)} löschen? Fotos bleiben erhalten.`)) return;
    try { await api("DELETE", `/api/tagebuch/${datum}`); zustand.ungespeichert = false; location.hash = "#/tagebuch"; } catch (e) { fehlerAnzeigen(e); }
  };

  $("#tag-fotos").onchange = async (ev) => {
    if (zustand.ungespeichert && !confirm("Ungespeicherte Eingaben gehen beim Neuladen verloren. Fortfahren?")) return;
    await mehrereHochladen("/api/fotos", [...ev.target.files], { datum }, $("#tag-upload-status"));
    zustand.ungespeichert = false;
    ansichtTagebuch(datum);
  };
}

/* ---------------------------------------------------------------- Einstellungen */

async function ansichtEinstellungen() {
  const [w, info] = await Promise.all([api("GET", "/api/einstellungen"), api("GET", "/api/info")]);
  inhalt.innerHTML = `
    <div class="werkzeugleiste"><h1>Einstellungen</h1></div>
    <div class="spalten">
      <form class="karte formular" id="einstellungen">
        <h2 class="breit">Projekt</h2>
        <label>Projektnummer<input name="projekt_nr" value="${esc(w.projekt_nr)}"></label>
        <label>Projektname<input name="projekt_name" value="${esc(w.projekt_name)}"></label>
        <label class="breit">Baustelle / Adresse<input name="adresse" value="${esc(w.adresse)}"></label>
        <label>Bauherr<input name="bauherr" value="${esc(w.bauherr)}"></label>
        <label>Bauleitung<input name="bauleiter" value="${esc(w.bauleiter)}"></label>
        <label class="breit">Gewerke (kommagetrennt, als Vorschläge)<textarea name="gewerke" rows="3">${esc(w.gewerke)}</textarea></label>
        <div class="breit dialog-fuss"><span class="abstand"></span><button class="knopf primaer">Speichern</button></div>
      </form>
      <section class="karte">
        <h2>System</h2>
        <dl class="info">
          <dt>Version</dt><dd>${esc(info.version)}</dd>
          <dt>Python</dt><dd>${esc(info.python)}</dd>
          <dt>Adresse</dt><dd>${esc(location.origin)}</dd>
          <dt>Datenordner</dt><dd><code>${esc(info.datenordner)}</code></dd>
          <dt>Sicherungen</dt><dd><code>${esc(info.sicherungsordner)}</code><br><small>letzte: ${esc(info.letzte_sicherung || "noch keine")}</small></dd>
          <dt>Fehlerprotokoll</dt><dd><code>${esc(info.logdatei)}</code></dd>
        </dl>
        <p class="hilfe">Bei jedem Start wird der Datenordner automatisch als ZIP gesichert. Port, Ordner und Anzahl der aufbewahrten Sicherungen stehen in <code>config.json</code>.</p>
      </section>
    </div>`;
  const form = $("#einstellungen");
  form.addEventListener("input", () => { zustand.ungespeichert = true; });
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      einstellungenUebernehmen(await api("PUT", "/api/einstellungen", Object.fromEntries(new FormData(form))));
      zustand.ungespeichert = false;
      meldung("Einstellungen gespeichert");
    } catch (e) { fehlerAnzeigen(e); }
  });
}

start();
