// ==========================================================================
// STORYBOARD STUDIO PRO - MAIN APPLICATION CONTROLLER
// ==========================================================================

let currentStoryboard = null;
let activeRatio = '16:9';
let selectedStyleKey = 'cinematic_concept';
let selectedVoiceIntention = 'epic_cinematic';
let selectedLanguage = 'es_MX';
let characterAnchorData = null;
let masterAudioInstance = null;
let isPlayingMasterAudio = false;
let totalAccumulatedTokens = 0;
let totalAccumulatedCostUSD = 0.0;

// Estado de la Matriz de Etiquetas
let selectedMatrixTags = {
  genres: "Cyberpunk Neo-Noir",
  protagonists: "Detective Cansado",
  conflicts: "Maletín con Código Prohibido",
  atmospheres: "Neo-Tokyo Lluvioso",
  tones: "Tenso y Claustrofóbico"
};

// PLANTILLAS RÁPIDAS
const PROMPT_PRESETS = {
  cyberpunk: "Un detective cibernético camina bajo una lluvia torrencial en Neo-Tokio iluminado por luces de neón magenta y cian. Encuentra un maletín misterioso con un holograma flotante. Cuando intenta abrirlo, un androide asesino salta desde el tejado con una katana de plasma. El detective esquiva el corte y activa su dron de defensa.",
  thriller: "En una cabaña aislada en un bosque nevado durante la noche, una escritora escucha golpes secos en el sótano. Baja con una linterna titilante. Entre viejas cajas de madera, descubre una puerta oculta con cerraduras recientes y un susurro que llama su nombre desde el otro lado.",
  emotional: "Una anciana encuentra en su ático un proyector de cine de 8mm y una cinta polvorienta de 1972. Al encenderlo contra una sábana blanca, ve a su difunto esposo sonriéndole y bailando en una playa al atardecer. Su nieta entra a la habitación y la abraza en silencio mientras la luz dorada baña sus rostros."
};

function initApp() {
  setupRatioSelector();
  updateCreativityLabel(50);
  updateTokenBadges();
}

function setupRatioSelector() {
  const buttons = document.querySelectorAll('.ratio-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeRatio = btn.dataset.ratio;
    });
  });
}

function toggleMatrixTag(btn) {
  const cat = btn.dataset.cat;
  const val = btn.dataset.val;
  if (!cat || !val) return;

  const parent = btn.parentElement;
  parent.querySelectorAll('.matrix-chip').forEach(chip => chip.classList.remove('active'));
  btn.classList.add('active');

  selectedMatrixTags[cat] = val;
}

// ASISTENTE DE GUION: CREAR PREMISA DESDE TAGS
async function assistPremiseWithAI() {
  const btn = document.getElementById('btnAssistPremise');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '✨ El Agente IA está redactando la premisa...';

  const apiKey = getStoredApiKey();
  const creativityVal = parseInt(document.getElementById('creativitySlider').value, 10) / 100.0;

  try {
    const res = await fetch('/api/storyboard/assist-premise', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_tags: selectedMatrixTags,
        creativity_scale: creativityVal,
        language_code: selectedLanguage,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error en la asistencia de premisa.");
    const data = await res.json();

    const textarea = document.getElementById('scriptInput');
    textarea.value = data.generated_premise;
    textarea.classList.add('flash-glow');
    setTimeout(() => textarea.classList.remove('flash-glow'), 1200);

    if (data.token_usage) recordTokenUsage(data.token_usage);
    showToast(`✨ Premisa cinematográfica generada: "${data.suggested_title || 'Nueva Historia'}"`, "success");
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

function updateCreativityLabel(val) {
  const label = document.getElementById('creativityValue');
  const num = parseInt(val, 10);
  if (num <= 25) {
    label.textContent = `${num}% Estricto (Fuente)`;
    label.style.color = '#38bdf8';
  } else if (num <= 70) {
    label.textContent = `${num}% Equilibrado`;
    label.style.color = '#3b82f6';
  } else {
    label.textContent = `${num}% Expansivo (IA)`;
    label.style.color = '#f59e0b';
  }
}

function loadPromptPreset(presetKey) {
  const input = document.getElementById('scriptInput');
  input.value = PROMPT_PRESETS[presetKey] || '';
  input.focus();
}

function onLanguageChange(langCode) {
  selectedLanguage = langCode;
  showToast(`Idioma configurado: ${langCode}`, "info");
}

function insertAudioTag(tag) {
  const input = document.getElementById('scriptInput');
  if (!input) return;

  const start = input.selectionStart;
  const end = input.selectionEnd;
  const text = input.value;
  
  input.value = text.substring(0, start) + " " + tag + " " + text.substring(end);
  input.focus();
  input.setSelectionRange(start + tag.length + 2, start + tag.length + 2);
  showToast(`Etiqueta insertada: ${tag}`, "info");
}

function onStyleChange(styleKey) {
  selectedStyleKey = styleKey;
  const descriptions = {
    cinematic_concept: "Estilo cinematográfico hiperdetallado con iluminación volumétrica y lentes 35mm.",
    pencil_sketch: "Boceto profesional a lápiz y carboncillo de producción cinematográfica con alto contraste.",
    film_noir: "Blanco y negro con sombras duras claroscuro estilo novela gráfica clásica.",
    studio_ghibli: "Pintura al agua suave, fondos exuberantes y atmósfera emotiva pintada a mano.",
    unreal_engine_3d: "Previsualización 3D digital nítida con iluminación Lumen y Ray Tracing.",
    anime_shonen: "Animación dinámica de alto presupuesto con líneas de acción y colores vibrantes.",
    vintage_35mm: "Fotograma de película analógica 35mm con grano sutil y paleta Kodak Portra."
  };
  document.getElementById('styleDescription').textContent = descriptions[styleKey] || '';
}

function onVoiceIntentionChange(intentionKey) {
  selectedVoiceIntention = intentionKey;
  const descriptions = {
    epic_cinematic: "Voz profunda, ritmo pausado con peso dramático, pausas calculadas y presencia de trailer.",
    tense_thriller: "Tono contenido, susurros dramáticos, respiración y tensión psicológica in crescendo.",
    emotional_warmth: "Cadencia cercana, intimista y conmovedora, con inflexiones de emoción genuina.",
    noir_detective: "Voz áspera de monólogo interior, ritmo pausado de jazz y cinismo urbano.",
    dynamic_action: "Ritmo rápido, urgencia en cada palabra, volumen proyectado y aceleración dramática.",
    whimsical_fantasy: "Voz colorida, mágica, con cambios divertidos de tono y expresión teatral."
  };
  const descEl = document.getElementById('voiceIntentionDescription');
  if (descEl) descEl.textContent = descriptions[intentionKey] || '';
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  const activeContent = document.getElementById(tabId);
  if (activeContent) activeContent.classList.add('active');

  const targetIndex = ['tabGrid', 'tabAnimatic', 'tabPodcast', 'tabShotList'].indexOf(tabId);
  const tabButtons = document.querySelectorAll('.tab-btn');
  if (tabButtons[targetIndex]) tabButtons[targetIndex].classList.add('active');

  if (tabId !== 'tabAnimatic' && typeof pauseAnimatic === 'function') {
    pauseAnimatic();
  }
}

// GESTIÓN DE TOKENS Y COSTOS
function recordTokenUsage(usage) {
  if (!usage) return;
  totalAccumulatedTokens += (usage.total_tokens || 0);
  totalAccumulatedCostUSD += (usage.estimated_cost_usd || 0.0);
  updateTokenBadges();
}

function updateTokenBadges() {
  const countText = document.getElementById('tokenCountText');
  const costText = document.getElementById('costValueText');
  const metaCostPill = document.getElementById('metaCostPill');

  const formattedTokens = totalAccumulatedTokens.toLocaleString();
  const formattedCost = totalAccumulatedCostUSD < 0.01 
    ? `$${totalAccumulatedCostUSD.toFixed(4)} USD` 
    : `$${totalAccumulatedCostUSD.toFixed(2)} USD`;

  if (countText) countText.textContent = `${formattedTokens} Tokens`;
  if (costText) costText.textContent = formattedCost;
  if (metaCostPill) metaCostPill.textContent = `🪙 Costo Est: ${formattedCost}`;
}

// 1. GENERAR STORYBOARD COMPLETO
async function generateStoryboard() {
  const scriptText = document.getElementById('scriptInput').value.trim();
  if (!scriptText) {
    showToast("Por favor escribe una premisa, guion o idea primero.", "info");
    return;
  }

  const apiKey = getStoredApiKey();
  const btn = document.getElementById('btnGenerateStoryboard');
  const btnText = document.getElementById('btnGenText');
  const originalText = btnText.textContent;
  btn.disabled = true;
  btnText.textContent = apiKey ? "🎬 Desglosando con Gemini 3.5..." : "🎬 Generando Storyboard Demo...";

  const creativityVal = parseInt(document.getElementById('creativitySlider').value, 10) / 100.0;
  const sceneCount = parseInt(document.getElementById('sceneCountSelect').value, 10);
  const duration = parseInt(document.getElementById('durationSelect').value, 10);
  const notes = document.getElementById('customDirectorNotes').value.trim();

  try {
    const response = await fetch('/api/storyboard/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_text: scriptText,
        style_key: selectedStyleKey,
        voice_intention_key: selectedVoiceIntention,
        language_code: selectedLanguage,
        aspect_ratio: activeRatio,
        scene_count: sceneCount,
        target_duration_sec: duration,
        creativity_scale: creativityVal,
        custom_instructions: notes || null,
        api_key: apiKey || null
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Error en el servidor");
    }

    currentStoryboard = await response.json();
    if (currentStoryboard.token_usage) {
      recordTokenUsage(currentStoryboard.token_usage);
    }

    renderStoryboardUI(currentStoryboard);
    
    if (apiKey) {
      showToast("¡Storyboard generado en vivo con Gemini 3.5!", "success");
    } else {
      showToast("¡Storyboard generado! (Modo Demo. Para IA en vivo, agrega tu clave en Configuración)", "info");
    }
    
    document.getElementById('btnExportPDF').disabled = false;
    initAnimaticPlayer(currentStoryboard.shots);

  } catch (err) {
    showToast(`Error al generar: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btnText.textContent = originalText;
  }
}

function renderStoryboardUI(storyboard) {
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('projectHeader').classList.remove('hidden');
  document.getElementById('shotsGrid').classList.remove('hidden');

  // Header
  document.getElementById('projectTitle').textContent = storyboard.title;
  document.getElementById('projectLogline').textContent = storyboard.logline;
  document.getElementById('projectGenreTag').textContent = storyboard.genre_and_tone;
  document.getElementById('metaDurationPill').textContent = `⏱️ ~${storyboard.target_duration_seconds}s`;
  document.getElementById('metaShotsPill').textContent = `🎥 ${storyboard.shots.length} Tomas`;
  document.getElementById('metaStylePill').textContent = `🎨 ${storyboard.visual_style}`;
  document.getElementById('metaRatioPill').textContent = `📐 ${storyboard.aspect_ratio}`;

  // Character bibles
  const cbList = document.getElementById('characterBibleList');
  cbList.innerHTML = '';
  if (storyboard.character_bibles && storyboard.character_bibles.length > 0) {
    storyboard.character_bibles.forEach(c => {
      const li = document.createElement('li');
      li.textContent = c;
      cbList.appendChild(li);
    });
  }

  // Render Shots Cards
  const grid = document.getElementById('shotsGrid');
  grid.innerHTML = '';

  storyboard.shots.forEach((shot) => {
    const card = document.createElement('div');
    card.className = 'shot-card';
    card.id = `shot-card-${shot.shot_number}`;

    const tcStart = shot.timecode_start_sec !== undefined ? shot.timecode_start_sec.toFixed(1) : '0.0';
    const tcEnd = shot.timecode_end_sec !== undefined ? shot.timecode_end_sec.toFixed(1) : shot.estimated_duration_sec.toFixed(1);

    card.innerHTML = `
      <div class="shot-card-header">
        <span class="shot-badge">TOMA #${shot.shot_number} • ${shot.shot_type}</span>
        <div class="shot-time-meta">
          <span class="shot-tc-badge" id="shot-tc-${shot.shot_number}">⏱️ ${tcStart}s - ${tcEnd}s</span>
          <span class="shot-duration">(${shot.estimated_duration_sec}s)</span>
        </div>
      </div>

      <div class="shot-image-container">
        <img id="shot-img-${shot.shot_number}" src="${shot.image_url}" alt="Toma ${shot.shot_number}">
        <div class="shot-image-overlay">
          <button class="btn btn-primary btn-sm" onclick="renderShotWithGemini(${shot.shot_number})">
            🎨 Renderizar con Gemini
          </button>
        </div>
      </div>

      <div class="shot-card-body">
        <h4 class="shot-title-text">${shot.shot_title}</h4>
        
        <div class="shot-meta-tags">
          <span class="tag-pill camera">🎥 ${shot.camera_movement}</span>
          <span class="tag-pill">💡 ${shot.lighting_and_atmosphere}</span>
          <span class="tag-pill speaker">🗣️ ${shot.speaker_label || 'Narrador'}</span>
        </div>

        <div class="shot-field">
          <span class="field-label">Acción Visual Detallada:</span>
          <p class="field-value">${shot.visual_action}</p>
        </div>

        ${shot.dialogue_or_voiceover ? `
          <div class="dialogue-box">
            <div class="dialogue-header-mini">
              <span class="acting-tag">🎭 ${shot.acting_intention || 'Actuación Vocal Expresiva'}</span>
              <span class="voice-badge-mini">🎙️ ${shot.voice_cast || 'TTS 3.1'} (${shot.speaker_label || 'Voz'})</span>
            </div>
            <p class="dialogue-text">"${shot.dialogue_or_voiceover}"</p>
            <button class="btn-speak-icon" id="btn-tts-${shot.shot_number}" onclick="synthesizeAndPlayShotAudio(${shot.shot_number})" title="Sintetizar locución con Gemini 3.1 Flash TTS">
              🔊
            </button>
          </div>
        ` : ''}

        <div class="shot-field">
          <span class="field-label">Efectos & Música:</span>
          <p class="field-value">${shot.sound_effects_and_music}</p>
        </div>

        <details class="shot-prompt-details">
          <summary>Ver Prompt de Generación Visual</summary>
          <p class="shot-prompt-text">${shot.visual_prompt_optimized}</p>
        </details>
      </div>
    `;

    grid.appendChild(card);
  });

  renderShotListTable(storyboard);
}

// SÍNTESIS DE MASTER AUDIO TRACK MULTI-HABLANTE (SINGLE CALL)
async function synthesizeStoryboardMasterAudio() {
  if (!currentStoryboard || !currentStoryboard.shots) return;
  const btn = document.getElementById('btnSynthesizeMasterAudio');
  const playBtn = document.getElementById('btnPlayMasterAudio');
  const badge = document.getElementById('masterAudioStatusBadge');

  btn.disabled = true;
  btn.textContent = "⚡ Sintetizando Master Audio (1 llamada)...";

  const apiKey = getStoredApiKey();

  try {
    const res = await fetch('/api/storyboard/synthesize-master-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shots: currentStoryboard.shots,
        voice_intention_key: selectedVoiceIntention,
        language_code: selectedLanguage,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error generando pista master de audio.");
    const data = await res.json();

    if (data.master_audio_url) {
      currentStoryboard.master_audio_url = data.master_audio_url;
      currentStoryboard.master_audio_duration_sec = data.master_duration_sec;
      currentStoryboard.master_audio_speakers = data.speakers;

      // Actualizar timecodes en cada toma
      if (data.shots) {
        data.shots.forEach((updatedShot, idx) => {
          if (currentStoryboard.shots[idx]) {
            currentStoryboard.shots[idx].timecode_start_sec = updatedShot.timecode_start_sec;
            currentStoryboard.shots[idx].timecode_end_sec = updatedShot.timecode_end_sec;
            currentStoryboard.shots[idx].estimated_duration_sec = updatedShot.estimated_duration_sec;

            const tcEl = document.getElementById(`shot-tc-${currentStoryboard.shots[idx].shot_number}`);
            if (tcEl) {
              tcEl.textContent = `⏱️ ${updatedShot.timecode_start_sec.toFixed(1)}s - ${updatedShot.timecode_end_sec.toFixed(1)}s`;
              tcEl.classList.add('tc-synced');
            }
          }
        });
      }

      if (data.token_usage) recordTokenUsage(data.token_usage);

      // Actualizar estado UI
      if (badge) {
        badge.textContent = `✅ Master Listo (${data.master_duration_sec}s)`;
        badge.classList.add('badge-success');
      }
      if (playBtn) playBtn.classList.remove('hidden');

      // Actualizar el reproductor Animatic con el nuevo master audio
      initAnimaticPlayer(currentStoryboard.shots);

      showToast(`🎙️ ¡Pista Master de Audio generada (${data.master_duration_sec}s)! Sincronizada con el Animatic Player.`, "success");
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "🎙️ Re-sintetizar Master Audio";
  }
}

function togglePlayMasterAudio() {
  if (!currentStoryboard || !currentStoryboard.master_audio_url) return;
  const playBtn = document.getElementById('btnPlayMasterAudio');

  if (!masterAudioInstance) {
    masterAudioInstance = new Audio(currentStoryboard.master_audio_url);
    masterAudioInstance.onended = () => {
      isPlayingMasterAudio = false;
      if (playBtn) playBtn.textContent = "▶️ Reproducir Master Track";
    };
  }

  if (isPlayingMasterAudio) {
    masterAudioInstance.pause();
    isPlayingMasterAudio = false;
    if (playBtn) playBtn.textContent = "▶️ Reproducir Master Track";
  } else {
    masterAudioInstance.src = currentStoryboard.master_audio_url;
    masterAudioInstance.play();
    isPlayingMasterAudio = true;
    if (playBtn) playBtn.textContent = "⏸️ Pausar Master Track";
  }
}

// 2. GENERAR CHARACTER ANCHOR SHEET
async function generateCharacterAnchor() {
  if (!currentStoryboard) {
    showToast("Primero genera un Storyboard.", "info");
    return;
  }

  const bibleText = (currentStoryboard.character_bibles || []).join(". ") || "Protagonista principal de la historia";
  const apiKey = getStoredApiKey();
  const btn = document.getElementById('btnGenerateAnchor');
  btn.disabled = true;
  btn.textContent = "⏳ Generando Anchor...";

  try {
    const res = await fetch('/api/storyboard/character-anchor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        character_bible: bibleText,
        style_key: selectedStyleKey,
        aspect_ratio: "1:1",
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error generando Anchor Sheet");

    const data = await res.json();
    if (data.image_data) {
      characterAnchorData = data.image_data;
      document.getElementById('characterAnchorImg').src = data.image_data;
      document.getElementById('characterAnchorCard').classList.remove('hidden');
      if (data.token_usage) recordTokenUsage(data.token_usage);
      showToast("¡Hoja de Personaje Base (Anchor) fijada con éxito!", "success");
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "★ Regenerar Anchor";
  }
}

// 3. PIPELINE DE RENDERIZADO SECUENCIAL COHERENTE
async function renderSequentialPipeline() {
  if (!currentStoryboard) {
    showToast("Primero genera un Storyboard.", "info");
    return;
  }

  const apiKey = getStoredApiKey();
  const btn = document.getElementById('btnRenderSequence');
  const progContainer = document.getElementById('sequenceProgressContainer');
  const progLabel = document.getElementById('seqProgressLabel');
  const progFill = document.getElementById('seqProgressFill');
  const progPercent = document.getElementById('seqProgressPercent');

  btn.disabled = true;
  progContainer.classList.remove('hidden');
  progLabel.textContent = "Iniciando renderizado secuencial con propagación de estilo...";
  progFill.style.width = "10%";
  progPercent.textContent = "10%";

  const bibleText = (currentStoryboard.character_bibles || []).join(". ") || null;
  const negPrompt = document.getElementById('negativePromptInput').value.trim();

  try {
    const res = await fetch('/api/storyboard/render-sequence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shots: currentStoryboard.shots,
        character_bible: bibleText,
        style_key: selectedStyleKey,
        aspect_ratio: currentStoryboard.aspect_ratio || activeRatio,
        negative_prompt: negPrompt || null,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error en el renderizado secuencial");

    const data = await res.json();
    
    // Si generó anchor sheet, mostrarlo
    if (data.anchor_sheet && data.anchor_sheet.image_data) {
      characterAnchorData = data.anchor_sheet.image_data;
      document.getElementById('characterAnchorImg').src = data.anchor_sheet.image_data;
      document.getElementById('characterAnchorCard').classList.remove('hidden');
    }

    // Actualizar cada toma renderizada
    if (data.rendered_shots) {
      data.rendered_shots.forEach((s) => {
        const shotObj = currentStoryboard.shots.find(item => item.shot_number === s.shot_number);
        if (shotObj && s.image_data) {
          shotObj.image_url = s.image_data;
          const imgEl = document.getElementById(`shot-img-${s.shot_number}`);
          if (imgEl) imgEl.src = s.image_data;
        }
      });

      progFill.style.width = "100%";
      progPercent.textContent = "100%";
      progLabel.textContent = "¡Secuencia completa renderizada con coherencia de estilo!";
      
      initAnimaticPlayer(currentStoryboard.shots);
      showToast("¡Secuencia completa renderizada con éxito!", "success");
    }

    if (data.token_usage) recordTokenUsage(data.token_usage);

  } catch (err) {
    showToast(`Error al renderizar secuencia: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    setTimeout(() => progContainer.classList.add('hidden'), 3500);
  }
}

// 4. RENDERIZAR TOMA INDIVIDUAL CON GEMINI
async function renderShotWithGemini(shotNumber) {
  if (!currentStoryboard) return;
  const shot = currentStoryboard.shots.find(s => s.shot_number === shotNumber);
  if (!shot) return;

  const imgEl = document.getElementById(`shot-img-${shotNumber}`);
  showToast(`Renderizando toma #${shotNumber} con Gemini 3.1...`, "info");

  const negPrompt = document.getElementById('negativePromptInput').value.trim();
  const apiKey = getStoredApiKey();

  try {
    const res = await fetch('/api/storyboard/render-panel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        visual_prompt: shot.visual_prompt_optimized,
        aspect_ratio: currentStoryboard.aspect_ratio || activeRatio,
        negative_prompt: negPrompt || null,
        style_key: selectedStyleKey,
        api_key: apiKey || null
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error en el renderizado");
    }

    const data = await res.json();
    if (data.image_data) {
      shot.image_url = data.image_data;
      imgEl.src = data.image_data;
      if (data.token_usage) recordTokenUsage(data.token_usage);
      initAnimaticPlayer(currentStoryboard.shots);
      showToast(`¡Toma #${shotNumber} renderizada!`, "success");
    }
  } catch (err) {
    showToast(`Error al renderizar: ${err.message}`, "error");
  }
}

// 5. SÍNTESIS DE AUDIO TTS INDIVIDUAL (GEMINI 3.1 FLASH TTS)
async function synthesizeAndPlayShotAudio(shotNumber) {
  if (!currentStoryboard) return;
  const shot = currentStoryboard.shots.find(s => s.shot_number === shotNumber);
  if (!shot || !shot.dialogue_or_voiceover) return;

  const btn = document.getElementById(`btn-tts-${shotNumber}`);
  if (btn) btn.textContent = "⏳";

  const apiKey = getStoredApiKey();

  try {
    const voiceKey = shot.voice_cast || "narrator_epic";
    const stylePrompt = shot.acting_intention || "dramático y cinematográfico con emoción";

    const res = await fetch('/api/audio/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: shot.dialogue_or_voiceover,
        voice_key: voiceKey,
        style_prompt: stylePrompt,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error en síntesis TTS");
    const data = await res.json();

    if (data.audio_data) {
      shot.audio_url = data.audio_data;
      if (data.token_usage) recordTokenUsage(data.token_usage);
      
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

// 6. AUDITORÍA DE COHERENCIA (AI INSPECTOR)
function openCoherenceModal() {
  document.getElementById('coherenceModal').classList.remove('hidden');
  if (currentStoryboard) {
    runCoherenceAudit();
  } else {
    showToast("Genera un Storyboard primero para ejecutar la auditoría.", "info");
  }
}

function closeCoherenceModal() {
  document.getElementById('coherenceModal').classList.add('hidden');
}

async function runCoherenceAudit() {
  if (!currentStoryboard) return;
  const apiKey = getStoredApiKey();

  const renderedCount = currentStoryboard.shots.filter(s => s.image_url && !s.image_url.includes("data:image/svg")).length;

  try {
    const res = await fetch('/api/storyboard/evaluate-coherence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        storyboard: currentStoryboard,
        has_character_anchor: Boolean(characterAnchorData),
        rendered_images_count: renderedCount,
        api_key: apiKey || null
      })
    });

    if (!res.ok) throw new Error("Error evaluando coherencia");

    const metrics = await res.json();
    if (metrics.token_usage) recordTokenUsage(metrics.token_usage);

    // Actualizar UI del modal
    document.getElementById('coherenceRadialScore').textContent = `${metrics.overall_score}`;
    document.getElementById('scoreNarrative').textContent = `${metrics.narrative_flow_score}/100`;
    document.getElementById('barNarrative').style.width = `${metrics.narrative_flow_score}%`;

    document.getElementById('scoreCharacter').textContent = `${metrics.character_consistency_score}/100`;
    document.getElementById('barCharacter').style.width = `${metrics.character_consistency_score}%`;

    document.getElementById('scoreVisual').textContent = `${metrics.visual_style_continuity_score}/100`;
    document.getElementById('barVisual').style.width = `${metrics.visual_style_continuity_score}%`;

    document.getElementById('scoreAudio').textContent = `${metrics.audio_dialogue_quality_score}/100`;
    document.getElementById('barAudio').style.width = `${metrics.audio_dialogue_quality_score}%`;

    // Strengths
    const sList = document.getElementById('evalStrengthsList');
    sList.innerHTML = '';
    (metrics.strengths || []).forEach(s => {
      const li = document.createElement('li');
      li.textContent = s;
      sList.appendChild(li);
    });

    // Issues
    const iList = document.getElementById('evalIssuesList');
    iList.innerHTML = '';
    (metrics.critical_issues || []).forEach(i => {
      const li = document.createElement('li');
      li.textContent = i;
      iList.appendChild(li);
    });

    // Recs
    const rList = document.getElementById('evalRecsList');
    rList.innerHTML = '';
    (metrics.director_recommendations || []).forEach(r => {
      const li = document.createElement('li');
      li.textContent = r;
      rList.appendChild(li);
    });

    // Mini badge en el header
    const badge = document.getElementById('headerCoherenceBadge');
    badge.classList.remove('hidden');
    badge.textContent = `${metrics.overall_score}/100`;

    showToast(`Auditoría completada: Calificación ${metrics.overall_score}/100`, "success");

  } catch (err) {
    showToast(`Error al auditar: ${err.message}`, "error");
  }
}

function renderShotListTable(storyboard) {
  const tbody = document.getElementById('shotTableBody');
  tbody.innerHTML = '';

  storyboard.shots.forEach(shot => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${shot.shot_number}</strong></td>
      <td><span class="tag-pill camera">${shot.shot_type}</span></td>
      <td>${shot.camera_movement}</td>
      <td><strong>${shot.shot_title}:</strong> ${shot.visual_action}</td>
      <td>${shot.lighting_and_atmosphere}</td>
      <td><em>${shot.dialogue_or_voiceover ? `"${shot.dialogue_or_voiceover}"` : `[SFX: ${shot.sound_effects_and_music}]`}</em></td>
      <td>${shot.estimated_duration_sec}s</td>
    `;
    tbody.appendChild(tr);
  });
}

// 7. EXPORTAR PDF
async function exportPDF() {
  if (!currentStoryboard) {
    showToast("Primero genera un Storyboard para exportar.", "info");
    return;
  }

  const btn = document.getElementById('btnExportPDF');
  const origText = btn.innerHTML;
  btn.innerHTML = '⏳ Generando PDF...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentStoryboard)
    });

    if (!res.ok) throw new Error("Error al generar PDF en el servidor.");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `storyboard_${currentStoryboard.title.replace(/\s+/g, '_').toLowerCase()}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    showToast("¡PDF descargado con éxito!", "success");
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

// NOTIFICACIONES TOAST
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> <span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

document.addEventListener('DOMContentLoaded', initApp);
