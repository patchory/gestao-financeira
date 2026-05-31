from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime, date
from collections import defaultdict

app = Flask(__name__)
DB_PATH = '/tmp/empresa.db'

CATEGORIAS_SAIDA = [
    'Marketing',
    'Papelaria / Escritório',
    'Impostos / Taxas',
    'Outros'
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada','saida')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT,
            data TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
    ''')
    conn.commit()
    conn.close()

def resumo_mes(ano, mes):
    conn = get_db()
    prefixo = f"{ano}-{mes:02d}"
    rows = conn.execute(
        "SELECT tipo, categoria, SUM(valor) as total FROM transacoes WHERE data LIKE ? GROUP BY tipo, categoria",
        (prefixo + '%',)
    ).fetchall()
    conn.close()

    entradas = 0.0
    saidas_por_categoria = defaultdict(float)

    for r in rows:
        if r['tipo'] == 'entrada':
            entradas += r['total']
        else:
            saidas_por_categoria[r['categoria'] or 'Outros'] += r['total']

    total_saidas = sum(saidas_por_categoria.values())
    lucro = entradas - total_saidas
    rentabilidade = (lucro / entradas * 100) if entradas > 0 else 0.0

    return {
        'entradas': entradas,
        'saidas': total_saidas,
        'saidas_por_categoria': dict(saidas_por_categoria),
        'lucro': lucro,
        'rentabilidade': rentabilidade,
    }

@app.route('/')
def index():
    hoje = date.today()
    ano = int(request.args.get('ano', hoje.year))
    mes = int(request.args.get('mes', hoje.month))

    conn = get_db()
    transacoes = conn.execute(
        "SELECT * FROM transacoes WHERE data LIKE ? ORDER BY data DESC, id DESC",
        (f"{ano}-{mes:02d}%",)
    ).fetchall()
    conn.close()

    res = resumo_mes(ano, mes)
    meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

    return render_template('index.html',
        transacoes=transacoes,
        resumo=res,
        categorias=CATEGORIAS_SAIDA,
        ano=ano, mes=mes,
        meses_nomes=meses_nomes,
        hoje=hoje,
    )

@app.route('/adicionar', methods=['POST'])
def adicionar():
    tipo = request.form.get('tipo')
    descricao = request.form.get('descricao', '').strip()
    valor_str = request.form.get('valor', '0').replace(',', '.')
    categoria = request.form.get('categoria') if tipo == 'saida' else None
    data = request.form.get('data') or date.today().isoformat()

    try:
        valor = float(valor_str)
        if valor <= 0 or not descricao:
            raise ValueError
    except ValueError:
        return redirect(url_for('index'))

    conn = get_db()
    conn.execute(
        "INSERT INTO transacoes (tipo, descricao, valor, categoria, data) VALUES (?,?,?,?,?)",
        (tipo, descricao, valor, categoria, data)
    )
    conn.commit()
    conn.close()

    ano, mes, _ = data.split('-')
    return redirect(url_for('index', ano=ano, mes=int(mes)))

@app.route('/excluir/<int:id>')
def excluir(id):
    conn = get_db()
    row = conn.execute("SELECT data FROM transacoes WHERE id=?", (id,)).fetchone()
    conn.execute("DELETE FROM transacoes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    if row:
        d = row['data'].split('-')
        return redirect(url_for('index', ano=d[0], mes=int(d[1])))
    return redirect(url_for('index'))

@app.route('/api/grafico')
def api_grafico():
    hoje = date.today()
    dados = []
    for i in range(5, -1, -1):
        m = hoje.month - i
        a = hoje.year
        while m <= 0:
            m += 12; a -= 1
        r = resumo_mes(a, m)
        meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        dados.append({
            'mes': meses_nomes[m-1],
            'entradas': round(r['entradas'], 2),
            'saidas': round(r['saidas'], 2),
            'lucro': round(r['lucro'], 2),
        })
    return jsonify(dados)

# Inicializa o banco sempre — funciona com gunicorn e python direto
init_db()

if __name__ == '__main__':
    print("\n✅ Sistema iniciado!")
    print("👉 Abra no navegador: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
