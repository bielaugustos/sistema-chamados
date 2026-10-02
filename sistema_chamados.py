"""Regras de negocio e persistencia dos chamados."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from chamado import Chamado, Prioridade, Status


class ChamadoNaoEncontrado(Exception):
    """Levantada quando nenhum chamado possui o id informado."""


class SistemaChamados:
    ARQUIVO_PADRAO = Path(__file__).parent / "dados" / "chamados.json"

    def __init__(self, arquivo: Optional[Path] = None) -> None:
        self.arquivo = Path(arquivo) if arquivo else self.ARQUIVO_PADRAO
        self._chamados: Dict[int, Chamado] = {}
        self._proximo_id = 1
        if self.arquivo.exists():
            self.carregar()

    def registrar(
        self,
        titulo: str,
        solicitante: str,
        descricao: str = "",
        prioridade: Prioridade = Prioridade.MEDIA,
    ) -> Chamado:
        chamado = Chamado(
            id=self._proximo_id,
            titulo=titulo,
            solicitante=solicitante,
            descricao=descricao,
            prioridade=prioridade,
        )
        self._chamados[chamado.id] = chamado
        self._proximo_id += 1
        self.salvar()
        return chamado

    def obter(self, id_chamado: int) -> Chamado:
        try:
            return self._chamados[id_chamado]
        except KeyError:
            raise ChamadoNaoEncontrado(f"Chamado {id_chamado} nao encontrado") from None

    def listar(
        self,
        status: Optional[Status] = None,
        prioridade: Optional[Prioridade] = None,
        busca: Optional[str] = None,
        em_aberto: bool = False,
    ) -> List[Chamado]:
        resultados = list(self._chamados.values())
        if status is not None:
            resultados = [c for c in resultados if c.status is status]
        if prioridade is not None:
            resultados = [c for c in resultados if c.prioridade is prioridade]
        if em_aberto:
            resultados = [c for c in resultados if c.em_aberto]
        if busca:
            termo = busca.strip().lower()
            resultados = [
                c
                for c in resultados
                if termo in c.titulo.lower()
                or termo in c.descricao.lower()
                or termo in c.solicitante.lower()
            ]
        return self.ordenar(resultados)

    def ordenar(
        self, chamados: Optional[List[Chamado]] = None
    ) -> List[Chamado]:
        base = list(chamados) if chamados is not None else list(self._chamados.values())
        return sorted(
            base,
            key=lambda c: (
                not c.em_aberto,
                -c.prioridade.value,
                c.data_abertura,
            ),
        )

    def atribuir(self, id_chamado: int, tecnico: str) -> Chamado:
        chamado = self.obter(id_chamado)
        chamado.atribuir(tecnico)
        self.salvar()
        return chamado

    def mudar_status(self, id_chamado: int, status: Status) -> Chamado:
        chamado = self.obter(id_chamado)
        chamado.mudar_status(status)
        self.salvar()
        return chamado

    def mudar_prioridade(
        self, id_chamado: int, prioridade: Prioridade
    ) -> Chamado:
        chamado = self.obter(id_chamado)
        chamado.mudar_prioridade(prioridade)
        self.salvar()
        return chamado

    def comentar(self, id_chamado: int, autor: str, texto: str) -> Chamado:
        chamado = self.obter(id_chamado)
        chamado.comentar(autor, texto)
        self.salvar()
        return chamado

    def fechar(self, id_chamado: int, texto_resolucao: str = "") -> Chamado:
        chamado = self.obter(id_chamado)
        if texto_resolucao:
            chamado.comentar(chamado.tecnico or chamado.solicitante, texto_resolucao)
        chamado.mudar_status(Status.RESOLVIDO)
        self.salvar()
        return chamado

    def remover(self, id_chamado: int) -> None:
        self.obter(id_chamado)
        del self._chamados[id_chamado]
        self.salvar()

    def estatisticas(self) -> Dict[str, object]:
        chamados = list(self._chamados.values())
        em_aberto = [c for c in chamados if c.em_aberto]
        return {
            "total": len(chamados),
            "em_aberto": len(em_aberto),
            "finalizados": len(chamados) - len(em_aberto),
            "por_status": dict(Counter(c.status.rotulo for c in chamados)),
            "por_prioridade": dict(Counter(c.prioridade.rotulo for c in chamados)),
            "tempo_medio": self._tempo_medio(em_aberto) if em_aberto else "-",
        }

    @staticmethod
    def _tempo_medio(chamados: List[Chamado]) -> str:
        segundos = sum(
            int((datetime.now() - c.data_abertura).total_seconds()) for c in chamados
        )
        minutos_medios = segundos // (60 * len(chamados))
        horas, minutos = divmod(minutos_medios, 60)
        if horas:
            return f"{horas}h {minutos:02d}min"
        return f"{minutos}min"

    def salvar(self) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        dados = [c.para_dict() for c in self._chamados.values()]
        self.arquivo.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def carregar(self) -> None:
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as erro:
            raise RuntimeError(f"Arquivo de chamados invalido: {erro}") from erro
        self._chamados = {}
        for item in dados:
            chamado = Chamado.de_dict(item)
            self._chamados[chamado.id] = chamado
        self._proximo_id = max(self._chamados, default=0) + 1

    def __len__(self) -> int:
        return len(self._chamados)


if __name__ == "__main__":
    sistema = SistemaChamados()
    sistema.registrar("Impressora sem rede", "Ana Souza", "Andar 2", Prioridade.ALTA)
    sistema.registrar("Solicitar acesso", "Bruno Lima")
    for chamado in sistema.listar():
        print(chamado)
