"""
test_sample_broken.py: Suite de prueba controlada para validar el auto-sanador.
Contiene casos normales, casos límite y pruebas de excepciones para `calculate_discount`.
"""

import pytest
from src_sample import calculate_discount


def test_discount_normal():
    """Valida un cálculo con porcentaje válido estándar."""
    result = calculate_discount(100.0, 20.0)
    assert result == 80.0, f"Esperado 80.0 pero se obtuvo {result}"


def test_discount_zero():
    """Valida el caso borde donde no se aplica descuento (0%)."""
    assert calculate_discount(50.0, 0.0) == 50.0


def test_discount_invalid_range():
    """Valida que porcentajes superiores al 100% lancen ValueError adecuadamente."""
    with pytest.raises(ValueError):
        calculate_discount(100.0, 150.0)