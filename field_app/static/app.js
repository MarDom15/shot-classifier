(() => {
  "use strict";

  const STRINGS = {
    fr: {
      brand_sub: "Poste d'écoute terrain",
      conn_waiting: "En attente de connexion…",
      conn_online: "Connecté au poste",
      conn_offline: "Connexion perdue — reconnexion...",
      status_headline_idle: "AUCUNE DONNÉE REÇUE",
      status_detail_idle: "En attente de la première capture du capteur…",
      status_headline_shot: "TIR DÉTECTÉ — {weapon}",
      unknown_weapon: "arme inconnue",
      status_headline_clear: "AUCUNE MENACE",
      status_detail_clear: "Impact non balistique — modèle étage 1 : {model}",
      status_detail_shot: "Modèle étage 1 : {m1} · Modèle étage 2 : {m2}{conf}",
      confidence_suffix: " ({pct}% de confiance)",
      wave_panel_title: "Dernière forme d'onde",
      history_panel_title: "Historique récent",
      th_time: "Heure",
      th_sensor: "Capteur",
      th_result: "Résultat",
      th_weapon: "Arme",
      th_confidence: "Confiance",
      empty_history: "Aucun évènement pour l'instant.",
      row_shot: "🔫 Tir",
      row_nonshot: "🪨 Non-tir",
      test_toggle_closed: "🧪 Test manuel (sans capteur) ▾",
      test_toggle_open: "🧪 Test manuel (sans capteur) ▴",
      test_hint: "Coller 512 octets hexadécimaux séparés par des espaces (ex. issus de l'app de démonstration).",
      test_button: "Classer cette forme d'onde",
      test_error_format: "Format invalide : octets hexadécimaux séparés par des espaces.",
      test_error_count: "512 valeurs attendues, {n} fournies.",
      test_error_server: "Erreur serveur ({status})",
      test_error_unreachable: "Impossible de contacter le serveur local.",
      footer: "Shot Classifier — prototype de recherche, non qualifié pour un usage opérationnel.",
      ago_now: "à l'instant",
      ago_seconds: "il y a {n}s",
      ago_minutes: "il y a {n} min",
    },
    en: {
      brand_sub: "Field listening post",
      conn_waiting: "Waiting for connection…",
      conn_online: "Connected",
      conn_offline: "Connection lost — reconnecting...",
      status_headline_idle: "NO DATA RECEIVED",
      status_detail_idle: "Waiting for the first sensor capture…",
      status_headline_shot: "SHOT DETECTED — {weapon}",
      unknown_weapon: "unknown weapon",
      status_headline_clear: "NO THREAT",
      status_detail_clear: "Non-ballistic impact — stage 1 model: {model}",
      status_detail_shot: "Stage 1 model: {m1} · Stage 2 model: {m2}{conf}",
      confidence_suffix: " ({pct}% confidence)",
      wave_panel_title: "Latest waveform",
      history_panel_title: "Recent history",
      th_time: "Time",
      th_sensor: "Sensor",
      th_result: "Result",
      th_weapon: "Weapon",
      th_confidence: "Confidence",
      empty_history: "No events yet.",
      row_shot: "🔫 Shot",
      row_nonshot: "🪨 Non-shot",
      test_toggle_closed: "🧪 Manual test (no sensor) ▾",
      test_toggle_open: "🧪 Manual test (no sensor) ▴",
      test_hint: "Paste 512 hexadecimal bytes separated by spaces (e.g. from the demo app).",
      test_button: "Classify this waveform",
      test_error_format: "Invalid format: hexadecimal bytes separated by spaces.",
      test_error_count: "512 values expected, {n} provided.",
      test_error_server: "Server error ({status})",
      test_error_unreachable: "Could not reach the local server.",
      footer: "Shot Classifier — research prototype, not qualified for operational use.",
      ago_now: "just now",
      ago_seconds: "{n}s ago",
      ago_minutes: "{n} min ago",
    },
  };

  let LANG = "fr";
  try {
    LANG = localStorage.getItem("fieldapp_lang") || "fr";
  } catch { /* stockage indisponible (mode prive, etc.) : on garde le defaut */ }

  function t(key, vars) {
    let text = (STRINGS[LANG] && STRINGS[LANG][key]) || key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        text = text.replace(`{${k}}`, v);
      }
    }
    return text;
  }

  const conn = document.getElementById("conn");
  const connLabel = document.getElementById("connLabel");
  const statusCard = document.getElementById("statusCard");
  const statusIcon = document.getElementById("statusIcon");
  const statusHeadline = document.getElementById("statusHeadline");
  const statusDetail = document.getElementById("statusDetail");
  const statusTime = document.getElementById("statusTime");
  const historyBody = document.getElementById("historyBody");
  const canvas = document.getElementById("waveCanvas");
  const ctx = canvas.getContext("2d");
  const testToggle = document.getElementById("testToggle");
  const testBody = document.getElementById("testBody");
  const testInput = document.getElementById("testInput");
  const testSubmit = document.getElementById("testSubmit");
  const testError = document.getElementById("testError");
  const langSwitch = document.getElementById("langSwitch");

  let lastEntry = null;
  let lastHistory = [];

  function fmtTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString();
  }

  function agoLabel(iso) {
    if (!iso) return "";
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (seconds < 5) return t("ago_now");
    if (seconds < 60) return t("ago_seconds", { n: seconds });
    return t("ago_minutes", { n: Math.round(seconds / 60) });
  }

  function drawWave(values) {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (!values || !values.length) return;

    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();

    const isAlert = statusCard.dataset.state === "alert";
    ctx.strokeStyle = isAlert ? "#e05a4d" : "#8fae5d";
    ctx.lineWidth = 2;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - (v / 255) * h;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function setConnState(state, labelKey) {
    conn.dataset.state = state;
    connLabel.dataset.i18n = labelKey;
    connLabel.textContent = t(labelKey);
  }

  function applyEntry(entry, { fromHistory = false } = {}) {
    lastEntry = entry;
    const s = entry.summary;

    if (s.is_shot) {
      statusCard.dataset.state = "alert";
      statusIcon.textContent = "⚠";
      const weapon = s.weapon || t("unknown_weapon");
      statusHeadline.removeAttribute("data-i18n");
      statusHeadline.textContent = t("status_headline_shot", { weapon });
      const conf = s.weapon_confidence != null
        ? t("confidence_suffix", { pct: Math.round(s.weapon_confidence * 100) })
        : "";
      statusDetail.removeAttribute("data-i18n");
      statusDetail.textContent = t("status_detail_shot", { m1: s.stage1_model, m2: s.stage2_model || "—", conf });
    } else {
      statusCard.dataset.state = "clear";
      statusIcon.textContent = "✓";
      statusHeadline.removeAttribute("data-i18n");
      statusHeadline.textContent = t("status_headline_clear");
      statusDetail.removeAttribute("data-i18n");
      statusDetail.textContent = t("status_detail_clear", { model: s.stage1_model });
    }
    statusTime.textContent = `${fmtTime(entry.received_at)} · ${agoLabel(entry.received_at)}`;

    drawWave(entry.values);

    if (!fromHistory) prependHistoryRow(entry);
  }

  function historyRowHTML(entry) {
    const s = entry.summary;
    const conf = s.weapon_confidence != null ? `${Math.round(s.weapon_confidence * 100)}%` : "—";
    return `
      <td>${fmtTime(entry.received_at)}</td>
      <td>${entry.sensor_id || "—"}</td>
      <td>${s.is_shot ? t("row_shot") : t("row_nonshot")}</td>
      <td>${s.weapon || "—"}</td>
      <td>${conf}</td>
    `;
  }

  function prependHistoryRow(entry) {
    const emptyRow = historyBody.querySelector(".empty-row");
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement("tr");
    if (entry.summary.is_shot) tr.classList.add("row-alert");
    tr.innerHTML = historyRowHTML(entry);
    historyBody.prepend(tr);
    while (historyBody.children.length > 50) {
      historyBody.removeChild(historyBody.lastChild);
    }
  }

  function renderHistory(entries) {
    lastHistory = entries;
    historyBody.innerHTML = "";
    if (!entries.length) {
      historyBody.innerHTML = `<tr class="empty-row"><td colspan="5" data-i18n="empty_history">${t("empty_history")}</td></tr>`;
      return;
    }
    entries.forEach((e) => prependHistoryRow(e));
    applyEntry(entries[0], { fromHistory: true });
  }

  // Rafraichit le "il y a Xs" sans attendre un nouvel evenement.
  setInterval(() => {
    if (lastEntry) {
      statusTime.textContent = `${fmtTime(lastEntry.received_at)} · ${agoLabel(lastEntry.received_at)}`;
    }
  }, 1000);

  function connectWS() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => setConnState("online", "conn_online");
    ws.onclose = () => {
      setConnState("offline", "conn_offline");
      setTimeout(connectWS, 2000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "history") {
        renderHistory(msg.payload);
      } else if (msg.type === "result") {
        renderHistory([msg.payload, ...lastHistory].slice(0, 50));
      }
    };
  }

  testToggle.addEventListener("click", () => {
    testBody.hidden = !testBody.hidden;
    testToggle.dataset.i18n = testBody.hidden ? "test_toggle_closed" : "test_toggle_open";
    testToggle.textContent = t(testToggle.dataset.i18n);
  });

  testSubmit.addEventListener("click", async () => {
    testError.textContent = "";
    const raw = testInput.value.trim();
    if (!raw) return;
    let values;
    try {
      values = raw.split(/\s+/).map((tok) => {
        const n = parseInt(tok, 16);
        if (Number.isNaN(n)) throw new Error("bad token");
        return n;
      });
    } catch {
      testError.textContent = t("test_error_format");
      return;
    }
    if (values.length !== 512) {
      testError.textContent = t("test_error_count", { n: values.length });
      return;
    }
    testSubmit.disabled = true;
    try {
      const res = await fetch("/api/manual-predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values, sensor_id: "manuel (UI)" }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        testError.textContent = body.detail || t("test_error_server", { status: res.status });
      }
    } catch {
      testError.textContent = t("test_error_unreachable");
    } finally {
      testSubmit.disabled = false;
    }
  });

  function applyStaticStrings() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.documentElement.lang = LANG;
    langSwitch.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === LANG);
    });
  }

  function setLang(lang) {
    LANG = lang;
    try {
      localStorage.setItem("fieldapp_lang", lang);
    } catch { /* stockage indisponible : la preference ne survivra pas au rechargement */ }
    applyStaticStrings();
    // Re-rend le contenu dynamique (carte de statut, historique) dans la nouvelle langue.
    if (lastHistory.length) {
      renderHistory(lastHistory);
    }
  }

  langSwitch.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".lang-btn");
    if (btn) setLang(btn.dataset.lang);
  });

  applyStaticStrings();
  connectWS();
})();
