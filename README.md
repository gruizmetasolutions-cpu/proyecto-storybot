# 🎬 Proyecto StoryBot (Storyboard Studio Pro)

> **Plataforma Integral de Generación de Storyboards Cinematográficos, Coherencia Visual Secuencial y Audio Overview con Google Gemini 3.x**

![StoryBot Banner](https://img.shields.io/badge/Gemini_3.x-Powered-3b82f6?style=for-the-badge&logo=google)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## 🌟 Características Principales

### 1. 🎞️ Pipeline de Coherencia Visual Secuencial (Character Anchor Sheet)
- **Character Anchor Sheet (Paso 0)**: Genera un fotograma maestro inmutable basado en la *Character Bible* (facciones, vestuario, peinado y accesorios).
- **Encadenamiento Secuencial ($K-1 \to K$)**: Cada plano se renderiza condicionado al Anchor Sheet y al plano anterior, garantizando continuidad de iluminación, atmósfera, ángulo y consistencia del protagonista.
- **Modelos**: Generación nativa con `gemini-3.1-flash-image` (`response_modalities=["IMAGE"]`).

### 2. 🎭 Actuación Vocal & Audio Tags Expresivos
- **Presets de Actuación Vocal**:
  - 🎬 *Trailer Épico / Impacto Cinematográfico* (`Charon`)
  - 🕵️ *Thriller Tenso / Suspenso Susurrado* (`Fenrir`)
  - ❤️ *Drama Humano / Cálido y Emotivo* (`Aoede`)
  - 🥃 *Film Noir / Detective Cínico* (`Puck`)
  - ⚡ *Acción & Adrenalina / Alta Energía* (`Kore`)
  - ✨ *Fantasía & Animación / Lúdica* (`Aoede`)
- **Audio Tags Integrados**: Control de pausas, emociones y cadencia directamente en el guion con chips interactivos (`[whispers]`, `[dramatic pause]`, `[slow breath]`, `[gasp]`, `[chuckles]`, `[sighs]`, `[urgent shout]`, `[fast cadence]`, `[deep resonance]`).
- **Normalización Multilingüe**: Acepta tags en español (`[susurro]`, `[pausa]`) y los traduce automáticamente al estándar de Gemini TTS.

### 3. 🎙️ Director Podcast & Diálogo Multi-Hablante Nativo
- **Sesión de Audio Overview (2 Hosts)**: Diálogo crítico entre **Elena** (*Aoede - Directora Visual*) y **Marcos** (*Puck - Guionista Principal*).
- **Single-Request Multi-Speaker TTS**: Síntesis nativa de ambos personajes en una sola solicitud con `MultiSpeakerVoiceConfig` en `gemini-3.1-flash-tts-preview`.
- Conversión a WAV de 24,000 Hz / 16-bit Mono.

### 4. 📱 Animatic Cinema Player con Viewport Adaptable
- Detección automática y ajuste responsive al formato del proyecto:
  - 📱 **9:16 Vertical**: Formato smartphone para Reels, TikTok y Shorts.
  - 🎬 **2.39:1 Cinemascope**: Pantalla ancha anamórfica de cine.
  - 📺 **4:3 Classic TV**: Proporción clásica de televisión.
  - 🟦 **1:1 Square**: Proporción cuadrada de redes sociales.
  - 🖥️ **16:9 Widescreen**: Formato panorámico estándar.
- Modo Ken Burns con zoom-pan dinámico y subtítulos sincronizados.

### 5. 🌐 Soporte Multilingüe (70+ Idiomas)
- Selector de idioma con soporte nativo para:
  - 🇲🇽 **Español (México / Latinoamérica)**
  - 🇪🇸 **Español (España / Castellano)**
  - 🇺🇸 **English (United States)**
  - 🇬🇧 **English (British / UK)**
  - 🇫🇷 **Français (France)**
  - 🇩🇪 **Deutsch (Deutschland)**
  - 🇧🇷 **Português (Brasil)**
  - 🇮🇹 **Italiano (Italia)**
  - 🇯🇵 **日本語 (Japanese)**

### 6. 🪙 Calculador de Tokens y Estimador de Costos
- Módulo `TokenTracker` con precios oficiales de Google Gemini (entrada/salida de texto, imágenes generadas y caracteres sintetizados).
- Badge interactivo en la barra superior con acumulación en tiempo real.

### 7. 🛡️ Suite de Auditoría de Coherencia IA (0-100)
- Módulo `CoherenceEvaluator` que califica:
  - Flujo Narrativo (30%)
  - Consistencia de Personaje (30%)
  - Continuidad de Estilo Visual (25%)
  - Calidad de Audio y Diálogos (15%)

---

## 🏗️ Arquitectura de Modelos (Gemini 3.x)

| Función | Modelo Gemini | Rol |
|---|---|---|
| **Estructuración & Guion** | `gemini-3.5-flash` | Desglose de planos, Structured JSON, character bibles |
| **Razonamiento Profundo** | `gemini-3.1-pro-preview` | Análisis crítico de directores y evaluación |
| **Generación Visual** | `gemini-3.1-flash-image` | Renderizado secuencial multimodal condicionado |
| **Síntesis de Audio / TTS** | `gemini-3.1-flash-tts-preview` | Locución monohablante y diálogo multi-speaker |

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
- Python 3.10 o superior
- Google Gemini API Key ([Obtener en Google AI Studio](https://aistudio.google.com/))

### 1. Clonar el repositorio
```bash
git clone https://github.com/gruizmetasolutions-cpu/proyecto-storybot.git
cd proyecto-storybot
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar API Key
Puedes definir tu clave en una variable de entorno o directamente en la interfaz web (botón de Configuración):
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="tu_gemini_api_key_aqui"

# Linux / macOS
export GEMINI_API_KEY="tu_gemini_api_key_aqui"
```

### 4. Iniciar el servidor
```bash
python app.py
```
Abre en tu navegador: 👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧪 Pruebas Automatizadas

La suite incluye 12 pruebas unitarias con límites estrictos de reintentos para evitar consumo innecesario de tokens:
```bash
python -m unittest tests/test_coherence_eval.py -v
```

---

## 📁 Estructura del Proyecto

```
proyecto-storybot/
├── app.py                      # Servidor FastAPI y endpoints REST
├── config.py                   # Configuración de modelos, voces, idiomas y precios
├── core/
│   ├── audio_engine.py         # Motor TTS, Multi-Speaker y Audio Tags (Gemini 3.1 TTS)
│   ├── visual_engine.py        # Pipeline secuencial de imagen y Character Anchor
│   ├── storyboard_engine.py    # Desglose cinematográfico con Gemini 3.5 Flash
│   ├── podcast_engine.py       # Audio Overview con 2 hosts (Elena & Marcos)
│   ├── evaluator.py            # Auditoría y scoring de coherencia (0-100)
│   ├── token_tracker.py        # Contador de tokens y costo en USD
│   └── gemini_client.py        # Cliente unificado Google GenAI SDK
├── static/
│   ├── index.html              # Interfaz de usuario (Studio Harness)
│   ├── css/
│   │   └── style.css           # Sistema de diseño, temas y viewport adaptable
│   └── js/
│       ├── app.js              # Controlador principal
│       ├── player.js           # Animatic Cinema Player (16:9, 9:16, 2.39:1...)
│       └── podcast.js          # Controlador de Audio Overview
├── tests/
│   └── test_coherence_eval.py  # Suite de 12 pruebas unitarias
└── requirements.txt            # Dependencias del proyecto
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
