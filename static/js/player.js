// ==========================================================================
// ANIMATIC CINEMA PLAYER (CINE MODE)
// ==========================================================================

let animaticShots = [];
let currentShotIndex = 0;
let isPlaying = false;
let playTimer = null;
let voiceoverEnabled = true;
let animaticMasterAudio = null;
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

  if (animaticMasterAudio) {
    animaticMasterAudio.pause();
    animaticMasterAudio = null;
  }

  // Sincronizar relación de aspecto
  if (currentStoryboard && currentStoryboard.aspect_ratio) {
    setPlayerAspectRatio(currentStoryboard.aspect_ratio);
  } else if (ratio) {
    setPlayerAspectRatio(ratio);
  }

  if (animaticShots.length > 0) {
    renderTimelineSegments();
    displayShot(0, false);
  }
}

function setPlayerAspectRatio(ratio) {
  const screen = document.getElementById('cinemaScreen');
  const badge = document.getElementById('animaticRatioBadge');
  if (!screen) return;

  screen.classList.remove('ratio-16-9', 'ratio-9-16', 'ratio-239-1', 'ratio-4-3', 'ratio-1-1');

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
      displayShot(index, false);
      if (animaticMasterAudio && shot.timecode_start_sec !== undefined) {
        animaticMasterAudio.currentTime = shot.timecode_start_sec;
      }
    };
    container.appendChild(seg);
  });
}

function displayShot(index, playSingleTTS = true) {
  if (!animaticShots || animaticShots.length === 0) return;
  if (index < 0) index = 0;
  if (index >= animaticShots.length) index = animaticShots.length - 1;

  currentShotIndex = index;
  const shot = animaticShots[index];

  // Actualizar imagen con efecto Ken Burns
  const imgEl = document.getElementById('animaticImage');
  if (imgEl) {
    imgEl.classList.remove('pan-zoom');
    void imgEl.offsetWidth; // trigger reflow
    imgEl.src = shot.image_url || '';
    imgEl.classList.add('pan-zoom');
  }

  // Metadatos en pantalla
  const shotNumEl = document.getElementById('animaticShotNumber');
  const shotTypeEl = document.getElementById('animaticShotType');
  const dialEl = document.getElementById('animaticDialogue');
  const actionEl = document.getElementById('animaticActionHint');

  if (shotNumEl) shotNumEl.textContent = `Toma #${shot.shot_number} de ${animaticShots.length}`;
  if (shotTypeEl) shotTypeEl.textContent = `${shot.shot_type} (${shot.speaker_label || 'Voz'})`;
  if (dialEl) dialEl.textContent = shot.dialogue_or_voiceover ? `"${shot.dialogue_or_voiceover}"` : `[SFX: ${shot.sound_effects_and_music}]`;
  if (actionEl) actionEl.textContent = shot.visual_action;

  // Actualizar segmentos de timeline
  const segments = document.querySelectorAll('.timeline-segment');
  segments.forEach((seg, i) => {
    seg.className = `timeline-segment ${i <= index ? 'active' : ''}`;
  });

  // Si no hay master audio corriendo y se solicitó locución individual
  if (playSingleTTS && !isPlaying && voiceoverEnabled && shot.dialogue_or_voiceover) {
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

  const hasMasterAudio = currentStoryboard && currentStoryboard.master_audio_url;

  if (hasMasterAudio) {
    if (!animaticMasterAudio) {
      animaticMasterAudio = new Audio(currentStoryboard.master_audio_url);
    } else {
      animaticMasterAudio.src = currentStoryboard.master_audio_url;
    }

    const currentShot = animaticShots[currentShotIndex];
    if (currentShot && currentShot.timecode_start_sec !== undefined) {
      animaticMasterAudio.currentTime = currentShot.timecode_start_sec;
    }

    animaticMasterAudio.ontimeupdate = () => {
      if (!isPlaying || !animaticMasterAudio) return;
      const curTime = animaticMasterAudio.currentTime;
      const totalDur = animaticMasterAudio.duration || (currentStoryboard.master_audio_duration_sec || 30);

      // Actualizar barra de progreso
      const percent = (curTime / totalDur) * 100;
      const fillEl = document.getElementById('animaticProgressFill');
      if (fillEl) fillEl.style.width = `${Math.min(100, percent)}%`;

      const curMin = Math.floor(curTime / 60).toString().padStart(2, '0');
      const curSec = Math.floor(curTime % 60).toString().padStart(2, '0');
      const totMin = Math.floor(totalDur / 60).toString().padStart(2, '0');
      const totSec = Math.floor(totalDur % 60).toString().padStart(2, '0');

      const timeCurEl = document.getElementById('playerCurrentTime');
      const timeTotEl = document.getElementById('playerTotalTime');
      if (timeCurEl) timeCurEl.textContent = `${curMin}:${curSec}`;
      if (timeTotEl) timeTotEl.textContent = `${totMin}:${totSec}`;

      // Encontrar toma correspondiente al segundo actual
      const matchIdx = animaticShots.findIndex(s => 
        s.timecode_start_sec !== undefined && 
        s.timecode_end_sec !== undefined && 
        curTime >= s.timecode_start_sec && 
        curTime < s.timecode_end_sec
      );

      if (matchIdx !== -1 && matchIdx !== currentShotIndex) {
        displayShot(matchIdx, false);
      }
    };

    animaticMasterAudio.onended = () => {
      pauseAnimatic();
      displayShot(0, false);
    };

    animaticMasterAudio.play().catch(err => {
      console.warn("Autoplay bloqueado:", err);
    });

  } else {
    // Fallback a temporizador secuencial
    const stepAnimatic = () => {
      if (!isPlaying) return;
      const shot = animaticShots[currentShotIndex];
      const duration = (shot.estimated_duration_sec || 4) * 1000;

      playTimer = setTimeout(() => {
        if (!isPlaying) return;
        if (currentShotIndex < animaticShots.length - 1) {
          displayShot(currentShotIndex + 1, true);
          stepAnimatic();
        } else {
          pauseAnimatic();
          displayShot(0, false);
        }
      }, duration);
    };

    displayShot(currentShotIndex, true);
    stepAnimatic();
  }
}

function pauseAnimatic() {
  isPlaying = false;
  clearTimeout(playTimer);
  document.getElementById('btnPlayPause').textContent = '▶️';
  if (animaticMasterAudio) {
    animaticMasterAudio.pause();
  }
  if (synth) synth.cancel();
}

function nextShot() {
  pauseAnimatic();
  if (currentShotIndex < animaticShots.length - 1) {
    displayShot(currentShotIndex + 1, false);
    if (animaticMasterAudio && animaticShots[currentShotIndex + 1].timecode_start_sec !== undefined) {
      animaticMasterAudio.currentTime = animaticShots[currentShotIndex + 1].timecode_start_sec;
    }
  }
}

function prevShot() {
  pauseAnimatic();
  if (currentShotIndex > 0) {
    displayShot(currentShotIndex - 1, false);
    if (animaticMasterAudio && animaticShots[currentShotIndex - 1].timecode_start_sec !== undefined) {
      animaticMasterAudio.currentTime = animaticShots[currentShotIndex - 1].timecode_start_sec;
    }
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
