import unittest
import struct
import wave
import io
import config
from core.token_tracker import TokenTracker
from core.audio_engine import AudioEngine
from core.storyboard_engine import StoryboardEngine, StoryboardProject, StoryboardShot
from core.visual_engine import VisualEngine
from core.podcast_engine import PodcastEngine
from core.evaluator import CoherenceEvaluator

class TestCoherenceAndSequentialHarness(unittest.TestCase):
    """
    Suite de pruebas automatizadas con límites estrictos de reintentos
    para evitar consumo accidental de tokens.
    """

    def setUp(self):
        # Asegurar límite máximo de intentos
        self.max_retries = config.MAX_TEST_RETRIES

    def test_token_tracker_calculations(self):
        """Verifica que el cálculo de tokens y estimación de costos en USD sea matemáticamente exacto."""
        usage = TokenTracker.calculate_cost(
            prompt_tokens=100_000,     # 100k @ $0.075/1M = $0.0075
            completion_tokens=50_000,  # 50k @ $0.300/1M = $0.0150
            images_count=2,            # 2 imgs @ $0.020 = $0.0400
            audio_chars=2000           # 2k chars @ $0.0005/1k = $0.0010
        )
        # Total esperado: 0.0075 + 0.0150 + 0.0400 + 0.0010 = 0.0635 USD
        self.assertAlmostEqual(usage.estimated_cost_usd, 0.0635, places=4)
        self.assertEqual(usage.total_tokens, 150_000)
        self.assertEqual(usage.images_generated, 2)
        self.assertEqual(usage.audio_chars_synthesized, 2000)
        self.assertIn("USD", usage.formatted_cost)

    def test_pcm_to_wav_header_integrity(self):
        """Valida que la conversión de PCM crudo genere un contenedor WAV válido de 24kHz y 16-bit."""
        raw_pcm = b'\x00\x00' * 2400  # 0.1s de silencio a 24kHz
        wav_bytes = AudioEngine.pcm_to_wav_bytes(raw_pcm, sample_rate=24000, channels=1, sample_width=2)
        
        # Validar cabecera RIFF
        self.assertTrue(wav_bytes.startswith(b'RIFF'))
        self.assertIn(b'WAVE', wav_bytes[:16])
        
        # Parsear con módulo wave estándar de Python
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 24000)
            self.assertEqual(wf.getnframes(), 2400)

    def test_procedural_speech_synthesis_multispeaker(self):
        """Valida que la síntesis de voz procedimental genere audios distintos para Elena y Marcos sin costo de API."""
        elena_res = AudioEngine.synthesize_speech("¡Hola, bienvenidos a la mesa de dirección!", voice_key="elena")
        marcos_res = AudioEngine.synthesize_speech("Totalmente de acuerdo, este guion es brillante.", voice_key="marcos")

        self.assertTrue(elena_res["success"])
        self.assertTrue(marcos_res["success"])
        self.assertTrue(elena_res["audio_data"].startswith("data:audio/wav;base64,"))
        self.assertTrue(marcos_res["audio_data"].startswith("data:audio/wav;base64,"))
        self.assertIn("Aoede", elena_res["voice_used"])
        self.assertIn("Puck", marcos_res["voice_used"])

    def test_audio_tags_normalization(self):
        """Valida que las etiquetas de audio en español se normalicen a las directivas de Gemini 3.1 Flash TTS."""
        raw_text = "[susurro] No hagan ruido... [pausa dramática] [jadeo] ¡Lo encontramos!"
        normalized = AudioEngine.normalize_expressive_tags(raw_text)
        
        self.assertIn("[whispers]", normalized)
        self.assertIn("[dramatic pause]", normalized)
        self.assertIn("[gasp]", normalized)
        self.assertNotIn("[susurro]", normalized)

    def test_voice_intentions_and_acting_directives(self):
        """Valida que los presets de intención vocal generen directivas actorales y tags de audio para Gemini 3.1 Flash TTS."""
        sb_tense = StoryboardEngine.generate_demo_storyboard(
            input_text="Escena de suspenso en la cabaña",
            voice_intention_key="tense_thriller",
            scene_count=4
        )
        self.assertEqual(sb_tense.voice_intention, "tense_thriller")
        for shot in sb_tense.shots:
            self.assertIsNotNone(shot.acting_intention)
            self.assertIsNotNone(shot.voice_cast)
            self.assertTrue(len(shot.acting_intention) > 5)
            self.assertTrue("[" in shot.dialogue_or_voiceover and "]" in shot.dialogue_or_voiceover)

    def test_multilingual_storyboard_support(self):
        """Valida que el generador admita códigos de idioma multilingüe (70+ idiomas)."""
        sb_fr = StoryboardEngine.generate_demo_storyboard(
            input_text="Une aventure à Paris",
            language_code="fr_FR",
            scene_count=4
        )
        self.assertEqual(sb_fr.language_code, "fr_FR")

        sb_mx = StoryboardEngine.generate_demo_storyboard(
            input_text="Persecución en Reforma",
            language_code="es_MX",
            scene_count=4
        )
        self.assertEqual(sb_mx.language_code, "es_MX")

    def test_vertical_aspect_ratio_9_16(self):
        """Valida que el generador y visualizador soporten correctamente la relación 9:16 (vertical mobile / Reels)."""
        sb_vertical = StoryboardEngine.generate_demo_storyboard(
            input_text="Comercial vertical para TikTok de moda futurista",
            aspect_ratio="9:16",
            scene_count=4
        )
        self.assertEqual(sb_vertical.aspect_ratio, "9:16")
        
        svg_placeholder = VisualEngine.generate_placeholder_svg("Escena vertical", "9:16", "Cinematic Concept Art")
        self.assertIn("data:image/svg+xml", svg_placeholder)

    def test_character_anchor_generation(self):
        """Verifica la generación de la Hoja de Personaje Base (Character Anchor Sheet)."""
        bible = "Detective K: Impermeable oscuro de cuello alto, implante cibernético cian en ojo derecho, cabello plateado."
        res = VisualEngine.render_character_anchor(
            character_bible=bible,
            style_key="cinematic_concept",
            allow_demo_fallback=True
        )
        self.assertTrue(res["success"])
        self.assertIn("data:image/", res["image_data"])
        self.assertIn("token_usage", res)

    def test_sequential_rendering_propagation(self):
        """Verifica que el pipeline secuencial propague el Anchor y el fotograma anterior."""
        shots = [
            {"shot_number": 1, "visual_action": "El detective camina bajo la lluvia."},
            {"shot_number": 2, "visual_action": "Abre el maletín con luz holográfica."},
            {"shot_number": 3, "visual_action": "Mira hacia la cornisa alertado."}
        ]
        bible = "Detective con impermeable oscuro y cabello plateado."
        
        pipeline_res = VisualEngine.render_sequential_pipeline(
            shots=shots,
            character_bible=bible,
            style_key="film_noir",
            allow_demo_fallback=True
        )
        
        self.assertTrue(pipeline_res["success"])
        self.assertEqual(pipeline_res["shots_count"], 3)
        self.assertIsNotNone(pipeline_res["anchor_sheet"])
        
        # Verificar condicionamiento en cadena
        rendered = pipeline_res["rendered_shots"]
        self.assertTrue(rendered[0]["conditioned_on_anchor"])
        self.assertFalse(rendered[0]["conditioned_on_previous"])
        self.assertTrue(rendered[1]["conditioned_on_previous"])
        self.assertTrue(rendered[2]["conditioned_on_previous"])

    def test_coherence_evaluator_high_score(self):
        """Valida que un storyboard bien estructurado con Character Anchor obtenga una alta puntuación (>80/100)."""
        sb = StoryboardEngine.generate_demo_storyboard("Misión de rescate en Neo-Tokyo", scene_count=6)
        metrics = CoherenceEvaluator.evaluate_storyboard(
            storyboard=sb,
            has_character_anchor=True,
            rendered_images_count=6,
            allow_demo_fallback=True
        )
        
        self.assertGreaterEqual(metrics.overall_score, 80)
        self.assertGreaterEqual(metrics.character_consistency_score, 85)
        self.assertGreaterEqual(metrics.narrative_flow_score, 75)
        self.assertGreaterEqual(len(metrics.strengths), 2)
        self.assertIsNotNone(metrics.token_usage)

    def test_coherence_evaluator_missing_anchor_detection(self):
        """Valida que el evaluador identifique la falta de Character Anchor y tomas sin renderizar."""
        sb = StoryboardEngine.generate_demo_storyboard("Prueba básica", scene_count=4)
        metrics = CoherenceEvaluator.evaluate_storyboard(
            storyboard=sb,
            has_character_anchor=False,
            rendered_images_count=0,
            allow_demo_fallback=True
        )
        
        issues_text = " ".join(metrics.critical_issues)
        self.assertIn("Anchor", issues_text)
        self.assertIn("renderizar", issues_text)

    def test_multi_speaker_single_request_flow(self):
        """Valida el flujo de síntesis multi-hablante nativa para diálogos de Elena y Marcos."""
        turns = [
            {"speaker": "Elena", "text": "[whispers] Mira este plano general, Marcos.", "tone": "intimo"},
            {"speaker": "Marcos", "text": "[dramatic pause] Es extraordinario, la luz volumétrica resalta la tensión.", "tone": "analitico"}
        ]
        
        res = AudioEngine.synthesize_multi_speaker_single_request(
            dialogue_turns=turns,
            allow_demo_fallback=True
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["full_audio_data"].startswith("data:audio/wav;base64,"))
        self.assertEqual(res["turns_count"], 2)
        self.assertGreater(res["token_usage"]["audio_chars_synthesized"], 0)

    def test_script_agent_premise_from_tags(self):
        """Valida que el ScriptAgent sintetice una premisa cinematográfica coherente a partir de la matriz de tags."""
        from core.storyboard_engine import ScriptAgent
        tags = {
            "genres": "Cyberpunk Neo-Noir",
            "protagonists": "Detective Cansado",
            "conflicts": "Maletín con Código Prohibido",
            "atmospheres": "Neo-Tokyo Lluvioso",
            "tones": "Tenso y Claustrofóbico"
        }
        res = ScriptAgent.generate_premise_from_tags(
            selected_tags=tags,
            creativity_scale=0.6,
            language_code="es_MX",
            allow_demo_fallback=True
        )
        self.assertIsNotNone(res.generated_premise)
        self.assertGreater(len(res.generated_premise), 40)
        self.assertIsNotNone(res.suggested_title)
        self.assertEqual(res.selected_tags["genres"], "Cyberpunk Neo-Noir")
        self.assertIsNotNone(res.token_usage)

    def test_storyboard_master_audio_synthesis_and_timecodes(self):
        """Valida que la síntesis de Master Audio Track genere un WAV continuo y calcule marcas de tiempo secuenciales."""
        shots = [
            {"shot_number": 1, "dialogue_or_voiceover": "[whispers] Caminando en la penumbra de Neo-Tokyo.", "speaker_label": "Narrador", "visual_action": "Silueta bajo la lluvia."},
            {"shot_number": 2, "dialogue_or_voiceover": "[dramatic pause] El paquete sigue aquí.", "speaker_label": "Protagonista", "visual_action": "Abre el maletín."},
            {"shot_number": 3, "dialogue_or_voiceover": "[urgent shout] ¡Cuidado con la cornisa!", "speaker_label": "Operadora", "visual_action": "Salto del asesino."}
        ]
        
        res = AudioEngine.synthesize_storyboard_master_audio(
            shots=shots,
            voice_intention_key="tense_thriller",
            language_code="es-MX",
            allow_demo_fallback=True
        )
        
        self.assertTrue(res["success"])
        self.assertTrue(res["master_audio_url"].startswith("data:audio/wav;base64,"))
        self.assertGreater(res["master_duration_sec"], 0)
        self.assertEqual(res["shots_count"], 3)
        self.assertEqual(len(res["shots"]), 3)
        
        # Verificar coherencia matemática de marcas de tiempo contiguas
        updated_shots = res["shots"]
        self.assertEqual(updated_shots[0]["timecode_start_sec"], 0.0)
        self.assertGreater(updated_shots[0]["timecode_end_sec"], 0.0)
        self.assertEqual(updated_shots[1]["timecode_start_sec"], updated_shots[0]["timecode_end_sec"])
        self.assertEqual(updated_shots[2]["timecode_start_sec"], updated_shots[1]["timecode_end_sec"])
        self.assertAlmostEqual(updated_shots[2]["timecode_end_sec"], res["master_duration_sec"], delta=0.2)

if __name__ == '__main__':
    unittest.main()
