import os
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Versiones de modelos de Google Gemini & GenAI (Agosto 2026)
# Ref: https://ai.google.dev/gemini-api/docs/models
#
DEFAULT_TEXT_MODEL = "gemini-3.5-flash"                 # Texto, structured output JSON, análisis
DEEP_REASONING_MODEL = "gemini-3.1-pro-preview"         # Razonamiento profundo y análisis complejo
IMAGE_MODEL = "gemini-3.1-flash-image"                  # Generación nativa de imágenes (response_modalities=IMAGE)
AUDIO_TTS_MODEL = "gemini-3.1-flash-tts-preview"        # Text-to-Speech multivoz de última generación

# Tabla de Precios Oficial de Google Gemini para Estimación Exacta de Costos (USD)
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
        "cost_per_1k_chars": 0.0005,     # $0.0005 por 1,000 caracteres de voz ($0.50 / 1M chars)
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

# Catálogo Expandido de Etiquetas de Audio Expresivas (16 Expressive Audio Tags)
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
    {"tag": "[emotional tremor]", "label": "🥺 Temblor Emotivo", "description": "Quiebre de voz por congoja o conmoción"},
    {"tag": "[cold monotone]", "label": "🤖 Tono Sintético", "description": "Voz robótica, fría y calculada sin emoción"},
    {"tag": "[tense whisper]", "label": "😰 Susurro Ansioso", "description": "Susurro temeroso bajo peligro inminente"},
    {"tag": "[intense crescendo]", "label": "🔥 Crescendo Vocal", "description": "Aumento progresivo de volumen y pasión"},
    {"tag": "[soft sigh]", "label": "🥀 Suspiro Suave", "description": "Exhalación delicada y melancólica"},
    {"tag": "[tactical radio]", "label": "📻 Radio Táctica", "description": "Cadencia militar comprimida de intercomunicador"},
    {"tag": "[weary pause]", "label": "🚬 Pausa de Fatiga", "description": "Silencio de cansancio existencial y pesadez"}
]

# Mapeo de voces para Gemini 3.1 Flash TTS
VOICE_MAPPINGS: Dict[str, Dict[str, str]] = {
    "elena": {
        "voice_name": "Aoede",
        "role": "Directora de Fotografía / Personaje Femenino A",
        "description": "Voz femenina articulada, entusiasta y analítica",
        "gender": "female"
    },
    "marcos": {
        "voice_name": "Puck",
        "role": "Guionista / Personaje Masculino B",
        "description": "Voz masculina reflexiva, persuasiva y enérgica",
        "gender": "male"
    },
    "narrator_epic": {
        "voice_name": "Charon",
        "role": "Narrador Épico Cinematográfico",
        "description": "Voz profunda con presencia dramática de trailer",
        "gender": "male"
    },
    "narrator_tense": {
        "voice_name": "Fenrir",
        "role": "Narrador de Thriller y Suspenso",
        "description": "Voz grave y misteriosa para drama psicológico",
        "gender": "male"
    },
    "narrator_warm": {
        "voice_name": "Aoede",
        "role": "Narradora Emotiva y Cercana",
        "description": "Voz femenina cálida con gran sensibilidad emocional",
        "gender": "female"
    },
    "narrator_dynamic": {
        "voice_name": "Kore",
        "role": "Narradora de Acción y Aventura",
        "description": "Voz femenina ágil con proyección y energía",
        "gender": "female"
    }
}

# Presets de Intención y Actuación Vocal para las Historias (11 Presets)
VOICE_INTENTIONS: Dict[str, Dict[str, str]] = {
    "epic_cinematic": {
        "name": "🎬 Trailer Épico / Impacto Cinematográfico",
        "category": "Hollywood & Blockbuster",
        "default_voice": "narrator_epic",
        "description": "Voz profunda, ritmo pausado con peso dramático, pausas calculadas y presencia de trailer de Hollywood.",
        "prompt_directive": "epic cinematic trailer voice, deep resonant tone, gravitas, dramatic pauses, powerful intensity, movie trailer narrator style",
        "audio_tags": ["[dramatic pause]", "[deep resonance]", "[intense crescendo]", "[slow breath]"]
    },
    "tense_thriller": {
        "name": "🕵️ Thriller Tenso / Suspenso Susurrado",
        "category": "Suspenso & Crimen",
        "default_voice": "narrator_tense",
        "description": "Tono contenido, susurros dramáticos, respiración y tensión psicológica in crescendo.",
        "prompt_directive": "tense psychological thriller narration, whispered intensity, anxious breathing, eerie tone, edge-of-seat pacing",
        "audio_tags": ["[whispers]", "[tense whisper]", "[gasp]", "[dramatic pause]"]
    },
    "emotional_warmth": {
        "name": "❤️ Drama Humano / Cálido y Emotivo",
        "category": "Drama & Intimidad",
        "default_voice": "narrator_warm",
        "description": "Cadencia cercana, intimista y conmovedora, con inflexiones de emoción genuina y vulnerabilidad.",
        "prompt_directive": "warm empathetic narration, emotional depth, heartfelt and vulnerable storytelling, gentle cadence",
        "audio_tags": ["[soft sigh]", "[emotional tremor]", "[whispers]", "[slow breath]"]
    },
    "noir_detective": {
        "name": "🥃 Film Noir / Detective Cínico",
        "category": "Suspenso & Crimen",
        "default_voice": "marcos",
        "description": "Voz áspera de monólogo interior, ritmo pausado de jazz, cinismo urbano, lluvia y humo de tabaco.",
        "prompt_directive": "gritty film noir inner monologue, cynical detective tone, dry wit, rhythmic cadence, smokey jazz atmosphere",
        "audio_tags": ["[chuckles]", "[weary pause]", "[sighs]", "[slow breath]"]
    },
    "dynamic_action": {
        "name": "⚡ Acción & Adrenalina / Alta Energía",
        "category": "Hollywood & Blockbuster",
        "default_voice": "narrator_dynamic",
        "description": "Ritmo rápido, urgencia en cada palabra, volumen proyectado y aceleración dramática.",
        "prompt_directive": "high adrenaline action narration, urgent cadence, energetic, intense excitement, fast-paced delivery",
        "audio_tags": ["[urgent shout]", "[fast cadence]", "[intense crescendo]", "[gasp]"]
    },
    "whimsical_fantasy": {
        "name": "✨ Fantasía & Animación / Lúdica",
        "category": "Fantasía & Aventura",
        "default_voice": "narrator_warm",
        "description": "Voz colorida, mágica, con cambios divertidos de tono, asombro y expresión teatral.",
        "prompt_directive": "whimsical fantasy storyteller, expressive theatrical delivery, lively and enchanting, fairytale wonder",
        "audio_tags": ["[chuckles]", "[gasp]", "[whispers]", "[slow breath]"]
    },
    "documentary_natural": {
        "name": "🎙️ Documental & Ensayo / Neutral y Reflexiva",
        "category": "Documental & Ensayo",
        "default_voice": "elena",
        "description": "Dicción impecable, objetividad serena, ritmo cadencioso de narración de National Geographic o BBC.",
        "prompt_directive": "prestigious documentary narrator, calm authoritative voice, precise articulation, articulate storytelling",
        "audio_tags": ["[slow breath]", "[dramatic pause]", "[deep resonance]"]
    },
    "cold_synthetic": {
        "name": "🤖 IA & Androide / Sintética y Calculada",
        "category": "Ciencia Ficción",
        "default_voice": "elena",
        "description": "Voz de inteligencia artificial o androide, fría, sin modulación emotiva, quirúrgica y precisa.",
        "prompt_directive": "synthetic AI voice, cold calculated monotone, precise pacing, emotionless digital intelligence, HAL 9000 style",
        "audio_tags": ["[cold monotone]", "[dramatic pause]"]
    },
    "gothic_horror": {
        "name": "🕯️ Terror Gótico / Pánico y Temblor",
        "category": "Terror & Misterio",
        "default_voice": "narrator_tense",
        "description": "Voz quebradiza, susurros temblorosos, respiración agitada y atmósfera de pesadilla gótica.",
        "prompt_directive": "gothic horror narrator, terrified trembling whispers, shallow panic breathing, dread, sinister folklore",
        "audio_tags": ["[emotional tremor]", "[tense whisper]", "[gasp]", "[slow breath]"]
    },
    "spy_espionage": {
        "name": "🕶️ Espionaje & Táctica / Susurro Cifrado",
        "category": "Suspenso & Crimen",
        "default_voice": "marcos",
        "description": "Tono profesional de agente encubierto, susurros tácticos por radio y calma bajo fuego.",
        "prompt_directive": "covert espionage operative, tactical quiet whisper, radio communication cadence, calm under extreme pressure",
        "audio_tags": ["[tactical radio]", "[tense whisper]", "[fast cadence]", "[dramatic pause]"]
    },
    "warrior_valiant": {
        "name": "⚔️ Épica Medieval / Discurso de Batalla",
        "category": "Fantasía & Aventura",
        "default_voice": "narrator_epic",
        "description": "Voz solemne de comandante, proyección marcial y llamado al heroísmo.",
        "prompt_directive": "valiant warrior commander, booming battle speech, martial solemnity, heroic inspiration, Lord of the Rings style",
        "audio_tags": ["[deep resonance]", "[intense crescendo]", "[urgent shout]"]
    }
}

# Parámetros de Audio PCM / WAV
AUDIO_SAMPLE_RATE = 24000  # 24kHz estándar de Gemini TTS
AUDIO_CHANNELS = 1         # Mono
AUDIO_SAMPLE_WIDTH = 2     # 16-bit (2 bytes per sample)

# Catálogo Expandido de Estilos Visuales Cinematográficos (16 Estilos)
STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    # --- AUTEUR CINEMA (DIRECTORES DE AUTOR) ---
    "villeneuve_scifi": {
        "name": "🎬 Denis Villeneuve (Dune / Blade Runner 2049)",
        "category": "Directores de Autor",
        "description": "Escalas monumentales brutalistas, paleta ocre/cian desaturada, niebla volumétrica y lentes anamórficas Cooke.",
        "prompt_suffix": "directed by Denis Villeneuve, cinematography by Roger Deakins, monumental brutalist scale, atmospheric dust haze, desaturated ochre and cyan tones, anamorphic 65mm lens, majestic cinematic lighting, masterpiece",
        "negative_prompt": "cartoon, oversaturated neon, flat lighting, amateur sketch, 3d render plastic, blurry, watermark"
    },
    "wes_anderson": {
        "name": "🏛️ Wes Anderson (The Grand Budapest Hotel)",
        "category": "Directores de Autor",
        "description": "Simetría axial perfecta, composición frontal de casa de muñecas, paleta pastel saturada y texturas artesanales.",
        "prompt_suffix": "directed by Wes Anderson, perfectly centered symmetrical composition, dollhouse framing, vibrant pastel color palette, whimsical vintage textures, theatrical flat lighting, 35mm film still",
        "negative_prompt": "dark gritty, Dutch angle, messy asymmetry, harsh shadows, monochrome, horror, cgi"
    },
    "del_toro_gothic": {
        "name": "🕯️ Guillermo del Toro (El Laberinto del Fauno)",
        "category": "Directores de Autor",
        "description": "Claroscuro barroco, contraste ámbar cálido y azul cobalto, texturas victorianas orgánicas y misticismo oscuro.",
        "prompt_suffix": "directed by Guillermo del Toro, dark gothic fairy tale aesthetic, rich amber and cobalt blue chiaroscuro lighting, intricate organic Victorian textures, moody cinematic shadows, 35mm film",
        "negative_prompt": "bright pastel, clean minimalist, flat lighting, cartoon, oversaturated modern look"
    },
    "nolan_imax_70mm": {
        "name": "🎞️ Christopher Nolan (Oppenheimer / Interstellar 70mm)",
        "category": "Directores de Autor",
        "description": "Formato IMAX 70mm de alta resolución, luz natural cruda, grano fotoquímico fino y realismo físico tangible.",
        "prompt_suffix": "shot on IMAX 70mm film, cinematography by Hoyte van Hoytema, Christopher Nolan direction, naturalistic lighting, razor sharp chemical film grain, authentic physical atmosphere, blockbuster scale",
        "negative_prompt": "digital CGI plastic look, anime, oversaturated videogame art, cartoon, blurry"
    },
    "fincher_clinical": {
        "name": "🔍 David Fincher (Seven / Mindhunter)",
        "category": "Directores de Autor",
        "description": "Iluminación de baja clave con dominante verdosa de tungsteno, encuadres bloqueados con precisión milimétrica.",
        "prompt_suffix": "directed by David Fincher, cinematography by Jeff Cronenweth, low-key lighting with sickly green-yellow tungsten tint, razor sharp locked-off framing, deep velvety shadows, clinical precision",
        "negative_prompt": "warm cheerful, soft focus, bright sunlight, pastel colors, cartoon, whimsical"
    },
    "wong_kar_wai_neon": {
        "name": "🏮 Wong Kar-wai (In the Mood for Love)",
        "category": "Directores de Autor",
        "description": "Step-printing, desenfoque poético de movimiento, neones esmeralda y rojo rubí, lentes 50mm f/1.2 melancólicas.",
        "prompt_suffix": "directed by Wong Kar-wai, cinematography by Christopher Doyle, saturated emerald green and ruby red neon hues, poetic motion blur, step-printing aesthetic, nostalgic 1960s Hong Kong cinema, moody shallow depth of field",
        "negative_prompt": "sterile, crisp clinical CGI, bright flat daylight, 3d cartoon, low quality"
    },

    # --- ANIMACIÓN & TÉCNICAS DE PRODUCCIÓN ---
    "studio_ghibli": {
        "name": "🍃 Studio Ghibli (Hayao Miyazaki Acuarela)",
        "category": "Animación & Ilustración",
        "description": "Pintura al agua suave, fondos exuberantes pintados a mano, iluminación cálida y emotiva estilo animación tradicional.",
        "prompt_suffix": "Studio Ghibli aesthetic, hand-painted watercolor and gouache background, lush natural lighting, soft atmospheric perspective, warm nostalgic color palette, painted by Hayao Miyazaki, anime masterpiece",
        "negative_prompt": "dark gritty, photoreal 3d, cgi, harsh shadows, monochrome, bad anatomy, text"
    },
    "anime_mappa_ufotable": {
        "name": "⚡ Anime Shōnen Moderno (MAPPA / Ufotable)",
        "category": "Animación & Ilustración",
        "description": "Animación de alta producción, líneas de acción dinámicas, cel-shading nítido y efectos de iluminación digital intensa.",
        "prompt_suffix": "modern high-budget cinematic anime, MAPPA and Ufotable key animation frame, dynamic action lines, crisp cel shading, dramatic particle lighting and chromatic flares, 4k masterpiece",
        "negative_prompt": "photorealistic, western comic, sketch, low quality, washed out, blurry"
    },
    "disney_color_script": {
        "name": "🎨 Disney / Pixar Color Script (Pastel & Gouache)",
        "category": "Arte de Preproducción",
        "description": "Boceto de color conceptual para largometraje animado, iluminación emocional y composición pictórica pura.",
        "prompt_suffix": "feature animation color script, gouache and oil pastel production painting, emotional lighting design, visual development art, Disney Pixar master artist, expressive brushstrokes",
        "negative_prompt": "photorealistic live action, 3d render octane, harsh noise, muddy colors"
    },
    "stop_motion_laika": {
        "name": "🧶 Stop-Motion Artesanal (Laika / Coraline)",
        "category": "Animación & Ilustración",
        "description": "Texturas táctiles de arcilla, tela en miniatura, madera tallada e iluminación cinematográfica real en estudio.",
        "prompt_suffix": "handcrafted stop-motion animation puppet, tactile clay and miniature fabric textures, detailed physical set, miniature studio lighting, Laika studio aesthetic, macro depth of field",
        "negative_prompt": "2d flat drawing, digital CGI render, photoreal human, anime, glossy plastic"
    },
    "film_noir_graphic": {
        "name": "🕶️ Graphic Novel Noir (Sin City / Comic Ink)",
        "category": "Novela Gráfica & Cómic",
        "description": "Alto contraste en blanco y negro puro con sombras duras tipo claroscuro y acentos de color selectivo.",
        "prompt_suffix": "graphic novel ink art style, Frank Miller Sin City aesthetic, extreme black and white chiaroscuro, razor sharp silhouettes, moody atmospheric rain, high contrast comic masterwork",
        "negative_prompt": "soft pastel, cheerful, flat lighting, 3d render, photoreal, blurry"
    },
    "pencil_sketch": {
        "name": "✏️ Storyboard Tradicional (Lápiz & Carboncillo)",
        "category": "Arte de Preproducción",
        "description": "Boceto profesional a lápiz y carboncillo de producción cinematográfica, trazos limpios y valores tonales en escala de grises.",
        "prompt_suffix": "professional movie production storyboard, dynamic charcoal and pencil sketch, clean linework, rough values, high contrast shading, film production art, black and white sketch with subtle gray wash",
        "negative_prompt": "color, photorealistic, 3d render, painting, watercolor, blurry, messy scribble, text"
    },
    "vintage_35mm_portra": {
        "name": "📷 35mm Analógico Kodak Portra 400 (New Hollywood)",
        "category": "Cinematografía Clásica",
        "description": "Fotograma de película analógica de 35mm, grano sutil, tonalidades Kodak Portra y atmósfera cinematográfica de los 70s.",
        "prompt_suffix": "authentic 35mm film still, Kodak Portra 400 color grading, subtle film grain, natural anamorphic lens distortion, vintage cinema aesthetic, 1970s cinematic lighting, masterpiece",
        "negative_prompt": "digital CGI, modern video look, cartoon, oversaturated, HDR overly sharpened, 3d render"
    },
    "unreal_engine_5": {
        "name": "🎮 Unreal Engine 5 Previz 3D (Lumen & Nanite)",
        "category": "Previsualización Digital",
        "description": "Previsualización 3D digital de alta fidelidad, iluminación en tiempo real Lumen y Ray Tracing de preproducción.",
        "prompt_suffix": "Unreal Engine 5 cinematic previsualization, ray tracing, Lumen lighting, 3D render octane render, crisp production model, realistic materials, photorealistic CGI, cinematic camera angle",
        "negative_prompt": "2d drawing, flat, watercolor, messy sketch, cartoon, low poly, noisy, blurry"
    },
    "documentary_16mm": {
        "name": "🎥 Documental Inmersivo 16mm (Roger Deakins)",
        "category": "Cinematografía Clásica",
        "description": "Cámara al hombro inmersiva, luz natural disponible, grano orgánico de 16mm y textura realista sin artificios.",
        "prompt_suffix": "raw 16mm documentary film still, handheld camera angle, natural available light, organic film grain, authentic gritty realism, cinematic documentary masterpiece",
        "negative_prompt": "studio glossy lighting, 3d CGI, anime, doll face, oversaturated fantasy"
    },
    "cinematic_concept": {
        "name": "✨ Concept Art Cinematográfico Blockbuster 8K",
        "category": "Arte de Preproducción",
        "description": "Estilo cinematográfico hiperdetallado, iluminación volumétrica, texturas realistas y profundidad de campo de cámara 35mm.",
        "prompt_suffix": "cinematic concept art, volumetric lighting, 8k resolution, photorealistic cinematic lighting, atmospheric, depth of field, dramatic composition, mastershot, 35mm lens",
        "negative_prompt": "cartoon, 3d render, plastic, oversaturated, amateur sketch, watermark, signature, text, blurry"
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
