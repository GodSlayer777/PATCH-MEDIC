"""
verifier.py: Validador en dos fases para parches aplicados.
Garantiza que un diff no solo repare el test específico que falló,
sino que no introduzca regresiones en el resto de la suite de pruebas.
"""

from dataclasses import dataclass
from patch_medic.runner import run_tests


@dataclass
class VerificationResult:
    """Resultado de la verificación por etapas de un parche."""
    success: bool      # True si pasó ambas fases sin ningún fallo
    phase: str        # 'unit' (falló el test objetivo), 'full_suite' (regresión) o 'complete'
    error_output: str = ""  # Salida de error de pytest en caso de fallo


class PatchVerifier:
    """Orquestador de verificación escalonada."""

    @classmethod
    def verify(cls, target_test: str) -> VerificationResult:
        """
        Ejecuta la validación en dos pasos:
        1. Fast Check: Evalúa únicamente el test que originó la falla.
        2. Regression Check: Si el test pasa, evalúa la suite completa.

        :param target_test: Ruta completa y nodo del test (ej. 'tests/test_x.py::test_y').
        :return: VerificationResult indicando estado y fase.
        """
        # Fase 1: Validar si el test objetivo fue solucionado con el parche
        fast_check = run_tests(target_test=target_test)
        if fast_check.exit_code != 0:
            return VerificationResult(
                success=False,
                phase="unit",
                error_output=fast_check.stdout or fast_check.stderr
            )

        # Fase 2: Validar que no se generaron efectos colaterales ni regresiones en otros tests
        full_suite = run_tests()
        if full_suite.exit_code != 0:
            return VerificationResult(
                success=False,
                phase="full_suite",
                error_output=full_suite.stdout or full_suite.stderr
            )

        return VerificationResult(success=True, phase="complete")