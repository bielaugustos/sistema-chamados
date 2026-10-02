# Sistema de Chamados (HelpDesk)

Sistema de gestão de chamados de suporte interno, com duas interfaces sobre o mesmo modelo de
dados:

- **Web** — aplicação Flask com SQLite: dashboard, listagem, cadastro e detalhe.
- **CLI** — interface de terminal com persistência em JSON, para uso em script ou automação.

As duas leem e escrevem os mesmos campos, com o mesmo vocabulário de status e prioridade. A
persistência continua separada: a web usa `instance/chamados.db` e a CLI usa
`dados/chamados.json` (veja [Persistência](#persistência)).

## Sumário

- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Executando](#executando)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Modelo de dados](#modelo-de-dados)
- [Aplicação web](#aplicação-web)
- [CLI](#cli)
- [Persistência](#persistência)
- [Uso como biblioteca](#uso-como-biblioteca)
- [Notas](#notas)

## Requisitos

- Python 3.8 ou superior
- Flask 3.1.3 (apenas para a interface web — a CLI não usa dependências externas)

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Executando

**Web:**

```bash
python app.py
```

Sobe em `http://127.0.0.1:5000` com debug ligado. Também funciona com `flask run`.

O banco `instance/chamados.db` e a tabela `chamados` são criados automaticamente na primeira
importação do módulo, nos dois modos de execução.

**CLI:**

```bash
python3 main.py --help
```

Não exige instalação — roda com o Python puro. Basta usar um interpretador compatível; o `.venv`
do projeto serve.

## Estrutura do projeto

```
sistema-chamados/
├── app.py               # Aplicação Flask: rotas e renderização
├── database.py          # Conexão SQLite e criação do schema
├── templates/           # Jinja2: base, dashboard, listagem, cadastro, detalhe
├── static/style.css     # Estilos da interface
├── instance/            # Banco SQLite (gerado, ignorado pelo git)
│
├── main.py              # CLI: parsing de argumentos e saída
├── chamado.py           # Modelo compartilhado: a classe Chamado
├── sistema_chamados.py  # Regras de negócio e persistência JSON da CLI
├── dados/               # JSON de chamados (gerado)
│
├── requirements.txt
└── README.md
```

## Modelo de dados

`chamado.py` define `Chamado`, um contêiner de dados usado pelas duas interfaces. Os campos
correspondem um a um às colunas da tabela `chamados` do SQLite:

| Campo | Tipo | Observação |
| --- | --- | --- |
| `id` | `int` | Sequencial; o SQLite usa autoincremento |
| `solicitante` | `str` | obrigatório |
| `titulo` | `str` | obrigatório |
| `descricao` | `str` | obrigatório |
| `prioridade` | `str` | `BAIXA`, `MEDIA` ou `ALTA` |
| `status` | `str` | `ABERTO`, `EM ATENDIMENTO` ou `FECHADO`; padrão `ABERTO` |
| `criado_em` | `datetime` | Preenchido com a data atual quando não informado |

Os valores válidos ficam centralizados em `sistema_chamados.py`
(`STATUS_VALIDOS`, `PRIORIDADES_VALIDAS`) e em `app.py` (`STATUS_VALIDOS`,
`PRIORIDADES_VALIDAS`). Entradas fora dessas listas são rejeitadas com `400` na web e com
mensagem em `stderr` e código de saída `1` na CLI.

Status e prioridade são texto, não enums: a mesma string circularia entre as duas camadas sem
conversão. As regras de transição não são impostas — qualquer status pode ir para qualquer outro.

A ordenação padrão nas duas interfaces é por prioridade (`ALTA` → `MEDIA` → `BAIXA`) e, dentro de
cada faixa, pelo id mais recente.

## Aplicação web

### Rotas

| Método | Rota | Função | Resultado |
| --- | --- | --- | --- |
| `GET` | `/` | Dashboard com contadores por status | `index.html` |
| `GET` | `/chamados` | Listagem ordenada por prioridade | `chamados.html` |
| `GET` | `/chamados/novo` | Formulário de abertura | `novo_chamado.html` |
| `POST` | `/chamados/novo` | Cria o chamado e redireciona para o detalhe | `302` |
| `GET` | `/chamados/<id>` | Detalhe e alteração de status | `chamado.html` |
| `POST` | `/chamados/<id>/status` | Atualiza o status | `302` |
| `POST` | `/chamados/<id>/excluir` | Remove o chamado | `302` |

Erros: `404` para chamado inexistente, `400` para status, prioridade ou campos obrigatórios inválidos.

### Fluxo

1. Em **Novo chamado**, preencha solicitante, título, descrição e prioridade.
2. Em **Chamados**, a listagem ordena por prioridade e, dentro de cada faixa, pelo id mais recente.
3. Em **Visualizar**, use o seletor de status para mover o chamado e o botão para excluí-lo.
4. O **Dashboard** mostra total, abertos, em atendimento e fechados.

O caminho `instance/` é criado automaticamente na primeira execução.

## CLI

### Comandos

| Comando | Função |
| --- | --- |
| `abrir` | Abre um novo chamado |
| `listar` | Lista os chamados, com filtros |
| `ver` | Mostra um chamado completo |
| `mover` | Altera o status |
| `prioridade` | Altera a prioridade |
| `remover` | Remove o chamado |
| `stats` | Resumo geral |

Opções globais: `--arquivo CAMINHO` para apontar outro arquivo de dados.

### Exemplos

```bash
# Abre um chamado
python3 main.py abrir --solicitante "Ana Souza" --titulo "Impressora sem rede" \
    --descricao "Andar 2 não responde" --prioridade ALTA

# Move o status e sobe a prioridade
python3 main.py mover 1 --status "EM ATENDIMENTO"
python3 main.py prioridade 1 --prioridade ALTA

# Consulta
python3 main.py listar
python3 main.py listar --abertos
python3 main.py listar --status ABERTO --prioridade MEDIA
python3 main.py listar --busca "impressora"
python3 main.py ver 1
python3 main.py stats
python3 main.py remover 1
```

Valores com espaço precisam de aspas: `--status "EM ATENDIMENTO"`.

Erros de entrada e de regra de negócio são impressos em `stderr` e encerram com código `1`.

## Persistência

**Web (SQLite).** `database.py` expõe `conectar()` e `criar_banco()`. A tabela é criada na
importação de `app.py`, e o caminho `instance/` é criado sob demanda. O caminho do banco é
ancorado no diretório do módulo, então o app funciona de qualquer diretório de trabalho.

**CLI (JSON).** Cada escrita chama `salvar()`, que serializa todos os chamados em `dados/chamados.json`.
Na inicialização, `SistemaChamados.carregar()` roda se o arquivo existir; JSON corrompido levanta
`RuntimeError`. A ordenação é recalculada a cada leitura e não é persistida.

Como são dois armazenamentos independentes, a web e a CLI não enxergam os mesmos dados.

## Uso como biblioteca

```python
from sistema_chamados import SistemaChamados

sistema = SistemaChamados()
chamado = sistema.registrar("Ana Souza", "Sem internet", "Sala 4", "ALTA")
sistema.mudar_status(chamado.id, "EM ATENDIMENTO")
sistema.mudar_status(chamado.id, "FECHADO")

print(sistema.estatisticas())
```

Na web, as funções de `database.py` podem ser usadas diretamente para consultas avulsas:

```python
from database import conectar

conexao = conectar()
chamados = conexao.execute(
    "SELECT * FROM chamados WHERE status = 'ABERTO' ORDER BY id DESC"
).fetchall()
conexao.close()
```

## Notas

- Não há autenticação: qualquer pessoa com acesso ao servidor abre, altera e exclui chamados.
- A web usa `debug=True`, adequado apenas para desenvolvimento local. Para produção, use um
  servidor WSGI.
- O modelo não distingue "em atendimento" de "aguardando terceiros", nem registra técnico,
  comentário ou data de encerramento — não há histórico de mudanças, só o estado atual.
- `chamado.py` é o único módulo lido pelas duas interfaces; `database.py` e
  `sistema_chamados.py` são específicos de cada uma.