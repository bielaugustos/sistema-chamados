from datetime import datetime


class Chamado:
    def __init__(
        self,
        id,
        solicitante,
        titulo,
        descricao,
        prioridade,
        status,
        criado_em=None,
    ):
        self.id = id
        self.solicitante = solicitante
        self.titulo = titulo
        self.descricao = descricao
        self.prioridade = prioridade
        self.status = status
        self.criado_em = criado_em or datetime.now()