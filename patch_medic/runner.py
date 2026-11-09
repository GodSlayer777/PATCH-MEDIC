"""
runner.py: Ejecutor de pytest mediante subprocesos.
Invoca pytest utilizando el mismo binario de Python del entorno virtual activo (sys.executable)
para evitar discrepancias de dependencias o problemas de PATH en Windows y Linux.
"""

import sys
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestRunResult:
    """Estructura con el resultado de ejecución del subproceso de pruebas."""
    exit_code: int  # 0 indica que todos los tests pasaron; distinto de 0 indica fallo o error
    stdout: str     # Salida estándar (captura reportes de aserciones y tablas de pytest)
    stderr: str     # Errores de flujo estándar del proceso


def run_tests(target_test: Optional[str] = None) -> TestRunResult:
    """
    Ejecuta pytest como módulo de Python con captura de salida completa.

    :param target_test: Especificador opcional de prueba o archivo (ej. 'tests/test_math.py::test_foo').
                        Si es None, se evalúa la suite completa del proyecto.
    :return: TestRunResult con el código de retorno y los flujos de texto capturados.
    """
    # --tb=long asegura trazas detalladas con variables locales para el contexto del LLM
    # -q mantiene la salida compacta sin ruido innecesario
    cmd = [sys.executable, "-m", "pytest", "--tb=long", "-q"]
    if target_test:
        cmd.append(target_test)

    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return TestRunResult(
        exit_code=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr
    )