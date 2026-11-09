"""
agent.py: Cliente HTTP encargado de la interacción con el LLM.
Transforma el contexto del fallo y el código AST extraído en un Unified Diff aplicable por Git.
"""

import os
import re
import time
import httpx
from patch_medic.extractor import CodeSnippet
from patch_medic.parser import FailureContext

# Carga de credenciales y configuración base.
# NOTA: En producción/CI nunca hardcodear API keys; usar variables de entorno.
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")


class PatchAgent:
    """Gestiona la formulación de prompts, llamadas al endpoint y saneamiento de diffs."""

    def __init__(self, api_key: str = API_KEY, base_url: str = BASE_URL, model: str = MODEL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_patch(self, failure: FailureContext, snippet: CodeSnippet) -> str:
        """
        Envía al LLM el contexto aislado del fallo y solicita un Unified Diff estándar.

        :param failure: Metadatos del error (archivo objetivo, línea, traceback).
        :param snippet: Fragmento de código delimitado por AST.
        :return: Diff unificado limpio listo para 'git apply'.
        """
        if not self.api_key:
            raise ValueError("Falta configurar la variable GEMINI_API_KEY o LLM_API_KEY.")

        # Instrucción estricta: forzar formato git diff para evitar respuestas conversacionales
        instructions = (
            "Genera UNICAMENTE un diff unificado estándar compatible con `git apply` para resolver el error.\n"
            f"El diff DEBE comenzar exactamente con:\n"
            f"--- a/{failure.filepath}\n"
            f"+++ b/{failure.filepath}\n"
            "seguido por el bloque de chunks '@@ ... @@' con las líneas a eliminar (-) y agregar (+).\n"
            "NO agregues texto explicativo, comentarios ni saludos antes o después."
        )

        # Contexto minimalista enfocado en el nodo AST para reducir consumo de tokens
        user_content = (
            f"Instrucción:\n{instructions}\n\n"
            f"Ruta del archivo objetivo: {failure.filepath}\n"
            f"Línea de falla: {failure.lineno}\n"
            f"Test fallido: {failure.test_name}\n"
            f"Error capturado: {failure.error_message}\n\n"
            f"Bloque de código original extraído por AST:\n"
            f"{snippet.content}\n\n"
            f"Traceback del fallo:\n"
            f"{failure.raw_traceback}\n"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Temperature en 0.0 para maximizar determinismo y consistencia sintáctica
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "user", "content": user_content}
            ]
        }

        # Manejo de peticiones con reintentos para mitigar límites de cuota (HTTP 429)
        max_http_retries = 3
        with httpx.Client(timeout=45.0) as client:
            for attempt in range(max_http_retries):
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)

                if response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()
                raw_diff = data["choices"][0]["message"]["content"]
                return self._clean_diff(raw_diff)

        raise RuntimeError("Se excedió la tasa de peticiones (429 Rate Limit) tras múltiples reintentos.")

    def _clean_diff(self, raw_diff: str) -> str:
        """
        Limpia bloques de Markdown (```diff) y recorta cualquier prefijo ajeno al diff.
        """
        # Extraer diff si el modelo lo encapsuló en backticks de Markdown
        diff_match = re.search(r"```(?:diff)?\s*\n(.*?)\n```", raw_diff, re.DOTALL)
        diff_text = diff_match.group(1) if diff_match else raw_diff

        # Garantizar que el diff comience exactamente en la cabecera de Git ('--- ')
        start_idx = diff_text.find("--- ")
        if start_idx != -1:
            diff_text = diff_text[start_idx:]

        return diff_text.strip() + "\n"