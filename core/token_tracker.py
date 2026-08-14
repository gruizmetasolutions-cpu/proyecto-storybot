import os
import json
import time
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import config

LEDGER_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "token_ledger.json")

class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Tokens consumidos en prompts de entrada")
    completion_tokens: int = Field(default=0, description="Tokens consumidos en respuestas generadas")
    total_tokens: int = Field(default=0, description="Suma total de tokens de texto")
    images_generated: int = Field(default=0, description="Cantidad de imágenes renderizadas")
    audio_chars_synthesized: int = Field(default=0, description="Cantidad de caracteres sintetizados con TTS")
    estimated_cost_usd: float = Field(default=0.0, description="Costo total estimado en USD")
    formatted_cost: str = Field(default="$0.0000 USD", description="Costo formateado para la UI")

class TokenTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    operation: str = Field(description="Nombre de la operación ejecutada")
    model: str = Field(default=config.DEFAULT_TEXT_MODEL, description="Modelo utilizado en la llamada")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    images_count: int = 0
    audio_chars: int = 0
    cost_usd: float = 0.0
    formatted_cost: str = "$0.0000 USD"
    details: Optional[str] = None

class TokenLedger:
    """
    Libro mayor persistente en disco (data/token_ledger.json).
    Actúa como la ÚNICA FUENTE DE VERDAD (Single Source of Truth) para el rastreo y cálculo
    del consumo de tokens y costos en USD durante toda la vida útil del proyecto.
    """
    @staticmethod
    def _ensure_storage_dir():
        storage_dir = os.path.dirname(LEDGER_FILE_PATH)
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

    @staticmethod
    def load_ledger() -> Dict[str, Any]:
        """Carga el ledger desde el disco o inicializa uno nuevo."""
        TokenLedger._ensure_storage_dir()
        if not os.path.exists(LEDGER_FILE_PATH):
            default_ledger = {
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "totals": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "images_generated": 0,
                    "audio_chars_synthesized": 0,
                    "estimated_cost_usd": 0.0,
                    "formatted_cost": "$0.0000 USD",
                    "total_transactions": 0
                },
                "transactions": []
            }
            TokenLedger._save_raw(default_ledger)
            return default_ledger

        try:
            with open(LEDGER_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso: Error leyendo ledger {LEDGER_FILE_PATH}: {e}. Reiniciando estructura limpia.")
            return {
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "totals": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "images_generated": 0,
                    "audio_chars_synthesized": 0,
                    "estimated_cost_usd": 0.0,
                    "formatted_cost": "$0.0000 USD",
                    "total_transactions": 0
                },
                "transactions": []
            }

    @staticmethod
    def _save_raw(data: Dict[str, Any]):
        TokenLedger._ensure_storage_dir()
        with open(LEDGER_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def record_transaction(
        operation: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        images_count: int = 0,
        audio_chars: int = 0,
        model: str = config.DEFAULT_TEXT_MODEL,
        details: Optional[str] = None
    ) -> TokenTransaction:
        """
        Registra una transacción contable inmutable, recalcula los totales globales y persiste a disco.
        """
        usage = TokenTracker.calculate_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            images_count=images_count,
            audio_chars=audio_chars
        )

        tx = TokenTransaction(
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            images_count=images_count,
            audio_chars=audio_chars,
            cost_usd=usage.estimated_cost_usd,
            formatted_cost=usage.formatted_cost,
            details=details
        )

        ledger = TokenLedger.load_ledger()
        totals = ledger.get("totals", {})
        
        totals["prompt_tokens"] = totals.get("prompt_tokens", 0) + prompt_tokens
        totals["completion_tokens"] = totals.get("completion_tokens", 0) + completion_tokens
        totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
        totals["images_generated"] = totals.get("images_generated", 0) + images_count
        totals["audio_chars_synthesized"] = totals.get("audio_chars_synthesized", 0) + audio_chars
        
        new_cost = round(totals.get("estimated_cost_usd", 0.0) + usage.estimated_cost_usd, 6)
        totals["estimated_cost_usd"] = new_cost
        totals["formatted_cost"] = f"${new_cost:.4f} USD"
        totals["total_transactions"] = totals.get("total_transactions", 0) + 1

        ledger["totals"] = totals
        ledger["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if "transactions" not in ledger:
            ledger["transactions"] = []
        ledger["transactions"].insert(0, tx.model_dump())
        
        # Limitar historial a las últimas 200 transacciones para mantener rapidez
        if len(ledger["transactions"]) > 200:
            ledger["transactions"] = ledger["transactions"][:200]

        TokenLedger._save_raw(ledger)
        return tx

    @staticmethod
    def get_summary() -> Dict[str, Any]:
        """Obtiene los totales acumulados del libro mayor."""
        ledger = TokenLedger.load_ledger()
        return ledger.get("totals", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "images_generated": 0,
            "audio_chars_synthesized": 0,
            "estimated_cost_usd": 0.0,
            "formatted_cost": "$0.0000 USD",
            "total_transactions": 0
        })

    @staticmethod
    def get_history(limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene el historial cronológico de transacciones."""
        ledger = TokenLedger.load_ledger()
        txs = ledger.get("transactions", [])
        return txs[:limit]

    @staticmethod
    def reset() -> Dict[str, Any]:
        """Reinicia el libro mayor a ceros de manera explícita."""
        default_ledger = {
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "totals": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "images_generated": 0,
                "audio_chars_synthesized": 0,
                "estimated_cost_usd": 0.0,
                "formatted_cost": "$0.0000 USD",
                "total_transactions": 0
            },
            "transactions": []
        }
        TokenLedger._save_raw(default_ledger)
        return default_ledger["totals"]

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
        Calcula el uso acumulado de tokens y el costo exacto en USD con base en las tarifas oficiales de Google Gemini.
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
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            images_generated=images_count,
            audio_chars_synthesized=audio_chars,
            estimated_cost_usd=round(total_cost, 6),
            formatted_cost=f"${total_cost:.4f} USD"
        )

    @staticmethod
    def estimate_from_text(prompt_text: str, completion_text: str = "", images_count: int = 0, audio_chars: int = 0) -> TokenUsage:
        """
        Heurística precisa para estimación offline: 1 token ≈ 4 caracteres en español/inglés.
        """
        p_tokens = math.ceil(len(prompt_text) / 4) if prompt_text else 0
        c_tokens = math.ceil(len(completion_text) / 4) if completion_text else 0
        return TokenTracker.calculate_cost(
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            images_count=images_count,
            audio_chars=audio_chars
        )
