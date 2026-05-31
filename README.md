# 💼 Sistema de Gestão Financeira

Sistema web simples e responsivo para gerenciar entradas, saídas, despesas e lucro da sua empresa. Funciona no **computador e no celular** pelo navegador.

---

## 📦 Requisitos

- Python 3.8 ou superior
- Pip (gerenciador de pacotes do Python)

---

## ▶️ Como instalar e rodar

### Windows

```bash
# 1. Abra o Prompt de Comando (CMD) na pasta do projeto
# 2. Instale o Flask
pip install flask

# 3. Inicie o servidor
python app.py
```

### Mac / Linux

```bash
# 1. Abra o Terminal na pasta do projeto
chmod +x iniciar.sh
./iniciar.sh
```

### Após iniciar

Abra o navegador em: **http://localhost:5000**

Para acessar pelo **celular** (na mesma rede Wi-Fi):
1. Descubra o IP do seu computador (ex: `ipconfig` no Windows)
2. Acesse: `http://192.168.x.x:5000`

---

## 🗂️ Funcionalidades

- **Dashboard mensal**: Entradas, Saídas, Lucro e Rentabilidade
- **Categorias de despesa**: Marketing, Papelaria/Escritório, Impostos/Taxas, Outros
- **Barra de progresso** por categoria
- **Gráfico dos últimos 6 meses**
- **Navegação por mês/ano**
- **Banco de dados SQLite** — seus dados ficam salvos no arquivo `empresa.db`

---

## 📁 Estrutura dos arquivos

```
gestao_empresa/
├── app.py              ← Servidor Python (Flask)
├── empresa.db          ← Banco de dados (criado automaticamente)
├── iniciar.sh          ← Script de inicialização (Mac/Linux)
├── README.md           ← Este arquivo
└── templates/
    └── index.html      ← Interface web
```

---

## 💾 Backup dos dados

Os dados ficam em `empresa.db`. Para fazer backup, basta copiar esse arquivo.
