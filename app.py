import os
import logging
import traceback
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response as FastAPIResponse
from pydantic import BaseModel, Field

import config
from core.gemini_client import gemini_service
from core.storyboard_engine import StoryboardEngine, StoryboardProject, StoryboardShot, ScriptAgent, PremiseAssistResult
from core.podcast_engine import PodcastEngine, DirectorPodcast
from core.visual_engine import VisualEngine
from core.audio_engine import AudioEngine
from core.evaluator import CoherenceEvaluator, CoherenceMetrics
from core.token_tracker import TokenTracker, TokenUsage
from core.pdf_exporter import StoryboardPDFExporter

# Configurar logging detallado
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("storyboard_harness")

app = FastAPI(
    title="Storyboard Studio PRO - NotebookLM Architecture",
    description="Motor de creación de Storyboards de alta calidad, Audio Overviews (Gemini 3.1 Flash TTS), Coherencia Secuencial y Suite de Evaluación",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Modelos de Request -----

class VerifyKeyRequest(BaseModel):
    api_key: str

class AssistPremiseRequest(BaseModel):
    selected_tags: Dict[str, str] = Field(default_factory=dict)
    creativity_scale: float = 0.6
    language_code: str = "es_MX"
    api_key: Optional[str] = None

class GenerateStoryboardRequest(BaseModel):
    input_text: str
    style_key: str = "cinematic_concept"
    voice_intention_key: str = "epic_cinematic"
    language_code: str = "es_MX"
    aspect_ratio: str = "16:9"
    scene_count: int = 6
    target_duration_sec: int = 30
    creativity_scale: float = 0.5
    custom_instructions: Optional[str] = None
    api_key: Optional[str] = None

class RenderPanelRequest(BaseModel):
    visual_prompt: str
    aspect_ratio: str = "16:9"
    negative_prompt: Optional[str] = None
    style_key: str = "cinematic_concept"
    api_key: Optional[str] = None

class CharacterAnchorRequest(BaseModel):
    character_bible: str
    style_key: str = "cinematic_concept"
    aspect_ratio: str = "1:1"
    api_key: Optional[str] = None

class RenderSequenceRequest(BaseModel):
    shots: List[Dict[str, Any]]
    character_bible: Optional[str] = None
    style_key: str = "cinematic_concept"
    aspect_ratio: str = "16:9"
    negative_prompt: Optional[str] = None
    api_key: Optional[str] = None

class MasterAudioRequest(BaseModel):
    shots: List[Dict[str, Any]]
    voice_intention_key: str = "epic_cinematic"
    language_code: str = "es-MX"
    api_key: Optional[str] = None

class SynthesizeSpeechRequest(BaseModel):
    text: str
    voice_key: str = "narrator_epic"
    style_prompt: Optional[str] = None
    language_code: str = "es-MX"
    api_key: Optional[str] = None

class SynthesizePodcastRequest(BaseModel):
    dialogue: List[Dict[str, Any]]
    api_key: Optional[str] = None

class GeneratePodcastRequest(BaseModel):
    storyboard: StoryboardProject
    api_key: Optional[str] = None

class EvaluateCoherenceRequest(BaseModel):
    storyboard: StoryboardProject
    has_character_anchor: bool = False
    rendered_images_count: int = 0
    api_key: Optional[str] = None

# ----- Favicon -----

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1e3a8a"/><rect x="4" y="6" width="24" height="20" rx="2" fill="#3b82f6"/><path d="M4 10h24M4 14h24M12 6v20M20 6v20" stroke="#fff" stroke-width="0.8" opacity="0.4"/></svg>'
    return FastAPIResponse(content=svg_icon, media_type="image/svg+xml")

# ----- API Config & Cost Info -----

@app.get("/api/config")
async def get_app_config():
    return {
        "styles": config.STYLE_PRESETS,
        "aspect_ratios": config.ASPECT_RATIOS,
        "voices": config.VOICE_MAPPINGS,
        "voice_intentions": config.VOICE_INTENTIONS,
        "languages": config.SUPPORTED_LANGUAGES,
        "audio_tags": config.EXPRESSIVE_AUDIO_TAGS,
        "tag_matrix": config.TAG_MATRIX_PRESETS,
        "models": {
            "text": config.DEFAULT_TEXT_MODEL,
            "reasoning": config.DEEP_REASONING_MODEL,
            "image": config.IMAGE_MODEL,
            "audio": config.AUDIO_TTS_MODEL
        },
        "pricing": config.MODEL_PRICING,
        "has_env_key": bool(os.environ.get("GEMINI_API_KEY"))
    }

# ----- Script Assistant: Premise from Tag Matrix -----

@app.post("/api/storyboard/assist-premise")
async def assist_premise(req: AssistPremiseRequest):
    """Genera una premisa cinematográfica profesional a partir de una selección de etiquetas."""
    try:
        result = ScriptAgent.generate_premise_from_tags(
            selected_tags=req.selected_tags,
            creativity_scale=req.creativity_scale,
            language_code=req.language_code,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error en assist_premise:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generando premisa: {str(e)}")

# ----- API Key Verification -----

@app.post("/api/settings/verify")
async def verify_api_key(req: VerifyKeyRequest):
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="La API Key no puede estar vacía.")
    result = gemini_service.test_connection(req.api_key.strip())
    return result

# ----- Storyboard Generation -----

@app.post("/api/storyboard/generate")
async def generate_storyboard(req: GenerateStoryboardRequest):
    """Genera un Storyboard estructurado completo con actuación vocal y soporte multilingüe."""
    if not req.input_text or not req.input_text.strip():
        raise HTTPException(status_code=400, detail="Debes proporcionar una idea, guion o premisa.")

    try:
        logger.info(f"Generando storyboard: lang={req.language_code}, style={req.style_key}, voice_intention={req.voice_intention_key}, ratio={req.aspect_ratio}, scenes={req.scene_count}")

        storyboard = StoryboardEngine.generate_storyboard(
            input_text=req.input_text,
            style_key=req.style_key,
            voice_intention_key=req.voice_intention_key,
            language_code=req.language_code,
            aspect_ratio=req.aspect_ratio,
            scene_count=req.scene_count,
            target_duration_sec=req.target_duration_sec,
            creativity_scale=req.creativity_scale,
            custom_instructions=req.custom_instructions,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )

        # Asignar placeholders visuales iniciales para cada toma sin imagen
        style_info = config.STYLE_PRESETS.get(req.style_key, config.STYLE_PRESETS["cinematic_concept"])
        for shot in storyboard.shots:
            if not shot.image_url:
                shot.image_url = VisualEngine.generate_placeholder_svg(
                    shot.visual_action,
                    req.aspect_ratio,
                    style_info["name"]
                )

        result = storyboard.model_dump()
        return result

    except Exception as e:
        logger.error(f"Error generando storyboard:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generando storyboard: {str(e)}")

# ----- Character Anchor Sheet Generation -----

@app.post("/api/storyboard/character-anchor")
async def generate_character_anchor(req: CharacterAnchorRequest):
    """Genera el Keyframe maestro / Hoja de personaje base para consistencia."""
    try:
        result = VisualEngine.render_character_anchor(
            character_bible=req.character_bible,
            style_key=req.style_key,
            aspect_ratio=req.aspect_ratio,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error generando Character Anchor:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generando Character Anchor: {str(e)}")

# ----- Sequential Coherent Rendering Pipeline -----

@app.post("/api/storyboard/render-sequence")
async def render_sequence(req: RenderSequenceRequest):
    """Ejecuta el renderizado secuencial encadenado con preservación de personaje y estilo."""
    try:
        result = VisualEngine.render_sequential_pipeline(
            shots=req.shots,
            character_bible=req.character_bible,
            style_key=req.style_key,
            aspect_ratio=req.aspect_ratio,
            negative_prompt=req.negative_prompt,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error en renderizado secuencial:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error en renderizado secuencial: {str(e)}")

# ----- Individual Panel Rendering -----

@app.post("/api/storyboard/render-panel")
async def render_panel_image(req: RenderPanelRequest):
    try:
        result = VisualEngine.render_panel_image(
            visual_prompt=req.visual_prompt,
            aspect_ratio=req.aspect_ratio,
            negative_prompt=req.negative_prompt,
            style_key=req.style_key,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error renderizando panel:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error renderizando panel: {str(e)}")

# ----- Gemini 3.1 Flash TTS Audio Synthesis -----

@app.post("/api/audio/synthesize")
async def synthesize_speech(req: SynthesizeSpeechRequest):
    """Sintetiza una frase con Gemini 3.1 Flash TTS (Aoede / Puck / Charon)."""
    try:
        result = AudioEngine.synthesize_speech(
            text=req.text,
            voice_key=req.voice_key,
            style_prompt=req.style_prompt,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error en síntesis TTS:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error en síntesis TTS: {str(e)}")

@app.post("/api/storyboard/synthesize-master-audio")
async def synthesize_storyboard_master_audio(req: MasterAudioRequest):
    """Sintetiza la pista de audio master completa del Storyboard en una sola llamada multi-hablante."""
    if not req.shots:
        raise HTTPException(status_code=400, detail="El storyboard no contiene tomas.")
    try:
        result = AudioEngine.synthesize_storyboard_master_audio(
            shots=req.shots,
            voice_intention_key=req.voice_intention_key,
            language_code=req.language_code,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error en synthesize_storyboard_master_audio:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generando pista master de audio: {str(e)}")

# ----- Podcast Overview & Full Audio Synthesis -----

@app.post("/api/podcast/generate")
async def generate_podcast(req: GeneratePodcastRequest):
    try:
        podcast = PodcastEngine.generate_director_overview(
            storyboard=req.storyboard,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return podcast
    except Exception as e:
        logger.error(f"Error generando podcast:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generando podcast: {str(e)}")

@app.post("/api/podcast/synthesize-full")
async def synthesize_full_podcast(req: SynthesizePodcastRequest):
    """Sintetiza y une todos los turnos del podcast de Elena y Marcos en un único audio continuo."""
    try:
        result = AudioEngine.synthesize_podcast_episode(
            dialogue_turns=req.dialogue,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error sintetizando podcast completo:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error sintetizando podcast completo: {str(e)}")

@app.post("/api/podcast/synthesize-multispeaker")
async def synthesize_multispeaker_podcast(req: SynthesizePodcastRequest):
    """Sintetiza diálogo multi-hablante nativo (Elena & Marcos) en una sola solicitud con MultiSpeakerVoiceConfig."""
    try:
        result = AudioEngine.synthesize_multi_speaker_single_request(
            dialogue_turns=req.dialogue,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return result
    except Exception as e:
        logger.error(f"Error en síntesis multi-speaker:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error en síntesis multi-speaker: {str(e)}")

# ----- Coherence Evaluation Suite -----

@app.post("/api/storyboard/evaluate-coherence")
async def evaluate_coherence(req: EvaluateCoherenceRequest):
    """Audita cuantitativamente la coherencia narrativa, de personaje, visual y de audio."""
    try:
        metrics = CoherenceEvaluator.evaluate_storyboard(
            storyboard=req.storyboard,
            has_character_anchor=req.has_character_anchor,
            rendered_images_count=req.rendered_images_count,
            api_key_override=req.api_key if req.api_key else None,
            allow_demo_fallback=True
        )
        return metrics.model_dump()
    except Exception as e:
        logger.error(f"Error evaluando coherencia:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error evaluando coherencia: {str(e)}")

# ----- PDF Export -----

@app.post("/api/export/pdf")
async def export_pdf(storyboard: StoryboardProject):
    try:
        pdf_bytes = StoryboardPDFExporter.export_pdf(storyboard)
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=storyboard_{storyboard.title.replace(' ', '_').lower()}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Error exportando PDF:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error exportando a PDF: {str(e)}")

# ----- Mount Static Files -----

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
