#!/usr/bin/env python3
"""
DISCORD MASS DM v2.0 — MULTI-TOKEN + PROXY
Dispara mensagens em massa usando vários tokens simultâneos
"""

import aiohttp, asyncio, json, sys, os, time, random, base64
from colorama import Fore, Style, init
init(autoreset=True)

# ── CONFIG ──
PROXY_FILE = "/data/data/com.termux/files/home/storage/downloads/Residencial Proxys/proxies_auth.txt"
TOKEN_FILE = "tokens_validos.txt"
MAX_CONCURRENT = 20
TIMEOUT = 15

stats = {"sent": 0, "failed": 0, "token_idx": 0}

def c(tipo, txt):
    cores = {
        "sent": f"{Fore.GREEN}[✅]{Fore.RESET}",
        "failed": f"{Fore.RED}[❌]{Fore.RESET}",
        "info": f"{Fore.BLUE}[i]{Fore.RESET}",
        "rate": f"{Fore.YELLOW}[⏳]{Fore.RESET}",
    }
    return f"{cores.get(tipo, '[?]')} {txt}"

def carregar_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            for line in f:
                line = line.strip()
                if line and '@' in line:
                    proxies.append(f"http://{line}")
        print(c("info", f"{len(proxies)} proxies"))
    return proxies

def carregar_tokens():
    tokens = []
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            for line in f:
                tk = line.strip().split()[0].strip('"').strip("'")
                if tk and len(tk) > 50:
                    tokens.append(tk)
        print(c("info", f"{len(tokens)} tokens carregados"))
    return tokens

async def get_friends(session, token, proxy):
    """Pega lista de amigos / DM channels do token"""
    hdrs = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with session.get("https://discord.com/api/v10/users/@me/relationships",
                             headers=hdrs, proxy=proxy,
                             timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
            if r.status == 200:
                data = await r.json()
                friends = []
                for rel in data:
                    if rel.get('type') == 1:  # friend
                        user = rel.get('user', {})
                        friends.append({
                            'id': user.get('id'),
                            'username': f"{user.get('username','?')}#{user.get('discriminator','0')}"
                        })
                return friends
    except:
        pass
    return []

async def send_dm(sem, token, user_id, username, message, proxy, proxies):
    async with sem:
        proxy_atual = random.choice(proxies)
        hdrs = {
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json"
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            try:
                # Cria/abre DM channel
                async with s.post("https://discord.com/api/v10/users/@me/channels",
                                headers=hdrs,
                                json={"recipient_id": user_id},
                                proxy=proxy_atual,
                                timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    if r.status != 200:
                        return False
                    ch = await r.json()
                    ch_id = ch.get('id')
                    if not ch_id:
                        return False
                
                # Envia mensagem
                async with s.post(f"https://discord.com/api/v10/channels/{ch_id}/messages",
                                headers=hdrs,
                                json={"content": message},
                                proxy=proxy_atual,
                                timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r2:
                    if r2.status == 200:
                        stats["sent"] += 1
                        print(c("sent", f"[{stats['sent']}] DM pra {username}"))
                        return True
                    elif r2.status == 429:
                        retry = int(r2.headers.get('Retry-After', 3))
                        print(c("rate", f"Rate! Esperando {retry}s..."))
                        await asyncio.sleep(retry + 1)
                        return False
                    else:
                        return False
            except:
                return False

async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║     DISCORD MASS DM v2.0                 ║
║     MULTI-TOKEN + PROXY RESIDENCIAL       ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    
    proxies = carregar_proxies()
    tokens = carregar_tokens()
    
    if not tokens:
        print(c("failed", "Nenhum token válido!"))
        return
    
    # Escolhe modo
    print("\nModo de envio:")
    print("  1) DM para amigos de cada token")
    print("  2) DM para user IDs específicos (arquivo)")
    print("  3) DM para membros de um servidor (precisa estar no server)")
    
    modo = input("\n➜ Modo (1-3) [1]: ").strip() or "1"
    
    message = input("📝 Mensagem a enviar: ").strip()
    if not message:
        print(c("failed", "Mensagem vazia!"))
        return
    
    # Delay entre DMs
    delay = float(input("⏱️ Delay entre DMs (segundos) [1.5]: ").strip() or "1.5")
    
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    if modo == "1":
        # Pega amigos de cada token
        all_targets = []
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            for i, token in enumerate(tokens):
                proxy = random.choice(proxies)
                friends = await get_friends(s, token, proxy)
                print(c("info", f"Token {i+1}: {len(friends)} amigos"))
                for f in friends:
                    all_targets.append((token, f['id'], f['username']))
                await asyncio.sleep(0.5)
        
        print(c("info", f"Total alvos: {len(all_targets)}"))
        
        tasks = []
        for token, uid, uname in all_targets:
            task = asyncio.create_task(send_dm(sem, token, uid, uname, message, random.choice(proxies), proxies))
            tasks.append(task)
            await asyncio.sleep(delay)
        
        await asyncio.gather(*tasks)
        
    elif modo == "2":
        # Lê user IDs de arquivo
        id_file = input("📁 Arquivo com user IDs [targets.txt]: ").strip() or "targets.txt"
        targets = []
        if os.path.exists(id_file):
            with open(id_file) as f:
                for line in f:
                    uid = line.strip()
                    if uid:
                        targets.append(uid)
        else:
            print(c("failed", f"Arquivo {id_file} não encontrado!"))
            return
        
        print(c("info", f"Enviando pra {len(targets)} alvos com {len(tokens)} tokens..."))
        
        tasks = []
        for i, uid in enumerate(targets):
            token = tokens[i % len(tokens)]
            task = asyncio.create_task(send_dm(sem, token, uid, uid, message, random.choice(proxies), proxies))
            tasks.append(task)
            await asyncio.sleep(delay)
        
        await asyncio.gather(*tasks)
        
    elif modo == "3":
        guild_id = input("🏰 ID do servidor: ").strip()
        if not guild_id:
            return
        
        # Pega membros
        token = tokens[0]
        proxy = random.choice(proxies)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            hdrs = {"Authorization": token, "User-Agent": "Mozilla/5.0"}
            members = []
            after = None
            while True:
                url = f"https://discord.com/api/v10/guilds/{guild_id}/members?limit=1000"
                if after:
                    url += f"&after={after}"
                try:
                    async with s.get(url, headers=hdrs, proxy=proxy,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status == 200:
                            batch = await r.json()
                            if not batch:
                                break
                            members.extend(batch)
                            after = batch[-1]['user']['id']
                            await asyncio.sleep(0.5)
                        else:
                            break
                except:
                    break
            
            print(c("info", f"{len(members)} membros encontrados"))
            
            tasks = []
            for i, m in enumerate(members):
                uid = m.get('user', {}).get('id')
                uname = f"{m.get('user',{}).get('username','?')}#{m.get('user',{}).get('discriminator','0')}"
                if uid:
                    tk = tokens[i % len(tokens)]
                    task = asyncio.create_task(send_dm(sem, tk, uid, uname, message, random.choice(proxies), proxies))
                    tasks.append(task)
                    await asyncio.sleep(delay)
            
            await asyncio.gather(*tasks)
    
    # Resumo
    print("\n" + "═" * 60)
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║  ENVIO FINALIZADO                       ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    print(f"  {Fore.GREEN}✅ Enviadas:  {stats['sent']}{Fore.RESET}")
    print(f"  {Fore.RED}❌ Falhas:    {stats['failed']}{Fore.RESET}")
    print("═" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrompido{Fore.RESET}")
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL] {e}{Fore.RESET}")
        import traceback
        traceback.print_exc()
