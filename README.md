# Sistema de Chamados

Sistema simples de gestao de chamados (tickets) de suporte interno, feito em Python puro, sem dependencias externas.

## Estrutura

```
sistema-chamados/
├── main.py              # CLI (abrir, listar, ver, atribuir, mover, comentar, fechar, stats)
├── chamado.py           # Modelo de dominio: Chamado, Comentario, Prioridade, Status
├── sistema_chamados.py  # Regras de negocio e persistencia em JSON
└── README.md
```

## Requisitos

Python 3.8 ou superior. Nenhuma biblioteca externa necessaria.

## Uso

```bash
python3 main.py --help
```

Os dados sao gravados em `dados/chamados.json`. Use `--arquivo` para apontar outro arquivo.

### Fluxo tipico

```bash
# Abre um chamado
python3 main.py abrir --titulo "Impressora sem rede" --solicitante "Ana Souza" \
    --descricao "Andar 2 nao responde" --prioridade alta

# Atribui um tecnico (muda o status para "em atendimento" automaticamente)
python3 main.py atribuir 1 --tecnico "Carlos Dias"

# Comenta e resolve
python3 main.py comentar 1 --autor "Carlos Dias" --texto "Troquei o cabo de rede"
python3 main.py fechar 1 --resolucao "Impressora voltou ao normal"

# Consulta
python3 main.py listar --abertos
python3 main.py ver 1
python3 main.py stats
```

## Conceitos

**Prioridade**: `BAIXA`, `MEDIA`, `ALTA`, `URGENTE`. Define a ordem na listagem.

**Status**: `ABERTO` -> `EM_ATENDIMENTO` / `AGUARDANDO` -> `RESOLVIDO` ou `CANCELADO`.

Transicoes invalidas levantam `TransicaoInvalida`. Exemplo: um chamado `RESOLVIDO` ou `CANCELADO` nao volta para aberto, e nao aceita novos comentarios de atribuicao.

**Comentario**: registro datado de autor e texto, mantidos em ordem cronologica no chamado.

**Ordenacao**: a listagem prioriza chamados em aberto, depois por prioridade decrescente, depois pelo mais antigo.

## Uso como biblioteca

```python
from chamado import Prioridade, Status
from sistema_chamados import SistemaChamados

sistema = SistemaChamados()
chamado = sistema.registrar("Sem internet", "Marina Reis", "Sala 4", Prioridade.URGENTE)
sistema.atribuir(chamado.id, "Carlos Dias")
sistema.comentar(chamado.id, "Marina Reis", "Roteador reiniciado, voltou")
sistema.fechar(chamado.id, "Chamado resolvido")

print(sistema.estatisticas())
```

## Persistencia

Cada operacao de escrita chama `salvar()`, que serializa todos os chamados em JSON. `SistemaChamados.carregar()` e executado na inicializacao quando o arquivo existe. Arquivos corrompidos levantam `RuntimeError`.