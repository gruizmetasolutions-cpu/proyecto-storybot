from typing import List, Optional
from pydantic import BaseModel, Field
import config
from core.gemini_client import gemini_service
from core.token_tracker import TokenTracker, TokenUsage

class StoryboardShot(BaseModel):
    shot_number: int = Field(description="Número correlativo de la toma (1, 2, 3...)")
    shot_title: str = Field(description="Título corto y expresivo del plano/toma")
    shot_type: str = Field(description="Tipo de plano cinematográfico detallado: e.g. 'Gran Plano General (EWS)', 'Plano Medio Largo (MLS)', 'Primer Plano Íntimo (CU)', 'Plano Detalle Macro (Insert)', 'Plano Cenital', 'Plano Contrapicado Heroico'")
    camera_movement: str = Field(description="Movimiento o ángulo de cámara preciso: e.g. 'Travelling circular lento de 180°', 'Dolly In acelerado con estabilizador Ronin', 'Cámara al hombro con respiración orgánica', 'Panorámica oblicua con desenfoque de movimiento'")
    visual_action: str = Field(description="Descripción visual hiperdetallada y rica de lo que ocurre en el cuadro: postura corporal, microexpresiones faciales, textura de vestimenta, partículas en el aire, interacción con el entorno y dinamismo de la escena.")
    lighting_and_atmosphere: str = Field(description="Iluminación profesional, esquema de luces y atmósfera sensorial: e.g. 'Luz de corte anamórfica azul cian, luz de relleno cálida de tungsteno, niebla volumétrica baja, reflejos de lluvia en asfalto mojado, bokeh suave de fondo'")
    dialogue_or_voiceover: str = Field(description="Diálogo o locución expresiva con tags de actuación de audio integrados (e.g. '[whispers] No te muevas... [gasp] Está detrás de ti', '[intense breath] Lo encontramos, pero ya es tarde').")
    acting_intention: str = Field(description="Directiva de dirección actoral y tono emocional para la locución: e.g. 'Voz contenida con temblor de ansiedad', 'Monólogo pausado con ironía y cinismo', 'Grito urgente de advertencia'")
    voice_cast: str = Field(default="narrator_epic", description="Identificador de voz recomendada: 'narrator_epic' (Charon), 'narrator_tense' (Fenrir), 'narrator_warm' (Aoede), 'narrator_dynamic' (Kore), 'elena', 'marcos'")
    sound_effects_and_music: str = Field(description="Diseño sonoro detallado (Foley, SFX ambientales, sub-bajos, textura musical incidental y crescendo).")
    estimated_duration_sec: float = Field(description="Duración estimada del plano en segundos (ej. 3.5, 4.0)")
    visual_prompt_optimized: str = Field(description="Prompt en inglés hiperdetallado y optimizado para Gemini 3.1 Flash Image, describiendo composición, lente, iluminación, texturas y personajes sin texto ni marcas de agua.")
    image_url: Optional[str] = Field(default=None, description="URL o base64 de la imagen generada")
    audio_url: Optional[str] = Field(default=None, description="URL o base64 del audio de locución sintetizado con Gemini 3.1 Flash TTS")

class StoryboardProject(BaseModel):
    title: str = Field(description="Título cinematográfico impactante del proyecto")
    logline: str = Field(description="Logline o premisa de una sola oración que resume el conflicto, protagonista y apuesta dramática")
    synopsis: str = Field(description="Sinopsis narrativa completa, profunda y cautivadora de la pieza audiovisual")
    genre_and_tone: str = Field(description="Género y tono dramático (ej. 'Thriller psicológico tenso y claustrofóbico con estética Neo-Noir')")
    visual_style: str = Field(description="Estilo visual y cinematográfico general asignado")
    aspect_ratio: str = Field(description="Relación de aspecto seleccionada (ej. 16:9, 2.39:1, 9:16, 4:3, 1:1)")
    voice_intention: str = Field(default="epic_cinematic", description="Preset de intención y actuación vocal aplicado al proyecto")
    language_code: str = Field(default="es_MX", description="Código del idioma del proyecto (ej: es_MX, es_ES, en_US, fr_FR, etc.)")
    target_duration_seconds: int = Field(description="Duración total estimada en segundos")
    character_bibles: List[str] = Field(description="Guía de consistencia de personajes principales (rasgos físicos clave, vestimenta, peinado, colores característicos y accesorios inmutables)")
    character_anchor_url: Optional[str] = Field(default=None, description="URL o base64 de la Hoja de Personaje Base (Anchor Sheet)")
    shots: List[StoryboardShot] = Field(description="Lista ordenada y secuencial de todos los planos del storyboard")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Métricas de consumo de tokens y costo del proyecto")

class StoryboardEngine:
    @staticmethod
    def generate_storyboard(
        input_text: str,
        style_key: str = "cinematic_concept",
        voice_intention_key: str = "epic_cinematic",
        language_code: str = "es_MX",
        aspect_ratio: str = "16:9",
        scene_count: int = 6,
        target_duration_sec: int = 30,
        creativity_scale: float = 0.5,
        custom_instructions: Optional[str] = None,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> StoryboardProject:
        """
        Genera un storyboard completo, hiperdetallado y cinematográfico
        con soporte multilingüe, directivas de actuación vocal y tags expresivos para Gemini 3.1 Flash TTS.
        """
        style_info = config.STYLE_PRESETS.get(style_key, config.STYLE_PRESETS["cinematic_concept"])
        style_name = style_info["name"]
        style_suffix = style_info["prompt_suffix"]

        lang_info = config.SUPPORTED_LANGUAGES.get(language_code, config.SUPPORTED_LANGUAGES["es_MX"])
        lang_name = lang_info["name"]
        lang_instruction = lang_info["system_instruction"]

        voice_intention = config.VOICE_INTENTIONS.get(voice_intention_key, config.VOICE_INTENTIONS["epic_cinematic"])
        voice_name = voice_intention["name"]
        voice_directive = voice_intention["prompt_directive"]
        default_voice = voice_intention["default_voice"]

        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                return StoryboardEngine.generate_demo_storyboard(
                    input_text=input_text,
                    style_key=style_key,
                    voice_intention_key=voice_intention_key,
                    language_code=language_code,
                    aspect_ratio=aspect_ratio,
                    scene_count=scene_count,
                    target_duration_sec=target_duration_sec
                )
            else:
                raise ValueError("Por favor configura tu Google Gemini API Key en el botón de Configuración.")

        temp = 0.25 + (creativity_scale * 0.70)

        system_instruction = f"""Eres un Director de Cine y Showrunner de Hollywood galardonado, especializado en narrativas visuales profundas, desglose de planos meticuloso y dirección actoral expresiva.

IDIOMA DEL PROYECTO:
- Debes redactar todo el contenido narrativo, títulos, sinopsis, acciones visuales y diálogos en: {lang_name}.
- Directiva de Idioma: {lang_instruction}

TUS PRINCIPIOS DE CREACIÓN DE STORYBOARD:
1. DETALLE NARRATIVO Y VISUAL MÁXIMO:
   - Describe minuciosamente cada plano: la textura de la piel, microexpresiones, la arquitectura del espacio, la iluminación precisa (temperatura Kelvin, sombras proyectadas, fuentes prácticas), y el movimiento de cámara con terminología técnica cinematográfica.
2. DIÁLOGOS CON ACTUACIÓN Y AUDIO TAGS EXPRESIVOS:
   - Los diálogos y locuciones DEBEN incluir tags de modulación de voz en corchetes para el sintetizador de voz Gemini 3.1 Flash TTS (e.g. [whispers], [dramatic pause], [slow breath], [gasp], [intense breath], [chuckles], [sighs], [urgent shout], [fast cadence], [deep resonance]).
   - Adapta el tono al estilo de actuación solicitado: "{voice_directive}".
3. CONSISTENCIA DE PERSONAJES (CHARACTER BIBLES):
   - Define en 'character_bibles' un desglose exhaustivo de los personajes (edad, facciones distintivas, peinado, ropa exacta, colores de vestuario, accesorios) para que sirvan de ancla visual.
4. PROMPTS PARA GEMINI 3.1 FLASH IMAGE:
   - Redacta cada 'visual_prompt_optimized' en inglés con estructura: [Subject & detailed action], [Environment, background & depth], [Camera lens, millimeter & angle], [Lighting scheme & volumetric atmosphere], seguido por: "{style_suffix}".

DIRECTIVA DE ACTUACIÓN VOCAL:
- Preset Activo: {voice_name}
- Guía de Voz: {voice_directive}
"""

        user_prompt = f"""Genera un Storyboard cinematográfico completo con EXACTAMENTE {scene_count} planos/tomas (shots).

PARÁMETROS DEL PROYECTO:
- Idioma Principal: {lang_name}
- Duración total objetivo: {target_duration_sec} segundos (distribuye la duración orgánicamente entre las {scene_count} tomas).
- Relación de Aspecto: {aspect_ratio}
- Estilo Visual: {style_name}
- Intención Vocal / Audio Acting: {voice_name}
- Voz Recomendada: {default_voice}
- Nivel de Creatividad / Imaginación: {int(creativity_scale * 100)}%

MATERIAL / GUION FUENTE DEL USUARIO:
\"\"\"
{input_text}
\"\"\"

{f"INSTRUCCIONES ADICIONALES DEL DIRECTOR: {custom_instructions}" if custom_instructions else ""}

Genera la estructura JSON completa respetando el esquema Pydantic en {lang_name}, con descripciones hiperdetalladas, directivas de actuación vocal y exactamente {scene_count} planos."""

        result, usage = gemini_service.generate_structured_with_usage(
            prompt=user_prompt,
            response_schema=StoryboardProject,
            system_instruction=system_instruction,
            temperature=temp,
            api_key_override=api_key_override
        )
        
        result.token_usage = usage
        result.aspect_ratio = aspect_ratio
        result.voice_intention = voice_intention_key
        result.language_code = language_code
        return result

    @staticmethod
    def generate_demo_storyboard(
        input_text: str,
        style_key: str = "cinematic_concept",
        voice_intention_key: str = "epic_cinematic",
        language_code: str = "es_MX",
        aspect_ratio: str = "16:9",
        scene_count: int = 6,
        target_duration_sec: int = 30
    ) -> StoryboardProject:
        """Genera un Storyboard de demostración hiperdetallado y con audio tags expresivos."""
        style_info = config.STYLE_PRESETS.get(style_key, config.STYLE_PRESETS["cinematic_concept"])
        style_name = style_info["name"]
        lang_info = config.SUPPORTED_LANGUAGES.get(language_code, config.SUPPORTED_LANGUAGES["es_MX"])
        voice_intention = config.VOICE_INTENTIONS.get(voice_intention_key, config.VOICE_INTENTIONS["epic_cinematic"])
        default_voice = voice_intention["default_voice"]

        shots_pool = [
            StoryboardShot(
                shot_number=1,
                shot_title="Apertura Atmosférica y Establecimiento del Conflicto",
                shot_type="Gran Plano General (EWS) con Composición en Tercios",
                camera_movement="Travelling lento hacia adelante con grúa descendente a nivel de calle (Dolly in a ras de suelo)",
                visual_action="La silueta solitaria del protagonista avanza en medio de un denso callejón empapado por lluvia torrencial. El agua salpica bajo sus botas de combate mientras la niebla baja refracta destellos de luz. Su mano enguantada descansa sobre el cuello alzado de su impermeable oscuro.",
                lighting_and_atmosphere="Iluminación volumétrica de hora azul con contrastes de neón ámbar y cian. Sombras alargadas y reflejos nítidos en el pavimento mojado, atmósfera densa y claustrofóbica.",
                dialogue_or_voiceover="[slow breath] [whispers] En una ciudad donde cada secreto tiene precio... [dramatic pause] nadie mira dos veces a quien camina en la sombra.",
                acting_intention="Locución pausada, íntima y cargada de misterio, con respiración perceptible antes de la frase.",
                voice_cast=default_voice,
                sound_effects_and_music="Lluvia continua golpeando el asfalto, eco lejano de sirenas urbanas y una nota grave sostenida de violonchelo con textura de sintetizador análogo.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Extreme wide shot, cinematic low angle, lone figure in long dark tactical trench coat walking through dense rain-soaked neon alleyway at dusk, volumetric blue rim light, golden reflections on puddles, anamorphic lens 35mm, {style_info['prompt_suffix']}"
            ),
            StoryboardShot(
                shot_number=2,
                shot_title="Aproximación y Tensión Creciente",
                shot_type="Plano Medio (MS) con Profundidad de Campo Reducida",
                camera_movement="Cámara al hombro estabilizada siguiendo el compás de sus pasos y deteniéndose en seco",
                visual_action="El protagonista se detiene bruscamente bajo el parpadeo de una farola. Su mandíbula se tensa mientras sus ojos escanean la penumbra circundante. Desliza lentamente los dedos hacia el cierre hermético de su bolsillo interior.",
                lighting_and_atmosphere="Luz lateral rasante bicolor (cian y naranja) que esculpe los pómulos y la textura del abrigo de cuero sintético. Gotas de lluvia resbalando por su rostro.",
                dialogue_or_voiceover="[tense whisper] El contacto debía estar aquí a las ocho en punto... [sharp intake of breath] No hay margen para errores.",
                acting_intention="Tensión contenida, pulso acelerado y vigilancia extrema en la entonación.",
                voice_cast=default_voice,
                sound_effects_and_music="Gotas pesadas cayendo sobre metal, crujido de grava bajo la suela y un latido rítmico sub-bajo que comienza a acelerar.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Medium shot, determined protagonist stopping under flickering street light, dramatic dual lighting cyan and amber, intense gaze, wet hair, realistic leather texture, depth of field f/1.8, {style_info['prompt_suffix']}"
            ),
            StoryboardShot(
                shot_number=3,
                shot_title="El Descubrimiento del Artefacto",
                shot_type="Primer Plano Detalle (Insert Shot / Macro)",
                camera_movement="Macro zoom suave con enfoque selectivo (Rack focus) desde los dedos hacia el núcleo holográfico",
                visual_action="Un maletín de titanio reforzado se abre con un chasquido presurizado. Desde su interior, un prisma holográfico se despliega emitiendo haces de datos lumínicos color esmeralda que iluminan las líneas de la mano del protagonista.",
                lighting_and_atmosphere="Resplandor verde esmeralda y cian de alta intensidad que genera un aura mágica en las manos y partículas de polvo en suspensión.",
                dialogue_or_voiceover="[gasp] El código de cifrado sigue intacto... [whispers with urgency] pero el transmisor de rastreo está encendido.",
                acting_intention="Asombro contenido que se transforma de inmediato en alerta y urgencia.",
                voice_cast=default_voice,
                sound_effects_and_music="Despresurización neumática 'hiss', zumbido electromagnético armónico de alta frecuencia y glissando de sintetizador.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Close-up macro insert shot, hands opening metallic cybernetic case emitting radiant emerald green holographic data geometry, volumetric dust particles, 50mm anamorphic lens, {style_info['prompt_suffix']}"
            ),
            StoryboardShot(
                shot_number=4,
                shot_title="La Amenaza en las Alturas",
                shot_type="Plano Contrapicado Dramático (Low Angle Dutch Angle)",
                camera_movement="Giro rápido de cámara con látigo (Whip pan) de 45 grados mirando hacia la cornisa superior",
                visual_action="En la cornisa del edificio superior, una silueta amenazante de aspecto ágil desenvaina un filo reflectante. La lluvia azota la estructura mientras la figura se inclina lista para saltar hacia la posición del protagonista.",
                lighting_and_atmosphere="Contraluz intenso con silueta recortada contra el cielo tormentoso iluminado por relámpagos lejanos.",
                dialogue_or_voiceover="[urgent shout] [sharp breath] ¡No estás solo! ¡Nos encontraron!",
                acting_intention="Impacto visceral, advertencia tajante y detonación de la acción.",
                voice_cast=default_voice,
                sound_effects_and_music="Trueno seco y retumbante, golpe orquestal dramático (braam) y sonido de acero cortando el viento.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Dramatic low angle Dutch tilt shot looking up, sleek assassin silhouette on rooftop ledge against stormy sky, sharp lightning backlight, high contrast, dynamic action composition, {style_info['prompt_suffix']}"
            ),
            StoryboardShot(
                shot_number=5,
                shot_title="La Determinación del Protagonista",
                shot_type="Primer Plano Emotivo Cerrado (Extreme Close-Up / ECU)",
                camera_movement="Dolly in ultra fluido y estabilizado directo a la mirada y pupila del personaje",
                visual_action="Primer plano de la mirada decidida del protagonista. En el iris se refleja el destello del holograma y la sombra del atacante descendiendo. Una gota de lluvia cruza su mejilla sin que parpadee.",
                lighting_and_atmosphere="Luz clave cálida frontal cruzada con un haz de destello anamórfico horizontal azulado que cruza el cuadro.",
                dialogue_or_voiceover="[deep breath] [intense confidence] Si quieren la verdad... [dramatic pause] tendrán que venir por ella.",
                acting_intention="Determinación absoluta, desafío frío y valentía inquebrantable.",
                voice_cast=default_voice,
                sound_effects_and_music="Crescendo orquestal arrollador con sección de cuerdas veloces y percusión cinematográfica estilo Taiko.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Extreme close up portrait, intense determined eyes, reflection of holographic light in pupils, anamorphic blue horizontal lens flare, hyper-detailed skin texture, master cinematography, {style_info['prompt_suffix']}"
            ),
            StoryboardShot(
                shot_number=6,
                shot_title="Clímax y Salida Épica",
                shot_type="Plano General en Movimiento (Dynamic Tracking Wide)",
                camera_movement="Cámara rápida retrocediendo mientras el protagonista avanza hacia el umbral de luz",
                visual_action="El protagonista activa un impulso propulsor y corre hacia la salida del túnel iluminada por una explosión de luz dorada, mientras la silueta enemiga impacta el suelo tras él.",
                lighting_and_atmosphere="Luz cegadora dorada de salida con silueta recortada en movimiento heroico y estelas de lluvia disolviéndose.",
                dialogue_or_voiceover="[epic crescendo] La cacería... [dramatic pause] apenas comienza.",
                acting_intention="Cierre épico de trailer, potencia vocal y resolución triunfal.",
                voice_cast=default_voice,
                sound_effects_and_music="Explosión orquestal final apoteósica que culmina en un golpe seco de percusión y desvanecimiento a silencio.",
                estimated_duration_sec=round(target_duration_sec / scene_count, 1),
                visual_prompt_optimized=f"Cinematic wide tracking shot, protagonist moving toward a blinding tunnel of bright warm light, silhouette motion blur, epic blockbuster final frame, {style_info['prompt_suffix']}"
            )
        ]

        selected_shots = shots_pool[:scene_count]
        for idx, shot in enumerate(selected_shots):
            shot.shot_number = idx + 1

        clean_premise = input_text.strip() if input_text else "Relato de suspenso y acción cinematográfica"
        usage = TokenTracker.estimate_from_text(prompt_text=clean_premise, completion_text=clean_premise * 8)

        return StoryboardProject(
            title="LA SOMBRA DEL DESTINO (Edición Cinematográfica)",
            logline=f"Inspirado en tu premisa: {clean_premise[:120]}...",
            synopsis=f"En un escenario de alta tensión visual, un protagonista enfrenta una encrucijada crucial ante una revelación oculta. Desglose generado con la arquitectura de NotebookLM en {scene_count} tomas a {aspect_ratio} con actuación vocal {voice_intention['name']}.",
            genre_and_tone="Thriller Cinematográfico de Tensión Creciente",
            visual_style=style_name,
            aspect_ratio=aspect_ratio,
            voice_intention=voice_intention_key,
            language_code=language_code,
            target_duration_seconds=target_duration_sec,
            character_bibles=[
                "Protagonista: Complexión atlética, impermeable táctico oscuro con cuello alto de protección, reloj análogo de titanio, mirada penetrante color avellana, cabello oscuro mojado por lluvia.",
                "Antagonista: Silueta estilizada y veloz, traje contemporáneo de aramida oscura con inserciones luminiscentes reflectantes en muñecas y hombros."
            ],
            shots=selected_shots,
            token_usage=usage
        )
