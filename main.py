"""Interface de linha de comando do sistema de chamados."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from chamado import Prioridade, Status, TransicaoInvalida
from sistema_chamados import ChamadoNaoEncontrado, SistemaChamados


def _linha(chamado) -> str:
    prioridade = f"[{chamado.prioridade.rotulo}]"
    return (
        f"#{chamado.id:<4} {prioridade:<10} {chamado.status.rotulo:<16} "
        f"{chamado.titulo[:40]:<40} {chamado.solicitante[:18]}"
    )


def _detalhar(chamado) -> str:
    partes = [
        f"Chamado #{chamado.id} - {chamado.titulo}",
        f"  Status      : {chamado.status.rotulo}",
        f"  Prioridade  : {chamado.prioridade.rotulo}",
        f"  Solicitante : {chamado.solicitante}",
        f"  Tecnico     : {chamado.tecnico or '-'}",
        f"  Aberto em   : {chamado.data_abertura:%d/%m/%Y %H:%M}",
        f"  Tempo       : {chamado.tempo_atendimento}",
    ]
    if chamado.descricao:
        partes.append(f"  Descricao   : {chamado.descricao}")
    if chamado.comentarios:
        partes.append("  Comentarios :")
        for comentario in chamado.comentarios:
            partes.append(
                f"    - [{comentario.data:%d/%m %H:%M}] {comentario.autor}: "
                f"{comentario.texto}"
            )
    return "\n".join(partes)


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
    abrir.add_argument("--titulo", required=True)
    abrir.add_argument("--solicitante", required=True)
    abrir.add_argument("--descricao", default="")
    abrir.add_argument(
        "--prioridade",
        default="media",
        choices=["baixa", "media", "alta", "urgente"],
    )

    listar = sub.add_parser("listar", help="Lista os chamados.")
    listar.add_argument("--status", choices=[s.value for s in Status])
    listar.add_argument("--prioridade", choices=["baixa", "media", "alta", "urgente"])
    listar.add_argument("--busca", help="Filtra por titulo, descricao ou solicitante.")
    listar.add_argument("--abertos", action="store_true", help="Somente em aberto.")

    ver = sub.add_parser("ver", help="Mostra um chamado completo.")
    ver.add_argument("id", type=int)

    atribuir = sub.add_parser("atribuir", help="Atribui um tecnico.")
    atribuir.add_argument("id", type=int)
    atribuir.add_argument("--tecnico", required=True)

    mover = sub.add_parser("mover", help="Altera o status do chamado.")
    mover.add_argument("id", type=int)
    mover.add_argument(
        "--status", required=True, choices=[s.value for s in Status]
    )

    prioridade = sub.add_parser("prioridade", help="Altera a prioridade.")
    prioridade.add_argument("id", type=int)
    prioridade.add_argument(
        "--prioridade", required=True, choices=["baixa", "media", "alta", "urgente"]
    )

    comentar = sub.add_parser("comentar", help="Adiciona um comentario.")
    comentar.add_argument("id", type=int)
    comentar.add_argument("--autor", required=True)
    comentar.add_argument("--texto", required=True)

    fechar = sub.add_parser("fechar", help="Resolve o chamado.")
    fechar.add_argument("id", type=int)
    fechar.add_argument("--resolucao", default="")

    sub.add_parser("stats", help="Resumo dos chamados.")

    remover = sub.add_parser("remover", help="Remove um chamado.")
    remover.add_argument("id", type=int)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _criar_parser().parse_args(argv)
    sistema = SistemaChamados(args.arquivo)
    comando = args.comando

    if comando == "abrir":
        chamado = sistema.registrar(
            titulo=args.titulo,
            solicitante=args.solicitante,
            descricao=args.descricao,
            prioridade=Prioridade.from_rotulo(args.prioridade),
        )
        print(f"Chamado #{chamado.id} criado.")
        return 0

    if comando == "listar":
        chamados = sistema.listar(
            status=Status.from_rotulo(args.status) if args.status else None,
            prioridade=(
                Prioridade.from_rotulo(args.prioridade) if args.prioridade else None
            ),
            busca=args.busca,
            em_aberto=args.abertos,
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

    if comando == "atribuir":
        sistema.atribuir(args.id, args.tecnico)
        print(f"Chamado #{args.id} atribuido a {args.tecnico}.")
        return 0

    if comando == "mover":
        sistema.mudar_status(args.id, Status.from_rotulo(args.status))
        print(f"Chamado #{args.id} movido.")
        return 0

    if comando == "prioridade":
        sistema.mudar_prioridade(args.id, Prioridade.from_rotulo(args.prioridade))
        print(f"Chamado #{args.id} prioridade atualizada.")
        return 0

    if comando == "comentar":
        sistema.comentar(args.id, args.autor, args.texto)
        print(f"Comentario registrado no chamado #{args.id}.")
        return 0

    if comando == "fechar":
        sistema.fechar(args.id, args.resolucao)
        print(f"Chamado #{args.id} resolvido.")
        return 0

    if comando == "remover":
        sistema.remover(args.id)
        print(f"Chamado #{args.id} removido.")
        return 0

    if comando == "stats":
        dados = sistema.estatisticas()
        print(f"Total        : {dados['total']}")
        print(f"Em aberto    : {dados['em_aberto']}")
        print(f"Finalizados  : {dados['finalizados']}")
        print(f"Tempo medio  : {dados['tempo_medio']}")
        print(f"Por status   : {dados['por_status']}")
        print(f"Por prioridade: {dados['por_prioridade']}")
        return 0

    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ChamadoNaoEncontrado, TransicaoInvalida, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        sys.exit(1)