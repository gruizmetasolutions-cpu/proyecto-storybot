from typing import List, Optional
from pydantic import BaseModel, Field
from core.gemini_client import gemini_service
from core.storyboard_engine import StoryboardProject
from core.token_tracker import TokenTracker, TokenUsage
import config

class DialogueTurnOutput(BaseModel):
    speaker: str = Field(description="Nombre del locutor: 'Elena' (Directora Visual) o 'Marcos' (Guionista Principal)")
    speaker_role: str = Field(description="Rol del locutor: 'Directora de Fotografía y Realización' o 'Guionista y Consultor Narrativo'")
    tone: str = Field(description="Emoción y tono del turno: e.g. 'Entusiasmada', 'Reflexivo', 'Curiosa', 'Enfático', 'Intrigado'")
    text: str = Field(description="Texto del diálogo hablado por este locutor, escrito con cadencia natural, ritmo fluido y estilo conversacional de podcast.")

class DirectorPodcastOutput(BaseModel):
    episode_title: str = Field(description="Título atractivo del episodio de podcast de dirección")
    summary: str = Field(description="Resumen ejecutivo del análisis creativo realizado en la sesión")
    key_takeaways: List[str] = Field(description="Puntos clave discutidos sobre la narrativa y el estilo visual")
    dialogue: List[DialogueTurnOutput] = Field(description="Secuencia cronológica de turnos de diálogo entre Elena y Marcos")

class DialogueTurn(BaseModel):
    speaker: str = Field(description="Nombre del locutor: 'Elena' (Directora Visual) o 'Marcos' (Guionista Principal)")
    speaker_role: str = Field(description="Rol del locutor: 'Directora de Fotografía y Realización' o 'Guionista y Consultor Narrativo'")
    tone: str = Field(description="Emoción y tono del turno: e.g. 'Entusiasmada', 'Reflexivo', 'Curiosa', 'Enfático', 'Intrigado'")
    text: str = Field(description="Texto del diálogo hablado por este locutor, escrito con cadencia natural, ritmo fluido y estilo conversacional de podcast.")
    audio_url: Optional[str] = Field(default=None, description="Audio sintetizado de este turno")

class DirectorPodcast(BaseModel):
    episode_title: str = Field(description="Título atractivo del episodio de podcast de dirección")
    summary: str = Field(description="Resumen ejecutivo del análisis creativo realizado en la sesión")
    key_takeaways: List[str] = Field(description="Puntos clave discutidos sobre la narrativa y el estilo visual")
    dialogue: List[DialogueTurn] = Field(description="Secuencia cronológica de turnos de diálogo entre Elena y Marcos")
    full_audio_url: Optional[str] = Field(default=None, description="Audio completo concatenado del episodio")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Consumo de tokens y costo del podcast")

class PodcastEngine:
    @staticmethod
    def generate_director_overview(
        storyboard: StoryboardProject,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> DirectorPodcast:
        """
        Genera un Audio Overview en formato Podcast de Dirección de 2 Voces utilizando la técnica
        de dos pasos de NotebookLM:
        Paso 1: Análisis crítico de directores (ritmo, planos, tono y decisiones creativas).
        Paso 2: Generación del guion conversacional hipernatural entre Elena y Marcos con audio tags expresivos.
        """
        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                return PodcastEngine.generate_demo_podcast(storyboard)
            else:
                raise ValueError("Por favor configura tu API Key de Gemini para generar el podcast en vivo.")

        shots_summary = "\n".join([
            f"- Toma #{s.shot_number} [{s.shot_type}]: {s.shot_title}. Acción: {s.visual_action}. Cámara: {s.camera_movement}. Luz: {s.lighting_and_atmosphere}. Diálogo/VO: \"{s.dialogue_or_voiceover}\""
            for s in storyboard.shots
        ])

        # PASO 1: Análisis y Brainstorming de Dirección
        step1_prompt = f"""Analiza a profundidad el siguiente Storyboard cinematográfico como si estuvieras preparando una sesión de mesa de dirección creativa en un estudio de cine.

TÍTULO: {storyboard.title}
LOGLINE: {storyboard.logline}
GÉNERO Y TONO: {storyboard.genre_and_tone}
ESTILO VISUAL: {storyboard.visual_style} (Aspect Ratio: {storyboard.aspect_ratio})

PLANOS DEL STORYBOARD:
{shots_summary}

GUÍA DE PERSONAJES:
{chr(10).join(['- ' + c for c in storyboard.character_bibles]) if storyboard.character_bibles else "Sin biblia."}

Realiza un desglose crítico cubriendo:
1. ¿Cuál es el momento de mayor impacto visual y por qué?
2. ¿Cómo funciona la progresión de planos desde la apertura hasta el clímax?
3. ¿Qué decisiones de iluminación y movimiento de cámara potencian la emoción?
4. Una observación sutil o detalle escondido en uno de los planos que enriquece la historia."""

        analysis_step1, usage1 = gemini_service.generate_text_with_usage(
            prompt=step1_prompt,
            system_instruction="Eres un asesor cinematográfico de élite. Haz un análisis perspicaz, apasionado y con vocabulario de producción real.",
            temperature=0.7,
            api_key_override=api_key_override
        )

        # PASO 2: Guion Conversacional Estilo NotebookLM con 2 Hosts
        step2_system_instruction = """Eres el creador y guionista de los aclamados 'Audio Overviews' estilo NotebookLM.
Tu objetivo es crear una conversación hablada vibrante, adictiva y súper natural entre dos expertos de la industria:
- **Elena (Directora de Fotografía y Arte)**: Apasionada por los planos, la luz, los colores, el ritmo de edición y la composición visual.
- **Marcos (Guionista y Showrunner)**: Obsesionado con el subtexto, los arcos de personajes, la tensión dramática y la empatía con el espectador.

REGLAS DE ORO DE LA CONVERSACIÓN NOTEBOOKLM:
1. CADENCIA HUMANA: Usa expresiones naturales de acuerdo mutuo ("Totalmente", "¡Es que justo eso!", "Fíjate en ese detalle", "¿Sabes qué me encanta?").
2. INTERACCIÓN DINÁMICA: No hagas monólogos largos. Que uno comience una idea y el otro la complemente o aporte una perspectiva visual/narrativa distinta.
3. CONEXIÓN DIRECTA CON EL STORYBOARD: Citen tomas específicas ("En la toma 3 cuando la cámara hace ese dolly in...", "Y luego el corte a primer plano en la toma 5...").
4. TONO: Accesible, apasionado, profesional pero fresco y divertido. Como dos colegas talentosos tomándose un café mientras revisan un proyecto brillante.
5. IDIOMA: Español latinoamericano/mexicano neutro de alta calidad."""

        step2_prompt = f"""Genera el episodio de podcast completo para la pieza '{storyboard.title}'.

ANÁLISIS PREVIO DE LA MESA CREATIVA:
{analysis_step1}

DETALLE DE LAS TOMAS:
{shots_summary}

El episodio debe tener entre 8 y 14 turnos de diálogo bien balanceados entre Elena y Marcos, cubriendo la apertura, los momentos cumbre y una conclusión inspiradora."""

        podcast_out, usage2 = gemini_service.generate_structured_with_usage(
            prompt=step2_prompt,
            response_schema=DirectorPodcastOutput,
            system_instruction=step2_system_instruction,
            temperature=0.8,
            api_key_override=api_key_override
        )

        total_tokens = usage1.total_tokens + usage2.total_tokens
        combined_cost = usage1.estimated_cost_usd + usage2.estimated_cost_usd
        
        dialogue_turns = [
            DialogueTurn(
                speaker=d.speaker,
                speaker_role=d.speaker_role,
                tone=d.tone,
                text=d.text
            ) for d in podcast_out.dialogue
        ]

        podcast_result = DirectorPodcast(
            episode_title=podcast_out.episode_title,
            summary=podcast_out.summary,
            key_takeaways=podcast_out.key_takeaways,
            dialogue=dialogue_turns,
            token_usage=TokenUsage(
                prompt_tokens=usage1.prompt_tokens + usage2.prompt_tokens,
                completion_tokens=usage1.completion_tokens + usage2.completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(combined_cost, 5),
                formatted_cost=f"${combined_cost:.4f} USD"
            )
        )

        return podcast_result

    @staticmethod
    def generate_demo_podcast(storyboard: StoryboardProject) -> DirectorPodcast:
        """Genera un episodio de muestra para el podcast de dirección con cadencia de NotebookLM."""
        title = storyboard.title or "La Sombra del Destino"
        
        dialogue = [
            DialogueTurn(
                speaker="Elena",
                speaker_role="Directora de Fotografía y Arte",
                tone="Entusiasmada",
                text=f"¡Hola a todos! Bienvenidos a la mesa de dirección. Hoy tenemos sobre la mesa un proyecto fascinante: '{title}'. Marcos, tengo que decirte que desde que vi el primer plano me atrapó por completo."
            ),
            DialogueTurn(
                speaker="Marcos",
                speaker_role="Guionista y Showrunner",
                tone="Reflexivo",
                text="Totalmente de acuerdo, Elena. Lo que más me fascina de este guion es cómo no necesita perder tiempo en explicaciones innecesarias; la atmósfera te sumerge al instante en el conflicto."
            ),
            DialogueTurn(
                speaker="Elena",
                speaker_role="Directora de Fotografía y Arte",
                tone="Apasionada",
                text="¡Exacto! Fíjate en la toma 1: ese travelling lento con la niebla volumétrica y los reflejos dorados en el pavimento mojado... te establece de golpe la escala y la soledad del personaje."
            ),
            DialogueTurn(
                speaker="Marcos",
                speaker_role="Guionista y Showrunner",
                tone="Intrigado",
                text="Y el contraste cuando pasamos a la toma 3 con el plano detalle del maletín. El resplandor holográfico azul iluminando sus manos cambia toda la dinámica de la escena."
            ),
            DialogueTurn(
                speaker="Elena",
                speaker_role="Directora de Fotografía y Arte",
                tone="Enfática",
                text="¡Ese detalle del destello anamórfico es clave! En cinematografía siempre decimos: 'la luz cuenta lo que las palabras callan'. Y ese destello azul nos avisa del peligro antes de que ocurra."
            ),
            DialogueTurn(
                speaker="Marcos",
                speaker_role="Guionista y Showrunner",
                tone="Emocionado",
                text="Y luego el corte al plano contrapicado con la amenaza en la cornisa. El ritmo sube como un latido acelerado hasta el primer plano de los ojos del protagonista. Una estructura de manual, pero ejecutada con muchísima frescura."
            ),
            DialogueTurn(
                speaker="Elena",
                speaker_role="Directora de Fotografía y Arte",
                tone="Sonriente",
                text="Un storyboard redondo, de verdad. Si están listos en el set, yo digo que preparemos las cámaras y ¡a rodar!"
            )
        ]

        usage = TokenTracker.calculate_cost(prompt_tokens=420, completion_tokens=580)

        return DirectorPodcast(
            episode_title=f"Mesa de Dirección: Desmenuzando '{title}'",
            summary="Elena y Marcos debaten las decisiones cinematográficas, el ritmo de los planos, la iluminación anamórfica y la revelación del clímax.",
            key_takeaways=[
                "El contraste entre el Gran Plano General inicial y el Plano Detalle genera una compresión espacial dramática muy efectiva.",
                "El uso de iluminación dual (neón cian vs ámbar cálido) refuerza el conflicto interno del protagonista.",
                "El ritmo de montaje se acelera progresivamente hacia la toma del clímax antes de disolverse en luz."
            ],
            dialogue=dialogue,
            token_usage=usage
        )
