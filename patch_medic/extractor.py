"""
extractor.py: Token-Pruner basado en AST (Abstract Syntax Tree).
Localiza y aísla exclusivamente la función o método Python donde ocurrió el fallo,
evitando enviar archivos enteros al LLM y ahorrando costos/tokens.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass
class CodeSnippet:
    """Contenedor de metadatos del fragmento de código recortado."""
    filepath: str           # Ruta relativa del archivo fuente
    target_node_name: str   # Nombre de la función aislada (ej. 'calculate_discount')
    start_line: int         # Línea inicial (1-indexed)
    end_line: int           # Línea final (1-indexed)
    content: str            # Texto fuente exacto de la función


# Tipo compuesto para admitir funciones síncronas y asíncronas
TargetFunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]


class SourceExtractor(ast.NodeVisitor):
    """
    Recorre el AST buscando el nodo funcional que envuelve la línea de falla.
    Si hay funciones anidadas, selecciona siempre la más interna (menor rango de líneas).
    """

    def __init__(self, target_line: int):
        self.target_line = target_line
        self.best_match: Optional[TargetFunctionNode] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visita definiciones de funciones estándar."""
        self._check_node(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visita definiciones de funciones async."""
        self._check_node(node)
        self.generic_visit(node)

    def _check_node(self, node: TargetFunctionNode):
        """
        Verifica si target_line cae dentro del rango de líneas del nodo.
        En caso de colisión (funciones dentro de funciones), conserva la de menor span.
        """
        start = node.lineno
        end = node.end_lineno
        if end is not None and start <= self.target_line <= end:
            if self.best_match is None:
                self.best_match = node
            else:
                prev_end = self.best_match.end_lineno or self.best_match.lineno
                prev_span = prev_end - self.best_match.lineno
                new_span = end - start
                # Si el nuevo nodo es más específico/pequeño, lo priorizamos
                if new_span < prev_span:
                    self.best_match = node


def extract_faulty_code(filepath: str, target_line: int) -> Optional[CodeSnippet]:
    """
    Parsea un archivo Python a AST y extrae la función envolvente de target_line.

    :param filepath: Ruta del archivo Python a analizar.
    :param target_line: Número de línea donde ocurrió la excepción.
    :return: CodeSnippet con el código aislado o None si falla el parseo o no hay función.
    """
    path = Path(filepath)
    if not path.exists():
        return None

    source_code = path.read_text(encoding="utf-8")
    try:
        # Generar el árbol sintáctico abstracto
        tree = ast.parse(source_code, filename=filepath)
    except SyntaxError:
        # Si el código no compila o tiene sintaxis rota, no se puede podar por AST
        return None

    extractor = SourceExtractor(target_line)
    extractor.visit(tree)

    # Validar que se haya encontrado una función válida y con línea final delimitada
    if not extractor.best_match or extractor.best_match.end_lineno is None:
        return None

    matched_node = extractor.best_match
    node_name = matched_node.name
    start_line = matched_node.lineno
    end_line = matched_node.end_lineno

    # Extraer el slice de líneas del archivo fuente original (1-indexed a 0-indexed)
    lines = source_code.splitlines()
    snippet_lines = lines[start_line - 1 : end_line]
    snippet_content = "\n".join(snippet_lines)

    return CodeSnippet(
        filepath=filepath,
        target_node_name=node_name,
        start_line=start_line,
        end_line=end_line,
        content=snippet_content
    )