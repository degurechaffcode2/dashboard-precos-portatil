#!/bin/bash
# Dashboard de Preços Portátil — Iniciar
# Sobe um mini servidor HTTP local e abre no navegador
# Zero dependências além do Python 3 (já vem no Linux)

DIR="$(cd "$(dirname "$0")" && pwd)"

# Verifica se dados.sqlite existe
if [ ! -f "$DIR/dados.sqlite" ]; then
    echo "ERRO: dados.sqlite não encontrado em $DIR"
    echo "Execute primeiro: python3 export_to_sqlite.py"
    exit 1
fi

# Encontra porta livre
PORT=8765
while ss -tlnp | grep -q ":$PORT "; do
    PORT=$((PORT + 1))
done

echo "============================================"
echo "  Dashboard de Preços — SINAPI + SEINFRA-CE"
echo "============================================"
echo ""
echo "  Servidor local: http://localhost:$PORT"
echo "  Pressione Ctrl+C para parar"
echo ""

# Abre o navegador (detecta qual está disponível)
if command -v xdg-open &>/dev/null; then
    sleep 1 && xdg-open "http://localhost:$PORT" &
elif command -v gnome-open &>/dev/null; then
    sleep 1 && gnome-open "http://localhost:$PORT" &
fi

# Inicia servidor HTTP
cd "$DIR"
python3 -m http.server $PORT --bind 127.0.0.1 2>/dev/null
