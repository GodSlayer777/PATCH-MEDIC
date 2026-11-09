"""
test_parser.py: Pruebas unitarias para los componentes centrales de análisis:
1. PytestOutputParser (extracción de metadatos de fallos a partir de salidas de terminal).
2. SourceExtractor (aislamiento de funciones por AST).
"""

import pytest
from pathlib import Path
from patch_medic.parser import PytestOutputParser
from patch_medic.extractor import extract_faulty_code

# Salida simulada representativa de un traceback estándar emitido por Pytest
DUMMY_PYTEST_OUTPUT = """
=================================== FAILURES ===================================
___________________________________ test_divide ___________________________________
tests/test_math.py:8: in test_divide
    assert divide(10, 0) == 0
E   ZeroDivisionError: division by zero
================ short test summary info ================
FAILED tests/test_math.py::test_divide - ZeroDivisionError: division by zero
"""


def test_parser_extracts_correct_failure_metadata():
    """Valida que el parser identifique archivo, línea, nombre de test y mensaje de error."""
    failures = PytestOutputParser.parse(DUMMY_PYTEST_OUTPUT)
    assert len(failures) == 1
    f = failures[0]
    assert f.filepath == "tests/test_math.py"
    assert f.lineno == 8
    assert f.test_name == "test_divide"
    assert "ZeroDivisionError" in f.error_message


def test_ast_extractor_isolates_only_enclosing_function(tmp_path: Path):
    """
    Valida que extract_faulty_code utilice el AST para recortar únicamente
    el bloque de la función culpable, descartando código periférico.
    """
    source = (
        "def helper():\n"
        "    return 42\n\n"
        "def faulty_function(a, b):\n"
        "    result = a / b\n"
        "    return result\n\n"
        "def other():\n"
        "    pass\n"
    )
    test_file = tmp_path / "sample.py"
    test_file.write_text(source, encoding="utf-8")

    # La línea 5 corresponde a 'result = a / b' dentro de faulty_function
    snippet = extract_faulty_code(str(test_file), target_line=5)

    assert snippet is not None
    assert snippet.target_node_name == "faulty_function"
    assert snippet.start_line == 4
    assert snippet.end_line == 6
    # Confirma que el recortador excluyó funciones ajenas al fallo
    assert "helper" not in snippet.content
    assert "other" not in snippet.content