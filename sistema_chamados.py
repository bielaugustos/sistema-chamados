"""Regras de negocio e persistencia dos chamados."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from chamado import Chamado

STATUS_VALIDOS = ("ABERTO", "EM ATENDIMENTO", "FECHADO")
PRIORIDADES_VALIDAS = ("BAIXA", "MEDIA", "ALTA")
STATUS_ABERTOS = ("ABERTO", "EM ATENDIMENTO")
PESO_PRIORIDADE = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}


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
        solicitante: str,
        titulo: str,
        descricao: str,
        prioridade: str = "MEDIA",
    ) -> Chamado:
        campos = {
            "solicitante": solicitante,
            "titulo": titulo,
            "descricao": descricao,
        }
        for campo, valor in campos.items():
            if not valor or not valor.strip():
                raise ValueError(f"O campo '{campo}' e obrigatorio")
        if prioridade not in PRIORIDADES_VALIDAS:
            raise ValueError(f"Prioridade invalida: {prioridade!r}")

        chamado = Chamado(
            id=self._proximo_id,
            solicitante=solicitante.strip(),
            titulo=titulo.strip(),
            descricao=descricao.strip(),
            prioridade=prioridade,
            status="ABERTO",
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
        status: Optional[str] = None,
        prioridade: Optional[str] = None,
        busca: Optional[str] = None,
        abertos: bool = False,
    ) -> List[Chamado]:
        if status is not None:
            self._validar_status(status)
        if prioridade is not None:
            self._validar_prioridade(prioridade)

        resultados = list(self._chamados.values())
        if status is not None:
            resultados = [c for c in resultados if c.status == status]
        if prioridade is not None:
            resultados = [c for c in resultados if c.prioridade == prioridade]
        if abertos:
            resultados = [c for c in resultados if c.status in STATUS_ABERTOS]
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

    def ordenar(self, chamados: Optional[List[Chamado]] = None) -> List[Chamado]:
        base = list(chamados) if chamados is not None else list(self._chamados.values())
        return sorted(
            base,
            key=lambda c: (PESO_PRIORIDADE[c.prioridade], -c.id),
        )

    def mudar_status(self, id_chamado: int, status: str) -> Chamado:
        self._validar_status(status)
        chamado = self.obter(id_chamado)
        chamado.status = status
        self.salvar()
        return chamado

    def mudar_prioridade(self, id_chamado: int, prioridade: str) -> Chamado:
        self._validar_prioridade(prioridade)
        chamado = self.obter(id_chamado)
        chamado.prioridade = prioridade
        self.salvar()
        return chamado

    def remover(self, id_chamado: int) -> None:
        self.obter(id_chamado)
        del self._chamados[id_chamado]
        self.salvar()

    def estatisticas(self) -> Dict[str, object]:
        chamados = list(self._chamados.values())
        contagem = Counter(c.status for c in chamados)
        return {
            "total": len(chamados),
            "abertos": contagem.get("ABERTO", 0),
            "em_atendimento": contagem.get("EM ATENDIMENTO", 0),
            "fechados": contagem.get("FECHADO", 0),
            "por_status": {s: contagem.get(s, 0) for s in STATUS_VALIDOS},
            "por_prioridade": dict(Counter(c.prioridade for c in chamados)),
        }

    @staticmethod
    def _validar_status(status: str) -> None:
        if status not in STATUS_VALIDOS:
            raise ValueError(f"Status invalido: {status!r}")

    @staticmethod
    def _validar_prioridade(prioridade: str) -> None:
        if prioridade not in PRIORIDADES_VALIDAS:
            raise ValueError(f"Prioridade invalida: {prioridade!r}")

    def salvar(self) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        dados = [self._para_dict(c) for c in self._chamados.values()]
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
            self._chamados[item["id"]] = self._de_dict(item)
        self._proximo_id = max(self._chamados, default=0) + 1

    @staticmethod
    def _para_dict(chamado: Chamado) -> Dict[str, object]:
        return {
            "id": chamado.id,
            "solicitante": chamado.solicitante,
            "titulo": chamado.titulo,
            "descricao": chamado.descricao,
            "prioridade": chamado.prioridade,
            "status": chamado.status,
            "criado_em": chamado.criado_em.isoformat(timespec="seconds"),
        }

    @staticmethod
    def _de_dict(dados: Dict[str, object]) -> Chamado:
        criado_em = dados.get("criado_em")
        return Chamado(
            id=dados["id"],
            solicitante=dados["solicitante"],
            titulo=dados["titulo"],
            descricao=dados.get("descricao", ""),
            prioridade=dados.get("prioridade", "MEDIA"),
            status=dados.get("status", "ABERTO"),
            criado_em=datetime.fromisoformat(criado_em) if criado_em else None,
        )

    def __len__(self) -> int:
        return len(self._chamados)