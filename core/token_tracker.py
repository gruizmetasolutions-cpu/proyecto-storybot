import math
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import config

class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Tokens consumidos en prompts de entrada")
    completion_tokens: int = Field(default=0, description="Tokens consumidos en respuestas generadas")
    total_tokens: int = Field(default=0, description="Suma total de tokens de texto")
    images_generated: int = Field(default=0, description="Cantidad de imágenes renderizadas")
    audio_chars_synthesized: int = Field(default=0, description="Cantidad de caracteres sintetizados con TTS")
    estimated_cost_usd: float = Field(default=0.0, description="Costo total estimado en USD")
    formatted_cost: str = Field(default="$0.0000 USD", description="Costo formateado para la UI")

class TokenTracker:
    @staticmethod
    def calculate_cost(
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = config.DEFAULT_TEXT_MODEL,
        images_count: int = 0,
        audio_chars: int = 0
    ) -> TokenUsage:
        """
        Calcula el uso acumulado de tokens y el costo en USD con base en los precios oficiales de Google Gemini.
        """
        pricing = config.MODEL_PRICING.get(model, config.MODEL_PRICING[config.DEFAULT_TEXT_MODEL])
        
        # Costo de texto
        in_cost = (prompt_tokens / 1_000_000.0) * pricing.get("input_per_million", 0.075)
        out_cost = (completion_tokens / 1_000_000.0) * pricing.get("output_per_million", 0.300)
        
        # Costo de imágenes
        img_pricing = config.MODEL_PRICING.get("gemini-3.1-flash-image", {"cost_per_image": 0.020})
        img_cost = images_count * img_pricing["cost_per_image"]
        
        # Costo de audio TTS
        tts_pricing = config.MODEL_PRICING.get("gemini-3.1-flash-tts-preview", {"cost_per_1k_chars": 0.0005})
        tts_cost = (audio_chars / 1000.0) * tts_pricing["cost_per_1k_chars"]
        
        total_cost = in_cost + out_cost + img_cost + tts_cost
        total_toks = prompt_tokens + completion_tokens
        
        # Formatear el costo con alta precisión (hasta 5 decimales si es muy pequeño)
        if total_cost < 0.01:
            formatted = f"${total_cost:.4f} USD"
        else:
            formatted = f"${total_cost:.2f} USD"
            
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_toks,
            images_generated=images_count,
            audio_chars_synthesized=audio_chars,
            estimated_cost_usd=round(total_cost, 5),
            formatted_cost=formatted
        )

    @staticmethod
    def estimate_from_text(prompt_text: str, completion_text: str = "", model: str = config.DEFAULT_TEXT_MODEL, images_count: int = 0, audio_chars: int = 0) -> TokenUsage:
        """
        Aproximación rápida de tokens basada en ratio de caracteres (~4 caracteres por token en español/inglés).
        Útil para presupuestar antes de llamar a la API o en modo offline/demo.
        """
        approx_prompt_tokens = max(1, int(len(prompt_text) / 3.8))
        approx_comp_tokens = max(1, int(len(completion_text) / 3.8)) if completion_text else 0
        return TokenTracker.calculate_cost(
            prompt_tokens=approx_prompt_tokens,
            completion_tokens=approx_comp_tokens,
            model=model,
            images_count=images_count,
            audio_chars=audio_chars
        )
