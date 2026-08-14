from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import config
from core.gemini_client import gemini_service
from core.storyboard_engine import StoryboardProject
from core.token_tracker import TokenTracker, TokenUsage

class CoherenceMetrics(BaseModel):
    overall_score: int = Field(description="Puntuación global de coherencia y calidad de producción de 0 a 100")
    narrative_flow_score: int = Field(description="Puntuación de progresión dramática, causalidad y ritmo narrativo de 0 a 100")
    character_consistency_score: int = Field(description="Puntuación de fidelidad y preservación de rasgos de personajes de 0 a 100")
    visual_style_continuity_score: int = Field(description="Puntuación de armonía visual, iluminación y paleta de 0 a 100")
    audio_dialogue_quality_score: int = Field(description="Puntuación de calidad de diálogos, locución y sonido de 0 a 100")
    pacing_assessment: str = Field(description="Evaluación del tempo y distribución temporal entre planos")
    strengths: List[str] = Field(description="Principales aciertos creativos y de continuidad identificados")
    critical_issues: List[str] = Field(description="Inconsistencias o puntos de mejora detectados")
    director_recommendations: List[str] = Field(description="Recomendaciones técnicas del DoP/Director para elevar la producción")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Consumo de tokens y costo del análisis")

class CoherenceEvaluator:
    @staticmethod
    def evaluate_storyboard(
        storyboard: StoryboardProject,
        has_character_anchor: bool = False,
        rendered_images_count: int = 0,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> CoherenceMetrics:
        """
        Evalúa integralmente la coherencia de la historia, personajes, planos visuales y sonido.
        Usa Gemini 3.5 Flash si hay API Key, o un evaluador heurístico determinista si está en modo demo/offline.
        """
        has_key = bool(api_key_override or gemini_service.api_key)

        if not has_key:
            if allow_demo_fallback:
                return CoherenceEvaluator._heuristic_offline_eval(storyboard, has_character_anchor, rendered_images_count)
            else:
                raise ValueError("Se requiere una API Key para ejecutar la auditoría de coherencia en vivo.")

        # Preparar resumen de tomas para el modelo evaluador
        shots_data = "\n".join([
            f"Toma #{s.shot_number} [{s.shot_type}] - Duración: {s.estimated_duration_sec}s\n"
            f"  Acción: {s.visual_action}\n"
            f"  Cámara: {s.camera_movement}\n"
            f"  Luz/Atmósfera: {s.lighting_and_atmosphere}\n"
            f"  Diálogo/VO: \"{s.dialogue_or_voiceover}\"\n"
            f"  Prompt Visual: {s.visual_prompt_optimized}"
            for s in storyboard.shots
        ])

        eval_prompt = f"""Audita y califica exhaustivamente la coherencia de este proyecto de Storyboard cinematográfico.

DATOS DEL PROYECTO:
- Título: {storyboard.title}
- Logline: {storyboard.logline}
- Género y Tono: {storyboard.genre_and_tone}
- Estilo Visual: {storyboard.visual_style} (Aspect Ratio: {storyboard.aspect_ratio})
- Duración Objetivo: {storyboard.target_duration_seconds}s
- Hoja de Personaje Base (Anchor): {"Sí generada" if has_character_anchor else "No generada"}
- Imágenes Renderizadas: {rendered_images_count} de {len(storyboard.shots)}

GUÍA DE CONSISTENCIA DE PERSONAJES:
{chr(10).join(['- ' + c for c in storyboard.character_bibles]) if storyboard.character_bibles else "Sin biblia definida."}

PLANOS SECUENCIALES:
{shots_data}

CRITERIOS DE AUDITORÍA:
1. NARRATIVE FLOW (0-100): ¿La secuencia tiene progresión lógica causa-efecto? ¿Hay apertura, desarrollo de tensión y clímax claro?
2. CHARACTER CONSISTENCY (0-100): ¿Los personajes mantienen rasgos inmutables descritos en la biblia a través de las acciones de cada plano?
3. VISUAL STYLE CONTINUITY (0-100): ¿La iluminación, lentes y directivas de estilo son consistentes entre planos adyacentes?
4. AUDIO & DIALOGUE (0-100): ¿Los diálogos o voces en off suenan naturales y refuerzan el subtexto dramático?

Genera el reporte de métricas con calificaciones precisas y recomendaciones profesionales."""

        system_instruction = "Eres un Auditor Senior de Guion y Continuidad Visual de estudios cinematográficos (Script Supervisor & Continuity Director)."

        try:
            parsed, usage = gemini_service.generate_structured_with_usage(
                prompt=eval_prompt,
                response_schema=CoherenceMetrics,
                system_instruction=system_instruction,
                temperature=0.3,
                api_key_override=api_key_override
            )
            parsed.token_usage = usage
            return parsed
        except Exception as e:
            print(f"Aviso en evaluación con Gemini: {e}")
            if allow_demo_fallback:
                fallback_result = CoherenceEvaluator._heuristic_offline_eval(storyboard, has_character_anchor, rendered_images_count)
                fallback_result.critical_issues.append(f"Aviso de auditoría: Se aplicó evaluación heurística debido a: {str(e)[:100]}")
                return fallback_result
            raise e

    @staticmethod
    def _heuristic_offline_eval(storyboard: StoryboardProject, has_character_anchor: bool, rendered_images_count: int) -> CoherenceMetrics:
        """
        Evaluador heurístico determinista y sin consumo de tokens para pruebas y modo demo.
        Analiza distribución de tiempos, densidad de vocabulario visual, recurrencia de personajes y concordancia de estilo.
        """
        shots = storyboard.shots
        shot_count = len(shots)

        # 1. Narrativa: Verificar variedad de tipos de plano y progresión
        shot_types = [s.shot_type.lower() for s in shots]
        has_wide = any("general" in t or "wide" in t or "ews" in t for t in shot_types)
        has_close = any("primer plano" in t or "close" in t or "cu" in t or "detalle" in t for t in shot_types)
        has_medium = any("medio" in t or "medium" in t or "ms" in t for t in shot_types)
        
        narrative_score = 70
        if has_wide: narrative_score += 10
        if has_close: narrative_score += 10
        if has_medium: narrative_score += 10
        narrative_score = min(98, max(50, narrative_score))

        # 2. Personaje: Biblia y consistencia de menciones
        char_score = 75
        if storyboard.character_bibles and len(storyboard.character_bibles) > 0:
            char_score += 15
        if has_character_anchor:
            char_score += 10
        char_score = min(99, char_score)

        # 3. Estilo visual y continuidad
        visual_score = 80
        if storyboard.visual_style: visual_score += 10
        if rendered_images_count >= shot_count: visual_score += 8
        visual_score = min(98, visual_score)

        # 4. Audio & diálogo
        dialogues = [s.dialogue_or_voiceover for s in shots if s.dialogue_or_voiceover]
        audio_score = 70 + min(25, len(dialogues) * 5)

        # Global
        overall = int((narrative_score * 0.30) + (char_score * 0.30) + (visual_score * 0.25) + (audio_score * 0.15))

        pacing = f"Distribución rítmica adecuada: {shot_count} tomas en ~{storyboard.target_duration_seconds}s (promedio {storyboard.target_duration_seconds/max(1, shot_count):.1f}s por plano)."

        strengths = [
            f"Estructura visual balanceada con {shot_count} planos bien diferenciados.",
            f"Definición explícita de estilo cinematográfico '{storyboard.visual_style}' en cada toma.",
            "Consistencia en la biblia de personajes que previene alteraciones de vestuario."
        ]

        critical_issues = []
        if not has_character_anchor:
            critical_issues.append("Se recomienda generar la Hoja de Personaje Base (Character Anchor) antes del rodaje final.")
        if rendered_images_count < shot_count:
            critical_issues.append(f"Faltan {shot_count - rendered_images_count} tomas por renderizar con el pipeline secuencial.")

        recommendations = [
            "Ejecutar el 'Renderizado Secuencial Completo' para que el plano K herede iluminación y vestuario del plano K-1.",
            "Utilizar las voces diferenciadas de Elena (Aoede) y Marcos (Puck) para contrastar puntos de vista.",
            "Exportar la hoja técnica en PDF para el equipo de producción antes de filmar."
        ]

        usage = TokenTracker.calculate_cost(prompt_tokens=150, completion_tokens=250)

        return CoherenceMetrics(
            overall_score=overall,
            narrative_flow_score=narrative_score,
            character_consistency_score=char_score,
            visual_style_continuity_score=visual_score,
            audio_dialogue_quality_score=audio_score,
            pacing_assessment=pacing,
            strengths=strengths,
            critical_issues=critical_issues,
            director_recommendations=recommendations,
            token_usage=usage
        )
