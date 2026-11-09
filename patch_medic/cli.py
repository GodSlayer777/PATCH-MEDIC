"""
cli.py: Punto de entrada de la interfaz de línea de comandos.
Orquesta el ciclo reactivo: ejecución -> triage -> extracción AST -> llamada al LLM -> parchado -> validación.
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from patch_medic.runner import run_tests
from patch_medic.parser import PytestOutputParser
from patch_medic.extractor import extract_faulty_code
from patch_medic.agent import PatchAgent
from patch_medic.patcher import Patcher
from patch_medic.verifier import PatchVerifier

console = Console()
MAX_RETRIES = 2


@click.group()
def cli():
    """patch-medic: Agente CLI para triaje y autoreparación de suites de test."""
    pass


@cli.command()
@click.option("--target", default=None, help="Ruta del test específico a ejecutar (ej. tests/test_calc.py).")
@click.option("--max-retries", default=MAX_RETRIES, help="Intentos máximos de auto-parche por fallo antes de abortar.")
def heal(target: str, max_retries: int):
    """
    Ejecuta un bucle reactivo continuo:
    1. Ejecuta tests y obtiene fallos en caliente.
    2. Si todo pasa, termina exitosamente.
    3. Si hay fallos, toma el primero, aplica parche y re-evalúa.
    """
    console.print("[bold cyan]🔍 [patch-medic][/bold cyan] Ejecutando suite de validación...")
    agent = PatchAgent()

    # Bucle reactivo dinámico: evalúa el estado del repositorio tras cada cambio
    while True:
        current_run = run_tests(target)
        if current_run.exit_code == 0:
            console.print("[bold green]✨ Todos los fallos han sido reparados con éxito. Toda la suite pasa.[/bold green]")
            sys.exit(0)

        # Parsear stack traces de la ejecución actual
        failures = PytestOutputParser.parse(current_run.stdout)
        if not failures:
            console.print("[bold red]✖ Los tests fallaron pero no se pudieron parsear los stack traces.[/bold red]")
            sys.exit(1)

        # Procesar de forma prioritaria el primer fallo activo
        failure = failures[0]

        console.print(Panel(
            f"[bold]Archivo a parchar:[/bold] {failure.filepath}:{failure.lineno}\n"
            f"[bold]Test fallando:[/bold] {failure.test_name} ({failure.test_filepath})\n"
            f"[bold]Causa:[/bold] {failure.error_message}",
            title="[red]Test Fallido[/red]",
            expand=False
        ))

        # Token-Pruning: aislar mediante AST solo la función responsable
        snippet = extract_faulty_code(failure.filepath, failure.lineno)
        if not snippet:
            console.print(f"[yellow]No se pudo recortar AST para {failure.filepath}. Abortando...[/yellow]\n")
            sys.exit(1)

        console.print(f"[cyan]📦 Token-Pruner: Extraído nodo '{snippet.target_node_name}' (Líneas {snippet.start_line}-{snippet.end_line})[/cyan]")

        repaired = False
        for attempt in range(1, max_retries + 1):
            console.print(f"  [magenta]➔ Intento {attempt}/{max_retries} de reparación para {failure.test_name}...[/magenta]")

            # 1. Generar diff a través del agente LLM
            try:
                diff = agent.generate_patch(failure, snippet)
            except Exception as e:
                console.print(f"  [red]Error al consultar el LLM:[/red] {e}")
                break

            # 2. Aplicar diff de forma atómica en el espacio de trabajo con git apply
            console.print("  [dim]Aplicando diff en el espacio de trabajo...[/dim]")
            applied = Patcher.apply_diff(diff)
            if not applied:
                console.print("  [red]✖ El diff devuelto por el modelo no es válido o no se pudo aplicar.[/red]")
                continue

            # 3. Verificación en dos fases:
            #    Fase A: test unitario individual.
            #    Fase B: suite completa (detección de regresiones).
            console.print("  [dim]Verificando test unitario y suite de regresión...[/dim]")
            target_spec = f"{failure.test_filepath}::{failure.test_name}"
            result = PatchVerifier.verify(target_test=target_spec)

            if result.success:
                repaired = True
                console.print(f"  [green]✔ Fallo en {failure.test_name} resuelto y validado.[/green]")
                console.print(Panel(Syntax(diff, "diff", theme="monokai"), title="[green]Parche Aplicado[/green]"))
                break  # Salir del bucle de reintentos y dejar que el while re-evalúe la suite
            else:
                # Si falló la verificación, revertir cambios inmediatamente para dejar el repo limpio
                console.print(f"  [yellow]⚠ Parche falló en fase '{result.phase}'. Revirtiendo cambios...[/yellow]")
                Patcher.rollback_file(failure.filepath)

        # Si agotó los reintentos sin éxito, revertir y detener ejecución
        if not repaired:
            Patcher.rollback_file(failure.filepath)
            console.print(f"  [red]✖ Abortado: No se pudo resolver automáticamente {failure.test_name}. Requiere revisión manual.[/red]\n")
            sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()