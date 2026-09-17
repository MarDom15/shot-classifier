(() => {
  "use strict";

  const conn = document.getElementById("conn");
  const connDot = document.getElementById("connDot");
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

  let lastEntry = null;

  function fmtTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleTimeString();
  }

  function agoLabel(iso) {
    if (!iso) return "";
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (seconds < 5) return "à l'instant";
    if (seconds < 60) return `il y a ${seconds}s`;
    const minutes = Math.round(seconds / 60);
    return `il y a ${minutes} min`;
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

  function setConnState(state, label) {
    conn.dataset.state = state;
    connLabel.textContent = label;
  }

  function applyEntry(entry, { fromHistory = false } = {}) {
    lastEntry = entry;
    const s = entry.summary;

    if (s.is_shot) {
      statusCard.dataset.state = "alert";
      statusIcon.textContent = "⚠";
      const weapon = s.weapon ? s.weapon : "arme inconnue";
      statusHeadline.textContent = `TIR DÉTECTÉ — ${weapon}`;
      const conf = s.weapon_confidence != null ? ` (${Math.round(s.weapon_confidence * 100)}% de confiance)` : "";
      statusDetail.textContent = `Modèle étage 1 : ${s.stage1_model} · Modèle étage 2 : ${s.stage2_model || "—"}${conf}`;
    } else {
      statusCard.dataset.state = "clear";
      statusIcon.textContent = "✓";
      statusHeadline.textContent = "AUCUNE MENACE";
      statusDetail.textContent = `Impact non balistique — modèle étage 1 : ${s.stage1_model}`;
    }
    statusTime.textContent = `${fmtTime(entry.received_at)} · ${agoLabel(entry.received_at)}`;

    drawWave(entry.values);

    if (!fromHistory) prependHistoryRow(entry);
  }

  function prependHistoryRow(entry) {
    const emptyRow = historyBody.querySelector(".empty-row");
    if (emptyRow) emptyRow.remove();

    const s = entry.summary;
    const tr = document.createElement("tr");
    if (s.is_shot) tr.classList.add("row-alert");
    const conf = s.weapon_confidence != null ? `${Math.round(s.weapon_confidence * 100)}%` : "—";
    tr.innerHTML = `
      <td>${fmtTime(entry.received_at)}</td>
      <td>${entry.sensor_id || "—"}</td>
      <td>${s.is_shot ? "🔫 Tir" : "🪨 Non-tir"}</td>
      <td>${s.weapon || "—"}</td>
      <td>${conf}</td>
    `;
    historyBody.prepend(tr);
    while (historyBody.children.length > 50) {
      historyBody.removeChild(historyBody.lastChild);
    }
  }

  function renderHistory(entries) {
    historyBody.innerHTML = "";
    if (!entries.length) {
      historyBody.innerHTML = '<tr class="empty-row"><td colspan="5">Aucun évènement pour l\'instant.</td></tr>';
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

    ws.onopen = () => setConnState("online", "Connecté au poste");
    ws.onclose = () => {
      setConnState("offline", "Connexion perdue — reconnexion...");
      setTimeout(connectWS, 2000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "history") {
        renderHistory(msg.payload);
      } else if (msg.type === "result") {
        applyEntry(msg.payload);
      }
    };
  }

  testToggle.addEventListener("click", () => {
    testBody.hidden = !testBody.hidden;
    testToggle.textContent = testBody.hidden ? "🧪 Test manuel (sans capteur) ▾" : "🧪 Test manuel (sans capteur) ▴";
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
      testError.textContent = "Format invalide : octets hexadécimaux séparés par des espaces.";
      return;
    }
    if (values.length !== 512) {
      testError.textContent = `512 valeurs attendues, ${values.length} fournies.`;
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
        testError.textContent = body.detail || `Erreur serveur (${res.status})`;
      }
    } catch (e) {
      testError.textContent = "Impossible de contacter le serveur local.";
    } finally {
      testSubmit.disabled = false;
    }
  });

  connectWS();
})();
