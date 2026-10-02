"""Interface de linha de comando do sistema de chamados."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from sistema_chamados import (
    PRIORIDADES_VALIDAS,
    STATUS_VALIDOS,
    ChamadoNaoEncontrado,
    SistemaChamados,
)


def _linha(chamado) -> str:
    prioridade = f"[{chamado.prioridade}]"
    return (
        f"#{chamado.id:<4} {prioridade:<8} {chamado.status:<16} "
        f"{chamado.titulo[:40]:<40} {chamado.solicitante[:18]}"
    )


def _detalhar(chamado) -> str:
    return "\n".join(
        [
            f"Chamado #{chamado.id} - {chamado.titulo}",
            f"  Status      : {chamado.status}",
            f"  Prioridade  : {chamado.prioridade}",
            f"  Solicitante : {chamado.solicitante}",
            f"  Criado em   : {chamado.criado_em:%d/%m/%Y %H:%M}",
            f"  Descricao   : {chamado.descricao}",
        ]
    )


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sistema-chamados",
        description="Gestao de chamados de suporte interno.",
    )
    parser.add_argument(
        "--arquivo",
        type=str,
        help="Caminho do arquivo JSON de dados.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    abrir = sub.add_parser("abrir", help="Abre um novo chamado.")
    abrir.add_argument("--solicitante", required=True)
    abrir.add_argument("--titulo", required=True)
    abrir.add_argument("--descricao", required=True)
    abrir.add_argument(
        "--prioridade", default="MEDIA", choices=PRIORIDADES_VALIDAS
    )

    listar = sub.add_parser("listar", help="Lista os chamados.")
    listar.add_argument("--status", choices=STATUS_VALIDOS)
    listar.add_argument("--prioridade", choices=PRIORIDADES_VALIDAS)
    listar.add_argument("--busca", help="Filtra por titulo, descricao ou solicitante.")
    listar.add_argument("--abertos", action="store_true", help="Somente em aberto.")

    ver = sub.add_parser("ver", help="Mostra um chamado completo.")
    ver.add_argument("id", type=int)

    mover = sub.add_parser("mover", help="Altera o status do chamado.")
    mover.add_argument("id", type=int)
    mover.add_argument("--status", required=True, choices=STATUS_VALIDOS)

    prioridade = sub.add_parser("prioridade", help="Altera a prioridade.")
    prioridade.add_argument("id", type=int)
    prioridade.add_argument(
        "--prioridade", required=True, choices=PRIORIDADES_VALIDAS
    )

    remover = sub.add_parser("remover", help="Remove um chamado.")
    remover.add_argument("id", type=int)

    sub.add_parser("stats", help="Resumo dos chamados.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _criar_parser().parse_args(argv)
    sistema = SistemaChamados(args.arquivo)
    comando = args.comando

    if comando == "abrir":
        chamado = sistema.registrar(
            solicitante=args.solicitante,
            titulo=args.titulo,
            descricao=args.descricao,
            prioridade=args.prioridade,
        )
        print(f"Chamado #{chamado.id} criado.")
        return 0

    if comando == "listar":
        chamados = sistema.listar(
            status=args.status,
            prioridade=args.prioridade,
            busca=args.busca,
            abertos=args.abertos,
        )
        if not chamados:
            print("Nenhum chamado encontrado.")
            return 0
        for chamado in chamados:
            print(_linha(chamado))
        print(f"\nTotal: {len(chamados)}")
        return 0

    if comando == "ver":
        print(_detalhar(sistema.obter(args.id)))
        return 0

    if comando == "mover":
        sistema.mudar_status(args.id, args.status)
        print(f"Chamado #{args.id} movido para {args.status}.")
        return 0

    if comando == "prioridade":
        sistema.mudar_prioridade(args.id, args.prioridade)
        print(f"Chamado #{args.id} prioridade atualizada.")
        return 0

    if comando == "remover":
        sistema.remover(args.id)
        print(f"Chamado #{args.id} removido.")
        return 0

    if comando == "stats":
        dados = sistema.estatisticas()
        print(f"Total          : {dados['total']}")
        print(f"Abertos        : {dados['abertos']}")
        print(f"Em atendimento : {dados['em_atendimento']}")
        print(f"Fechados       : {dados['fechados']}")
        print(f"Por status     : {dados['por_status']}")
        print(f"Por prioridade : {dados['por_prioridade']}")
        return 0

    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ChamadoNaoEncontrado, ValueError, RuntimeError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        sys.exit(1)