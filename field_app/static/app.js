(() => {
  "use strict";

  const STRINGS = {
    fr: {
      brand_sub: "Poste d'écoute terrain",
      conn_waiting: "En attente de connexion…",
      conn_online: "Connecté au poste",
      conn_offline: "Connexion perdue — reconnexion...",
      status_headline_idle: "AUCUNE DONNÉE REÇUE",
      status_headline_idle_target: "AUCUNE DONNÉE — {label}",
      status_detail_idle: "En attente de la première capture du capteur…",
      status_headline_shot: "TIR DÉTECTÉ — {weapon}",
      unknown_weapon: "arme inconnue",
      status_headline_clear: "AUCUNE MENACE",
      status_detail_clear: "Impact non balistique — modèle étage 1 : {model}",
      status_detail_shot: "Modèle étage 1 : {m1} · Modèle étage 2 : {m2}{conf}",
      confidence_suffix: " ({pct}% de confiance)",
      targets_panel_title: "Cibles",
      targets_hint: "Cliquez sur une cible pour voir son détail ci-dessous.",
      target_no_data: "Aucune donnée",
      unpin_target: "✕ Revenir à la dernière alerte",
      wave_panel_title: "Dernière forme d'onde",
      history_panel_title: "Historique récent",
      th_time: "Heure",
      th_target: "Cible",
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
      test_target_label: "Cible à simuler",
      test_target_generic: "Test générique (aucune cible)",
      test_button: "Classer cette forme d'onde",
      test_error_format: "Format invalide : octets hexadécimaux séparés par des espaces.",
      test_error_count: "512 valeurs attendues, {n} fournies.",
      test_error_server: "Erreur serveur ({status})",
      test_error_unreachable: "Impossible de contacter le serveur local.",
      footer: "Shot Classifier — prototype de recherche, non qualifié pour un usage opérationnel.",
      ago_now: "à l'instant",
      ago_seconds: "il y a {n}s",
      ago_minutes: "il y a {n} min",
      th_verified: "Vérifié",
      verify_hint: "Cliquez sur « Vérifier » pour confirmer ou corriger une classification — seules les captures vérifiées par un opérateur sont utilisables pour améliorer les modèles.",
      verify_button: "Vérifier",
      verify_confirmed: "✅ Confirmé",
      verify_corrected: "✏️ Corrigé",
      confirm_title: "Vérifier cette capture",
      confirm_was_shot: "C'était un tir",
      confirm_was_noshot: "Ce n'était pas un tir",
      confirm_weapon_label: "Arme réelle",
      confirm_weapon_unknown: "Inconnue / autre",
      confirm_submit: "Valider",
      confirm_cancel: "Annuler",
    },
    en: {
      brand_sub: "Field listening post",
      conn_waiting: "Waiting for connection…",
      conn_online: "Connected",
      conn_offline: "Connection lost — reconnecting...",
      status_headline_idle: "NO DATA RECEIVED",
      status_headline_idle_target: "NO DATA — {label}",
      status_detail_idle: "Waiting for the first sensor capture…",
      status_headline_shot: "SHOT DETECTED — {weapon}",
      unknown_weapon: "unknown weapon",
      status_headline_clear: "NO THREAT",
      status_detail_clear: "Non-ballistic impact — stage 1 model: {model}",
      status_detail_shot: "Stage 1 model: {m1} · Stage 2 model: {m2}{conf}",
      confidence_suffix: " ({pct}% confidence)",
      targets_panel_title: "Targets",
      targets_hint: "Click a target to see its detail below.",
      target_no_data: "No data",
      unpin_target: "✕ Back to latest alert",
      wave_panel_title: "Latest waveform",
      history_panel_title: "Recent history",
      th_time: "Time",
      th_target: "Target",
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
      test_target_label: "Target to simulate",
      test_target_generic: "Generic test (no target)",
      test_button: "Classify this waveform",
      test_error_format: "Invalid format: hexadecimal bytes separated by spaces.",
      test_error_count: "512 values expected, {n} provided.",
      test_error_server: "Server error ({status})",
      test_error_unreachable: "Could not reach the local server.",
      footer: "Shot Classifier — research prototype, not qualified for operational use.",
      ago_now: "just now",
      ago_seconds: "{n}s ago",
      ago_minutes: "{n} min ago",
      th_verified: "Verified",
      verify_hint: "Click “Verify” to confirm or correct a classification — only operator-verified captures can be used to improve the models.",
      verify_button: "Verify",
      verify_confirmed: "✅ Confirmed",
      verify_corrected: "✏️ Corrected",
      confirm_title: "Verify this capture",
      confirm_was_shot: "It was a shot",
      confirm_was_noshot: "It was not a shot",
      confirm_weapon_label: "Actual weapon",
      confirm_weapon_unknown: "Unknown / other",
      confirm_submit: "Submit",
      confirm_cancel: "Cancel",
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
  const targetsGrid = document.getElementById("targetsGrid");
  const statusCard = document.getElementById("statusCard");
  const statusIcon = document.getElementById("statusIcon");
  const statusTarget = document.getElementById("statusTarget");
  const statusHeadline = document.getElementById("statusHeadline");
  const statusDetail = document.getElementById("statusDetail");
  const statusTime = document.getElementById("statusTime");
  const statusUnpin = document.getElementById("statusUnpin");
  const waveTarget = document.getElementById("waveTarget");
  const historyBody = document.getElementById("historyBody");
  const canvas = document.getElementById("waveCanvas");
  const ctx = canvas.getContext("2d");
  const testToggle = document.getElementById("testToggle");
  const testBody = document.getElementById("testBody");
  const testInput = document.getElementById("testInput");
  const testTarget = document.getElementById("testTarget");
  const testSubmit = document.getElementById("testSubmit");
  const testError = document.getElementById("testError");
  const langSwitch = document.getElementById("langSwitch");
  const confirmPanel = document.getElementById("confirmPanel");
  const confirmWeaponRow = document.getElementById("confirmWeaponRow");
  const confirmWeapon = document.getElementById("confirmWeapon");
  const confirmSubmit = document.getElementById("confirmSubmit");
  const confirmCancel = document.getElementById("confirmCancel");

  let lastEntry = null;
  let lastHistory = [];
  let confirmTargetId = null;
  let targetsList = [];
  let targetLastResult = {};
  let selectedTargetId = null; // null = suit automatiquement le dernier evenement, quelle que soit la cible

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

  function targetLabelById(id) {
    const tgt = targetsList.find((x) => x.id === id);
    return tgt ? tgt.label : "";
  }

  function applyEntry(entry) {
    lastEntry = entry;
    const s = entry.summary;
    statusTarget.textContent = entry.target_label || "";

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
    waveTarget.textContent = `${entry.target_label || ""} · ${fmtTime(entry.received_at)}`;
    drawWave(entry.values);
  }

  function showIdleForTarget(targetId) {
    lastEntry = null;
    const label = targetId != null ? targetLabelById(targetId) : "";
    statusTarget.textContent = label;
    statusCard.dataset.state = "idle";
    statusIcon.textContent = "◎";
    statusHeadline.removeAttribute("data-i18n");
    statusHeadline.textContent = targetId != null
      ? t("status_headline_idle_target", { label })
      : t("status_headline_idle");
    statusDetail.setAttribute("data-i18n", "status_detail_idle");
    statusDetail.textContent = t("status_detail_idle");
    statusTime.textContent = "";
    waveTarget.textContent = label ? `${label} — ${t("target_no_data")}` : "";
    drawWave(null);
  }

  function refreshDetail() {
    let entry = null;
    if (selectedTargetId !== null) {
      entry = targetLastResult[selectedTargetId] || null;
    } else if (lastHistory.length) {
      entry = lastHistory[0];
    }
    if (entry) {
      applyEntry(entry);
    } else {
      showIdleForTarget(selectedTargetId);
    }
  }

  function renderTargetsGrid() {
    targetsGrid.innerHTML = "";
    targetsList.forEach((tgt) => {
      const entry = targetLastResult[tgt.id];
      let state = "idle";
      let info = t("target_no_data");
      if (entry) {
        state = entry.summary.is_shot ? "alert" : "clear";
        info = entry.summary.is_shot ? (entry.summary.weapon || t("unknown_weapon")) : t("row_nonshot");
      }
      const box = document.createElement("button");
      box.type = "button";
      box.className = "target-box" + (selectedTargetId === tgt.id ? " selected" : "");
      box.dataset.targetId = String(tgt.id);
      box.dataset.state = state;
      box.innerHTML = `
        <span class="target-box-icon">🎯</span>
        <span class="target-box-label">${tgt.label}</span>
        <span class="target-box-ip">${tgt.ip}</span>
        <span class="target-box-info">${info}</span>
      `;
      targetsGrid.appendChild(box);
    });
  }

  targetsGrid.addEventListener("click", (ev) => {
    const box = ev.target.closest(".target-box");
    if (!box) return;
    selectedTargetId = Number(box.dataset.targetId);
    statusUnpin.hidden = false;
    renderTargetsGrid();
    refreshDetail();
    statusCard.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  statusUnpin.addEventListener("click", () => {
    selectedTargetId = null;
    statusUnpin.hidden = true;
    renderTargetsGrid();
    refreshDetail();
  });

  function populateTestTargetOptions() {
    testTarget.innerHTML = "";
    testTarget.appendChild(new Option(t("test_target_generic"), ""));
    targetsList.forEach((tgt) => {
      testTarget.appendChild(new Option(`${tgt.label} (${tgt.ip})`, String(tgt.id)));
    });
  }

  function verifyCellHTML(entry) {
    if (!entry.id) return "—";
    if (!entry.confirmed) {
      return `<button type="button" class="btn-verify" data-verify-id="${entry.id}">${t("verify_button")}</button>`;
    }
    const changed = entry.confirmed.is_shot !== entry.summary.is_shot
      || (entry.confirmed.is_shot && entry.confirmed.weapon && entry.confirmed.weapon !== entry.summary.weapon);
    const cls = changed ? "corrected" : "confirmed";
    const label = changed ? t("verify_corrected") : t("verify_confirmed");
    return `<span class="verify-badge ${cls}">${label}</span>`;
  }

  function historyRowHTML(entry) {
    const s = entry.summary;
    const conf = s.weapon_confidence != null ? `${Math.round(s.weapon_confidence * 100)}%` : "—";
    return `
      <td>${fmtTime(entry.received_at)}</td>
      <td>${entry.target_label || "—"}</td>
      <td>${entry.sensor_id || "—"}</td>
      <td>${s.is_shot ? t("row_shot") : t("row_nonshot")}</td>
      <td>${s.weapon || "—"}</td>
      <td>${conf}</td>
      <td>${verifyCellHTML(entry)}</td>
    `;
  }

  function prependHistoryRow(entry) {
    const emptyRow = historyBody.querySelector(".empty-row");
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement("tr");
    tr.dataset.id = entry.id || "";
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
      historyBody.innerHTML = `<tr class="empty-row"><td colspan="7" data-i18n="empty_history">${t("empty_history")}</td></tr>`;
      return;
    }
    // entries est trie du plus recent au plus ancien ; on les prepend dans
    // l'ordre inverse pour que le plus recent reste bien en haut du tableau.
    [...entries].reverse().forEach((e) => prependHistoryRow(e));
  }

  function findEntry(id) {
    return lastHistory.find((e) => e.id === id);
  }

  historyBody.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-verify-id]");
    if (btn) openConfirmPanel(btn.dataset.verifyId);
  });

  function openConfirmPanel(id) {
    confirmTargetId = id;
    confirmPanel.hidden = false;
    confirmPanel.querySelector('input[value="shot"]').checked = true;
    confirmWeaponRow.hidden = false;
    confirmPanel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  confirmPanel.addEventListener("change", (ev) => {
    if (ev.target.name === "confirmShot") {
      confirmWeaponRow.hidden = ev.target.value !== "shot";
    }
  });

  confirmCancel.addEventListener("click", () => {
    confirmPanel.hidden = true;
    confirmTargetId = null;
  });

  confirmSubmit.addEventListener("click", async () => {
    if (!confirmTargetId) return;
    const isShot = confirmPanel.querySelector('input[name="confirmShot"]:checked').value === "shot";
    const weapon = isShot ? confirmWeapon.value : null;
    confirmSubmit.disabled = true;
    try {
      await fetch("/api/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: confirmTargetId, is_shot: isShot, weapon }),
      });
    } catch {
      // Le serveur local est injoignable : rien a faire de plus ici, l'operateur
      // le remarquera (la ligne restera marquee "a verifier").
    } finally {
      confirmSubmit.disabled = false;
      confirmPanel.hidden = true;
      confirmTargetId = null;
    }
  });

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
        refreshDetail();
      } else if (msg.type === "targets") {
        targetsList = msg.payload.targets;
        targetLastResult = msg.payload.last_results || {};
        populateTestTargetOptions();
        renderTargetsGrid();
        refreshDetail();
      } else if (msg.type === "result") {
        lastHistory = [msg.payload, ...lastHistory].slice(0, 50);
        prependHistoryRow(msg.payload);
        const tid = msg.payload.target_id;
        if (tid != null) targetLastResult[tid] = msg.payload;
        renderTargetsGrid();
        if (selectedTargetId === null || selectedTargetId === tid) {
          applyEntry(msg.payload);
        }
      } else if (msg.type === "confirmation") {
        const e = findEntry(msg.payload.id);
        if (e) {
          e.confirmed = msg.payload.confirmed;
          renderHistory(lastHistory);
        }
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
        body: JSON.stringify({
          values,
          sensor_id: "manuel (UI)",
          target_id: testTarget.value ? Number(testTarget.value) : null,
        }),
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
    populateTestTargetOptions();
    renderTargetsGrid();
    renderHistory(lastHistory);
    refreshDetail();
  }

  langSwitch.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".lang-btn");
    if (btn) setLang(btn.dataset.lang);
  });

  applyStaticStrings();
  connectWS();
})();
