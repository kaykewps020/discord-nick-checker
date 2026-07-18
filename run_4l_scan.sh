#!/data/data/com.termux/files/usr/bin/bash
# DISCORD 4L USERNAME RUSH — AUTO
# 1. Cria conta throwaway
# 2. Já testa os 4L

cd /data/data/com.termux/files/home/discord_tools

echo "╔══════════════════════════════════════════╗"
echo "║  4L USERNAME RUSH — AUTO                 ║"
echo "╚══════════════════════════════════════════╝"

# Verifica se já tem token
if [ ! -f throwaway_token.txt ] || [ ! -s throwaway_token.txt ]; then
    echo "[i] Criando conta throwaway..."
    python3 create_throwaway.py
    
    if [ ! -f throwaway_token.txt ] || [ ! -s throwaway_token.txt ]; then
        echo "[!] Falha ao criar conta. Cria uma manual e cola o token em throwaway_token.txt"
        exit 1
    fi
fi

echo "[i] Token encontrado! Iniciando scan 4L..."
python3 username_checker.py
