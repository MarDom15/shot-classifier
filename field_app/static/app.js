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
      test_import_button: "📁 Importer un fichier",
      test_error_import: "Fichier illisible — formats acceptés : .txt brut du capteur (« Triggered:... »), JSON ({\"values\":[...]}), ou octets hexadécimaux séparés par des espaces.",
      test_import_image_button: "🖼️ Importer une image du signal",
      test_image_warning: "⚠️ Extraction approximative depuis l'image — vérifiez que la courbe ci-dessous correspond bien au signal avant de classer.",
      test_error_image: "Impossible d'extraire une courbe de cette image (aucune ligne détectée sur fond uni).",
      test_scale_bottom: "Valeur en bas de l'image",
      test_scale_top: "Valeur en haut de l'image",
      test_redigitize: "↻ Recalculer",
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
      test_import_button: "📁 Import a file",
      test_error_import: "Unreadable file — accepted formats: raw sensor .txt (\"Triggered:...\"), JSON ({\"values\":[...]}), or hexadecimal bytes separated by spaces.",
      test_import_image_button: "🖼️ Import a signal image",
      test_image_warning: "⚠️ Approximate extraction from the image — check that the curve below actually matches the signal before classifying.",
      test_error_image: "Could not extract a curve from this image (no line detected on a solid background).",
      test_scale_bottom: "Value at bottom of image",
      test_scale_top: "Value at top of image",
      test_redigitize: "↻ Recompute",
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
  const testImportButton = document.getElementById("testImportButton");
  const testFileInput = document.getElementById("testFileInput");
  const testImportName = document.getElementById("testImportName");
  const testImportImageButton = document.getElementById("testImportImageButton");
  const testImageInput = document.getElementById("testImageInput");
  const testImagePreview = document.getElementById("testImagePreview");
  const testImagePreviewCtx = testImagePreview.getContext("2d");
  const testImagePreviewHint = document.getElementById("testImagePreviewHint");
  const testScaleRow = document.getElementById("testScaleRow");
  const testScaleBottom = document.getElementById("testScaleBottom");
  const testScaleTop = document.getElementById("testScaleTop");
  const testRedigitize = document.getElementById("testRedigitize");
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
  let lastImportedImageData = null; // ImageData de la derniere image importee, pour "Recalculer"

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

  function drawWaveOn(targetCtx, targetCanvas, values, strokeColor) {
    const w = targetCanvas.width, h = targetCanvas.height;
    targetCtx.clearRect(0, 0, w, h);
    if (!values || !values.length) return;

    targetCtx.strokeStyle = "rgba(255,255,255,0.06)";
    targetCtx.lineWidth = 1;
    targetCtx.beginPath();
    targetCtx.moveTo(0, h / 2);
    targetCtx.lineTo(w, h / 2);
    targetCtx.stroke();

    targetCtx.strokeStyle = strokeColor;
    targetCtx.lineWidth = 2;
    targetCtx.beginPath();
    values.forEach((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - (v / 255) * h;
      i === 0 ? targetCtx.moveTo(x, y) : targetCtx.lineTo(x, y);
    });
    targetCtx.stroke();
  }

  function drawWave(values) {
    const isAlert = statusCard.dataset.state === "alert";
    drawWaveOn(ctx, canvas, values, isAlert ? "#e05a4d" : "#8fae5d");
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

  function parseHexTokens(text) {
    const values = text.trim().split(/\s+/).filter(Boolean).map((tok) => parseInt(tok, 16));
    if (!values.length || values.some((v) => Number.isNaN(v))) return null;
    return values;
  }

  function parseImportedFile(text) {
    text = text.trim();
    // Format capture (captures.jsonl) : une ligne JSON {"values": [...], ...}.
    if (text.startsWith("{")) {
      try {
        const obj = JSON.parse(text.split("\n")[0]);
        if (Array.isArray(obj.values) && obj.values.every((v) => typeof v === "number")) {
          return obj.values;
        }
      } catch { /* pas du JSON valide sur la premiere ligne, on essaie les autres formats */ }
    }
    // Format brut du capteur : "Triggered:XX XX XX ..." (comme dans l'archive
    // d'origine et les exports de field_app, voir src/data/parse_raw.py).
    if (text.includes("Triggered:")) {
      const segments = text.split("Triggered:").map((s) => s.trim()).filter(Boolean);
      if (segments.length) return parseHexTokens(segments[segments.length - 1]);
    }
    // Sinon : meme format que le champ de collage manuel (hex separes par des espaces).
    return parseHexTokens(text);
  }

  testImportButton.addEventListener("click", () => testFileInput.click());

  function hideImagePreview() {
    testImagePreview.hidden = true;
    testImagePreviewHint.hidden = true;
    testScaleRow.hidden = true;
  }

  testFileInput.addEventListener("change", async () => {
    const file = testFileInput.files[0];
    testFileInput.value = "";
    if (!file) return;
    testError.textContent = "";
    lastImportedImageData = null;
    hideImagePreview();
    testImportName.textContent = file.name;
    try {
      const text = await file.text();
      const values = parseImportedFile(text);
      if (!values) throw new Error("parse failed");
      testInput.value = values.map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join(" ");
      if (values.length !== 512) {
        testError.textContent = t("test_error_count", { n: values.length });
      }
    } catch {
      testError.textContent = t("test_error_import");
    }
  });

  /**
   * Digitalisation approximative d'une courbe tracee sur fond uni : la
   * couleur de fond est estimee a partir des quatre coins de l'image, puis
   * pour chaque colonne on moyenne la position verticale des pixels qui en
   * different significativement (la trace). Les colonnes sans trace
   * detectee reprennent la derniere valeur connue.
   *
   * Calibration : la valeur est interpolee entre `bottomValue` (bas de
   * l'image) et `topValue` (haut de l'image) — PAS sur l'etendue verticale
   * observee de la trace elle-meme, qui sous-estimerait fortement une
   * ligne de base plate avec un pic isole (verifie empiriquement : erreur
   * moyenne ~120/255 avec l'etendue de la trace, ~0 avec la hauteur totale
   * de l'image, sur un signal de test connu). Par defaut 0-255 (pleine
   * hauteur = plage ADC complete, comme les graphiques generes par ce
   * projet) ; a corriger dans l'UI si l'image source utilise une autre
   * echelle — c'est une estimation a verifier visuellement, pas une
   * lecture exacte.
   */
  function digitizeImageData(imgData, bottomValue = 0, topValue = 255) {
    const { data, width, height } = imgData;
    const at = (x, y) => {
      const i = (y * width + x) * 4;
      return [data[i], data[i + 1], data[i + 2]];
    };
    const corners = [at(0, 0), at(width - 1, 0), at(0, height - 1), at(width - 1, height - 1)];
    const bg = [0, 1, 2].map((c) => Math.round(corners.reduce((s, p) => s + p[c], 0) / 4));
    const dist = (p) => Math.sqrt((p[0] - bg[0]) ** 2 + (p[1] - bg[1]) ** 2 + (p[2] - bg[2]) ** 2);
    const THRESHOLD = 45;

    const rows = new Array(width).fill(null);
    for (let x = 0; x < width; x++) {
      let sum = 0, count = 0;
      for (let y = 0; y < height; y++) {
        if (dist(at(x, y)) > THRESHOLD) { sum += y; count++; }
      }
      if (count) rows[x] = sum / count;
    }

    let last = rows.find((r) => r != null);
    if (last == null) return null; // aucune trace detectee du tout
    for (let x = 0; x < width; x++) {
      if (rows[x] == null) rows[x] = last;
      else last = rows[x];
    }

    const resampled = [];
    for (let i = 0; i < 512; i++) {
      const srcX = Math.min(width - 1, Math.floor((i / 511) * (width - 1)));
      resampled.push(rows[srcX]);
    }

    return resampled.map((r) => {
      const frac = 1 - r / Math.max(1, height - 1); // 0 en bas de l'image, 1 en haut
      const v = bottomValue + frac * (topValue - bottomValue);
      return Math.max(0, Math.min(255, Math.round(v)));
    });
  }

  function runDigitization() {
    if (!lastImportedImageData) return;
    const bottom = Number(testScaleBottom.value) || 0;
    const top = Number(testScaleTop.value) || 0;
    const values = digitizeImageData(lastImportedImageData, bottom, top);
    if (!values) {
      testError.textContent = t("test_error_image");
      hideImagePreview();
      return;
    }
    testError.textContent = "";
    testInput.value = values.map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join(" ");
    testImagePreview.hidden = false;
    testImagePreviewHint.hidden = false;
    testScaleRow.hidden = false;
    drawWaveOn(testImagePreviewCtx, testImagePreview, values, "#d9a441");
  }

  testImportImageButton.addEventListener("click", () => testImageInput.click());

  testImageInput.addEventListener("change", async () => {
    const file = testImageInput.files[0];
    testImageInput.value = "";
    if (!file) return;
    testError.textContent = "";
    testImportName.textContent = file.name;
    try {
      const bitmap = await createImageBitmap(file);
      const off = document.createElement("canvas");
      off.width = bitmap.width;
      off.height = bitmap.height;
      const octx = off.getContext("2d");
      octx.drawImage(bitmap, 0, 0);
      lastImportedImageData = octx.getImageData(0, 0, off.width, off.height);
      runDigitization();
    } catch {
      lastImportedImageData = null;
      testError.textContent = t("test_error_image");
      hideImagePreview();
      testScaleRow.hidden = true;
    }
  });

  testRedigitize.addEventListener("click", runDigitization);

  testSubmit.addEventListener("click", async () => {
    testError.textContent = "";
    const raw = testInput.value.trim();
    if (!raw) return;
    const values = parseHexTokens(raw);
    if (!values) {
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
