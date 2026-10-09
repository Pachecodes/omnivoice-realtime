#!/usr/bin/env node
'use strict';
// Execute the shipped handler, not a copy. No browser, network or model required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../src/omnivoice_realtime/ui/pro/app.js'), 'utf8');
const start = source.indexOf('async function cloneVoice(event) {');
const end = source.indexOf('\nfunction resetControls()', start);
assert.ok(start >= 0 && end > start, 'shipped cloneVoice extraction boundary');
const handler = source.slice(start, end);
const turn = () => new Promise(resolve => setImmediate(resolve));
function barrier() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function fixture() {
  const upload = barrier(), json = barrier(), library = barrier();
  const button = { disabled: false, textContent: 'Crear y precargar voz' };
  const nodes = {
    '#cloneStatus': { textContent: 'old status' },
    '#voice': { value: 'previous' },
    '#fileName': { textContent: 'reference.wav' },
  };
  const inputs = { ref_audio: 'reference.wav', ref_text: 'private transcript', voice_id: 'fixture', language: 'English' };
  let resets = 0, libraryCalls = 0, selectedMode = null, prevented = false, posted;
  const form = {
    reset() { resets++; Object.keys(inputs).forEach(key => { inputs[key] = ''; }); },
    querySelector(selector) {
      assert.equal(selector, '[name=language]');
      return { set value(value) { inputs.language = value; } };
    },
  };
  const context = vm.createContext({
    $: selector => { assert.ok(nodes[selector]); return nodes[selector]; },
    FormData: class { constructor(target) { assert.equal(target, form); this.fields = { ...inputs }; } },
    fetch: (url, options) => {
      assert.equal(url, '/v1/voices/clone-cache');
      assert.equal(options.method, 'POST');
      posted = options.body.fields;
      return upload.promise;
    },
    loadVoices: () => { libraryCalls++; return library.promise; },
    selectVoiceMode: mode => { selectedMode = mode; },
  });
  vm.runInContext(handler, context);
  const event = { currentTarget: form, submitter: button, preventDefault() { prevented = true; } };
  const pending = context.cloneVoice(event);
  // DOM dispatch ends synchronously; subsequent asynchronous phases see null.
  event.currentTarget = null;
  event.submitter = null; // also prove the original button is retained locally
  assert.equal(prevented, true);
  assert.equal(button.disabled, true);
  assert.equal(button.textContent, 'Transcribiendo y clonando…');
  assert.equal(nodes['#cloneStatus'].textContent, '');
  assert.equal(posted.ref_audio, 'reference.wav');
  function restored() {
    assert.equal(button.disabled, false);
    assert.equal(button.textContent, 'Crear y precargar voz');
  }
  return { upload, json, library, pending, button, nodes, inputs, restored,
    get resets() { return resets; }, get libraryCalls() { return libraryCalls; },
    get selectedMode() { return selectedMode; } };
}
for (const transcript of ['recognized transcript', '']) {
  test(`successful delayed clone clears references and preserves success (${transcript ? 'transcript' : 'ASR fallback'})`, async () => {
    const f = fixture();
    await turn();
    assert.equal(f.button.disabled, true);
    f.upload.resolve({ ok: true, json: () => f.json.promise });
    await turn();
    assert.equal(f.button.disabled, true);
    f.json.resolve({ voice_id: 'fixture', ref_text: transcript });
    await turn();
    assert.equal(f.libraryCalls, 1);
    assert.equal(f.button.disabled, true);
    assert.equal(f.resets, 0);
    f.library.resolve();
    await f.pending;
    assert.equal(f.nodes['#cloneStatus'].textContent, `fixture está lista. Transcripción: ${transcript || 'ASR completado'}`);
    assert.equal(f.resets, 1);
    assert.equal(f.inputs.ref_audio, '');
    assert.equal(f.inputs.ref_text, '');
    assert.equal(f.inputs.voice_id, '');
    assert.equal(f.inputs.language, 'Spanish');
    assert.equal(f.nodes['#fileName'].textContent, 'WAV, MP3, M4A, OGG, FLAC o AAC');
    assert.equal(f.nodes['#voice'].value, 'fixture');
    assert.equal(f.selectedMode, 'clone');
    f.restored();
  });
}
for (const failure of ['HTTP', 'network', 'JSON']) {
  test(`delayed ${failure} failure reports error, retains retry inputs and restores button`, async () => {
    const f = fixture();
    await turn();
    if (failure === 'network') f.upload.reject(new Error('network failed'));
    else {
      f.upload.resolve({ ok: failure !== 'HTTP', json: () => f.json.promise });
      await turn();
      assert.equal(f.button.disabled, true);
      if (failure === 'JSON') f.json.reject(new Error('JSON failed'));
      else f.json.resolve({ detail: 'HTTP failed' });
    }
    await f.pending;
    assert.equal(f.nodes['#cloneStatus'].textContent, `${failure} failed`);
    assert.equal(f.resets, 0);
    assert.equal(f.libraryCalls, 0);
    assert.equal(f.inputs.ref_audio, 'reference.wav');
    assert.equal(f.inputs.ref_text, 'private transcript');
    assert.equal(f.nodes['#fileName'].textContent, 'reference.wav');
    assert.equal(f.nodes['#voice'].value, 'previous');
    assert.equal(f.selectedMode, null);
    f.restored();
  });
}
