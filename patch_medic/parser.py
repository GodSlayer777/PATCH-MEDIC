"""
parser.py: Triage y extracción de metadatos desde la salida estándar de Pytest.
Distingue de forma inteligente entre el archivo de test (donde falló el assert)
y el archivo de código fuente (donde reside el bug real que debe ser parchado).
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FailureContext:
    """Contenedor de información de contexto de un test roto."""
    filepath: str          # Archivo de lógica a editar/parchear (ej. src_sample.py)
    test_filepath: str     # Archivo donde reside la prueba (ej. tests/test_sample_broken.py)
    lineno: int            # Línea precisa de la falla en el archivo a parchar
    test_name: str         # Nombre de la prueba rota (ej. test_discount_normal)
    error_message: str     # Mensaje de excepción (ej. ZeroDivisionError, AssertionError)
    raw_traceback: str     # Traceback textual completo para alimentar al LLM


class PytestOutputParser:
    """Parsea tracebacks de pytest para extraer fallos individuales y sus coordenadas."""

    # Captura patrones tipo 'tests/test_foo.py:12:' o 'src/calc.py:45:'
    LOCATION_REGEX = re.compile(r"^([a-zA-Z0-9_\-\./\\]+\.py):(\d+):", re.MULTILINE)
    # Captura mensajes de error finales tipo 'E   ZeroDivisionError: division by zero'
    ERROR_REGEX = re.compile(r"^(E\s+[A-Za-z0-9_]+:.*)$", re.MULTILINE)

    @classmethod
    def parse(cls, output: str) -> List[FailureContext]:
        """
        Divide la salida general de pytest en bloques de tests individuales fallidos.
        """
        failures: List[FailureContext] = []
        
        # Aislar la sección 'FAILURES' descartando cabeceras y resúmenes finales
        chunks = output.split("=================================== FAILURES ===================================")
        target_block = chunks[1].split("================ short test summary info ================")[0] if len(chunks) > 1 else output

        # Separar por cada bloque delimitado por guiones bajos (ej. '___ test_name ___')
        test_blocks = re.split(r"_{3,}\s+([a-zA-Z0-9_\[\]\-\.]+)\s+_{3,}", target_block)
        
        if len(test_blocks) > 1:
            for i in range(1, len(test_blocks), 2):
                test_name = test_blocks[i]
                trace = test_blocks[i + 1]
                context = cls._extract_context(trace, test_name)
                if context:
                    failures.append(context)
        else:
            # Fallback si pytest no usó cabeceras estándar
            context = cls._extract_context(target_block, "unknown_test")
            if context:
                failures.append(context)

        return failures

    @classmethod
    def _extract_context(cls, block: str, default_test_name: str) -> Optional[FailureContext]:
        """
        Extrae la ruta del archivo objetivo, normaliza a POSIX (barras '/') y detecta el archivo a parchar.
        """
        raw_locations = cls.LOCATION_REGEX.findall(block)
        errors = cls.ERROR_REGEX.findall(block)

        if not raw_locations:
            return None

        # Normalizar rutas Windows ('\\') a estilo POSIX ('/') para evitar rechazos en 'git apply'
        normalized = [(path.replace("\\", "/"), int(line)) for path, line in raw_locations]

        # Discriminar archivos de prueba (tests/) de archivos de código fuente de la app
        test_locs = [loc for loc in normalized if loc[0].startswith("tests/") or "test_" in loc[0]]
        source_locs = [loc for loc in normalized if not loc[0].startswith("tests/") and not "test_" in loc[0]]

        # Guardar la ruta del test original para que la verificación apunte al archivo correcto
        test_filepath = test_locs[0][0] if test_locs else normalized[0][0]

        # Priorizar siempre el archivo de código fuente real para generar el parche.
        # Si la falla fue exclusivamente un assert dentro del propio test, se parchea el test.
        if source_locs:
            patch_filepath, lineno = source_locs[-1]
        else:
            patch_filepath, lineno = normalized[-1]

        error_msg = errors[-1] if errors else "AssertionError or Runtime Failure"

        return FailureContext(
            filepath=patch_filepath.strip(),
            test_filepath=test_filepath.strip(),
            lineno=lineno,
            test_name=default_test_name.strip(),
            error_message=error_msg.strip(),
            raw_traceback=block.strip()
        )