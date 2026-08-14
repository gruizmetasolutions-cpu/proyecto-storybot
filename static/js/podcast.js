// ==========================================================================
// DIRECTOR PODCAST / AUDIO OVERVIEW (2-HOST NOTEBOOKLM & GEMINI 3.1 TTS)
// ==========================================================================

let currentPodcast = null;
let isPlayingPodcast = false;
let currentPodcastAudioEl = null;
let currentPodcastTurnIndex = 0;

async function generatePodcast() {
  if (!currentStoryboard) {
    showToast("Primero genera un Storyboard para que Elena y Marcos puedan analizarlo.", "info");
    return;
  }

  const btn = document.getElementById('btnGeneratePodcast');
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ Analizando planos en 2 pasos...';
  btn.disabled = true;

  try {
    const key = getStoredApiKey();
    const res = await fetch('/api/podcast/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        storyboard: currentStoryboard,
        api_key: key || null
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error en la generación del podcast");
    }

    currentPodcast = await res.json();
    if (currentPodcast.token_usage) {
      recordTokenUsage(currentPodcast.token_usage);
    }

    renderPodcastUI(currentPodcast);
    showToast("¡Audio Overview generado con éxito!", "success");
    const btnMulti = document.getElementById('btnSynthesizeMultiSpeaker');
    if (btnMulti) btnMulti.disabled = false;
    document.getElementById('btnSynthesizeFullAudio').disabled = false;
    document.getElementById('btnPlayFullPodcast').disabled = false;
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function renderPodcastUI(podcast) {
  document.getElementById('podcastTitle').textContent = podcast.episode_title;
  document.getElementById('podcastSummary').textContent = podcast.summary;

  // Cost badge
  const costBadge = document.getElementById('podcastCostBadge');
  if (costBadge && podcast.token_usage) {
    costBadge.textContent = `🪙 Costo Est: ${podcast.token_usage.formatted_cost}`;
  }

  // Takeaways
  const takeawaysBox = document.getElementById('podcastTakeawaysBox');
  const takeawaysList = document.getElementById('podcastTakeawaysList');
  takeawaysList.innerHTML = '';
  if (podcast.key_takeaways && podcast.key_takeaways.length > 0) {
    podcast.key_takeaways.forEach(point => {
      const li = document.createElement('li');
      li.textContent = point;
      takeawaysList.appendChild(li);
    });
    takeawaysBox.classList.remove('hidden');
  }

  // Transcripción Interactiva
  const transcriptList = document.getElementById('podcastTranscriptList');
  transcriptList.innerHTML = '';

  podcast.dialogue.forEach((turn, idx) => {
    const card = document.createElement('div');
    card.className = 'transcript-turn';
    card.id = `turn-${idx}`;

    const isElena = turn.speaker.toLowerCase().includes('elena');
    const avatarClass = isElena ? 'Elena' : 'Marcos';
    const voiceCode = isElena ? 'Aoede' : 'Puck';

    card.innerHTML = `
      <div class="speaker-avatar-circle ${avatarClass}" title="${turn.speaker} (${voiceCode})">
        ${isElena ? 'E' : 'M'}
      </div>
      <div class="turn-content">
        <div class="turn-header">
          <div>
            <span class="speaker-name">${turn.speaker}</span>
            <span class="speaker-role-tag">${turn.speaker_role || (isElena ? 'Directora Visual' : 'Guionista Principal')} • <em style="color:#60a5fa">${voiceCode}</em></span>
          </div>
          <span class="turn-tone-badge">${turn.tone || 'Enfático'}</span>
        </div>
        <p class="turn-text">${turn.text}</p>
      </div>
      <button class="btn btn-secondary btn-sm" id="btn-turn-audio-${idx}" onclick="synthesizeTurnTTS(${idx})" title="Sintetizar y escuchar con Gemini 3.1 Flash TTS">🔊</button>
    `;

    transcriptList.appendChild(card);
  });
}

// SINTETIZAR AUDIO DE UN TURNO INDIVIDUAL
async function synthesizeTurnTTS(idx) {
  if (!currentPodcast || !currentPodcast.dialogue[idx]) return;
  const turn = currentPodcast.dialogue[idx];
  const btn = document.getElementById(`btn-turn-audio-${idx}`);
  if (btn) btn.textContent = "⏳";

  const isElena = turn.speaker.toLowerCase().includes('elena');
  const voiceKey = isElena ? 'elena' : 'marcos';
  const apiKey = getStoredApiKey();

  try {
    const res = await fetch('/api/audio/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: turn.text,
        voice_key: voiceKey,
        style_prompt: turn.tone || "conversacional y apasionado",
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error en síntesis TTS");
    const data = await res.json();

    if (data.audio_data) {
      turn.audio_url = data.audio_data;
      if (data.token_usage) recordTokenUsage(data.token_usage);
      
      highlightTurn(idx);
      const audio = new Audio(data.audio_data);
      audio.play();
      showToast(`Reproduciendo voz de ${data.voice_used}`, "info");
    }
  } catch (err) {
    showToast(`Error TTS: ${err.message}`, "error");
  } finally {
    if (btn) btn.textContent = "🔊";
  }
}

// SÍNTESIS MULTI-SPEAKER NATIVA EN UNA SOLA LLAMADA (GEMINI 3.1 FLASH TTS)
async function synthesizeNativeMultiSpeakerAudio() {
  if (!currentPodcast || !currentPodcast.dialogue) return;
  const btn = document.getElementById('btnSynthesizeMultiSpeaker');
  btn.disabled = true;
  btn.textContent = "⚡ Sintetizando Multi-Speaker Nativo (1 llamada)...";

  const apiKey = getStoredApiKey();

  try {
    const res = await fetch('/api/podcast/synthesize-multispeaker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dialogue: currentPodcast.dialogue,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error en síntesis multi-speaker nativa");
    const data = await res.json();

    if (data.full_audio_data) {
      currentPodcast.full_audio_url = data.full_audio_data;
      if (data.token_usage) recordTokenUsage(data.token_usage);
      
      showToast("¡Diálogo multi-hablante nativo sintetizado con éxito (Elena & Marcos)! Haz clic en Reproducir.", "success");
      document.getElementById('btnPlayFullPodcast').classList.add('btn-highlight-play');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🎙️ Síntesis Multi-Hablante Nativa (Single Call)";
  }
}

// SINTETIZAR PODCAST COMPLETO TURNO A TURNO
async function synthesizeFullPodcastAudio() {
  if (!currentPodcast || !currentPodcast.dialogue) return;
  const btn = document.getElementById('btnSynthesizeFullAudio');
  btn.disabled = true;
  btn.textContent = "⏳ Sintetizando todas las voces...";

  const apiKey = getStoredApiKey();

  try {
    const res = await fetch('/api/podcast/synthesize-full', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dialogue: currentPodcast.dialogue,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error sintetizando episodio completo");
    const data = await res.json();

    if (data.full_audio_data) {
      currentPodcast.full_audio_url = data.full_audio_data;
      if (data.token_usage) recordTokenUsage(data.token_usage);
      
      showToast("¡Episodio completo sintetizado con éxito (Elena & Marcos)! Haz clic en Reproducir.", "success");
      document.getElementById('btnPlayFullPodcast').classList.add('btn-highlight-play');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "📻 Re-sintetizar Turno a Turno";
  }
}

function highlightTurn(idx) {
  document.querySelectorAll('.transcript-turn').forEach((el, i) => {
    if (i === idx) {
      el.classList.add('active-turn');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      el.classList.remove('active-turn');
    }
  });
}

function togglePlayFullPodcast() {
  if (isPlayingPodcast) {
    stopFullPodcast();
  } else {
    playFullPodcast();
  }
}

function playFullPodcast() {
  if (!currentPodcast || currentPodcast.dialogue.length === 0) return;

  // Si ya tenemos el audio completo sintetizado en WAV
  if (currentPodcast.full_audio_url) {
    isPlayingPodcast = true;
    document.getElementById('btnPlayFullPodcast').textContent = '⏹️ Pausar Episodio';

    if (!currentPodcastAudioEl) {
      currentPodcastAudioEl = new Audio(currentPodcast.full_audio_url);
      currentPodcastAudioEl.onended = () => stopFullPodcast();
    }
    currentPodcastAudioEl.play();
    showToast("Reproduciendo episodio completo multivoz (Aoede & Puck)", "info");
    return;
  }

  // Si no está pre-sintetizado, sintetizar turno por turno secuencialmente
  isPlayingPodcast = true;
  currentPodcastTurnIndex = 0;
  document.getElementById('btnPlayFullPodcast').textContent = '⏹️ Detener Podcast';

  const playNextTurn = async () => {
    if (!isPlayingPodcast || currentPodcastTurnIndex >= currentPodcast.dialogue.length) {
      stopFullPodcast();
      return;
    }

    const turn = currentPodcast.dialogue[currentPodcastTurnIndex];
    highlightTurn(currentPodcastTurnIndex);

    const isElena = turn.speaker.toLowerCase().includes('elena');
    const voiceKey = isElena ? 'elena' : 'marcos';
    const apiKey = getStoredApiKey();

    try {
      const res = await fetch('/api/audio/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: turn.text,
          voice_key: voiceKey,
          style_prompt: turn.tone || "conversacional",
          api_key: apiKey || null
        })
      });
      const data = await res.json();
      if (data.token_usage) recordTokenUsage(data.token_usage);

      if (data.audio_data && isPlayingPodcast) {
        const audio = new Audio(data.audio_data);
        audio.onended = () => {
          if (isPlayingPodcast) {
            currentPodcastTurnIndex++;
            setTimeout(playNextTurn, 250);
          }
        };
        audio.play();
      } else {
        currentPodcastTurnIndex++;
        playNextTurn();
      }
    } catch (e) {
      currentPodcastTurnIndex++;
      playNextTurn();
    }
  };

  playNextTurn();
}

function stopFullPodcast() {
  isPlayingPodcast = false;
  document.getElementById('btnPlayFullPodcast').textContent = '▶️ Reproducir Episodio';
  if (currentPodcastAudioEl) {
    currentPodcastAudioEl.pause();
    currentPodcastAudioEl.currentTime = 0;
  }
  document.querySelectorAll('.transcript-turn').forEach(el => el.classList.remove('active-turn'));
}
