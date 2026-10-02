"""Modelo de dominio do chamado (ticket) e seus enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Prioridade(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    URGENTE = 4

    @classmethod
    def from_rotulo(cls, rotulo: str) -> "Prioridade":
        normalizado = rotulo.strip().upper().replace("-", "").replace(" ", "")
        aliases = {
            "BAIXA": cls.BAIXA,
            "NORMAL": cls.MEDIA,
            "MEDIA": cls.MEDIA,
            "ALTA": cls.ALTA,
            "URGENTE": cls.URGENTE,
            "CRITICA": cls.URGENTE,
        }
        if normalizado not in aliases:
            raise ValueError(f"Prioridade invalida: {rotulo!r}")
        return aliases[normalizado]

    @property
    def rotulo(self) -> str:
        return self.name.capitalize()


class Status(Enum):
    ABERTO = "aberto"
    EM_ATENDIMENTO = "em_atendimento"
    AGUARDANDO = "aguardando"
    RESOLVIDO = "resolvido"
    CANCELADO = "cancelado"

    @classmethod
    def from_rotulo(cls, rotulo: str) -> "Status":
        normalizado = rotulo.strip().lower().replace("-", "_").replace(" ", "_")
        try:
            return cls(normalizado)
        except ValueError as erro:
            raise ValueError(f"Status invalido: {rotulo!r}") from erro

    @property
    def rotulo(self) -> str:
        return self.value.replace("_", " ").capitalize()

    @property
    def finalizado(self) -> bool:
        return self in (Status.RESOLVIDO, Status.CANCELADO)


TRANSICOES = {
    Status.ABERTO: (Status.EM_ATENDIMENTO, Status.AGUARDANDO, Status.RESOLVIDO, Status.CANCELADO),
    Status.EM_ATENDIMENTO: (Status.AGUARDANDO, Status.RESOLVIDO, Status.CANCELADO),
    Status.AGUARDANDO: (Status.EM_ATENDIMENTO, Status.RESOLVIDO, Status.CANCELADO),
    Status.RESOLVIDO: (),
    Status.CANCELADO: (),
}


class TransicaoInvalida(Exception):
    """Levantada quando o status solicitado nao e permitido a partir do atual."""


@dataclass(frozen=True)
class Comentario:
    autor: str
    texto: str
    data: datetime = field(default_factory=datetime.now)

    def para_dict(self) -> Dict[str, Any]:
        return {
            "autor": self.autor,
            "texto": self.texto,
            "data": self.data.isoformat(timespec="seconds"),
        }

    @classmethod
    def de_dict(cls, dados: Dict[str, Any]) -> "Comentario":
        return cls(
            autor=dados["autor"],
            texto=dados["texto"],
            data=datetime.fromisoformat(dados["data"]),
        )


@dataclass
class Chamado:
    titulo: str
    solicitante: str
    descricao: str = ""
    prioridade: Prioridade = Prioridade.MEDIA
    status: Status = Status.ABERTO
    id: Optional[int] = None
    tecnico: Optional[str] = None
    comentarios: List[Comentario] = field(default_factory=list)
    data_abertura: datetime = field(default_factory=datetime.now)
    data_encerramento: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.titulo = self.titulo.strip()
        self.solicitante = self.solicitante.strip()
        self.descricao = self.descricao.strip()
        if not self.titulo:
            raise ValueError("O titulo do chamado e obrigatorio")
        if not self.solicitante:
            raise ValueError("O solicitante do chamado e obrigatorio")

    def atribuir(self, tecnico: str) -> "Chamado":
        if self.status.finalizado:
            raise TransicaoInvalida(f"Chamado {self.id} esta finalizado")
        self.tecnico = tecnico.strip()
        if self.status is Status.ABERTO:
            self.mudar_status(Status.EM_ATENDIMENTO)
        return self

    def mudar_prioridade(self, prioridade: Prioridade) -> "Chamado":
        self.prioridade = prioridade
        return self

    def mudar_status(self, novo_status: Status) -> "Chamado":
        if novo_status is self.status:
            return self
        permitidos = TRANSICOES[self.status]
        if novo_status not in permitidos:
            origem = self.status.rotulo
            raise TransicaoInvalida(
                f"Nao e possivel ir de '{origem}' para '{novo_status.rotulo}'"
            )
        self.status = novo_status
        if novo_status.finalizado:
            self.data_encerramento = datetime.now()
        elif self.data_encerramento is not None:
            self.data_encerramento = None
        return self

    def comentar(self, autor: str, texto: str) -> "Comentario":
        if not texto.strip():
            raise ValueError("O comentario nao pode ser vazio")
        comentario = Comentario(autor=autor.strip() or "anonimo", texto=texto.strip())
        self.comentarios.append(comentario)
        return comentario

    @property
    def tempo_atendimento(self) -> Optional[str]:
        fim = self.data_encerramento or datetime.now()
        segundos = int((fim - self.data_abertura).total_seconds())
        horas, resto = divmod(segundos, 3600)
        minutos = resto // 60
        if horas:
            return f"{horas}h {minutos:02d}min"
        return f"{minutos}min"

    @property
    def em_aberto(self) -> bool:
        return not self.status.finalizado

    def para_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "solicitante": self.solicitante,
            "descricao": self.descricao,
            "prioridade": self.prioridade.name,
            "status": self.status.value,
            "tecnico": self.tecnico,
            "data_abertura": self.data_abertura.isoformat(timespec="seconds"),
            "data_encerramento": (
                self.data_encerramento.isoformat(timespec="seconds")
                if self.data_encerramento
                else None
            ),
            "comentarios": [c.para_dict() for c in self.comentarios],
        }

    @classmethod
    def de_dict(cls, dados: Dict[str, Any]) -> "Chamado":
        return cls(
            titulo=dados["titulo"],
            solicitante=dados["solicitante"],
            descricao=dados.get("descricao", ""),
            prioridade=Prioridade[dados.get("prioridade", "MEDIA")],
            status=Status.from_rotulo(dados.get("status", "aberto")),
            id=dados.get("id"),
            tecnico=dados.get("tecnico"),
            comentarios=[Comentario.de_dict(c) for c in dados.get("comentarios", [])],
            data_abertura=datetime.fromisoformat(dados["data_abertura"]),
            data_encerramento=(
                datetime.fromisoformat(dados["data_encerramento"])
                if dados.get("data_encerramento")
                else None
            ),
        )
