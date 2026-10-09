const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = {
  job: 'single',
  voiceMode: 'clone',
  voices: [],
  objectUrls: [],
};

const defaults = {
  duration: '', speed: '1.00', steps: '32', guidance: '2.0', tShift: '0.10',
  positionTemperature: '5.0', classTemperature: '0.0', layerPenalty: '5.0',
  padding: '0.10', fade: '0.10', chunkDuration: '15', chunkThreshold: '30',
};

function showError(message = '') {
  $('#error').textContent = message;
  $('#error').hidden = !message;
}

function setBusy(busy, label = 'Ejecutar generación') {
  $('#generate').disabled = busy;
  $('#generate span').textContent = busy ? 'Procesando…' : label;
}

function numberValue(id) {
  const value = $(`#${id}`).value.trim();
  return value === '' ? null : Number(value);
}

function pronunciationMap() {
  const dictionary = {};
  $$('.dictionary-row').forEach((row) => {
    const written = row.querySelector('.written').value.trim();
    const spoken = row.querySelector('.spoken').value.trim();
    if (written && spoken) dictionary[written] = spoken;
  });
  return dictionary;
}

function buildBasePayload(text = $('#text').value.trim()) {
  return {
    text,
    language: $('#language').value.trim() || null,
    voice_mode: state.voiceMode,
    voice_id: state.voiceMode === 'clone' ? ($('#voice').value || null) : null,
    instruct: $('#instruct').value.trim() || null,
    pronunciation_profile: $('#latamProfile').checked ? 'es-latam-tech' : 'none',
    custom_pronunciations: pronunciationMap(),
    normalize_text: $('#normalize').checked,
    num_step: numberValue('steps'),
    speed: numberValue('speed'),
    duration: numberValue('duration'),
    guidance_scale: numberValue('guidance'),
    t_shift: numberValue('tShift'),
    position_temperature: numberValue('positionTemperature'),
    class_temperature: numberValue('classTemperature'),
    layer_penalty_factor: numberValue('layerPenalty'),
    denoise: $('#denoise').checked,
    preprocess_prompt: $('#preprocess').checked,
    postprocess_output: $('#postprocess').checked,
    pad_duration: numberValue('padding'),
    fade_duration: numberValue('fade'),
    audio_chunk_duration: numberValue('chunkDuration'),
    audio_chunk_threshold: numberValue('chunkThreshold'),
    format: $('#format').value,
  };
}

function batchTexts() {
  return $('#text').value
    .split(/\n\s*---+\s*\n/g)
    .map((text) => text.trim())
    .filter(Boolean);
}

function updatePreview() {
  try {
    const payload = buildBasePayload(state.job === 'batch' ? batchTexts()[0] || '' : $('#text').value.trim());
    $('#jsonPreview').textContent = JSON.stringify(
      state.job === 'batch' ? { items: batchTexts().map((text) => ({ ...payload, text })) } : payload,
      null,
      2,
    );
  } catch (_) {
    $('#jsonPreview').textContent = '{}';
  }
  $('#charCount').textContent = `${$('#text').value.length.toLocaleString('es-PR')} caracteres`;
}

function addPronunciation(written = '', spoken = '') {
  const row = document.createElement('div');
  row.className = 'dictionary-row';
  const writtenInput = document.createElement('input');
  writtenInput.className = 'written';
  writtenInput.placeholder = 'Texto escrito';
  writtenInput.setAttribute('aria-label', 'Texto escrito');
  writtenInput.value = written;
  const arrow = document.createElement('span');
  arrow.setAttribute('aria-hidden', 'true');
  arrow.textContent = '→';
  const spokenInput = document.createElement('input');
  spokenInput.className = 'spoken';
  spokenInput.placeholder = 'Cómo debe sonar';
  spokenInput.setAttribute('aria-label', 'Pronunciación');
  spokenInput.value = spoken;
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'remove-term';
  remove.setAttribute('aria-label', 'Eliminar término');
  remove.textContent = '×';
  remove.addEventListener('click', () => { row.remove(); updatePreview(); });
  [writtenInput, spokenInput].forEach((input) => input.addEventListener('input', updatePreview));
  row.append(writtenInput, arrow, spokenInput, remove);
  $('#dictionary').append(row);
  writtenInput.focus();
}

function selectVoiceMode(mode) {
  state.voiceMode = mode;
  $$('#voiceMode button').forEach((button) => button.classList.toggle('active', button.dataset.mode === mode));
  $('#voiceField').hidden = mode !== 'clone';
  updatePreview();
}

function selectJob(job) {
  state.job = job;
  $$('#jobMode button').forEach((button) => button.classList.toggle('active', button.dataset.job === job));
  const batch = job === 'batch';
  $('#scriptLabel').textContent = batch ? 'Guiones del lote' : 'Guion';
  $('#scriptHint').textContent = batch
    ? 'Separa cada pieza con una línea que contenga ---. Máximo 20 piezas por lote.'
    : 'Puedes incluir pausas, puntuación expresiva y marcadores no verbales compatibles.';
  if (batch && !$('#text').value.includes('\n---\n')) {
    $('#text').value = `${$('#text').value.trim()}\n---\nSegunda pieza del lote.`;
  }
  updatePreview();
}

async function loadHealth() {
  try {
    const response = await fetch('/health');
    if (!response.ok) throw new Error();
    const health = await response.json();
    $('#serviceState').classList.add('ready');
    $('#serviceState b').textContent = `${health.engine} · activo`;
  } catch (_) {
    $('#serviceState').classList.remove('ready');
    $('#serviceState b').textContent = 'Sin conexión';
  }
}

function renderVoices() {
  const select = $('#voice');
  const list = $('#voiceList');
  select.replaceChildren();
  list.replaceChildren();
  if (!state.voices.length) {
    select.append(new Option('No hay voces registradas', ''));
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = 'Clona la primera voz desde este laboratorio.';
    list.append(empty);
    return;
  }
  const saved = localStorage.getItem('omnivoice-pro-voice');
  state.voices.forEach((voice, index) => {
    const label = voice.label || voice.voice_id;
    select.append(new Option(label, voice.voice_id));
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'voice-item';
    button.dataset.voiceId = voice.voice_id;
    const title = document.createElement('strong');
    title.textContent = label;
    const id = document.createElement('small');
    id.textContent = voice.voice_id;
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = voice.cached ? 'En memoria' : (voice.ref_audio_exists ? 'Disponible' : 'Referencia ausente');
    button.append(title, id, badge);
    button.addEventListener('click', () => {
      select.value = voice.voice_id;
      selectVoiceMode('clone');
      localStorage.setItem('omnivoice-pro-voice', voice.voice_id);
      $$('.voice-item').forEach((item) => item.classList.toggle('selected', item.dataset.voiceId === voice.voice_id));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    list.append(button);
    if ((saved && saved === voice.voice_id) || (!saved && index === 0)) select.value = voice.voice_id;
  });
  $('#voiceCount').textContent = `${state.voices.length} voces`;
  updatePreview();
}

async function loadVoices() {
  try {
    const response = await fetch('/v1/voices');
    if (!response.ok) throw new Error('No se pudo cargar la biblioteca');
    state.voices = (await response.json()).voices || [];
    renderVoices();
  } catch (error) {
    $('#voiceList').textContent = error.message;
  }
}

async function previewText() {
  const text = state.job === 'batch' ? batchTexts()[0] : $('#text').value.trim();
  if (!text) return;
  const response = await fetch('/v1/text/prepare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      pronunciation_profile: $('#latamProfile').checked ? 'es-latam-tech' : 'none',
      custom_pronunciations: pronunciationMap(),
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'No se pudo preparar el texto');
  $('#preparedText').textContent = data.prepared_text;
  $('#preparedText').hidden = false;
  $('#replacementCount').textContent = `${data.replacements} reemplazos`;
}

function audioBlob(base64, encoding) {
  const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: encoding === 'wav' ? 'audio/wav' : 'application/octet-stream' });
}

function clearResults() {
  state.objectUrls.forEach((url) => URL.revokeObjectURL(url));
  state.objectUrls = [];
  $('#resultList').replaceChildren();
}

function renderResults(items, elapsed) {
  clearResults();
  items.forEach((item, index) => {
    const blob = audioBlob(item.audio_base64, item.encoding);
    const url = URL.createObjectURL(blob);
    state.objectUrls.push(url);
    const row = document.createElement('article');
    row.className = 'result-item';
    const number = document.createElement('span');
    number.className = 'result-number';
    number.textContent = String(index + 1).padStart(2, '0');
    const meta = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = item.voice_id || state.voiceMode;
    const detail = document.createElement('small');
    detail.textContent = `${item.duration_seconds.toFixed(2)} s · RTF ${item.metrics.rtf.toFixed(3)} · ${item.encoding.toUpperCase()}`;
    meta.append(title, detail);
    let media;
    if (item.encoding === 'wav') {
      media = document.createElement('audio');
      media.controls = true;
      media.src = url;
    } else {
      media = document.createElement('span');
      media.className = 'muted';
      media.textContent = 'PCM16 disponible para descarga';
    }
    const download = document.createElement('a');
    download.className = 'download';
    download.href = url;
    download.download = `omnivoice-pro-${String(index + 1).padStart(2, '0')}.${item.encoding === 'wav' ? 'wav' : 'pcm16'}`;
    download.textContent = 'Descargar';
    row.append(number, meta, media, download);
    $('#resultList').append(row);
  });
  $('#runMeta').textContent = `${items.length} salida${items.length === 1 ? '' : 's'} · ${elapsed.toFixed(1)} s total`;
  $('#results').hidden = false;
  $('#results').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function generate() {
  showError();
  const texts = state.job === 'batch' ? batchTexts() : [$('#text').value.trim()];
  if (!texts[0]) return showError('Escribe al menos un guion.');
  if (texts.length > 20) return showError('El lote admite un máximo de 20 piezas.');
  if (state.voiceMode === 'clone' && !$('#voice').value) return showError('Selecciona o clona una voz.');
  setBusy(true);
  const started = performance.now();
  try {
    const base = buildBasePayload(texts[0]);
    const batch = state.job === 'batch';
    const url = batch ? '/v1/tts/batch' : '/v1/tts';
    const body = batch ? { items: texts.map((text) => ({ ...base, text })) } : base;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Falló la generación');
    renderResults(batch ? data.items : [data], (performance.now() - started) / 1000);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function cloneVoice(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = event.submitter;
  const status = $('#cloneStatus');
  button.disabled = true;
  button.textContent = 'Transcribiendo y clonando…';
  status.textContent = '';
  try {
    const response = await fetch('/v1/voices/clone-cache', { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'No se pudo clonar la voz');
    status.textContent = `${data.voice_id} está lista. Transcripción: ${data.ref_text || 'ASR completado'}`;
    await loadVoices();
    $('#voice').value = data.voice_id;
    selectVoiceMode('clone');
    form.reset();
    form.querySelector('[name=language]').value = 'Spanish';
    $('#fileName').textContent = 'WAV, MP3, M4A, OGG, FLAC o AAC';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Crear y precargar voz';
  }
}

function resetControls() {
  Object.entries(defaults).forEach(([id, value]) => { $(`#${id}`).value = value; });
  $('#preprocess').checked = true;
  $('#postprocess').checked = true;
  $('#denoise').checked = true;
  $('#normalize').checked = true;
  $('#language').value = 'Spanish';
  $('#format').value = 'wav';
  selectVoiceMode('clone');
  updatePreview();
}

$('#addPronunciation').addEventListener('click', () => addPronunciation());
$('#previewText').addEventListener('click', () => previewText().catch((error) => showError(error.message)));
$('#generate').addEventListener('click', generate);
$('#resetControls').addEventListener('click', resetControls);
$('#refreshVoices').addEventListener('click', loadVoices);
$('#cloneForm').addEventListener('submit', cloneVoice);
$('#cloneForm [name=ref_audio]').addEventListener('change', (event) => {
  $('#fileName').textContent = event.target.files[0]?.name || 'WAV, MP3, M4A, OGG, FLAC o AAC';
});
$('#voice').addEventListener('change', () => {
  localStorage.setItem('omnivoice-pro-voice', $('#voice').value);
  updatePreview();
});
$$('#jobMode button').forEach((button) => button.addEventListener('click', () => selectJob(button.dataset.job)));
$$('#voiceMode button').forEach((button) => button.addEventListener('click', () => selectVoiceMode(button.dataset.mode)));
$$('input, select, textarea').forEach((input) => input.addEventListener('input', updatePreview));
$$('.dictionary-row input').forEach((input) => input.addEventListener('input', updatePreview));
$$('.remove-term').forEach((button) => button.addEventListener('click', () => { button.closest('.dictionary-row').remove(); updatePreview(); }));

updatePreview();
loadHealth();
loadVoices();
setInterval(loadHealth, 30000);
