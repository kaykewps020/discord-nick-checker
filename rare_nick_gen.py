#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║     DISCORD RARE NICK CHECKER v7.0 — FIXED                      ║
║                                                                 ║
║  ✅ Resume de onde parou (progress.json)                       ║
║  ✅ Roda no GitHub Actions ou local                            ║
║  ✅ Endpoint unauthed + proxies residenciais                    ║
║  ✅ Webhook automático quando acha nick                        ║
║  ✅ Git commit periódico (não perde progresso)                 ║
║  ✅ Rate limit global (não caos entre threads)                 ║
║                                                                 ║
║  Uso:                                                           ║
║    python3 rare_nick_gen.py                    # modo interativo║
║    python3 rare_nick_gen.py --resume           # continua de onde║
║    python3 rare_nick_gen.py --pattern 3C       # roda só 3C     ║
║    python3 rare_nick_gen.py --pattern 3C --start 9274           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import aiohttp, asyncio, json, sys, os, time, random, string
import itertools, datetime, traceback, signal, argparse, subprocess
from colorama import Fore, init, Style
init(autoreset=True)

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "progress.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "found_nicks")

CONFIG = {
    "max_concurrent": 15,        # reduzido de 20 pra 15 — menos colisão
    "timeout": 12,
    "max_retries": 3,
    "batch_size": 75,            # batches menores = menos rate limit
    "save_every": 250,           # salva progresso a cada 250 checks
    "git_commit_every": 500,     # git commit a cada 500 checks
    "rate_limit_cooldown": 5,    # cooldown global quando 429 (segundos)
    "webhook": os.environ.get("DISCORD_WEBHOOK",
        "https://discord.com/api/webhooks/1526764679492538551/HdM8nuu-iV_tnW7BxbETQ-NI5G4auG7wHhkfeMuFoL5lqUPksEqfYwRiJf7HJuI3s3ng"),
}

ENDPOINT = "https://discord.com/api/v9/unique-username/username-suggestions-unauthed"

PROXY_PATHS = [
    os.path.expanduser("~/storage/downloads/Residencial Proxys/proxies_auth.txt"),
    os.path.expanduser("~/storage/downloads/Residencial Proxys/proxies_simple.txt"),
    os.path.join(SCRIPT_DIR, "proxies.txt"),
]

PADROES = {
    "1L": ("1 Letra (a-z)", 26),
    "1C": ("1 Char (a-z0-9)", 36),
    "2L": ("2 Letras (aa-zz)", 676),
    "2C": ("2 Chars (aa-99)", 1296),
    "3L": ("3 Letras (aaa-zzz)", 17576),
    "3C": ("3 Chars (aaa-999)", 46656),
    "4L": ("4 Letras (aaaa-zzzz)", 456976),
    "4C": ("4 Chars (aaaa-9999)", 1679616),
}

PADROES_ORDEM = ["1L", "1C", "2L", "2C", "3L", "3C", "4L", "4C"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# ═══════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════

def color(tipo, txt):
    cores = {
        "avail": f"{Fore.GREEN}{Style.BRIGHT}[✓]{Style.RESET_ALL}",
        "info":  f"{Fore.CYAN}[i]{Style.RESET_ALL}",
        "warn":  f"{Fore.MAGENTA}[!]{Style.RESET_ALL}",
        "fatal": f"{Fore.RED}{Style.BRIGHT}[☠]{Style.RESET_ALL}",
        "save":  f"{Fore.GREEN}[💾]{Style.RESET_ALL}",
    }
    return f"{cores.get(tipo, '[?]')} {txt}"

# ═══════════════════════════════════════════════════════════════════
# GIT HELPERS
# ═══════════════════════════════════════════════════════════════════

def git_commit_push(msg):
    """Commit e push progress.json + found_nicks pro repo"""
    try:
        os.chdir(SCRIPT_DIR)
        subprocess.run(["git", "config", "user.name", "nick-checker[bot]"],
                       capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "nick-checker[bot]@users.noreply.github.com"],
                       capture_output=True, timeout=10)
        subprocess.run(["git", "add", "progress.json", "found_nicks/"],
                       capture_output=True, timeout=10)
        result = subprocess.run(["git", "diff", "--staged", "--quiet"],
                                capture_output=True, timeout=10)
        if result.returncode != 0:  # tem mudanças
            subprocess.run(["git", "commit", "-m", msg], capture_output=True, timeout=10)
            subprocess.run(["git", "push"], capture_output=True, timeout=30)
            return True
    except Exception as e:
        print(f"  {color('warn', f'Git push falhou: {e}')}")
    return False

# ═══════════════════════════════════════════════════════════════════
# PROGRESS (checkpoint)
# ═══════════════════════════════════════════════════════════════════

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        "current_pattern": "1L",
        "pattern_index": 0,
        "checked_in_pattern": 0,
        "total_checked": 0,
        "total_found": [],
        "last_update": None,
    }

def save_progress(progress):
    progress["last_update"] = datetime.datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

# ═══════════════════════════════════════════════════════════════════
# PROXIES
# ═══════════════════════════════════════════════════════════════════

def load_proxies():
    proxies = []

    # 1. Arquivos locais
    for path in PROXY_PATHS:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '@' in line:
                        proxies.append(f"http://{line}" if not line.startswith('http') else line)
                    elif line.count(':') == 3:
                        parts = line.split(':')
                        proxies.append(f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}")
                    elif line.count(':') == 1:
                        proxies.append(f"http://{line}")
        except:
            pass

    # 2. Variável de ambiente (pro GitHub Actions)
    env_proxies = os.environ.get("PROXY_LIST", "")
    if env_proxies:
        for line in env_proxies.split("\n"):
            line = line.strip()
            if line and '@' in line:
                proxies.append(f"http://{line}" if not line.startswith('http') else line)

    # Deduplica
    seen = set()
    unique = []
    for p in proxies:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique

# ═══════════════════════════════════════════════════════════════════
# COMBOS
# ═══════════════════════════════════════════════════════════════════

def gerar_combinacoes(padrao):
    letras = string.ascii_lowercase
    todos = string.ascii_lowercase + string.digits
    mapa = {"1L": (letras,1), "1C": (todos,1), "2L": (letras,2), "2C": (todos,2),
            "3L": (letras,3), "3C": (todos,3), "4L": (letras,4), "4C": (todos,4)}
    chars, length = mapa[padrao]
    return [''.join(p) for p in itertools.product(chars, repeat=length)]

# ═══════════════════════════════════════════════════════════════════
# CHECKER — COM RATE LIMIT GLOBAL
# ═══════════════════════════════════════════════════════════════════

class Checker:
    def __init__(self, proxies):
        self.proxies = proxies
        self.session = None
        self.running = True
        self.lock = asyncio.Lock()
        self.proxy_idx = 0
        self.webhook_url = CONFIG["webhook"]
        self.stats = {"checked": 0, "available": 0, "taken": 0, "errors": 0, "rate_limited": 0}

        # RATE LIMIT GLOBAL — todas as threads param quando uma toma 429
        self.rate_limit_until = 0  # timestamp quando pode voltar
        self.rate_limit_lock = asyncio.Lock()

    def next_proxy(self):
        if not self.proxies:
            return None
        p = self.proxies[self.proxy_idx % len(self.proxies)]
        self.proxy_idx += 1
        return p

    def headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Referer": "https://discord.com/",
            "Origin": "https://discord.com",
        }

    async def wait_for_rate_limit(self):
        """Espera se tiver rate limit ativo"""
        async with self.rate_limit_lock:
            now = time.time()
            if now < self.rate_limit_until:
                wait_time = self.rate_limit_until - now
                print(f"  {color('warn', f'RATE LIMIT GLOBAL — esperando {wait_time:.0f}s')}")
                await asyncio.sleep(wait_time)

    async def trigger_rate_limit(self, seconds):
        """Ativa rate limit global"""
        async with self.rate_limit_lock:
            new_until = time.time() + seconds
            if new_until > self.rate_limit_until:
                self.rate_limit_until = new_until
                print(f"  {color('warn', f'429! Rate limit: {seconds:.1f}s cooldown global')}")

    async def webhook(self, username):
        if not self.webhook_url or not self.session:
            return
        payload = {
            "username": "Nick Checker",
            "content": f"🎉 **@{username}** disponível! (len:{len(username)})",
            "embeds": [{
                "title": "✅ Nick Disponível!",
                "description": f"**@{username}**",
                "color": 0x00FF00,
                "fields": [
                    {"name": "Username", "value": f"`{username}`", "inline": True},
                    {"name": "Tamanho", "value": f"{len(username)}", "inline": True},
                ],
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }],
        }
        try:
            async with self.session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)):
                pass
        except:
            pass

    async def check(self, username, sem):
        if not self.running:
            return None

        async with sem:
            for _ in range(CONFIG["max_retries"]):
                if not self.running:
                    return None

                # Espera se rate limit ativo
                await self.wait_for_rate_limit()

                proxy = self.next_proxy()
                url = f"{ENDPOINT}?global_name={username}"

                try:
                    async with self.session.get(
                        url, headers=self.headers(), proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=CONFIG["timeout"]),
                    ) as resp:
                        if resp.status == 200:
                            data = json.loads(await resp.text())
                            suggested = data.get('username')

                            if suggested == username:
                                async with self.lock:
                                    self.stats["checked"] += 1
                                    self.stats["available"] += 1
                                return username  # DISPONÍVEL
                            else:
                                async with self.lock:
                                    self.stats["checked"] += 1
                                    self.stats["taken"] += 1
                                return False  # INDISPONÍVEL

                        elif resp.status == 429:
                            async with self.lock:
                                self.stats["rate_limited"] += 1
                            try:
                                retry = (await resp.json()).get('retry_after', 5)
                            except:
                                retry = 5
                            # ATIVA COOLDOWN GLOBAL — todas as threads param
                            await self.trigger_rate_limit(retry + 1)
                            continue
                        elif resp.status == 403:
                            async with self.lock:
                                self.stats["errors"] += 1
                            await asyncio.sleep(2)
                            continue
                        else:
                            async with self.lock:
                                self.stats["errors"] += 1
                            continue

                except (aiohttp.ClientError, asyncio.TimeoutError):
                    async with self.lock:
                        self.stats["errors"] += 1
                    await asyncio.sleep(0.3)
                    continue
                except:
                    async with self.lock:
                        self.stats["errors"] += 1
                    continue

            return None

    async def run(self, combos, start_index, label, progress):
        """Roda scan com checkpoint — salva progresso + git commit periodicamente"""
        total = len(combos)
        combos_slice = combos[start_index:]

        ci = lambda m: color('info', m)
        print("\n" + ci(f"▶ {label} — começando de #{start_index:,}/{total:,}"))
        print(ci(f"  Restam: {len(combos_slice):,} | Proxies: {len(self.proxies)} | Threads: {CONFIG['max_concurrent']}"))
        print("─" * 75)

        connector = aiohttp.TCPConnector(ssl=False, limit=0, ttl_dns_cache=300, keepalive_timeout=30)
        start_time = time.time()
        batch_count = 0
        checked_since_save = 0
        checked_since_git = 0

        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            sem = asyncio.Semaphore(CONFIG["max_concurrent"])
            batch_size = CONFIG["batch_size"]
            processed = 0

            for i in range(0, len(combos_slice), batch_size):
                if not self.running:
                    break

                batch = combos_slice[i:i+batch_size]
                tasks = [asyncio.create_task(self.check(u, sem)) for u in batch]
                results = await asyncio.gather(*tasks)

                # Salva disponíveis
                for r in results:
                    if isinstance(r, str) and r:
                        os.makedirs(OUTPUT_DIR, exist_ok=True)
                        with open(os.path.join(OUTPUT_DIR, f"{label}.txt"), 'a') as f:
                            f.write(f"{r}\n")
                        asyncio.create_task(self.webhook(r))
                        print(f"  {Fore.GREEN}✅ {r} DISPONÍVEL!{Fore.RESET}")

                processed += len(batch)
                batch_count += 1
                global_idx = start_index + processed
                checked_since_save += len(batch)
                checked_since_git += len(batch)

                elapsed = time.time() - start_time
                # Calcula velocidade só com os checks efetivos (não contando cooldown)
                rate = self.stats["checked"] / elapsed if elapsed > 0 else 0
                remaining = len(combos_slice) - processed
                eta = remaining / rate if rate > 0 else 0
                pct = (global_idx) / total * 100

                eta_s = f"{eta//60:.0f}m{eta%60:.0f}s" if eta < 3600 else f"{eta//3600:.0f}h{(eta%3600)//60:.0f}m"

                sys.stdout.write(
                    f"\r{Fore.CYAN}[{global_idx:,}/{total:,}] {pct:.1f}% | "
                    f"{Fore.GREEN}✓{self.stats['available']} "
                    f"{Fore.RED}✗{self.stats['taken']} "
                    f"{Fore.YELLOW}⚠{self.stats['errors']} "
                    f"{Fore.MAGENTA}429:{self.stats['rate_limited']} "
                    f"{Fore.RESET}| {rate:.1f}/s | ETA: {eta_s}   "
                )
                sys.stdout.flush()

                # Salva progresso local a cada N checks
                if checked_since_save >= CONFIG["save_every"]:
                    progress["checked_in_pattern"] = global_idx
                    progress["total_checked"] = progress.get("total_checked_base", 0) + self.stats["checked"]
                    save_progress(progress)
                    checked_since_save = 0

                # Git commit + push a cada N checks
                if checked_since_git >= CONFIG["git_commit_every"]:
                    checked_since_git = 0
                    # salva primeiro
                    progress["checked_in_pattern"] = global_idx
                    progress["total_checked"] = progress.get("total_checked_base", 0) + self.stats["checked"]
                    save_progress(progress)
                    # git push em background
                    commit_msg = f"bot: {label} #{global_idx:,}/{total:,} ({self.stats['available']} found)"
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, git_commit_push, commit_msg)

            self.session = None

        # Salva progresso final do padrão
        progress["checked_in_pattern"] = total
        progress["total_checked"] = progress.get("total_checked_base", 0) + self.stats["checked"]
        save_progress(progress)

        # Git push final do padrão
        commit_msg = f"bot: {label} CONCLUÍDO ({self.stats['available']} found)"
        git_commit_push(commit_msg)

        elapsed = time.time() - start_time
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

        rate = self.stats["checked"] / elapsed if elapsed > 0 else 0
        print(f"\n{color('save', f'{label} CONCLUÍDO')}")
        print(f"  ✓ {self.stats['available']} disponíveis | ✗ {self.stats['taken']} indisponíveis")
        print(f"  ⏱ {elapsed//60:.0f}m{elapsed%60:.0f}s | {rate:.1f}/s")

        return self.stats["available"]

# ═══════════════════════════════════════════════════════════════════
# MODOS
# ═══════════════════════════════════════════════════════════════════

def run_interactive():
    """Modo interativo (menu)"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}PADRÕES:{Style.RESET_ALL}")
    for i, k in enumerate(PADROES_ORDEM, 1):
        print(f"  [{i}] {PADROES[k][0]:<20} {PADROES[k][1]:>8,}")
    print(f"  [T] Todos")
    print("─" * 50)

    choice = input("➜ Selecione: ").strip().upper()

    if choice == 'T':
        return PADROES_ORDEM
    try:
        idx = int(choice) - 1
        return [PADROES_ORDEM[idx]]
    except:
        return []

async def run_resume():
    """Continua de onde parou"""
    progress = load_progress()
    current = progress.get("current_pattern", "1L")
    start_idx = progress.get("checked_in_pattern", 0)

    print(f"\n{color('save', '📂 CHECKPOINT ENCONTRADO')}")
    print(f"  Padrão: {current} ({PADROES[current][0]})")
    print(f"  Posição: #{start_idx:,}/{PADROES[current][1]:,}")
    print(f"  Último update: {progress.get('last_update', '?')}")

    proxies = load_proxies()
    print(f"  Proxies carregadas: {len(proxies)}")
    checker = Checker(proxies)

    padroes = PADROES_ORDEM[PADROES_ORDEM.index(current):]

    for padrao in padroes:
        if not checker.running:
            break

        label, total = PADROES[padrao]
        start = start_idx if padrao == current else 0

        combos = gerar_combinacoes(padrao)
        await checker.run(combos, start, label, progress)

        # Marca padrão como completo
        progress["current_pattern"] = padrao
        progress["checked_in_pattern"] = 0
        progress["pattern_index"] = PADROES_ORDEM.index(padrao) + 1
        # Acumula total_checked_base pra não resetar entre padrões
        progress["total_checked_base"] = progress.get("total_checked", 0)
        save_progress(progress)

        # Git push entre padrões
        commit_msg = f"bot: {padrao} finalizado, indo pro próximo"
        git_commit_push(commit_msg)

        start_idx = 0

    print(f"\n{'═'*50}")
    print(f"{Fore.GREEN}✅ TUDO CONCLUÍDO!{Fore.RESET}")
    print(f"  Total checks: {checker.stats['checked']:,}")
    print(f"  Encontrados: {checker.stats['available']:,}")

async def run_pattern(pattern, start=0):
    """Roda um padrão específico"""
    if pattern not in PADROES:
        print(f"Padrão inválido: {pattern}")
        return

    proxies = load_proxies()
    print(f"  Proxies carregadas: {len(proxies)}")
    checker = Checker(proxies)

    progress = {
        "current_pattern": pattern,
        "checked_in_pattern": start,
        "total_checked": 0,
        "total_checked_base": 0,
        "last_update": None,
    }

    label, total = PADROES[pattern]
    combos = gerar_combinacoes(pattern)
    await checker.run(combos, start, label, progress)

    # Atualiza progress
    progress["current_pattern"] = pattern
    progress["checked_in_pattern"] = total
    save_progress(progress)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Discord Rare Nick Checker v7.0")
    parser.add_argument("--resume", action="store_true", help="Continua de onde parou")
    parser.add_argument("--pattern", type=str, help="Padrão específico (1L, 2C, 3C, etc)")
    parser.add_argument("--start", type=int, default=0, help="Índice inicial (com --pattern)")
    args = parser.parse_args()

    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"""{Fore.MAGENTA}{Style.BRIGHT}
╔══════════════════════════════════════════════════════════════════╗
║     ✦ DISCORD RARE NICK CHECKER v7.0 ✦                        ║
║     Endpoint: unauthed | Checkpoint + Git Push                 ║
║     Rate limit: GLOBAL cooldown (não individual)               ║
╚══════════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}""")

    def signal_handler(sig, frame):
        print(f"\n\n{color('warn', 'Salvando progresso...')}")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        if args.pattern:
            asyncio.run(run_pattern(args.pattern, args.start))
        elif args.resume:
            asyncio.run(run_resume())
        else:
            # Modo interativo
            padroes = run_interactive()
            if padroes:
                proxies = load_proxies()
                print(f"{color('info', f'{len(proxies)} proxies carregados')}")
                checker = Checker(proxies)

                progress = {
                    "current_pattern": padroes[0],
                    "checked_in_pattern": 0,
                    "total_checked": 0,
                    "total_checked_base": 0,
                    "last_update": None,
                }

                for p in padroes:
                    if not checker.running:
                        break
                    label, total = PADROES[p]
                    combos = gerar_combinacoes(p)
                    asyncio.run(checker.run(combos, 0, label, progress))
                    progress["current_pattern"] = p
                    progress["checked_in_pattern"] = 0
                    save_progress(progress)
    except KeyboardInterrupt:
        print(f"\n{color('warn', 'Interrompido. Progresso salvo.')}")
    except Exception as e:
        print(f"\n{color('fatal', str(e))}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
