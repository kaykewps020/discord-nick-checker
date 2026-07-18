#!/usr/bin/env python3
"""
DISCORD THROWAWAY ACCOUNT CREATOR
Cria conta descartável + pega token pra usar no username checker
"""

import aiohttp, asyncio, json, sys, os, random, string, time, re
from colorama import Fore, init
init(autoreset=True)

PROXY_FILE = "/data/data/com.termux/files/home/storage/downloads/Residencial Proxys/proxies_auth.txt"

def carregar_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            for line in f:
                line = line.strip()
                if line and '@' in line:
                    proxies.append(f"http://{line}")
    return proxies

def gen_email():
    """Gera email temporário"""
    domains = ["@gmail.com", "@outlook.com", "@yahoo.com", "@hotmail.com",
               "@protonmail.com", "@mail.com", "@yopmail.com"]
    nome = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"discord_{nome}{random.choice(domains)}"

def gen_password():
    """Gera senha forte"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=16))

def gen_username():
    """Gera username aleatório pro registro"""
    return ''.join(random.choices(string.ascii_lowercase, k=8))

async def create_account():
    """Cria conta Discord e retorna o token"""
    proxies = carregar_proxies()
    if not proxies:
        print(f"{Fore.RED}[!] Sem proxies!{Fore.RESET}")
        return None
    
    email = gen_email()
    password = gen_password()
    username = gen_username()
    
    print(f"{Fore.CYAN}[i] Criando conta...{Fore.RESET}")
    print(f"    Email: {email}")
    print(f"    User:  {username}")
    print(f"    Pass:  {password}")
    
    proxy = random.choice(proxies)
    
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/register",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    payload = {
        "email": email,
        "password": password,
        "username": username,
        "consent": True,
        "date_of_birth": "2000-01-01",
        "gift_code_sku_id": None,
        "captcha_key": None,
        "promotional_email_opt_in": False
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as s:
        try:
            async with s.post("https://discord.com/api/v10/auth/register",
                           headers=hdrs,
                           json=payload,
                           proxy=proxy,
                           timeout=aiohttp.ClientTimeout(total=30)) as r:
                
                res = await r.json()
                
                if r.status == 200 or r.status == 201:
                    token = res.get('token', '')
                    user = res.get('user', {})
                    
                    print(f"{Fore.GREEN}[✅] Conta criada!{Fore.RESET}")
                    print(f"    ID: {user.get('id', '?')}")
                    print(f"    Token: {token[:40]}...")
                    
                    # Salva dados
                    with open("throwaway_account.txt", 'w') as f:
                        f.write(f"Email: {email}\n")
                        f.write(f"Password: {password}\n")
                        f.write(f"Username: {username}\n")
                        f.write(f"ID: {user.get('id', '?')}\n")
                        f.write(f"Token: {token}\n")
                    
                    # Salva token pro username checker
                    with open("throwaway_token.txt", 'w') as f:
                        f.write(f"{token}\n")
                    
                    return token, email, password
                    
                elif r.status == 400:
                    msg = res.get('message', '')
                    code = res.get('code', 0)
                    
                    if code == 20032 or 'captcha' in msg:
                        print(f"{Fore.YELLOW}[!] Captcha necessário (IP bloqueado){Fore.RESET}")
                        print(f"    Tentando com outro proxy...")
                        return await create_account()  # Retry
                    elif 'email' in msg.lower() or 'already' in msg.lower():
                        print(f"{Fore.YELLOW}[!] Retry com novo email...{Fore.RESET}")
                        return await create_account()
                    else:
                        print(f"{Fore.RED}[!] Erro 400: {msg[:100]}{Fore.RESET}")
                        return None
                        
                elif r.status == 429:
                    retry = int(r.headers.get('Retry-After', 5))
                    print(f"{Fore.YELLOW}[!] Rate: esperando {retry}s{Fore.RESET}")
                    await asyncio.sleep(retry + 2)
                    return await create_account()
                    
                else:
                    print(f"{Fore.RED}[!] HTTP {r.status}: {str(res)[:200]}{Fore.RESET}")
                    return None
                    
        except Exception as e:
            print(f"{Fore.RED}[!] Erro: {e}{Fore.RESET}")
            return None

async def main():
    print(f"""{Fore.CYAN}
╔══════════════════════════════════════════╗
║  DISCORD THROWAWAY ACCOUNT CREATOR       ║
║  Cria conta + token pra username scan    ║
╚══════════════════════════════════════════╝{Fore.RESET}
""")
    
    print(f"{Fore.YELLOW}[!] Nota: Discord pode pedir captcha se detectar IP suspeito{Fore.RESET}")
    print(f"{Fore.YELLOW}[!] Os proxies residenciais ajudam a bypassar{Fore.RESET}")
    
    result = await create_account()
    
    if result:
        token, email, password = result
        print(f"\n{Fore.GREEN}╔══ PRONTO ══╗{Fore.RESET}")
        print(f"  Token: {token}")
        print(f"  Email: {email}")
        print(f"  Pass:  {password}")
        print(f"{Fore.GREEN}╚════════════╝{Fore.RESET}")
        print(f"\nAgora executa o username checker:")
        print(f"  python3 username_checker.py")
        print(f"  → Cola esse token quando pedir")
    else:
        print(f"\n{Fore.RED}[!] Não foi possível criar conta{Fore.RESET}")
        print(f"    Tenta criar uma manualmente no navegador,")
        print(f"    pega o token e cola no username_checker.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Cancelado{Fore.RESET}")
