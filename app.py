import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SCOPES         = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SHEET_NAME     = os.environ.get('SHEET_NAME', 'Fallas')

# ── HTML embebido ──────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reporte de Fallas · Historial</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet" />
  <style>
    :root {
      --primary: #1a3c5e;
      --accent: #e84545;
      --light-bg: #f4f7fb;
    }
    body {
      background-color: var(--light-bg);
      font-family: 'Segoe UI', sans-serif;
      min-height: 100vh;
      padding-bottom: 20px;
    }
    .app-header {
      background: linear-gradient(135deg, var(--primary), #2a5f8f);
      color: white;
      padding: 1.2rem 1rem 1rem;
      text-align: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .app-header h1 { font-size: 1.4rem; font-weight: 700; margin: 0; }
    .app-header p  { font-size: .8rem; margin: .2rem 0 0; opacity: .8; }
    .card { border: none; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
    .form-label { font-weight: 600; font-size: .85rem; color: var(--primary); margin-bottom: .2rem; }
    .form-control, .form-select {
      border-radius: 10px; border: 1.5px solid #dce3ef; font-size: .95rem;
    }
    .form-control:focus, .form-select:focus {
      border-color: #2a5f8f; box-shadow: 0 0 0 3px rgba(42,95,143,.12);
    }
    .btn-submit {
      background: linear-gradient(135deg, var(--accent), #c0392b);
      border: none; border-radius: 12px; font-weight: 700; padding: .7rem;
    }
    .section-badge {
      display: inline-block; background: var(--primary); color: white;
      border-radius: 6px; font-size: .7rem; font-weight: 700;
      padding: 2px 8px; margin-bottom: .5rem; text-transform: uppercase;
    }
    #customFallaWrapper { display: none; }
    .historial-item {
      background: white; border-radius: 12px; padding: 10px 14px;
      margin-bottom: 10px; border-left: 5px solid var(--accent);
      box-shadow: 0 2px 6px rgba(0,0,0,.05); font-size: .9rem;
    }
    .linea-superior {
      display: flex; gap: 12px; font-weight: 600;
      color: var(--primary); flex-wrap: wrap;
    }
    .linea-inferior {
      display: flex; gap: 12px; color: #2c3e50;
      flex-wrap: wrap; align-items: baseline;
    }
    .badge-falla {
      background: #eef2f6; padding: 2px 8px; border-radius: 20px;
      font-size: .75rem; font-weight: 600; color: var(--primary);
    }
    .fecha-hora {
      font-family: 'Courier New', monospace; background: #f0f3f8;
      padding: 2px 6px; border-radius: 8px; font-size: .75rem;
    }
    /* Toast */
    .toast-container {
      position: fixed; top: 1rem; left: 50%; transform: translateX(-50%);
      z-index: 9999; width: 90%; max-width: 420px;
    }
    /* Botón spinner */
    #btnSpinner { display: none; }
    .btn-submit:active { transform: scale(.97); }
  </style>
</head>
<body>

<div class="app-header">
  <h1><i class="bi bi-exclamation-triangle-fill me-2"></i>Reporte de Fallas</h1>
  <p>Registro + historial en Google Sheets</p>
</div>

<div class="container py-2 px-3" style="max-width:560px;">

  <!-- Toast de éxito / error -->
  <div class="toast-container">
    <div id="toast" class="toast align-items-center border-0" role="alert" data-bs-autohide="true" data-bs-delay="4500">
      <div class="d-flex">
        <div class="toast-body fw-semibold" id="toastMsg"></div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>
  </div>

  <!-- Formulario de captura -->
  <div class="card p-3 mb-4">
    <form id="faultForm" novalidate>

      <span class="section-badge"><i class="bi bi-pencil-fill me-1"></i>Nueva falla</span>

      <!-- Tipo falla -->
      <div class="mb-2">
        <label class="form-label">Tipo de falla</label>
        <select class="form-select" id="tipo_falla" required>
          <option value="" disabled selected>— Seleccionar —</option>
          <option>Missing</option>
          <option>Extra Addr</option>
          <option>Fault</option>
          <option>Extra Addr No Device</option>
          <option>WRONG TYPE</option>
          <option>NODE MSNG</option>
          <option>NETWK FLT</option>
          <option>Otros</option>
        </select>
        <div id="customFallaWrapper" class="mt-2">
          <input type="text" class="form-control" id="falla_custom"
            placeholder="Especificar falla..." maxlength="100" />
        </div>
      </div>

      <!-- Dispositivo -->
      <div class="mb-2">
        <label class="form-label">Dispositivo</label>
        <select class="form-select" id="dispositivo" required>
          <option value="" disabled selected>— Seleccionar —</option>
          <option>Photo Detector</option>
          <option>Photo/Heat Detector</option>
          <option>Manual Stations</option>
          <option>Nac Aom NS</option>
          <option>FORM C AOM NS</option>
          <option>Supervisory Sw</option>
          <option>Waterflow Sil</option>
          <option>N.O. Contacts</option>
          <option>Trbl Ack Sw</option>
        </select>
      </div>

      <!-- Sitio y Nodo -->
      <div class="row g-2 mb-2">
        <div class="col-7">
          <label class="form-label">Sitio</label>
          <input type="text" class="form-control" id="sitio"
            placeholder="Ej: Edificio Central" maxlength="80" required />
        </div>
        <div class="col-5">
          <label class="form-label">Nodo (1-64)</label>
          <input type="number" class="form-control" id="nodo"
            placeholder="01" min="1" max="64" required />
        </div>
      </div>

      <!-- Laso y Fecha + Hora -->
      <div class="row g-2 mb-3">
        <div class="col-4">
          <label class="form-label">Laso</label>
          <div class="d-flex gap-3 mt-1">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="laso" id="lasoL1" value="L1" required />
              <label class="form-check-label fw-semibold" for="lasoL1">L1</label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="laso" id="lasoL2" value="L2" />
              <label class="form-check-label fw-semibold" for="lasoL2">L2</label>
            </div>
          </div>
        </div>
        <div class="col-8">
          <label class="form-label">Fecha y hora</label>
          <input type="datetime-local" class="form-control" id="fecha_hora" required />
        </div>
      </div>

      <button type="submit" class="btn btn-submit btn-danger w-100 text-white">
        <span id="btnText"><i class="bi bi-send-fill me-2"></i>Agregar al historial</span>
        <span id="btnSpinner">
          <span class="spinner-border spinner-border-sm me-2"></span>Guardando...
        </span>
      </button>
    </form>
  </div>

  <!-- Historial local (renderizado desde localStorage) -->
  <div class="card p-3">
    <div class="d-flex justify-content-between align-items-center mb-2">
      <span class="section-badge"><i class="bi bi-clock-history me-1"></i>Últimas fallas</span>
      <span class="text-muted small" id="contadorFallas">0 registros</span>
    </div>
    <div id="historialContainer">
      <p class="text-muted text-center small py-3">Aún no hay fallas registradas</p>
    </div>
  </div>

  <p class="text-center text-muted mt-2" style="font-size:.7rem;">
    <i class="bi bi-shield-check me-1"></i>Datos guardados en Google Sheets
  </p>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
(function () {
  // Elementos
  const tipoFalla   = document.getElementById('tipo_falla');
  const customWrap  = document.getElementById('customFallaWrapper');
  const fallaCustom = document.getElementById('falla_custom');
  const form        = document.getElementById('faultForm');
  const sitioEl     = document.getElementById('sitio');
  const nodoEl      = document.getElementById('nodo');
  const disposEl    = document.getElementById('dispositivo');
  const lasoRadios  = document.getElementsByName('laso');
  const fechaHoraEl = document.getElementById('fecha_hora');
  const histCont    = document.getElementById('historialContainer');
  const contador    = document.getElementById('contadorFallas');
  const btnText     = document.getElementById('btnText');
  const btnSpinner  = document.getElementById('btnSpinner');

  let fallas = [];

  // ── Historial local ──────────────────────────────────────────────────────────
  function cargarFallas() {
    try { fallas = JSON.parse(localStorage.getItem('fallasReporte') || '[]'); }
    catch { fallas = []; }
    renderizarHistorial();
  }

  function guardarLocal(f) {
    fallas.push(f);
    localStorage.setItem('fallasReporte', JSON.stringify(fallas));
    renderizarHistorial();
  }

  function formatearFechaHora(str) {
    if (!str) return '—';
    const [fecha, hora] = str.split('T');
    const [yyyy, mm, dd] = fecha.split('-');
    return `${dd}/${mm}/${yyyy.slice(2)} ${hora}`;
  }

  function renderizarHistorial() {
    if (!fallas.length) {
      histCont.innerHTML = '<p class="text-muted text-center small py-3">Aún no hay fallas registradas</p>';
      contador.innerText = '0 registros';
      return;
    }
    const ordenadas = [...fallas].sort((a,b) => b.fechaHora.localeCompare(a.fechaHora));
    histCont.innerHTML = ordenadas.map(f => {
      const tipo = f.tipoFalla === 'Otros' ? f.fallaCustom : f.tipoFalla;
      return `
        <div class="historial-item">
          <div class="linea-superior">
            <span><i class="bi bi-hdd-stack-fill me-1"></i>Nodo ${String(f.nodo).padStart(2,'0')}</span>
            <span><i class="bi bi-geo-alt-fill me-1"></i>${f.sitio}</span>
          </div>
          <div class="linea-inferior mt-1">
            <span class="badge-falla">${tipo}</span>
            <span>${f.dispositivo}</span>
            <span>${f.laso}</span>
            <span class="fecha-hora"><i class="bi bi-clock me-1"></i>${formatearFechaHora(f.fechaHora)}</span>
          </div>
        </div>`;
    }).join('');
    contador.innerText = `${fallas.length} ${fallas.length === 1 ? 'registro' : 'registros'}`;
  }

  // ── Toast ────────────────────────────────────────────────────────────────────
  function showToast(msg, success) {
    const el = document.getElementById('toast');
    el.classList.remove('bg-success','bg-danger','text-white');
    el.classList.add(success ? 'bg-success' : 'bg-danger', 'text-white');
    document.getElementById('toastMsg').textContent = msg;
    new bootstrap.Toast(el).show();
  }

  // ── Fecha/hora ahora ─────────────────────────────────────────────────────────
  function setNow() {
    const now    = new Date();
    const offset = now.getTimezoneOffset() * 60000;
    const local  = new Date(now - offset);
    fechaHoraEl.value = local.toISOString().slice(0,16);
  }

  // ── Mostrar/ocultar campo Otros ──────────────────────────────────────────────
  tipoFalla.addEventListener('change', () => {
    const es = tipoFalla.value === 'Otros';
    customWrap.style.display = es ? 'block' : 'none';
    fallaCustom.required = es;
    if (!es) fallaCustom.value = '';
  });

  // ── Submit ───────────────────────────────────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Validaciones
    if (!tipoFalla.value)               { alert('Selecciona tipo de falla'); return; }
    if (!disposEl.value)                { alert('Selecciona dispositivo'); return; }
    if (!sitioEl.value.trim())          { alert('Sitio es obligatorio'); return; }
    if (!nodoEl.value || nodoEl.value < 1 || nodoEl.value > 64) { alert('Nodo debe ser entre 1 y 64'); return; }
    if (!fechaHoraEl.value)             { alert('Selecciona fecha y hora'); return; }

    let lasoSel = null;
    for (let r of lasoRadios) { if (r.checked) { lasoSel = r.value; break; } }
    if (!lasoSel) { alert('Selecciona L1 o L2'); return; }

    if (tipoFalla.value === 'Otros' && !fallaCustom.value.trim()) {
      alert('Especifica el tipo de falla'); return;
    }

    // Armar objeto
    const registro = {
      tipoFalla:   tipoFalla.value,
      fallaCustom: fallaCustom.value.trim(),
      dispositivo: disposEl.value,
      sitio:       sitioEl.value.trim(),
      nodo:        parseInt(nodoEl.value, 10),
      laso:        lasoSel,
      fechaHora:   fechaHoraEl.value
    };

    // Spinner ON
    btnText.style.display    = 'none';
    btnSpinner.style.display = 'inline';

    try {
      // Enviar a Flask → Google Sheets
      const fd = new FormData();
      Object.entries(registro).forEach(([k,v]) => fd.append(k, v));
      const res  = await fetch('/submit', { method: 'POST', body: fd });
      const data = await res.json();

      showToast(data.message, data.success);

      if (data.success) {
        guardarLocal(registro);   // también en localStorage para el historial
        form.reset();
        customWrap.style.display = 'none';
        setNow();
      }
    } catch {
      showToast('Error de conexión. Intenta de nuevo.', false);
    } finally {
      btnText.style.display    = 'inline';
      btnSpinner.style.display = 'none';
    }
  });

  // ── Init ─────────────────────────────────────────────────────────────────────
  cargarFallas();
  setNow();
})();
</script>
</body>
</html>"""


# ── Google Sheets ──────────────────────────────────────────────────────────────

def get_sheets_service():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON no está configurado en .env")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(creds_json), scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)


def ensure_header(sheet):
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A1:G1'
    ).execute()
    if not result.get('values'):
        headers = [['Fecha/Hora Evento', 'Tipo de Falla', 'Falla Personalizada',
                     'Dispositivo Afectado', 'Sitio', 'Nodo', 'Laso']]
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A1',
            valueInputOption='RAW',
            body={'values': headers}
        ).execute()


def append_to_sheet(data):
    service = get_sheets_service()
    sheet   = service.spreadsheets()
    ensure_header(sheet)
    row = [[
        data['fecha_hora'],
        data['tipo_falla'],
        data.get('falla_custom', ''),
        data['dispositivo'],
        data['sitio'],
        data['nodo'],
        data['laso'],
    ]]
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f'{SHEET_NAME}!A1',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body={'values': row}
    ).execute()


# ── Rutas Flask ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return HTML


@app.route('/submit', methods=['POST'])
def submit():
    try:
        tipo_falla   = request.form.get('tipoFalla',   '').strip()
        falla_custom = request.form.get('fallaCustom', '').strip()
        dispositivo  = request.form.get('dispositivo', '').strip()
        sitio        = request.form.get('sitio',       '').strip()
        nodo         = request.form.get('nodo',        '').strip()
        laso         = request.form.get('laso',        '').strip()
        fecha_hora   = request.form.get('fechaHora',   '').strip()

        # Validaciones
        if not all([tipo_falla, dispositivo, sitio, nodo, laso, fecha_hora]):
            return jsonify({'success': False, 'message': 'Todos los campos son obligatorios.'}), 400

        if tipo_falla == 'Otros' and not falla_custom:
            return jsonify({'success': False, 'message': 'Especifica el tipo de falla personalizado.'}), 400

        nodo_int = int(nodo)
        if not (1 <= nodo_int <= 64):
            return jsonify({'success': False, 'message': 'El nodo debe estar entre 01 y 64.'}), 400

        # Formatear fecha: "2025-06-10T14:30" → "10/06/2025 14:30"
        dt = datetime.fromisoformat(fecha_hora)
        fecha_formateada = dt.strftime('%d/%m/%Y %H:%M')

        tipo_final = tipo_falla if tipo_falla != 'Otros' else f'Otros: {falla_custom}'

        data = {
            'fecha_hora':   fecha_formateada,
            'tipo_falla':   tipo_final,
            'falla_custom': falla_custom,
            'dispositivo':  dispositivo,
            'sitio':        sitio,
            'nodo':         str(nodo_int).zfill(2),
            'laso':         laso,
        }

        append_to_sheet(data)
        return jsonify({'success': True, 'message': '✅ Falla registrada en Google Sheets.'})

    except ValueError as ve:
        return jsonify({'success': False, 'message': f'Error de validación: {ve}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al guardar: {e}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
