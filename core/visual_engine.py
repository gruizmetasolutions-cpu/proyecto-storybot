import io
import base64
from typing import Optional, Dict, Any, List
from PIL import Image

import config
from core.gemini_client import gemini_service
from core.token_tracker import TokenTracker, TokenUsage

class VisualEngine:
    @staticmethod
    def render_character_anchor(
        character_bible: str,
        style_key: str = "cinematic_concept",
        aspect_ratio: str = "1:1",
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Genera la 'Hoja de Personaje Base' (Character Anchor Sheet / Model Keyframe).
        Esta imagen sirve de ancla inmutable para todas las tomas del storyboard.
        """
        style_info = config.STYLE_PRESETS.get(style_key, config.STYLE_PRESETS["cinematic_concept"])
        anchor_prompt = (
            f"Character concept model sheet, turnaround reference portrait, {character_bible}. "
            f"Neutral cinematic pose, clear facial features, definitive costume design, {style_info['prompt_suffix']}"
        )

        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                svg_data = VisualEngine.generate_character_anchor_svg(character_bible, style_info["name"])
                token_usage = TokenTracker.calculate_cost(images_count=1)
                return {
                    "success": True,
                    "image_data": svg_data,
                    "source": "procedural_anchor_demo",
                    "prompt_used": anchor_prompt,
                    "token_usage": token_usage.model_dump()
                }
            else:
                raise ValueError("Se requiere una API Key para generar la hoja de personaje en vivo.")

        try:
            img_bytes = gemini_service.generate_image_sequential(
                prompt=anchor_prompt,
                aspect_ratio="1:1",
                api_key_override=api_key_override
            )
            token_usage = TokenTracker.calculate_cost(images_count=1)

            if img_bytes:
                mime = "image/png" if img_bytes[:4] == b'\x89PNG' else "image/jpeg"
                b64_img = base64.b64encode(img_bytes).decode("utf-8")
                return {
                    "success": True,
                    "image_data": f"data:{mime};base64,{b64_img}",
                    "source": config.IMAGE_MODEL,
                    "prompt_used": anchor_prompt,
                    "token_usage": token_usage.model_dump()
                }
        except Exception as e:
            print(f"Aviso en render de Character Anchor: {e}")
            if allow_demo_fallback:
                svg_data = VisualEngine.generate_character_anchor_svg(character_bible, style_info["name"])
                token_usage = TokenTracker.calculate_cost(images_count=1)
                return {
                    "success": True,
                    "image_data": svg_data,
                    "source": "procedural_anchor_demo_fallback",
                    "prompt_used": anchor_prompt,
                    "error_detail": str(e),
                    "token_usage": token_usage.model_dump()
                }
            raise e

        svg_data = VisualEngine.generate_character_anchor_svg(character_bible, style_info["name"])
        token_usage = TokenTracker.calculate_cost(images_count=1)
        return {
            "success": True,
            "image_data": svg_data,
            "source": "procedural_anchor_demo",
            "prompt_used": anchor_prompt,
            "token_usage": token_usage.model_dump()
        }

    @staticmethod
    def render_panel_image(
        visual_prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        style_key: str = "cinematic_concept",
        reference_image_bytes: Optional[bytes] = None,
        anchor_image_bytes: Optional[bytes] = None,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Genera la imagen de un panel de storyboard usando Gemini 3.1 Flash Image.
        Acepta referencia del personaje (anchor) y de la toma anterior (previous) para coherencia.
        """
        style_info = config.STYLE_PRESETS.get(style_key, config.STYLE_PRESETS["cinematic_concept"])
        full_prompt = f"{visual_prompt}, {style_info['prompt_suffix']}"
        if negative_prompt:
            full_prompt += f". Do not include: {negative_prompt}"

        has_key = bool(api_key_override or gemini_service.api_key)
        if not has_key:
            if allow_demo_fallback:
                svg_data = VisualEngine.generate_placeholder_svg(visual_prompt, aspect_ratio, style_info["name"])
                token_usage = TokenTracker.calculate_cost(images_count=1)
                return {
                    "success": True,
                    "image_data": svg_data,
                    "source": "procedural_preview",
                    "prompt_used": full_prompt,
                    "token_usage": token_usage.model_dump()
                }
            else:
                raise ValueError("Se requiere una API Key para renderizar paneles con Gemini 3.1 Flash Image.")

        try:
            image_bytes = gemini_service.generate_image_sequential(
                prompt=full_prompt,
                reference_image_bytes=reference_image_bytes,
                anchor_image_bytes=anchor_image_bytes,
                aspect_ratio=aspect_ratio,
                api_key_override=api_key_override
            )
            token_usage = TokenTracker.calculate_cost(images_count=1)

            if image_bytes:
                mime = "image/png" if image_bytes[:4] == b'\x89PNG' else "image/jpeg"
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                return {
                    "success": True,
                    "image_data": f"data:{mime};base64,{b64_img}",
                    "raw_bytes": image_bytes,
                    "source": config.IMAGE_MODEL,
                    "prompt_used": full_prompt,
                    "token_usage": token_usage.model_dump()
                }
        except Exception as e:
            print(f"Aviso en renderizado de imagen secuencial: {e}")
            if allow_demo_fallback:
                svg_data = VisualEngine.generate_placeholder_svg(visual_prompt, aspect_ratio, style_info["name"])
                token_usage = TokenTracker.calculate_cost(images_count=1)
                return {
                    "success": True,
                    "error": str(e),
                    "image_data": svg_data,
                    "source": "procedural_preview_fallback",
                    "prompt_used": full_prompt,
                    "token_usage": token_usage.model_dump()
                }
            raise e

        svg_data = VisualEngine.generate_placeholder_svg(visual_prompt, aspect_ratio, style_info["name"])
        token_usage = TokenTracker.calculate_cost(images_count=1)
        return {
            "success": True,
            "image_data": svg_data,
            "source": "procedural_preview",
            "prompt_used": full_prompt,
            "token_usage": token_usage.model_dump()
        }

    @staticmethod
    def render_sequential_pipeline(
        shots: List[Dict[str, Any]],
        character_bible: Optional[str] = None,
        style_key: str = "cinematic_concept",
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        api_key_override: Optional[str] = None,
        allow_demo_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta el Pipeline de Renderizado Secuencial Completo:
        1. Renderiza el Character Anchor Sheet.
        2. Renderiza la Toma 1 condicionada al Anchor.
        3. Renderiza cada Toma K condicionada al Anchor + Toma K-1.
        Garantiza consistencia absoluta de personaje, paleta y estilo.
        """
        results = []
        anchor_bytes = None
        anchor_result = None
        total_images = 0

        # Paso 1: Generar Character Anchor si se proporcionó una biblia de personaje
        if character_bible:
            anchor_result = VisualEngine.render_character_anchor(
                character_bible=character_bible,
                style_key=style_key,
                aspect_ratio="1:1",
                api_key_override=api_key_override,
                allow_demo_fallback=allow_demo_fallback
            )
            total_images += 1
            if anchor_result.get("image_data") and "base64," in anchor_result["image_data"]:
                try:
                    b64_str = anchor_result["image_data"].split("base64,")[1]
                    anchor_bytes = base64.b64decode(b64_str)
                except Exception:
                    pass

        # Paso 2: Renderizado Secuencial Encadenado
        prev_shot_bytes = None

        for shot in shots:
            shot_num = shot.get("shot_number", len(results) + 1)
            prompt = shot.get("visual_prompt_optimized") or shot.get("visual_action", "")
            
            shot_res = VisualEngine.render_panel_image(
                visual_prompt=prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                style_key=style_key,
                reference_image_bytes=prev_shot_bytes,
                anchor_image_bytes=anchor_bytes,
                api_key_override=api_key_override,
                allow_demo_fallback=allow_demo_fallback
            )
            
            total_images += 1
            results.append({
                "shot_number": shot_num,
                "image_data": shot_res.get("image_data"),
                "source": shot_res.get("source"),
                "conditioned_on_anchor": bool(anchor_bytes),
                "conditioned_on_previous": bool(prev_shot_bytes)
            })

            # Actualizar prev_shot_bytes para la siguiente toma
            if shot_res.get("raw_bytes"):
                prev_shot_bytes = shot_res["raw_bytes"]
            elif shot_res.get("image_data") and "base64," in shot_res["image_data"]:
                try:
                    b64_str = shot_res["image_data"].split("base64,")[1]
                    prev_shot_bytes = base64.b64decode(b64_str)
                except Exception:
                    pass

        total_usage = TokenTracker.calculate_cost(images_count=total_images)

        return {
            "success": True,
            "anchor_sheet": anchor_result,
            "rendered_shots": results,
            "shots_count": len(results),
            "token_usage": total_usage.model_dump()
        }

    @staticmethod
    def generate_character_anchor_svg(character_desc: str, style_name: str) -> str:
        """Genera un SVG representativo de la Hoja de Personaje Base (Character Anchor Sheet)."""
        clean_desc = character_desc[:180] + "..." if len(character_desc) > 180 else character_desc
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" width="100%" height="100%">
  <defs>
    <linearGradient id="anchorBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a101d"/>
      <stop offset="50%" stop-color="#121b2d"/>
      <stop offset="100%" stop-color="#060911"/>
    </linearGradient>
    <linearGradient id="goldGlow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#fbbf24"/>
    </linearGradient>
  </defs>
  <rect width="800" height="800" fill="url(#anchorBg)"/>
  <rect x="25" y="25" width="750" height="750" rx="16" fill="none" stroke="rgba(245, 158, 11, 0.3)" stroke-width="2" stroke-dasharray="8,8"/>
  <circle cx="400" cy="320" r="140" fill="rgba(245, 158, 11, 0.08)" stroke="rgba(245, 158, 11, 0.25)" stroke-width="2"/>
  <circle cx="400" cy="270" r="65" fill="rgba(255,255,255,0.06)" stroke="#f59e0b" stroke-width="2"/>
  <path d="M 330 430 C 330 360, 470 360, 470 430 Z" fill="rgba(255,255,255,0.08)" stroke="#f59e0b" stroke-width="2"/>
  <path d="M 40 70 L 40 40 L 70 40" fill="none" stroke="#f59e0b" stroke-width="3"/>
  <path d="M 760 70 L 760 40 L 730 40" fill="none" stroke="#f59e0b" stroke-width="3"/>
  <path d="M 40 730 L 40 760 L 70 760" fill="none" stroke="#f59e0b" stroke-width="3"/>
  <path d="M 760 730 L 760 760 L 730 760" fill="none" stroke="#f59e0b" stroke-width="3"/>
  <rect x="50" y="55" width="280" height="32" rx="8" fill="rgba(245, 158, 11, 0.2)" stroke="#f59e0b"/>
  <text x="65" y="77" fill="#fbbf24" font-family="sans-serif" font-size="14" font-weight="700" letter-spacing="1.5">★ CHARACTER ANCHOR SHEET</text>
  <text x="740" y="77" text-anchor="end" fill="#94a3b8" font-family="sans-serif" font-size="13">{style_name}</text>
  <rect x="50" y="600" width="700" height="140" rx="12" fill="rgba(15, 23, 42, 0.9)" stroke="rgba(255,255,255,0.1)"/>
  <text x="75" y="635" fill="#f8fafc" font-family="sans-serif" font-size="15" font-weight="600">Guía de Consistencia de Personaje:</text>
  <text x="75" y="665" fill="#cbd5e1" font-family="sans-serif" font-size="13" font-weight="400">{clean_desc}</text>
  <text x="75" y="715" fill="#f59e0b" font-family="sans-serif" font-size="12" font-weight="500">🔒 Ancla visual fijada para propagación secuencial de tomas 1..N</text>
</svg>"""
        b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"

    @staticmethod
    def generate_placeholder_svg(description: str, aspect_ratio: str, style_name: str) -> str:
        """Genera un SVG tipo cinematográfico como preview."""
        width = 1280
        height = 720
        if aspect_ratio == "2.39:1":
            height = 536
        elif aspect_ratio == "9:16":
            width = 720
            height = 1280
        elif aspect_ratio == "4:3":
            height = 960
        elif aspect_ratio == "1:1":
            height = 1280

        clean_desc = description[:160] + "..." if len(description) > 160 else description

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f141c"/>
      <stop offset="50%" stop-color="#161f2e"/>
      <stop offset="100%" stop-color="#0a0d13"/>
    </linearGradient>
    <radialGradient id="lensGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="rgba(41, 152, 255, 0.12)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0)"/>
    </radialGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bgGrad)"/>
  <circle cx="{width/2}" cy="{height/2}" r="{min(width, height)*0.45}" fill="url(#lensGlow)"/>
  <line x1="{width*0.33}" y1="0" x2="{width*0.33}" y2="{height}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,6"/>
  <line x1="{width*0.66}" y1="0" x2="{width*0.66}" y2="{height}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,6"/>
  <line x1="0" y1="{height*0.33}" x2="{width}" y2="{height*0.33}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,6"/>
  <line x1="0" y1="{height*0.66}" x2="{width}" y2="{height*0.66}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="4,6"/>
  <path d="M 40 80 L 40 40 L 80 40" fill="none" stroke="#2998ff" stroke-width="2" opacity="0.6"/>
  <path d="M {width-80} 40 L {width-40} 40 L {width-40} 80" fill="none" stroke="#2998ff" stroke-width="2" opacity="0.6"/>
  <path d="M 40 {height-80} L 40 {height-40} L 80 {height-40}" fill="none" stroke="#2998ff" stroke-width="2" opacity="0.6"/>
  <path d="M {width-80} {height-40} L {width-40} {height-40} L {width-40} {height-80}" fill="none" stroke="#2998ff" stroke-width="2" opacity="0.6"/>
  <line x1="{width/2-15}" y1="{height/2}" x2="{width/2+15}" y2="{height/2}" stroke="#2998ff" stroke-width="1.5" opacity="0.4"/>
  <line x1="{width/2}" y1="{height/2-15}" x2="{width/2}" y2="{height/2+15}" stroke="#2998ff" stroke-width="1.5" opacity="0.4"/>
  <rect x="50" y="55" width="220" height="28" rx="6" fill="rgba(41, 152, 255, 0.15)" stroke="rgba(41, 152, 255, 0.3)"/>
  <text x="60" y="74" fill="#64b5f6" font-family="sans-serif" font-size="13" font-weight="600" letter-spacing="1">STORYBOARD SHOT</text>
  <text x="{width-60}" y="74" text-anchor="end" fill="#8ca0b8" font-family="sans-serif" font-size="13" font-weight="500">{aspect_ratio}</text>
  <rect x="50" y="{height-120}" width="{width-100}" height="72" rx="8" fill="rgba(10, 14, 22, 0.85)" stroke="rgba(255,255,255,0.08)"/>
  <text x="70" y="{height-88}" fill="#e6edf3" font-family="sans-serif" font-size="14" font-weight="500">{clean_desc}</text>
  <text x="70" y="{height-65}" fill="#6b7c93" font-family="sans-serif" font-size="12">Renderizado secuencial con coherencia Gemini 3.1 Flash Image.</text>
</svg>"""
        b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{b64}"
