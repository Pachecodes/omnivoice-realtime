const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = { mode: 'clone', voices: [], audioUrl: null };
const presets = {
  natural: { speed: 1.08, instruct: 'female, young adult, moderate pitch', padding: 0.05, fade: 0.05 },
  promo: { speed: 1.14, instruct: 'female, young adult, moderate pitch', padding: 0.02, fade: 0.04 },
  calm: { speed: 0.96, instruct: 'female, young adult, moderate pitch', padding: 0.08, fade: 0.08 },
};

function setBusy(busy) {
  const button = $('#generate');
  button.disabled = busy;
  button.querySelector('span').textContent = busy ? 'Generando…' : 'Generar audio';
}

function showError(message = '') {
  const target = $('#error');
  target.textContent = message;
  target.hidden = !message;
}

function updateSpeed() {
  const input = $('#speed');
  const min = Number(input.min);
  const max = Number(input.max);
  const value = Number(input.value);
  const progress = ((value - min) / (max - min)) * 100;
  input.style.background = `linear-gradient(90deg, var(--blue) ${progress}%, #2b384a ${progress}%)`;
  $('#speedValue').textContent = `${value.toFixed(2)}×`;
}

function setMode(mode) {
  state.mode = mode;
  $$('.mode').forEach((button) => button.classList.toggle('active', button.dataset.mode === mode));
  $('#voiceField').hidden = mode !== 'clone';
  $('#instruct').closest('.field').hidden = mode === 'auto';
}

function applyPreset(name) {
  const preset = presets[name];
  if (!preset) return;
  $('#speed').value = preset.speed;
  $('#instruct').value = preset.instruct;
  $('#padding').value = preset.padding;
  $('#fade').value = preset.fade;
  updateSpeed();
  $$('.preset').forEach((button) => button.classList.toggle('active', button.dataset.preset === name));
}

async function checkHealth() {
  const badge = $('#serviceState');
  try {
    const response = await fetch('/health');
    if (!response.ok) throw new Error('Servicio no disponible');
    const data = await response.json();
    badge.classList.toggle('ready', Boolean(data.ready));
    badge.querySelector('b').textContent = data.ready ? `Activo · ${data.engine}` : 'Cargando modelo';
  } catch (error) {
    badge.classList.remove('ready');
    badge.querySelector('b').textContent = 'Sin conexión';
  }
}

function renderVoices() {
  const select = $('#voice');
  const grid = $('#voiceGrid');
  select.replaceChildren();
  grid.replaceChildren();

  if (!state.voices.length) {
    const option = new Option('No hay voces registradas', '');
    select.add(option);
    const empty = document.createElement('p');
    empty.className = 'muted';
    empty.textContent = 'Clona la primera voz para comenzar.';
    grid.append(empty);
    return;
  }

  state.voices.forEach((voice) => {
    select.add(new Option(voice.label || voice.voice_id, voice.voice_id));
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'voice-card';
    const name = document.createElement('strong');
    name.textContent = voice.label || voice.voice_id;
    const id = document.createElement('small');
    id.textContent = voice.voice_id;
    const cache = document.createElement('span');
    cache.className = 'cache';
    cache.textContent = voice.cached ? 'Lista en memoria' : 'Disponible';
    card.append(name, id, cache);
    card.addEventListener('click', () => {
      select.value = voice.voice_id;
      setMode('clone');
      window.scrollTo({ top: $('.workspace').offsetTop - 18, behavior: 'smooth' });
    });
    grid.append(card);
  });

  const saved = localStorage.getItem('omnivoice.voice');
  if (saved && state.voices.some((voice) => voice.voice_id === saved)) select.value = saved;
}

async function loadVoices() {
  try {
    const response = await fetch('/v1/voices');
    if (!response.ok) throw new Error('No se pudo cargar la biblioteca');
    const data = await response.json();
    state.voices = data.voices || [];
    renderVoices();
  } catch (error) {
    $('#voiceGrid').textContent = error.message;
  }
}

async function prepareText() {
  const response = await fetch('/v1/text/prepare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: $('#text').value,
      pronunciation_profile: $('#pronunciation').checked ? 'es-latam-tech' : 'none',
    }),
  });
  if (!response.ok) throw new Error('No se pudo preparar la pronunciación');
  return response.json();
}

async function generate() {
  showError();
  const text = $('#text').value.trim();
  if (!text) return showError('Escribe un guion antes de generar.');
  const voiceId = $('#voice').value;
  if (state.mode === 'clone' && !voiceId) return showError('Selecciona o registra una voz.');

  setBusy(true);
  try {
    localStorage.setItem('omnivoice.voice', voiceId);
    const payload = {
      text,
      language: 'Spanish',
      voice_mode: state.mode,
      voice_id: state.mode === 'clone' ? voiceId : null,
      instruct: state.mode === 'auto' ? null : ($('#instruct').value.trim() || null),
      pronunciation_profile: $('#pronunciation').checked ? 'es-latam-tech' : 'none',
      normalize_text: $('#normalize').checked,
      num_step: Number($('#steps').value),
      speed: Number($('#speed').value),
      guidance_scale: Number($('#guidance').value),
      pad_duration: Number($('#padding').value),
      fade_duration: Number($('#fade').value),
      format: 'wav',
    };
    const started = performance.now();
    const response = await fetch('/v1/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'No se pudo generar el audio');

    const binary = atob(data.audio_base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
    state.audioUrl = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }));
    $('#audio').src = state.audioUrl;
    $('#download').href = state.audioUrl;
    $('#output').hidden = false;
    const elapsed = ((performance.now() - started) / 1000).toFixed(1);
    $('#metrics').textContent = `${data.duration_seconds.toFixed(1)} s de audio · generado en ${elapsed} s · ${data.voice_id || state.mode}`;
    $('#output').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    $('#audio').play().catch(() => {});
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function registerVoice(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const status = $('#cloneStatus');
  const button = form.querySelector('button[type="submit"]');
  status.textContent = 'Transcribiendo y clonando…';
  button.disabled = true;
  try {
    const response = await fetch('/v1/voices/clone-cache', { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'No se pudo registrar la voz');
    status.textContent = `Voz ${data.voice_id} registrada. Transcripción: ${data.ref_text || 'ASR completado'}`;
    form.reset();
    await loadVoices();
    $('#voice').value = data.voice_id;
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

$('#text').addEventListener('input', () => { $('#charCount').textContent = `${$('#text').value.length} caracteres`; });
$('#speed').addEventListener('input', updateSpeed);
$('#voice').addEventListener('change', (event) => localStorage.setItem('omnivoice.voice', event.target.value));
$$('.mode').forEach((button) => button.addEventListener('click', () => setMode(button.dataset.mode)));
$$('.preset').forEach((button) => button.addEventListener('click', () => applyPreset(button.dataset.preset)));
$('#previewText').addEventListener('click', async () => {
  try {
    const data = await prepareText();
    const target = $('#preparedText');
    target.textContent = data.prepared_text;
    target.hidden = false;
  } catch (error) { showError(error.message); }
});
$('#generate').addEventListener('click', generate);
$('#toggleClone').addEventListener('click', () => { $('#cloneForm').hidden = !$('#cloneForm').hidden; });
$('#cloneForm').addEventListener('submit', registerVoice);

updateSpeed();
setMode('clone');
$('#text').dispatchEvent(new Event('input'));
checkHealth();
loadVoices();
setInterval(checkHealth, 30000);
