import os
import io
import base64
from typing import Optional, Type, Any, List, Dict
from pydantic import BaseModel
from google import genai
from google.genai import types
from PIL import Image

import config
from core.token_tracker import TokenTracker, TokenUsage, TokenLedger

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None

    def get_client(self, api_key_override: Optional[str] = None) -> genai.Client:
        key = api_key_override or self.api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("No se proporcionó una clave de API de Gemini (GEMINI_API_KEY).")
        return genai.Client(api_key=key)

    def test_connection(self, api_key: str) -> dict:
        """Prueba si una API key es válida ejecutando una consulta ultra liviana."""
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=config.DEFAULT_TEXT_MODEL,
                contents="Ping. Responde únicamente 'PONG'.",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=10
                )
            )
            return {
                "success": True,
                "message": f"Conexión exitosa con Google Gemini API (modelo: {config.DEFAULT_TEXT_MODEL}).",
                "response": response.text.strip() if response.text else "PONG"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error al validar API Key: {str(e)}"
            }

    def generate_structured_with_usage(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        api_key_override: Optional[str] = None,
        model: Optional[str] = None
    ) -> tuple[Any, TokenUsage]:
        """Genera una respuesta con esquema estructurado validado con Pydantic y retorna métricas de tokens/costo."""
        client = self.get_client(api_key_override)
        use_model = model or config.DEFAULT_TEXT_MODEL

        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=temperature,
            system_instruction=system_instruction
        )

        response = client.models.generate_content(
            model=use_model,
            contents=prompt,
            config=gen_config
        )

        # Extraer metadatos de tokens si están disponibles
        p_tokens = 0
        c_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            p_tokens = response.usage_metadata.prompt_token_count or 0
            c_tokens = response.usage_metadata.candidates_token_count or 0
        
        if p_tokens == 0 and c_tokens == 0:
            usage = TokenTracker.estimate_from_text(prompt, str(response.text or ""), model=use_model)
        else:
            usage = TokenTracker.calculate_cost(prompt_tokens=p_tokens, completion_tokens=c_tokens, model=use_model)

        TokenLedger.record_transaction(
            operation=f"structured_generation ({response_schema.__name__})",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            model=use_model,
            details=f"Tokens: {usage.total_tokens} (In: {usage.prompt_tokens}, Out: {usage.completion_tokens})"
        )

        return response.parsed, usage

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        api_key_override: Optional[str] = None,
        model: Optional[str] = None
    ) -> Any:
        """Wrapper compatible que retorna únicamente el objeto parseado."""
        parsed, _ = self.generate_structured_with_usage(
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=temperature,
            api_key_override=api_key_override,
            model=model
        )
        return parsed

    def generate_text_with_usage(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        api_key_override: Optional[str] = None,
        model: Optional[str] = None
    ) -> tuple[str, TokenUsage]:
        """Genera texto libre utilizando Gemini y calcula los tokens consumidos."""
        client = self.get_client(api_key_override)
        use_model = model or config.DEFAULT_TEXT_MODEL

        gen_config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction
        )

        response = client.models.generate_content(
            model=use_model,
            contents=prompt,
            config=gen_config
        )

        p_tokens = 0
        c_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            p_tokens = response.usage_metadata.prompt_token_count or 0
            c_tokens = response.usage_metadata.candidates_token_count or 0

        text_result = response.text or ""
        if p_tokens == 0 and c_tokens == 0:
            usage = TokenTracker.estimate_from_text(prompt, text_result, model=use_model)
        else:
            usage = TokenTracker.calculate_cost(prompt_tokens=p_tokens, completion_tokens=c_tokens, model=use_model)

        TokenLedger.record_transaction(
            operation="text_generation",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            model=use_model,
            details=f"Tokens: {usage.total_tokens}"
        )

        return text_result, usage

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        api_key_override: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        text_out, _ = self.generate_text_with_usage(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            api_key_override=api_key_override,
            model=model
        )
        return text_out

    def generate_image_sequential(
        self,
        prompt: str,
        reference_image_bytes: Optional[bytes] = None,
        anchor_image_bytes: Optional[bytes] = None,
        aspect_ratio: str = "16:9",
        api_key_override: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Genera una imagen con Gemini 3.1 Flash Image utilizando condicionamiento multimodal secuencial.
        Permite inyectar la imagen de referencia del personaje base (Anchor) y la imagen de la toma anterior (Previous Shot)
        para preservar la coherencia de vestuario, anatomía, iluminación y estilo de arte.
        """
        client = self.get_client(api_key_override)
        use_model = model or config.IMAGE_MODEL

        valid_ratios = ["1:1", "3:4", "4:3", "9:16", "16:9"]
        norm_ratio = aspect_ratio if aspect_ratio in valid_ratios else "16:9"
        if aspect_ratio == "2.39:1":
            norm_ratio = "16:9"

        # Construir la lista de contenidos multimodales
        contents: List[Any] = []

        # 1. Inyectar Anchor Sheet (Personaje base) si existe
        if anchor_image_bytes:
            try:
                anchor_img = Image.open(io.BytesIO(anchor_image_bytes))
                contents.append(anchor_img)
                contents.append("PRIMARY CHARACTER REFERENCE (Keep exact face features, outfit, hair and color scheme consistent):")
            except Exception as e:
                print(f"Aviso al cargar Anchor Image: {e}")

        # 2. Inyectar Previous Shot (Toma anterior) si existe
        if reference_image_bytes:
            try:
                ref_img = Image.open(io.BytesIO(reference_image_bytes))
                contents.append(ref_img)
                contents.append("PREVIOUS SHOT REFERENCE (Maintain visual continuity, art style and lighting atmosphere):")
            except Exception as e:
                print(f"Aviso al cargar Reference Image: {e}")

        # 3. Prompt de la toma actual
        contents.append(prompt)

        try:
            response = client.models.generate_content(
                model=use_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=norm_ratio,
                    ),
                ),
            )

            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        return part.inline_data.data
        except Exception as e:
            print(f"Error generando imagen secuencial con {use_model}: {e}")
            raise e

        return None

# Instancia singleton del servicio
gemini_service = GeminiService()
