from flask import Flask, abort, redirect, render_template, request, url_for

from database import conectar, criar_banco

app = Flask(__name__)

STATUS_VALIDOS = ("ABERTO", "EM ATENDIMENTO", "FECHADO")
PRIORIDADES_VALIDAS = ("BAIXA", "MEDIA", "ALTA")

criar_banco()


def _ordenacao_prioridade():
    return "CASE prioridade WHEN 'ALTA' THEN 1 WHEN 'MEDIA' THEN 2 ELSE 3 END"


@app.route("/")
def dashboard():
    conexao = conectar()
    totais = conexao.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status = 'ABERTO' THEN 1 ELSE 0 END), 0) AS abertos,
            COALESCE(SUM(CASE WHEN status = 'EM ATENDIMENTO' THEN 1 ELSE 0 END), 0)
                AS atendimento,
            COALESCE(SUM(CASE WHEN status = 'FECHADO' THEN 1 ELSE 0 END), 0) AS fechados
        FROM chamados
        """
    ).fetchone()
    conexao.close()
    return render_template("index.html", **dict(totais))


@app.route("/chamados")
def listar_chamados():
    conexao = conectar()
    chamados = conexao.execute(
        f"SELECT * FROM chamados ORDER BY {_ordenacao_prioridade()}, id DESC"
    ).fetchall()
    conexao.close()
    return render_template("chamados.html", chamados=chamados)


@app.route("/chamados/novo", methods=["GET", "POST"])
def novo_chamado():
    if request.method == "POST":
        solicitante = request.form["solicitante"].strip()
        titulo = request.form["titulo"].strip()
        descricao = request.form["descricao"].strip()
        prioridade = request.form["prioridade"]

        if not solicitante or not titulo or not descricao:
            abort(400, "Solicitante, titulo e descricao sao obrigatorios.")
        if prioridade not in PRIORIDADES_VALIDAS:
            abort(400, "Prioridade invalida.")

        conexao = conectar()
        cursor = conexao.execute(
            """
            INSERT INTO chamados (solicitante, titulo, descricao, prioridade, status)
            VALUES (?, ?, ?, ?, 'ABERTO')
            """,
            (solicitante, titulo, descricao, prioridade),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
        conexao.close()
        return redirect(url_for("visualizar_chamado", id=novo_id))

    return render_template("novo_chamado.html")


@app.route("/chamados/<int:id>")
def visualizar_chamado(id):
    conexao = conectar()
    chamado = conexao.execute(
        "SELECT * FROM chamados WHERE id = ?",
        (id,),
    ).fetchone()
    conexao.close()
    if chamado is None:
        abort(404, "Chamado nao encontrado.")
    return render_template(
        "chamado.html",
        chamado=chamado,
        status_validos=STATUS_VALIDOS,
    )


@app.route("/chamados/<int:id>/status", methods=["POST"])
def alterar_status(id):
    status = request.form["status"]
    if status not in STATUS_VALIDOS:
        abort(400, "Status invalido.")

    conexao = conectar()
    cursor = conexao.execute(
        """
        UPDATE chamados
        SET status = ?
        WHERE id = ?
        """,
        (status, id),
    )
    conexao.commit()
    conexao.close()
    if cursor.rowcount == 0:
        abort(404, "Chamado nao encontrado.")
    return redirect(
        url_for("visualizar_chamado", id=id)
    )


@app.route("/chamados/<int:id>/excluir", methods=["POST"])
def excluir_chamado(id):
    conexao = conectar()
    conexao.execute(
        "DELETE FROM chamados WHERE id = ?",
        (id,),
    )
    conexao.commit()
    conexao.close()
    return redirect(url_for("listar_chamados"))


if __name__ == "__main__":
    app.run(debug=True)