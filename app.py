from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
import sqlite3, os, io, json
from datetime import datetime, date
from collections import defaultdict
from functools import wraps

app = Flask(__name__)
app.secret_key = 'gestao_financeira_secret_2024'
DB_PATH = '/tmp/empresa.db'

# ── Senha de acesso ──────────────────────────────────────────
SENHA_ACESSO = 'tiago123'  # ← troque aqui

CATEGORIAS_SAIDA = [
    'Shopee Ads', 'Marketing', 'Papelaria / Escritório',
    'Impostos / Taxas', 'Contas a Pagar', 'Outros'
]

# ── Banco de dados ───────────────────────────────────────────
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
            observacao TEXT,
            data TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            meta_entrada REAL DEFAULT 0,
            meta_lucro REAL DEFAULT 0,
            UNIQUE(ano, mes)
        );
        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('pagar','receber')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            vencimento TEXT NOT NULL,
            pago INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
    ''')
    conn.commit()
    conn.close()

# ── Login ────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    erro = ''
    if request.method == 'POST':
        if request.form.get('senha') == SENHA_ACESSO:
            session['logado'] = True
            return redirect(url_for('index'))
        erro = 'Senha incorreta!'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Resumo mensal ────────────────────────────────────────────
def resumo_mes(ano, mes):
    conn = get_db()
    prefixo = f"{ano}-{mes:02d}"
    rows = conn.execute(
        "SELECT tipo, categoria, SUM(valor) as total FROM transacoes WHERE data LIKE ? GROUP BY tipo, categoria",
        (prefixo + '%',)
    ).fetchall()
    meta = conn.execute("SELECT * FROM metas WHERE ano=? AND mes=?", (ano, mes)).fetchone()
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
    ads = saidas_por_categoria.get('Shopee Ads', 0.0)
    roas = (entradas / ads) if ads > 0 else 0.0
    pct_ads = (ads / entradas * 100) if entradas > 0 else 0.0

    meta_entrada = meta['meta_entrada'] if meta else 0
    meta_lucro   = meta['meta_lucro']   if meta else 0
    pct_meta_entrada = (entradas / meta_entrada * 100) if meta_entrada > 0 else 0
    pct_meta_lucro   = (lucro   / meta_lucro   * 100) if meta_lucro   > 0 else 0

    return {
        'entradas': entradas, 'saidas': total_saidas,
        'saidas_por_categoria': dict(saidas_por_categoria),
        'lucro': lucro, 'rentabilidade': rentabilidade,
        'ads': ads, 'roas': roas, 'pct_ads': pct_ads,
        'meta_entrada': meta_entrada, 'meta_lucro': meta_lucro,
        'pct_meta_entrada': min(pct_meta_entrada, 100),
        'pct_meta_lucro':   min(pct_meta_lucro,   100),
        'meta_entrada_raw': pct_meta_entrada,
        'meta_lucro_raw':   pct_meta_lucro,
    }

# ── Rotas principais ─────────────────────────────────────────
@app.route('/')
@login_required
def index():
    hoje = date.today()
    ano = int(request.args.get('ano', hoje.year))
    mes = int(request.args.get('mes', hoje.month))
    conn = get_db()
    transacoes = conn.execute(
        "SELECT * FROM transacoes WHERE data LIKE ? ORDER BY data DESC, id DESC",
        (f"{ano}-{mes:02d}%",)
    ).fetchall()
    contas_pendentes = conn.execute(
        "SELECT * FROM contas WHERE pago=0 ORDER BY vencimento ASC LIMIT 5"
    ).fetchall()
    conn.close()
    res = resumo_mes(ano, mes)
    meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    return render_template('index.html',
        transacoes=transacoes, resumo=res,
        categorias=CATEGORIAS_SAIDA,
        ano=ano, mes=mes, meses_nomes=meses_nomes,
        hoje=hoje, contas_pendentes=contas_pendentes,
    )

@app.route('/adicionar', methods=['POST'])
@login_required
def adicionar():
    tipo = request.form.get('tipo')
    descricao = request.form.get('descricao','').strip()
    valor_str = request.form.get('valor','0').replace(',','.')
    categoria = request.form.get('categoria') if tipo == 'saida' else None
    observacao = request.form.get('observacao','').strip() or None
    data = request.form.get('data') or date.today().isoformat()
    try:
        valor = float(valor_str)
        if valor <= 0 or not descricao: raise ValueError
    except ValueError:
        return redirect(url_for('index'))
    conn = get_db()
    conn.execute(
        "INSERT INTO transacoes (tipo,descricao,valor,categoria,observacao,data) VALUES (?,?,?,?,?,?)",
        (tipo, descricao, valor, categoria, observacao, data)
    )
    conn.commit(); conn.close()
    ano, mes, _ = data.split('-')
    return redirect(url_for('index', ano=ano, mes=int(mes)))

@app.route('/excluir/<int:id>')
@login_required
def excluir(id):
    conn = get_db()
    row = conn.execute("SELECT data FROM transacoes WHERE id=?", (id,)).fetchone()
    conn.execute("DELETE FROM transacoes WHERE id=?", (id,))
    conn.commit(); conn.close()
    if row:
        d = row['data'].split('-')
        return redirect(url_for('index', ano=d[0], mes=int(d[1])))
    return redirect(url_for('index'))

# ── Meta mensal ──────────────────────────────────────────────
@app.route('/meta', methods=['POST'])
@login_required
def salvar_meta():
    ano = int(request.form.get('ano', date.today().year))
    mes = int(request.form.get('mes', date.today().month))
    me  = float(request.form.get('meta_entrada','0').replace(',','.') or 0)
    ml  = float(request.form.get('meta_lucro','0').replace(',','.') or 0)
    conn = get_db()
    conn.execute(
        "INSERT INTO metas(ano,mes,meta_entrada,meta_lucro) VALUES(?,?,?,?) "
        "ON CONFLICT(ano,mes) DO UPDATE SET meta_entrada=?,meta_lucro=?",
        (ano,mes,me,ml,me,ml)
    )
    conn.commit(); conn.close()
    return redirect(url_for('index', ano=ano, mes=mes))

# ── Contas a pagar/receber ───────────────────────────────────
@app.route('/contas')
@login_required
def contas():
    conn = get_db()
    pagar    = conn.execute("SELECT * FROM contas WHERE tipo='pagar'  ORDER BY pago, vencimento").fetchall()
    receber  = conn.execute("SELECT * FROM contas WHERE tipo='receber' ORDER BY pago, vencimento").fetchall()
    conn.close()
    hoje = date.today()
    return render_template('contas.html', pagar=pagar, receber=receber, hoje=hoje)

@app.route('/contas/adicionar', methods=['POST'])
@login_required
def conta_adicionar():
    tipo = request.form.get('tipo')
    descricao = request.form.get('descricao','').strip()
    valor = float(request.form.get('valor','0').replace(',','.') or 0)
    vencimento = request.form.get('vencimento')
    if descricao and valor > 0 and vencimento:
        conn = get_db()
        conn.execute("INSERT INTO contas(tipo,descricao,valor,vencimento) VALUES(?,?,?,?)",
                     (tipo,descricao,valor,vencimento))
        conn.commit(); conn.close()
    return redirect(url_for('contas'))

@app.route('/contas/pagar/<int:id>')
@login_required
def conta_pagar(id):
    conn = get_db()
    conn.execute("UPDATE contas SET pago=1 WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('contas'))

@app.route('/contas/excluir/<int:id>')
@login_required
def conta_excluir(id):
    conn = get_db()
    conn.execute("DELETE FROM contas WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('contas'))

# ── Importar Shopee Excel ────────────────────────────────────
@app.route('/importar-shopee', methods=['POST'])
@login_required
def importar_shopee():
    arquivo = request.files.get('arquivo')
    if not arquivo:
        return redirect(url_for('index'))
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(arquivo.read()))
        ws = wb.active
        conn = get_db()
        importados = 0
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0: continue  # pula cabeçalho
            try:
                data_val = row[0]
                valor_val = row[1] if len(row) > 1 else None
                if not data_val or not valor_val: continue
                if hasattr(data_val, 'strftime'):
                    data_str = data_val.strftime('%Y-%m-%d')
                else:
                    data_str = str(data_val)[:10]
                valor = float(str(valor_val).replace('R$','').replace(',','.').strip())
                if valor <= 0: continue
                conn.execute(
                    "INSERT INTO transacoes(tipo,descricao,valor,categoria,data) VALUES(?,?,?,?,?)",
                    ('entrada', 'Venda Shopee (importado)', valor, None, data_str)
                )
                importados += 1
            except: continue
        conn.commit(); conn.close()
    except Exception as e:
        pass
    return redirect(url_for('index'))

# ── Relatório anual ──────────────────────────────────────────
@app.route('/relatorio-anual')
@login_required
def relatorio_anual():
    ano = int(request.args.get('ano', date.today().year))
    meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    dados = []
    total_e = total_s = total_l = total_ads = 0
    for m in range(1, 13):
        r = resumo_mes(ano, m)
        dados.append({'mes': meses_nomes[m-1], 'num': m, **r})
        total_e   += r['entradas']
        total_s   += r['saidas']
        total_l   += r['lucro']
        total_ads += r['ads']
    rent_anual = (total_l / total_e * 100) if total_e > 0 else 0
    return render_template('relatorio.html',
        dados=dados, ano=ano,
        total_e=total_e, total_s=total_s,
        total_l=total_l, total_ads=total_ads,
        rent_anual=rent_anual,
        meses_nomes=meses_nomes,
    )

# ── API gráfico ──────────────────────────────────────────────
@app.route('/api/grafico')
@login_required
def api_grafico():
    hoje = date.today()
    dados = []
    for i in range(5, -1, -1):
        m = hoje.month - i; a = hoje.year
        while m <= 0: m += 12; a -= 1
        r = resumo_mes(a, m)
        meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        dados.append({
            'mes': meses_nomes[m-1],
            'entradas': round(r['entradas'],2),
            'saidas': round(r['saidas'],2),
            'lucro': round(r['lucro'],2),
            'ads': round(r['ads'],2),
        })
    return jsonify(dados)

# ── Exportar PDF ─────────────────────────────────────────────
@app.route('/exportar-pdf')
@login_required
def exportar_pdf():
    hoje = date.today()
    ano = int(request.args.get('ano', hoje.year))
    mes = int(request.args.get('mes', hoje.month))
    meses_nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    conn = get_db()
    transacoes = conn.execute(
        "SELECT * FROM transacoes WHERE data LIKE ? ORDER BY data DESC",
        (f"{ano}-{mes:02d}%",)
    ).fetchall()
    conn.close()
    res = resumo_mes(ano, mes)
    html = render_template('pdf_relatorio.html',
        transacoes=transacoes, resumo=res,
        ano=ano, mes=mes, meses_nomes=meses_nomes, hoje=hoje
    )
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

init_db()

if __name__ == '__main__':
    print("\n✅ Sistema iniciado! Acesse: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
