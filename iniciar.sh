#!/bin/bash
# ============================================
#  GESTÃO FINANCEIRA - Script de Inicialização
# ============================================

echo ""
echo "🚀 Preparando o sistema de gestão financeira..."
echo ""

# Instalar dependências
pip install flask --quiet

echo "✅ Dependências instaladas!"
echo ""
echo "▶  Iniciando o servidor..."
echo ""
echo "📱 Acesse pelo celular ou computador em:"
echo "   → http://localhost:5000"
echo ""
echo "   (Para acessar pelo celular na mesma rede Wi-Fi,"
echo "    use o IP do seu computador: http://SEU_IP:5000)"
echo ""
echo "   Pressione CTRL+C para encerrar."
echo ""

python app.py
