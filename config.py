import os
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Versiones de modelos de Google Gemini & GenAI (Agosto 2026)
# Ref: https://ai.google.dev/gemini-api/docs/models
#
# Familia Gemini 3.x (estables):
#   gemini-3.5-flash             - Texto/JSON, estructuración de guion, razonamiento, structured output
#   gemini-3.6-flash             - Último y más rápido modelo flash
#   gemini-3.1-pro-preview        - Razonamiento profundo y análisis de directores
#   gemini-3.1-flash-image        - Generación de imágenes nativa y edición multimodal condicionada
#   gemini-3.1-flash-lite-image   - Generación ligera de imágenes
#   gemini-3-pro-image            - Generación de imágenes de alta calidad
#   gemini-3.1-flash-tts-preview  - Síntesis de voz expresiva (TTS de alta fidelidad, multi-speaker y audio tags)
#   gemini-3.1-flash-live-preview - Audio en tiempo real / Live API
#
DEFAULT_TEXT_MODEL = "gemini-3.5-flash"                 # Texto, structured output JSON, análisis
DEEP_REASONING_MODEL = "gemini-3.1-pro-preview"         # Razonamiento profundo y análisis complejo
IMAGE_MODEL = "gemini-3.1-flash-image"                  # Generación nativa de imágenes (response_modalities=IMAGE)
AUDIO_TTS_MODEL = "gemini-3.1-flash-tts-preview"        # Text-to-Speech multivoz de última generación

# Tabla de Precios para Estimación de Costos (USD por millón de tokens / unidad)
MODEL_PRICING = {
    "gemini-3.5-flash": {
        "input_per_million": 0.075,      # $0.075 por 1M tokens de entrada
        "output_per_million": 0.300,     # $0.300 por 1M tokens de salida
    },
    "gemini-3.1-pro-preview": {
        "input_per_million": 1.250,      # $1.25 por 1M tokens de entrada
        "output_per_million": 5.000,     # $5.00 por 1M tokens de salida
    },
    "gemini-3.1-flash-image": {
        "cost_per_image": 0.020,         # $0.020 por imagen generada
    },
    "gemini-3.1-flash-tts-preview": {
        "cost_per_1k_chars": 0.0005,     # $0.0005 por 1,000 caracteres de voz
    }
}

# Límites de seguridad para evitar loops y consumo descontrolado
MAX_TEST_RETRIES = 2
MAX_SEQUENCE_SHOTS = 16

# Matriz de Selección de Etiquetas Creativas (Tag Matrix)
TAG_MATRIX_PRESETS: Dict[str, Dict[str, Any]] = {
    "genres": {
        "title": "🎬 Género",
        "options": [
            {"id": "cyberpunk", "label": "Cyberpunk Neo-Noir", "icon": "🏙️"},
            {"id": "psychological_thriller", "label": "Thriller Psicológico", "icon": "🕵️"},
            {"id": "space_scifi", "label": "Sci-Fi Espacial", "icon": "🚀"},
            {"id": "dark_fantasy", "label": "Fantasía Oscura", "icon": "⚔️"},
            {"id": "gothic_horror", "label": "Terror Gótico", "icon": "🕯️"},
            {"id": "intimate_drama", "label": "Drama Íntimo", "icon": "💔"},
            {"id": "blockbuster_action", "label": "Acción & Adrenalina", "icon": "💥"},
            {"id": "post_apocalyptic", "label": "Postapocalíptico", "icon": "☢️"}
        ]
    },
    "protagonists": {
        "title": "👤 Protagonista",
        "options": [
            {"id": "weary_detective", "label": "Detective Cansado y Cínico", "icon": "🧥"},
            {"id": "rebel_hacker", "label": "Hacker Rebelde Fugitiva", "icon": "💻"},
            {"id": "lone_astronaut", "label": "Astronauta en Misión Solitaria", "icon": "👨‍🚀"},
            {"id": "visionary_scientist", "label": "Científica Obsesionada", "icon": "🔬"},
            {"id": "covert_operative", "label": "Agente Encubierto Traicionado", "icon": "🕶️"},
            {"id": "myth_hunter", "label": "Cazador de Reliquias Antiguas", "icon": "🗡️"},
            {"id": "synthetic_android", "label": "Androide con Conciencia Despertando", "icon": "🤖"}
        ]
    },
    "conflicts": {
        "title": "⚡ Detonante / Conflicto",
        "options": [
            {"id": "forbidden_artifact", "label": "Maletín con Código Prohibido", "icon": "💼"},
            {"id": "alien_signal", "label": "Transmisión Alienígena Inexplicable", "icon": "📡"},
            {"id": "betrayal_ambush", "label": "Emboscada y Traición Interna", "icon": "🗡️"},
            {"id": "countdown_clock", "label": "Cuenta Regresiva de Auto-Destrucción", "icon": "⏳"},
            {"id": "rogue_ai", "label": "IA Militar Fuera de Control", "icon": "🧠"},
            {"id": "time_paradox", "label": "Anomalía Temporal Repitiéndose", "icon": "🌀"},
            {"id": "deadly_secret", "label": "Revelación de Identidad Oculta", "icon": "📜"}
        ]
    },
    "atmospheres": {
        "title": "🌌 Atmósfera & Entorno",
        "options": [
            {"id": "rainy_neotokyo", "label": "Neo-Tokyo Lluvioso y Neones", "icon": "🌧️"},
            {"id": "snowy_cabin", "label": "Cabaña Aislada en Ventisca", "icon": "❄️"},
            {"id": "derelict_ship", "label": "Nave Abandonada a Oscuras", "icon": "🛸"},
            {"id": "underground_catacombs", "label": "Subsuelo y Túneles Clandestinos", "icon": "🔦"},
            {"id": "golden_dusk", "label": "Hora Dorada Melancólica en Ciudad", "icon": "🌇"},
            {"id": "victorian_mansion", "label": "Mansión Victoriana en Penumbra", "icon": "🏰"},
            {"id": "scorched_wasteland", "label": "Páramo Desértico con Polvo Rojo", "icon": "🏜️"}
        ]
    },
    "tones": {
        "title": "🎭 Tono & Emoción",
        "options": [
            {"id": "tense_claustrophobic", "label": "Tenso y Claustrofóbico", "icon": "😰"},
            {"id": "frenetic_adrenaline", "label": "Frenético y Lleno de Urgencia", "icon": "⚡"},
            {"id": "poetic_melancholy", "label": "Poético y Melancólico", "icon": "🎻"},
            {"id": "epic_triumphant", "label": "Épico y Triunfal", "icon": "🎺"},
            {"id": "eerie_mysterious", "label": "Inquietante y Enigmático", "icon": "👁️"}
        ]
    }
}

# Soporte Multilingüe (70+ idiomas en Gemini 3.1 TTS)
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "es_MX": {
        "name": "Español (México / Latinoamérica)",
        "flag": "🇲🇽",
        "system_instruction": "Español mexicano neutro y cinematográfico de alta calidad.",
        "locale": "es-MX"
    },
    "es_ES": {
        "name": "Español (España)",
        "flag": "🇪🇸",
        "system_instruction": "Español de España con dicción castellana y vocabulario cinematográfico.",
        "locale": "es-ES"
    },
    "en_US": {
        "name": "English (United States)",
        "flag": "🇺🇸",
        "system_instruction": "Standard American English with cinematic Hollywood storytelling cadence.",
        "locale": "en-US"
    },
    "en_GB": {
        "name": "English (British / UK)",
        "flag": "🇬🇧",
        "system_instruction": "British English with articulate dramatic delivery.",
        "locale": "en-GB"
    },
    "fr_FR": {
        "name": "Français (France)",
        "flag": "🇫🇷",
        "system_instruction": "Français cinématographique avec une grande expressivité et élégance.",
        "locale": "fr-FR"
    },
    "de_DE": {
        "name": "Deutsch (Deutschland)",
        "flag": "🇩🇪",
        "system_instruction": "Deutsches cineastisches Storytelling mit präziser Aussprache.",
        "locale": "de-DE"
    },
    "pt_BR": {
        "name": "Português (Brasil)",
        "flag": "🇧🇷",
        "system_instruction": "Português brasileiro expressivo, caloroso e cinematográfico.",
        "locale": "pt-BR"
    },
    "it_IT": {
        "name": "Italiano (Italia)",
        "flag": "🇮🇹",
        "system_instruction": "Italiano cinematografico con passione e ritmo drammatico.",
        "locale": "it-IT"
    },
    "ja_JP": {
        "name": "日本語 (Japanese)",
        "flag": "🇯🇵",
        "system_instruction": "映画のような表現力豊かな日本語（アニメ・映画風のナレーション）。",
        "locale": "ja-JP"
    }
}

# Catálogo de Etiquetas de Audio Expresivas (Expressive Audio Tags)
EXPRESSIVE_AUDIO_TAGS: List[Dict[str, str]] = [
    {"tag": "[whispers]", "label": "🤫 Susurro", "description": "Baja la intensidad a un susurro íntimo o tenso"},
    {"tag": "[dramatic pause]", "label": "⏱️ Pausa Dramática", "description": "Inserta un silencio medido de tensión"},
    {"tag": "[slow breath]", "label": "😮‍💨 Respiración", "description": "Toma de aire antes de hablar"},
    {"tag": "[gasp]", "label": "😱 Jadeo / Asombro", "description": "Reacción súbita de sorpresa o susto"},
    {"tag": "[chuckles]", "label": "😏 Risa Irónica", "description": "Risa contenida o sarcástica"},
    {"tag": "[sighs]", "label": "😔 Suspiro", "description": "Exhalación de alivio, pesadez o tristeza"},
    {"tag": "[urgent shout]", "label": "⚡ Grito Urgente", "description": "Proyección vocal de alerta y acción"},
    {"tag": "[fast cadence]", "label": "🏃‍♂️ Ritmo Rápido", "description": "Acelera la cadencia del habla"},
    {"tag": "[deep resonance]", "label": "🎙️ Voz Profunda", "description": "Resonancia grave y solemne"},
    {"tag": "[emotional tremor]", "label": "🥺 Temblor Emotivo", "description": "Quiebre de voz por congoja o conmoción"}
]

# Mapeo de voces para Gemini 3.1 Flash TTS
VOICE_MAPPINGS: Dict[str, Dict[str, str]] = {
    "elena": {
        "voice_name": "Aoede",  # Voz femenina sofisticada, cálida y cinematográfica
        "role": "Directora de Fotografía / Personaje Femenino A",
        "description": "Voz femenina articulada, entusiasta y analítica",
        "gender": "female"
    },
    "marcos": {
        "voice_name": "Puck",   # Voz masculina ágil, curiosa y dinámica
        "role": "Guionista / Personaje Masculino B",
        "description": "Voz masculina reflexiva, persuasiva y enérgica",
        "gender": "male"
    },
    "narrator_epic": {
        "voice_name": "Charon", # Voz grave, pausada y teatral para locución y voice-over
        "role": "Narrador Épico Cinematográfico",
        "description": "Voz profunda con presencia dramática de trailer",
        "gender": "male"
    },
    "narrator_tense": {
        "voice_name": "Fenrir", # Voz áspera, tensa y atmosférica
        "role": "Narrador de Thriller y Suspenso",
        "description": "Voz grave y misteriosa para drama psicológico",
        "gender": "male"
    },
    "narrator_warm": {
        "voice_name": "Aoede",  # Voz cálida y humana
        "role": "Narradora Emotiva y Cercana",
        "description": "Voz femenina cálida con gran sensibilidad emocional",
        "gender": "female"
    },
    "narrator_dynamic": {
        "voice_name": "Kore",   # Voz energética y vibrante
        "role": "Narradora de Acción y Aventura",
        "description": "Voz femenina ágil con proyección y energía",
        "gender": "female"
    }
}

# Presets de Intención y Actuación Vocal para las Historias
VOICE_INTENTIONS: Dict[str, Dict[str, str]] = {
    "epic_cinematic": {
        "name": "🎬 Trailer Épico / Impacto Cinematográfico",
        "default_voice": "narrator_epic",
        "description": "Voz profunda, ritmo pausado con peso dramático, pausas calculadas y presencia de trailer de Hollywood.",
        "prompt_directive": "epic cinematic trailer voice, deep resonant tone, gravitas, dramatic pauses, powerful intensity, movie trailer narrator style",
        "audio_tags": ["[dramatic pause]", "[deep breath]", "[whispers with intensity]", "[epic crescendo]"]
    },
    "tense_thriller": {
        "name": "🕵️ Thriller Tenso / Suspenso Susurrado",
        "default_voice": "narrator_tense",
        "description": "Tono contenido, susurros dramáticos, respiración y tensión psicológica in crescendo.",
        "prompt_directive": "tense psychological thriller narration, whispered intensity, anxious breathing, eerie tone, edge-of-seat pacing",
        "audio_tags": ["[whispers]", "[anxious breath]", "[gasp]", "[sudden silence]"]
    },
    "emotional_warmth": {
        "name": "❤️ Drama Humano / Cálido y Emotivo",
        "default_voice": "narrator_warm",
        "description": "Cadencia cercana, intimista y conmovedora, con inflexiones de emoción genuina.",
        "prompt_directive": "warm empathetic narration, emotional depth, heartfelt and vulnerable storytelling, gentle cadence",
        "audio_tags": ["[soft sigh]", "[emotional pause]", "[tender whisper]", "[warm smile]"]
    },
    "noir_detective": {
        "name": "🥃 Film Noir / Detective Cínico",
        "default_voice": "marcos",
        "description": "Voz áspera de monólogo interior, ritmo pausado de jazz, cinismo urbano y lluvia.",
        "prompt_directive": "gritty film noir inner monologue, cynical detective tone, dry wit, rhythmic cadence, smokey jazz atmosphere",
        "audio_tags": ["[cynical chuckle]", "[slow sigh]", "[strikes a match]", "[weary pause]"]
    },
    "dynamic_action": {
        "name": "⚡ Acción & Adrenalina / Alta Energía",
        "default_voice": "narrator_dynamic",
        "description": "Ritmo rápido, urgencia en cada palabra, volumen proyectado y aceleración dramática.",
        "prompt_directive": "high adrenaline action narration, urgent cadence, energetic, intense excitement, fast-paced delivery",
        "audio_tags": ["[intense shout]", "[heavy breath]", "[fast cadence]", "[urgent warning]"]
    },
    "whimsical_fantasy": {
        "name": "✨ Fantasía & Animación / Lúdica",
        "default_voice": "narrator_warm",
        "description": "Voz colorida, mágica, con cambios divertidos de tono y expresión teatral.",
        "prompt_directive": "whimsical fantasy storyteller, expressive theatrical delivery, lively and enchanting, fairytale wonder",
        "audio_tags": ["[playful laugh]", "[wondering gasp]", "[mischievous whisper]", "[joyful sparkle]"]
    }
}

# Parámetros de Audio PCM / WAV
AUDIO_SAMPLE_RATE = 24000  # 24kHz estándar de Gemini TTS
AUDIO_CHANNELS = 1         # Mono
AUDIO_SAMPLE_WIDTH = 2     # 16-bit (2 bytes per sample)

# Presets de Estilo Visual Cinematográfico
STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "cinematic_concept": {
        "name": "Cinematic Concept Art",
        "description": "Estilo cinematográfico hiperdetallado, iluminación volumétrica, texturas realistas y profundidad de campo de cámara 35mm.",
        "prompt_suffix": "cinematic concept art, volumetric lighting, 8k resolution, photorealistic cinematic lighting, atmospheric, depth of field, dramatic composition, mastershot, 35mm lens",
        "negative_prompt": "cartoon, 3d render, plastic, oversaturated, amateur sketch, watermark, signature, text, blurry"
    },
    "pencil_sketch": {
        "name": "Storyboard Pencil Sketch",
        "description": "Boceto profesional a lápiz y carboncillo de producción cinematográfica, líneas limpias y sombreado rápido de storyboard.",
        "prompt_suffix": "professional movie production storyboard, dynamic charcoal and pencil sketch, clean linework, rough values, high contrast shading, film production art, black and white sketch with subtle gray wash",
        "negative_prompt": "color, photorealistic, 3d render, painting, watercolor, blurry, messy scribble, text"
    },
    "film_noir": {
        "name": "Film Noir Graphic Novel",
        "description": "Alto contraste en blanco y negro, sombras duras tipo claroscuro, estética de novela gráfica estilo Sin City / Batman.",
        "prompt_suffix": "film noir graphic novel style, extreme chiaroscuro, high contrast black and white, deep shadows, razor sharp silhouettes, moody atmosphere, comic book ink art style, dramatic rim light",
        "negative_prompt": "color, soft pastel, cheerful, flat lighting, 3d render, photoreal, blurry"
    },
    "studio_ghibli": {
        "name": "Studio Ghibli Watercolor",
        "description": "Pintura al agua suave, fondos exuberantes pintados a mano, iluminación cálida y emotiva estilo animación tradicional japonesa.",
        "prompt_suffix": "Studio Ghibli style, hand-painted watercolor background, lush natural lighting, soft atmospheric perspective, warm nostalgic color palette, master animation background, painted by Hayao Miyazaki",
        "negative_prompt": "dark gritty, photoreal 3d, cgi, harsh shadows, monochrome, bad anatomy, text"
    },
    "unreal_engine_3d": {
        "name": "Unreal Engine 5 3D Previz",
        "description": "Previsualización 3D digital de alta fidelidad, iluminación Lumen y Ray Tracing, texturas nítidas de pre-producción.",
        "prompt_suffix": "Unreal Engine 5 cinematic previsualization, ray tracing, Lumen lighting, 3D render octane render, crisp production model, realistic materials, photorealistic CGI, cinematic camera angle",
        "negative_prompt": "2d drawing, flat, watercolor, messy sketch, cartoon, low poly, noisy, blurry"
    },
    "anime_shonen": {
        "name": "Anime / Modern Animation",
        "description": "Animación japonesa moderna, líneas dinámicas de acción, colores vibrantes e iluminación de alto impacto dramático.",
        "prompt_suffix": "modern high-budget anime style, Ufotable / MAPPA aesthetic, dynamic action lines, cel shading, vibrant colors, crisp key animation frame, dramatic lens flare, 4k anime masterpiece",
        "negative_prompt": "photorealistic, western comic, live action, low quality, sketch, washed out"
    },
    "vintage_35mm": {
        "name": "Vintage 35mm Film Still",
        "description": "Fotograma de película analógica de 35mm, grano sutil, tonalidades Kodak Portra y atmósfera cinematográfica clásica.",
        "prompt_suffix": "authentic 35mm film still, Kodak Portra 400 color grading, subtle film grain, natural anamorphic lens distortion, vintage cinema aesthetic, 1970s 1980s cinematic lighting, masterpiece",
        "negative_prompt": "digital CGI, modern video look, cartoon, oversaturated, HDR overly sharpened, 3d render"
    }
}

# Ratios de Aspecto soportados
ASPECT_RATIOS: Dict[str, str] = {
    "16:9": "16:9 (Panorámico Cinematográfico Estándar)",
    "2.39:1": "2.39:1 (Cinemascope / Anamórfico Épico)",
    "9:16": "9:16 (Vertical / Reels / TikTok / Mobile)",
    "4:3": "4:3 (Televisión Clásica / Academy Ratio)",
    "1:1": "1:1 (Cuadrado / Social Feed)"
}
