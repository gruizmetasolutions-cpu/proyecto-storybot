import io
import math
import struct
import base64
import wave
import re
from typing import Optional, List, Dict, Any
from google.genai import types
import config
from core.gemini_client import gemini_service
from core.token_tracker import TokenTracker, TokenUsage

class AudioEngine:
    @staticmethod
    def pcm_to_wav_bytes(
        pcm_bytes: bytes,
        sample_rate: int = config.AUDIO_SAMPLE_RATE,
        channels: int = config.AUDIO_CHANNELS,
        sample_width: int = config.AUDIO_SAMPLE_WIDTH
    ) -> bytes:
        """
        Envuelve datos PCM crudos (16-bit little endian) en un contenedor WAV estándar.
        """
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        return wav_io.getvalue()

    @staticmethod
    def generate_silence_pcm(duration_sec: float, sample_rate: int = config.AUDIO_SAMPLE_RATE) -> bytes:
        """Genera bytes PCM de silencio para separar turnos de conversación."""
        num_samples = int(sample_rate * duration_sec)
        return b'\x00\x00' * num_samples

    @staticmethod
    def normalize_expressive_tags(text: str) -> str:
        """
        Normaliza etiquetas de audio en español al estándar reconocido por Gemini 3.1 Flash TTS.
        Permite que el usuario escriba tanto [susurro] como [whispers], [pausa] como [dramatic pause], etc.
        """
        tag_mappings = {
            r'\[susurro\]': '[whispers]',
            r'\[susurrando\]': '[whispers]',
            r'\[pausa\]': '[dramatic pause]',
            r'\[pausa dram[aá]tica\]': '[dramatic pause]',
            r'\[respiraci[oó]n\]': '[slow breath]',
            r'\[jadeo\]': '[gasp]',
            r'\[asombro\]': '[gasp]',
            r'\[risa\]': '[chuckles]',
            r'\[risa sutil\]': '[chuckles]',
            r'\[suspiro\]': '[sighs]',
            r'\[grito urgente\]': '[urgent shout]',
            r'\[grito\]': '[screams]',
            r'\[ritmo r[aá]pido\]': '[fast cadence]',
            r'\[voz profunda\]': '[deep resonance]',
            r'\[temblor emotivo\]': '[emotional tremor]'
        }
        normalized = text
        for pattern, replacement in tag_mappings.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        return normalized

    @staticmethod
    def generate_procedural_speech_wav(
        text: str,
        voice_type: str = "female",
        sample_rate: int = config.AUDIO_SAMPLE_RATE
    ) -> bytes:
        """
        Genera un audio procedural con modulación de formantes, pausas dinámicas y cadencia
        como fallback demo offline, simulando efectos de audio tags como [whispers] o [dramatic pause].
        """
        words = text.split()
        total_duration = max(1.2, len(words) * 0.35)
        
        # Si contiene pausas dramáticas, aumentar duración
        if "[dramatic pause]" in text or "[pause" in text:
            total_duration += 1.0

        num_samples = int(sample_rate * total_duration)
        base_pitch = 220.0 if voice_type == "female" else 130.0
        
        # Si es susurro, reducir volumen y alterar armónicos
        is_whisper = "[whispers]" in text or "[susurro]" in text
        volume_factor = 4000.0 if is_whisper else 12000.0
        
        pcm_data = bytearray()
        
        for i in range(num_samples):
            t = i / sample_rate
            word_idx = int((t / total_duration) * len(words))
            pitch_mod = math.sin(2 * math.pi * 3.0 * t) * 15.0
            cur_pitch = (base_pitch * 0.85 if is_whisper else base_pitch) + pitch_mod
            
            s1 = math.sin(2 * math.pi * cur_pitch * t)
            s2 = 0.5 * math.sin(2 * math.pi * (cur_pitch * 2.1) * t)
            s3 = 0.25 * math.sin(2 * math.pi * (cur_pitch * 3.4) * t)
            
            syllable_env = (math.sin(2 * math.pi * 4.5 * t) ** 2) * 0.7 + 0.3
            fade = min(1.0, t * 8.0) * min(1.0, (total_duration - t) * 8.0)
            
            sample_val = int((s1 + s2 + s3) * syllable_env * fade * volume_factor)
            sample_val = max(-32767, min(32767, sample_val))
            pcm_data.extend(struct.pack('<h', sample_val))
            
        return AudioEngine.pcm_to_wav_bytes(bytes(pcm_data), sample_rate=sample_rate)

    @staticmethod
    def synthesize_speech(
        text: str,
        voice_key: str = "narrator_epic",
        style_prompt: Optional[str] = None,
        language_code: str = "es-MX",
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Sintetiza locución monohablante con Gemini 3.1 Flash TTS (gemini-3.1-flash-tts-preview)
        interpretando etiquetas de audio expresivas ([whispers], [dramatic pause], [gasp], etc.).
        """
        voice_info = config.VOICE_MAPPINGS.get(voice_key, config.VOICE_MAPPINGS["narrator_epic"])
        voice_name = voice_info["voice_name"]
        normalized_text = AudioEngine.normalize_expressive_tags(text)
        text_chars = len(normalized_text)

        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                voice_gender = voice_info.get("gender", "male")
                wav_bytes = AudioEngine.generate_procedural_speech_wav(normalized_text, voice_gender)
                b64 = base64.b64encode(wav_bytes).decode("utf-8")
                token_usage = TokenTracker.calculate_cost(audio_chars=text_chars)
                return {
                    "success": True,
                    "audio_data": f"data:audio/wav;base64,{b64}",
                    "source": "procedural_demo_tts",
                    "voice_used": f"{voice_info['role']} ({voice_name})",
                    "sample_rate": config.AUDIO_SAMPLE_RATE,
                    "token_usage": token_usage.model_dump()
                }
            else:
                raise ValueError("Se requiere una clave de API de Gemini para la síntesis con Gemini 3.1 Flash TTS.")

        try:
            client = gemini_service.get_client(api_key_override)
            
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )

            prompt_content = normalized_text
            if style_prompt:
                prompt_content = f"[{style_prompt}] {normalized_text}"

            response = client.models.generate_content(
                model=config.AUDIO_TTS_MODEL,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config
                )
            )

            pcm_bytes = None
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        pcm_bytes = part.inline_data.data
                        break

            token_usage = TokenTracker.calculate_cost(audio_chars=text_chars)

            if pcm_bytes:
                wav_bytes = AudioEngine.pcm_to_wav_bytes(pcm_bytes)
                b64 = base64.b64encode(wav_bytes).decode("utf-8")
                return {
                    "success": True,
                    "audio_data": f"data:audio/wav;base64,{b64}",
                    "source": config.AUDIO_TTS_MODEL,
                    "voice_used": f"{voice_info['role']} ({voice_name})",
                    "sample_rate": config.AUDIO_SAMPLE_RATE,
                    "token_usage": token_usage.model_dump()
                }
            else:
                raise ValueError("La API no devolvió datos de audio en la respuesta.")

        except Exception as e:
            print(f"Aviso en síntesis TTS con {config.AUDIO_TTS_MODEL}: {e}")
            if allow_demo_fallback:
                voice_gender = voice_info.get("gender", "male")
                wav_bytes = AudioEngine.generate_procedural_speech_wav(normalized_text, voice_gender)
                b64 = base64.b64encode(wav_bytes).decode("utf-8")
                token_usage = TokenTracker.calculate_cost(audio_chars=text_chars)
                return {
                    "success": True,
                    "audio_data": f"data:audio/wav;base64,{b64}",
                    "source": "procedural_demo_tts_fallback",
                    "voice_used": f"{voice_info['role']} ({voice_name})",
                    "error_detail": str(e),
                    "sample_rate": config.AUDIO_SAMPLE_RATE,
                    "token_usage": token_usage.model_dump()
                }
            raise e

    @staticmethod
    def synthesize_multi_speaker_single_request(
        dialogue_turns: List[Dict[str, str]],
        speaker_voices: Dict[str, str] = None,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Sintetiza un diálogo completo entre dos hablantes en una ÚNICA solicitud a Gemini 3.1 Flash TTS
        usando MultiSpeakerVoiceConfig y etiquetas de audio expresivas nativas.
        """
        if speaker_voices is None:
            speaker_voices = {
                "Elena": "Aoede",
                "Marcos": "Puck"
            }

        # Construir el guion etiquetado para multi-speaker
        script_lines = []
        total_chars = 0
        for turn in dialogue_turns:
            spk = turn.get("speaker", "Elena").strip()
            # Normalizar nombre del speaker
            spk_label = "Elena" if "elena" in spk.lower() else "Marcos"
            txt = AudioEngine.normalize_expressive_tags(turn.get("text", ""))
            total_chars += len(txt)
            script_lines.append(f"{spk_label}: {txt}")

        multi_speaker_prompt = "\n".join(script_lines)

        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                # Fallback concatenado procedimental de demostración
                return AudioEngine.synthesize_podcast_episode(
                    dialogue_turns=dialogue_turns,
                    api_key_override=None,
                    allow_demo_fallback=True
                )
            else:
                raise ValueError("Se requiere una API Key de Gemini para la síntesis multi-speaker nativa.")

        try:
            client = gemini_service.get_client(api_key_override)
            
            # Configurar multi-speaker voice config nativo de Gemini 3.1 Flash TTS
            speaker_configs = [
                types.SpeakerVoiceConfig(
                    speaker="Elena",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=speaker_voices.get("Elena", "Aoede")
                        )
                    )
                ),
                types.SpeakerVoiceConfig(
                    speaker="Marcos",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=speaker_voices.get("Marcos", "Puck")
                        )
                    )
                )
            ]

            multi_voice_config = types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=speaker_configs
            )

            speech_config = types.SpeechConfig(
                multi_speaker_voice_config=multi_voice_config
            )

            response = client.models.generate_content(
                model=config.AUDIO_TTS_MODEL,
                contents=multi_speaker_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config
                )
            )

            pcm_bytes = None
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        pcm_bytes = part.inline_data.data
                        break

            token_usage = TokenTracker.calculate_cost(audio_chars=total_chars)

            if pcm_bytes:
                wav_bytes = AudioEngine.pcm_to_wav_bytes(pcm_bytes)
                b64 = base64.b64encode(wav_bytes).decode("utf-8")
                return {
                    "success": True,
                    "full_audio_data": f"data:audio/wav;base64,{b64}",
                    "method": "single_request_multi_speaker",
                    "speakers": ["Elena (Aoede)", "Marcos (Puck)"],
                    "turns_count": len(dialogue_turns),
                    "model": config.AUDIO_TTS_MODEL,
                    "token_usage": token_usage.model_dump()
                }
        except Exception as e:
            print(f"Aviso en MultiSpeaker single call: {e}. Aplicando concatenación con pausas.")
            return AudioEngine.synthesize_podcast_episode(
                dialogue_turns=dialogue_turns,
                api_key_override=api_key_override,
                allow_demo_fallback=allow_demo_fallback
            )

    @staticmethod
    def synthesize_podcast_episode(
        dialogue_turns: List[Dict[str, str]],
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Sintetiza el episodio completo del podcast intercalando las voces de Elena y Marcos,
        concatenando los flujos de audio con pausas naturales entre turnos.
        """
        full_pcm_stream = bytearray()
        turn_audios = []
        total_audio_chars = 0

        for turn in dialogue_turns:
            speaker_name = turn.get("speaker", "Elena").lower()
            voice_key = "elena" if "elena" in speaker_name else "marcos"
            text = AudioEngine.normalize_expressive_tags(turn.get("text", ""))
            tone = turn.get("tone", "natural")
            total_audio_chars += len(text)

            result = AudioEngine.synthesize_speech(
                text=text,
                voice_key=voice_key,
                style_prompt=tone,
                api_key_override=api_key_override,
                allow_demo_fallback=allow_demo_fallback
            )
            
            turn_audios.append({
                "speaker": turn.get("speaker", "Elena"),
                "audio_data": result.get("audio_data")
            })

            if result.get("audio_data") and "base64," in result["audio_data"]:
                wav_b64 = result["audio_data"].split("base64,")[1]
                wav_raw = base64.b64decode(wav_b64)
                if len(wav_raw) > 44:
                    full_pcm_stream.extend(wav_raw[44:])
                    full_pcm_stream.extend(AudioEngine.generate_silence_pcm(0.30))

        full_wav = AudioEngine.pcm_to_wav_bytes(bytes(full_pcm_stream))
        full_b64 = base64.b64encode(full_wav).decode("utf-8")
        token_usage = TokenTracker.calculate_cost(audio_chars=total_audio_chars)

        return {
            "success": True,
            "full_audio_data": f"data:audio/wav;base64,{full_b64}",
            "turn_audios": turn_audios,
            "turns_count": len(dialogue_turns),
            "model": config.AUDIO_TTS_MODEL,
            "token_usage": token_usage.model_dump()
        }
