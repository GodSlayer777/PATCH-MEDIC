"""
patcher.py: Aplicador de diffs atómico y tolerante a fallos.
Usa 'git apply' con flags de flexibilidad para tolerar pequeñas desalineaciones
de líneas y saltos de línea CRLF/LF de Windows, garantizando rollbacks limpios.
"""

import subprocess
import tempfile
from pathlib import Path


class Patcher:
    """Gestiona la aplicación de parches y la restauración del workspace."""

    @staticmethod
    def apply_diff(diff_content: str) -> bool:
        """
        Aplica un diff unificado sobre el árbol de trabajo actual.

        Flags utilizados para máxima compatibilidad:
        - newline='\\n': Evita saltos CRLF accidentales en el archivo temporal.
        - -C1: Reduce a 1 línea el requisito de contexto idéntico.
        - --ignore-whitespace: Ignora diferencias entre espacios y tabulaciones.
        - --recount: Recalcula automáticamente las cuentas de líneas de los chunks.
        - --unidiff-zero: Permite diffs generados sin números de contexto exactos.
        - --3way: Fallback para fusionar cambios si hubo pequeñas divergencias.
        """
        with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False, newline="\n", encoding="utf-8") as tmp:
            tmp.write(diff_content)
            tmp_path = tmp.name

        try:
            # Intento principal con tolerancia avanzada de diff
            result = subprocess.run(
                [
                    "git", "apply",
                    "-C1",
                    "--ignore-whitespace",
                    "--recount",
                    "--unidiff-zero",
                    tmp_path
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"\n[git apply error]: {result.stderr.strip()}")
                
                # Segundo intento: fallback con merge de tres vías (--3way)
                fallback = subprocess.run(
                    ["git", "apply", "--3way", "--ignore-whitespace", tmp_path],
                    capture_output=True,
                    text=True
                )
                return fallback.returncode == 0

            return True
        finally:
            # Asegurar siempre la eliminación del archivo temporal
            Path(tmp_path).unlink(missing_ok=True)

    @staticmethod
    def rollback_file(filepath: str):
        """
        Restaura un archivo específico al último commit registrado en Git.
        Descarta cualquier cambio no comiteado introducido por un parche fallido.
        """
        subprocess.run(["git", "checkout", "--", filepath], capture_output=True)

    @staticmethod
    def rollback_all():
        """Descarta absolutamente todas las modificaciones pendientes en el repositorio."""
        subprocess.run(["git", "restore", "."], capture_output=True)