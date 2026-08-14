// ==========================================================================
// ANIMATIC CINEMA PLAYER (CINE MODE)
// ==========================================================================

let animaticShots = [];
let currentShotIndex = 0;
let isPlaying = false;
let playTimer = null;
let voiceoverEnabled = true;
let synth = window.speechSynthesis;
let availableVoices = [];

function loadVoices() {
  if (synth) {
    availableVoices = synth.getVoices();
    synth.onvoiceschanged = () => {
      availableVoices = synth.getVoices();
    };
  }
}
loadVoices();

function initAnimaticPlayer(shots, ratio = '16:9') {
  animaticShots = shots || [];
  currentShotIndex = 0;
  isPlaying = false;
  clearInterval(playTimer);

  // Sincronizar relación de aspecto
  if (currentStoryboard && currentStoryboard.aspect_ratio) {
    setPlayerAspectRatio(currentStoryboard.aspect_ratio);
  } else if (ratio) {
    setPlayerAspectRatio(ratio);
  }

  if (animaticShots.length > 0) {
    renderTimelineSegments();
    displayShot(0);
  }
}

function setPlayerAspectRatio(ratio) {
  const screen = document.getElementById('cinemaScreen');
  const badge = document.getElementById('animaticRatioBadge');
  if (!screen) return;

  // Limpiar clases de ratio previas
  screen.classList.remove('ratio-16-9', 'ratio-9-16', 'ratio-239-1', 'ratio-4-3', 'ratio-1-1');

  // Mapear ratio a clase CSS
  const ratioMap = {
    '16:9': 'ratio-16-9',
    '9:16': 'ratio-9-16',
    '2.39:1': 'ratio-239-1',
    '4:3': 'ratio-4-3',
    '1:1': 'ratio-1-1'
  };

  const cssClass = ratioMap[ratio] || 'ratio-16-9';
  screen.classList.add(cssClass);

  if (badge) badge.textContent = `📐 ${ratio}`;

  // Actualizar botones activos
  document.querySelectorAll('.animatic-ratio-btn').forEach(btn => {
    if (btn.dataset.playerRatio === ratio) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

function renderTimelineSegments() {
  const container = document.getElementById('shotTimelineSegments');
  if (!container) return;
  container.innerHTML = '';

  animaticShots.forEach((shot, index) => {
    const seg = document.createElement('div');
    seg.className = `timeline-segment ${index === currentShotIndex ? 'active' : ''}`;
    seg.onclick = () => {
      pauseAnimatic();
      displayShot(index);
    };
    container.appendChild(seg);
  });
}

function displayShot(index) {
  if (!animaticShots || animaticShots.length === 0) return;
  if (index < 0) index = 0;
  if (index >= animaticShots.length) index = animaticShots.length - 1;

  currentShotIndex = index;
  const shot = animaticShots[index];

  // Actualizar imagen con efecto Ken Burns
  const imgEl = document.getElementById('animaticImage');
  imgEl.classList.remove('pan-zoom');
  void imgEl.offsetWidth; // trigger reflow
  imgEl.src = shot.image_url || '';
  imgEl.classList.add('pan-zoom');

  // Metadatos en pantalla
  document.getElementById('animaticShotNumber').textContent = `Toma #${shot.shot_number} de ${animaticShots.length}`;
  document.getElementById('animaticShotType').textContent = `${shot.shot_type} (${shot.camera_movement})`;
  document.getElementById('animaticDialogue').textContent = shot.dialogue_or_voiceover ? `"${shot.dialogue_or_voiceover}"` : `[SFX: ${shot.sound_effects_and_music}]`;
  document.getElementById('animaticActionHint').textContent = shot.visual_action;

  // Actualizar indicador de progreso
  const progressPercent = ((index + 1) / animaticShots.length) * 100;
  document.getElementById('animaticProgressFill').style.width = `${progressPercent}%`;
  document.getElementById('playerCurrentTime').textContent = `Toma ${index + 1}`;
  document.getElementById('playerTotalTime').textContent = `${animaticShots.length} Tomas`;

  // Actualizar segmentos de timeline
  const segments = document.querySelectorAll('.timeline-segment');
  segments.forEach((seg, i) => {
    seg.className = `timeline-segment ${i <= index ? 'active' : ''}`;
  });

  // Hablar locución si está activada
  if (voiceoverEnabled && shot.dialogue_or_voiceover) {
    if (shot.audio_url) {
      const audio = new Audio(shot.audio_url);
      audio.play().catch(() => {});
    } else if (synth) {
      speakText(shot.dialogue_or_voiceover, 'Elena');
    }
  }
}

function togglePlayAnimatic() {
  if (isPlaying) {
    pauseAnimatic();
  } else {
    playAnimatic();
  }
}

function playAnimatic() {
  if (animaticShots.length === 0) return;
  isPlaying = true;
  document.getElementById('btnPlayPause').textContent = '⏸️';

  const stepAnimatic = () => {
    if (!isPlaying) return;
    const shot = animaticShots[currentShotIndex];
    const duration = (shot.estimated_duration_sec || 4) * 1000;

    playTimer = setTimeout(() => {
      if (!isPlaying) return;
      if (currentShotIndex < animaticShots.length - 1) {
        displayShot(currentShotIndex + 1);
        stepAnimatic();
      } else {
        pauseAnimatic();
        displayShot(0); // Reiniciar al inicio
      }
    }, duration);
  };

  stepAnimatic();
}

function pauseAnimatic() {
  isPlaying = false;
  clearTimeout(playTimer);
  document.getElementById('btnPlayPause').textContent = '▶️';
  if (synth) synth.cancel();
}

function nextShot() {
  pauseAnimatic();
  if (currentShotIndex < animaticShots.length - 1) {
    displayShot(currentShotIndex + 1);
  }
}

function prevShot() {
  pauseAnimatic();
  if (currentShotIndex > 0) {
    displayShot(currentShotIndex - 1);
  }
}

function toggleVoiceover() {
  voiceoverEnabled = !voiceoverEnabled;
  const btn = document.getElementById('btnToggleAudio');
  if (voiceoverEnabled) {
    btn.textContent = '🔊 VO Activada';
    btn.style.borderColor = 'var(--accent-primary)';
  } else {
    btn.textContent = '🔇 VO Silenciada';
    btn.style.borderColor = 'var(--border-medium)';
    if (synth) synth.cancel();
  }
}

function speakText(text, persona = 'Elena') {
  if (!synth) return;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'es-MX';

  // Buscar mejor voz en español
  const esVoice = availableVoices.find(v => v.lang.startsWith('es') && (persona === 'Elena' ? (v.name.includes('female') || v.name.includes('Paulina') || v.name.includes('Sabina') || v.name.includes('Dalia')) : (v.name.includes('male') || v.name.includes('Jorge') || v.name.includes('Raul')))) || availableVoices.find(v => v.lang.startsWith('es'));

  if (esVoice) utterance.voice = esVoice;
  utterance.pitch = persona === 'Elena' ? 1.05 : 0.95;
  utterance.rate = 1.0;

  synth.speak(utterance);
}
