#!/usr/bin/env python3
"""
DISCORD USERNAME CHECKER v3.0 — 4L RUSH
Varre usernames de 4 caracteres (a-z + 0-9) no Discord
Usa PATCH em conta throwaway + proxies residenciais
"""

import aiohttp, asyncio, json, sys, os, time, random, base64, itertools, string
from colorama import Fore, init
init(autoreset=True)

PROXY_FILE = "/data/data/com.termux/files/home/storage/downloads/Residencial Proxys/proxies_auth.txt"
TOKEN_FILE = "throwaway_token.txt"
OUTPUT_FILE = "4l_disponiveis.txt"
MAX_CONCURRENT = 8
TIMEOUT = 15

stats = {"checked": 0, "available": 0, "taken": 0}

def c(tipo, txt):
    cores = {
        "avail": f"{Fore.GREEN}[✅]{Fore.RESET}",
        "taken": f"{Fore.RED}[❌]{Fore.RESET}",
        "rate": f"{Fore.YELLOW}[⏳]{Fore.RESET}",
        "info": f"{Fore.BLUE}[i]{Fore.RESET}",
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

def load_or_input_token():
    """Tenta carregar token salvo ou pede pro usuário"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            tk = f.read().strip()
            if tk:
                return tk
    tk = input("🔑 Token da conta throwaway: ").strip()
    if tk:
        with open(TOKEN_FILE, 'w') as f:
            f.write(tk)
    return tk

async def check(sem, username, proxies, token):
    """Verifica 1 username — tenta endpoint específico primeiro, fallback PATCH"""
    async with sem:
        proxy = random.choice(proxies)
        
        hdrs = {
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "X-Super-Properties": base64.b64encode(json.dumps({
                "os":"Windows","browser":"Chrome","device":"","system_locale":"en-US",
                "browser_version":"120.0.0.0","os_version":"10","release_channel":"stable",
                "client_build_number":random.randint(210000,235000)
            }).encode()).decode()
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            try:
                # ── MÉTODO 1: Endpoint de verificação direto ──
                async with s.post("https://discord.com/api/v10/unique-username/username",
                                headers=hdrs,
                                json={"username": username},
                                proxy=proxy,
                                timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    
                    if r.status == 200:
                        data = await r.json()
                        # Resposta: se não tiver erro, está disponível
                        stats["checked"] += 1
                        stats["available"] += 1
                        print(f"\n{c('avail', f'{username}')}")
                        with open(OUTPUT_FILE, 'a') as f:
                            f.write(f"{username}\n")
                        return True
                    
                    elif r.status == 400:
                        err = await r.json()
                        # Código 20035 = taken
                        if 'taken' in str(err).lower() or err.get('code') == 20035:
                            stats["checked"] += 1
                            stats["taken"] += 1
                            return False
                        # Outro erro 400 = pode ser inválido
                        return None
                    
                    elif r.status == 429:
                        await asyncio.sleep(5)
                        return None
                
                # Se chegou aqui, o endpoint pode não existir (Discord mudou)
                # Fallback pro método PATCH
                
            except Exception:
                pass  # Fallback pro PATCH
            
            # ── MÉTODO 2: PATCH (fallback) ──
            try:
                # Pega username atual pra restaurar depois
                async with s.get("https://discord.com/api/v10/users/@me",
                               headers=hdrs, proxy=proxy,
                               timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    if r.status != 200:
                        return None
                    me = await r.json()
                    original = me.get('username', '') or me.get('global_name', '')
                
                # Tenta PATCH pro username desejado
                async with s.patch("https://discord.com/api/v10/users/@me",
                                 headers=hdrs,
                                 json={"username": username},
                                 proxy=random.choice(proxies),
                                 timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r2:
                    
                    stats["checked"] += 1
                    
                    if r2.status == 200:
                        stats["available"] += 1
                        
                        # Restaura username original
                        await s.patch("https://discord.com/api/v10/users/@me",
                                    headers=hdrs,
                                    json={"username": original},
                                    proxy=random.choice(proxies),
                                    timeout=aiohttp.ClientTimeout(total=TIMEOUT))
                        
                        print(f"\n{c('avail', f'{username}')}")
                        with open(OUTPUT_FILE, 'a') as f:
                            f.write(f"{username}\n")
                        return True
                        
                    elif r2.status == 400:
                        err = await r2.json()
                        code = err.get('code', 0)
                        if code == 20035 or 'taken' in str(err).lower():
                            stats["taken"] += 1
                        return False
                    
                    elif r2.status == 429:
                        retry = int(r2.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry + 2)
                        return None
                    
                    elif r2.status == 401:
                        print(c("info", "Token inválido!"))
                        return None
                    
                    return False
                        
            except:
                return None

async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║    DISCORD 4L USERNAME RUSH v3.0         ║
║    a-z + 0-9 = 36^4 = 1.6M combos        ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    
    proxies = carregar_proxies()
    if not proxies:
        return print(c("info", "Sem proxies!"))
    
    token = load_or_input_token()
    if not token:
        return print(c("info", "Precisa de token! Usa create_throwaway.py primeiro"))
    
    print(f"\nEstratégia de varredura:")
    print(f"  1) Só letras (aaaa-zzzz) — 456.976 — MAIS VALIOSOS")
    print(f"  2) Letras + números (aaaa-9999) — 1.679.616")
    print(f"  3) Prioridade: letras > letra+numero > tudo")
    
    opt = input("\n➜ Opção (1-3) [3]: ").strip() or "3"
    
    chars = string.ascii_lowercase + string.digits
    all_combos = [''.join(p) for p in itertools.product(chars, repeat=4)]
    
    if opt == "1":
        all_combos = [c for c in all_combos if c.isalpha()]
    elif opt == "3":
        # Ordena: primeiro tudo letra, depois letra+numero
        alpha = [c for c in all_combos if c.isalpha()]
        mixed = [c for c in all_combos if not c.isalpha()]
        random.shuffle(alpha)
        random.shuffle(mixed)
        all_combos = alpha + mixed
    else:
        random.shuffle(all_combos)
    
    if opt != "3":
        random.shuffle(all_combos)
    
    total = len(all_combos)
    print(f"\n{c('info', f'{total} usernames pra verificar')}")
    print(f"{c('info', f'{len(proxies)} proxies')}")
    print("─" * 60)
    
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    start = time.time()
    checkpoint = start
    
    tasks = []
    for i, name in enumerate(all_combos):
        tasks.append(asyncio.create_task(check(sem, name, proxies, token)))
        
        if (i + 1) % 200 == 0:
            now = time.time()
            rate = 200 / (now - checkpoint) if (now - checkpoint) > 0 else 0
            elapsed = now - start
            pct = (i + 1) / total * 100
            eta = (total - i - 1) / rate if rate > 0 else 0
            
            print(f"\r{Fore.BLUE}[{i+1}/{total}] {pct:.1f}% | ✅{stats['available']} ❌{stats['taken']} | {rate:.0f}/s | ETA: {eta//60:.0f}m{eta%60:.0f}s{Fore.RESET}", end='')
            checkpoint = now
        
        await asyncio.sleep(0.02)
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    print("\n" + "═" * 60)
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║  SCAN CONCLUÍDO                         ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    print(f"  📊 Verificados: {stats['checked']}")
    print(f"  {Fore.GREEN}✅ Disponíveis: {stats['available']}{Fore.RESET}")
    print(f"  {Fore.RED}❌ Indisponíveis: {stats['taken']}{Fore.RESET}")
    print(f"  ⏱️ Tempo: {elapsed//60:.0f}m{elapsed%60:.0f}s")
    print(f"  📁 Salvos: {OUTPUT_FILE}")
    
    if stats['available'] > 0:
        print(f"\n{Fore.GREEN}🏆 AMOSTRA DOS DISPONÍVEIS:{Fore.RESET}")
        with open(OUTPUT_FILE) as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        for name in lines[:30]:
            print(f"    {Fore.GREEN}→ {name}{Fore.RESET}")
    
    print("═" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Parado{Fore.RESET}")
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL] {e}{Fore.RESET}")
        import traceback; traceback.print_exc()
