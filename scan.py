#!/usr/bin/env python3
"""
Scanner v5 — Hybrid Direct+Proxy
- Tenta com proxy primeiro
- Se todos proxies banidos (>60s cooldown), cai pra direto
- Direto: retry 403, handle 429 curtos
- Pacing adaptativo baseado no resultado
- Salva progresso, leva webhook, nao trava o celular
"""

import aiohttp, asyncio, json, time, random, string, itertools, sys, os, signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS = os.path.join(SCRIPT_DIR, "progress.json")
FOUND_DIR = os.path.join(SCRIPT_DIR, "found_nicks")
PROXY_FILE = os.path.join(SCRIPT_DIR, "proxies.txt")
ENDPOINT = "https://discord.com/api/v9/unique-username/username-suggestions-unauthed"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1526764679492538551/HdM8nuu-iV_tnW7BxbETQ-NI5G4auG7wHhkfeMuFoL5lqUPksEqfYwRiJf7HJuI3s3ng")

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

PADROES = [
    ("1L", string.ascii_lowercase, 1),
    ("1C", string.ascii_lowercase + string.digits, 1),
    ("2L", string.ascii_lowercase, 2),
    ("2C", string.ascii_lowercase + string.digits, 2),
    ("3L", string.ascii_lowercase, 3),
    ("3C", string.ascii_lowercase + string.digits, 3),
    ("4L", string.ascii_lowercase, 4),
    ("4C", string.ascii_lowercase + string.digits, 4),
]

running = True

def handle_signal(sig, frame):
    global running
    print("\n\n⚡ Salvando progresso...")
    running = False

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def load_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "@" in line:
                    proxies.append(f"http://{line}" if not line.startswith("http") else line)
                elif line.count(":") == 1:
                    proxies.append(f"http://{line}")
    return proxies


def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {"pattern_idx": 0, "index": 0, "total": 0}


def save_progress(p):
    with open(PROGRESS, "w") as f:
        json.dump(p, f, indent=2)


class ProxyRotator:
    def __init__(self, proxies):
        self.proxies = proxies
        self.idx = 0
        self.cooldowns = {}

    def next(self):
        if not self.proxies:
            return None
        now = time.time()
        tried = 0
        while tried < len(self.proxies):
            p = self.proxies[self.idx % len(self.proxies)]
            idx = self.idx % len(self.proxies)
            self.idx += 1
            tried += 1
            if idx in self.cooldowns and now < self.cooldowns[idx]:
                continue
            return p
        return None

    def mark_limited(self, proxy, seconds):
        if not proxy:
            return
        now = time.time()
        for i, p in enumerate(self.proxies):
            if p == proxy:
                self.cooldowns[i] = now + seconds
                break

    def available_count(self):
        now = time.time()
        on_cooldown = sum(1 for i, t in self.cooldowns.items() if t > now)
        return len(self.proxies) - on_cooldown

    def next_cooldown_end(self):
        now = time.time()
        future = [t for t in self.cooldowns.values() if t > now]
        return min(future) - now if future else 0

    def all_banned_long(self, min_secs=60):
        """True se TODOS os proxies tao com cooldown >= min_secs"""
        now = time.time()
        if not self.cooldowns:
            return False
        return all(t - now >= min_secs for t in self.cooldowns.values())


async def check_one(session, name, rotator):
    """
    Check hibrido:
    1. Tenta com proxy se disponível
    2. Se todos banidos longos, tenta direto
    3. Handle 403 como retry
    """
    # ═══ COM PROXY ═══
    if not rotator.all_banned_long(60):
        proxy = rotator.next()
        if proxy:
            try:
                async with session.get(
                    f"{ENDPOINT}?global_name={name}",
                    headers={"User-Agent": random.choice(UAS), "Accept": "application/json",
                             "Referer": "https://discord.com/", "Origin": "https://discord.com"},
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    if r.status == 200:
                        data = json.loads(await r.text())
                        # Marca como usada com cooldown curto
                        now = time.time()
                        for i, p in enumerate(rotator.proxies):
                            if p == proxy:
                                if i not in rotator.cooldowns or rotator.cooldowns[i] < now:
                                    rotator.cooldowns[i] = now + 2
                                break
                        return ("ok", data.get("username") == name, "proxy")
                    elif r.status == 429:
                        try:
                            retry = (await r.json()).get("retry_after", 10)
                        except:
                            retry = 10
                        rotator.mark_limited(proxy, retry)
                        return ("429", retry, "proxy")
                    elif r.status == 403:
                        rotator.mark_limited(proxy, 5)
                        return ("403", 0, "proxy")
                    else:
                        return ("err", r.status, "proxy")
            except Exception:
                rotator.mark_limited(proxy, 5)
                return ("err", 0, "proxy")

    # ═══ DIRETO (sem proxy) ═══
    try:
        async with session.get(
            f"{ENDPOINT}?global_name={name}",
            headers={"User-Agent": random.choice(UAS), "Accept": "application/json",
                     "Referer": "https://discord.com/", "Origin": "https://discord.com"},
            timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                data = json.loads(await r.text())
                return ("ok", data.get("username") == name, "direct")
            elif r.status == 429:
                try:
                    retry = (await r.json()).get("retry_after", 10)
                except:
                    retry = 10
                return ("429", retry, "direct")
            elif r.status == 403:
                return ("403", 0, "direct")
            else:
                return ("err", r.status, "direct")
    except Exception:
        return ("err", 0, "direct")


async def send_webhook(session, name):
    try:
        payload = {
            "username": "Nick Checker",
            "content": f"🎉 **@{name}** disponível!",
            "embeds": [{"title": "✅ Nick!", "description": f"**@{name}**", "color": 0x00FF00}],
        }
        async with session.post(WEBHOOK, json=payload, timeout=aiohttp.ClientTimeout(total=10)):
            pass
    except:
        pass


async def main():
    progress = load_progress()
    pat_idx = progress.get("pattern_idx", 0)
    start_idx = progress.get("index", 0)
    total_all = progress.get("total", 0)
    proxies = load_proxies()
    rotator = ProxyRotator(proxies)

    print(f"\n\033[36m[i]\033[0m Proxies: {len(proxies)}")
    print(f"\033[36m[i]\033[0m Retomando: PADROES[{pat_idx}]#{start_idx} (total: {total_all})\n")

    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        # ═══ WARMUP ═══
        print("\033[36m[i]\033[0m Warmup...")
        while running:
            try:
                async with session.get(
                    f"{ENDPOINT}?global_name={random.choice(string.ascii_lowercase)}",
                    headers={"User-Agent": random.choice(UAS), "Accept": "application/json",
                             "Referer": "https://discord.com/", "Origin": "https://discord.com"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    if r.status == 200:
                        print("\033[36m[i]\033[0m Endpoint liberado!")
                        break
                    elif r.status == 429:
                        try:
                            wait = (await r.json()).get("retry_after", 30)
                        except:
                            wait = 30
                        wait = min(wait, 1800)  # cap warmup wait em 30 min
                        print(f"\033[33m[!]\033[0m 429! Aguardando {wait:.0f}s...")
                        waited = 0
                        while waited < wait and running:
                            chunk = min(15, wait - waited)
                            await asyncio.sleep(chunk)
                            waited += chunk
                            sys.stdout.write(f"\r  ⏳ {wait - waited:.0f}s restantes   ")
                            sys.stdout.flush()
                        print()
                        continue
                    else:
                        print(f"\033[33m[!]\033[0m HTTP {r.status}, tentando em 3s...")
                        await asyncio.sleep(3)
            except Exception as e:
                print(f"\033[33m[!]\033[0m Erro: {e}, tentando em 3s...")
                await asyncio.sleep(3)

        # ═══ SCAN — Concorrente com batches ═══
        CONCURRENCY = 8  # requests simultâneos
        sem = asyncio.Semaphore(CONCURRENCY)
        consecutive_429 = 0
        stats = {"proxy": 0, "direct": 0, "429": 0, "403": 0}

        async def do_check(idx, name):
            async with sem:
                if not running:
                    return None
                # Espera proxy livre
                for _ in range(30):
                    if rotator.next() is not None or rotator.all_banned_long(60):
                        break
                    await asyncio.sleep(0.5)
                return (idx, name, await check_one(session, name, rotator))

        for pi in range(pat_idx, len(PADROES)):
            if not running:
                break

            nome, chars, length = PADROES[pi]
            combos = ["".join(p) for p in itertools.product(chars, repeat=length)]
            si = start_idx if pi == pat_idx else 0
            total = len(combos)
            avail = 0
            taken = 0
            start_time = time.time()
            last_save = time.time()

            print(f"\n{'═'*60}")
            print(f"\033[36m[i]\033[0m ▶ {nome} — #{si:,}/{total:,} | {len(proxies)} proxies | {CONCURRENCY} threads")
            print(f"{'═'*60}\n")

            BATCH = 50
            for batch_start in range(si, total, BATCH):
                if not running:
                    break
                batch_end = min(batch_start + BATCH, total)

                # Verifica proxies livres — se todos banidos longos, espera
                free = rotator.available_count()
                if free == 0 and not rotator.all_banned_long(60):
                    # Todos em cooldown curto, espera pouco
                    await asyncio.sleep(2)
                elif rotator.all_banned_long(60):
                    # Todos banidos longos (30min) — espera cooldown
                    wait_secs = rotator.next_cooldown_end()
                    if wait_secs > 30:
                        print(f"\n  \033[33m⏳ Todos banidos — esperando {wait_secs:.0f}s (caiu pra direto)...\033[0m")
                        # Nao espera — o check_one ja cai pra direto

                tasks = [asyncio.create_task(do_check(i, combos[i])) for i in range(batch_start, batch_end)]
                results = await asyncio.gather(*tasks)

                batch_429 = 0
                for r in results:
                    if r is None:
                        continue
                    idx, name, result = r
                    if result is None:
                        continue

                    status, info, via = result
                    if status == "ok":
                        consecutive_429 = 0
                        stats[via] = stats.get(via, 0) + 1
                        if info:
                            avail += 1
                            print(f"\n  \033[32m✅ @{name} DISPONÍVEL! (via {via})\033[0m")
                            os.makedirs(FOUND_DIR, exist_ok=True)
                            with open(os.path.join(FOUND_DIR, f"{nome}.txt"), "a") as f:
                                f.write(f"{name}\n")
                            await send_webhook(session, name)
                        else:
                            taken += 1
                    elif status == "429":
                        consecutive_429 += 1
                        batch_429 += 1
                        stats["429"] = stats.get("429", 0) + 1
                    elif status == "403":
                        stats["403"] = stats.get("403", 0) + 1
                    else:
                        taken += 1

                done = batch_end - si
                elapsed = time.time() - start_time
                rate = done / elapsed if elapsed > 0 else 0
                remaining = total - batch_end
                eta = remaining / rate if rate > 0 else 0
                free = rotator.available_count()
                pct = done / (total - si) * 100
                proxy_banned = "🚫" if rotator.all_banned_long(60) else f"{free}/{len(proxies)}"

                sys.stdout.write(
                    f"\r  [{done:,}/{total-si:,}] {pct:.1f}% | "
                    f"\033[32m✓{avail}\033[0m \033[31m✗{taken}\033[0m | "
                    f"{rate:.1f}/s | px:{proxy_banned} | "
                    f"429:{stats['429']} 403:{stats['403']} | ETA: {eta/60:.0f}m   "
                )
                sys.stdout.flush()

                # Salva progresso
                if time.time() - last_save > 15:
                    save_progress({"pattern_idx": pi, "index": batch_end, "total": total_all + done})
                    last_save = time.time()

                # Delay entre batches — se muitos 429, espera mais
                if batch_429 > 20:
                    print(f"\n  \033[33m⏳ {batch_429}/50 429 — pausando 30s...\033[0m")
                    await asyncio.sleep(30)
                elif batch_429 > 5:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(0.5)

            # ═══ FIM DO PATTERN ═══
            done = total - si
            total_all += done
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0

            if not running:
                save_progress({"pattern_idx": pi, "index": batch_end if 'batch_end' in dir() else total, "total": total_all})
                print(f"\n\n  \033[33m⏸ Interrompido no {nome}\033[0m")
                print(f"     ✓{avail} disponíveis | ✗{taken} indisponíveis")
                print(f"     ⏱ {elapsed/60:.0f}m | {rate:.1f}/s | Stats: {stats}")
                break

            save_progress({"pattern_idx": pi + 1, "index": 0, "total": total_all})
            print(f"\n\n  \033[32m✅ {nome} CONCLUIDO!\033[0m")
            print(f"     ✓{avail} disponíveis | ✗{taken} indisponíveis")
            print(f"     ⏱ {elapsed/60:.0f}m | {rate:.1f}/s | Stats: {stats}")
            start_idx = 0

    print(f"\n{'═'*60}")
    print(f"\033[32m🎉 TUDO CONCLUÍDO! Total: {total_all:,}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())
