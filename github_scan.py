#!/usr/bin/env python3
"""
GitHub Actions Scanner — Chunk Paralelo
Cada job do GitHub roda um chunk diferente com IP diferente.
Sem proxy necessário — cada runner tem IP unico.
Envia achados direto pro webhook.

Uso: python3 github_scan.py --pattern 3C --chunk 0 --total-chunks 50
"""

import aiohttp, asyncio, json, time, random, string, itertools, sys, os, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FOUND_DIR = os.path.join(SCRIPT_DIR, "found_nicks")
ENDPOINT = "https://discord.com/api/v9/unique-username/username-suggestions-unauthed"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

PADROES = {
    "1L": ("1L", string.ascii_lowercase, 1),
    "1C": ("1C", string.ascii_lowercase + string.digits, 1),
    "2L": ("2L", string.ascii_lowercase, 2),
    "2C": ("2C", string.ascii_lowercase + string.digits, 2),
    "3L": ("3L", string.ascii_lowercase, 3),
    "3C": ("3C", string.ascii_lowercase + string.digits, 3),
    "4L": ("4L", string.ascii_lowercase, 4),
    "4C": ("4C", string.ascii_lowercase + string.digits, 4),
}


def get_chunk(combos, chunk_id, total_chunks):
    """Divide combos em chunks"""
    chunk_size = len(combos) // total_chunks
    remainder = len(combos) % total_chunks
    start = chunk_id * chunk_size + min(chunk_id, remainder)
    end = start + chunk_size + (1 if chunk_id < remainder else 0)
    return combos[start:end]


async def send_webhook(session, name, pattern):
    if not WEBHOOK:
        return
    try:
        payload = {
            "username": "Nick Checker",
            "content": f"🎉 **@{name}** disponível! ({pattern})",
            "embeds": [{
                "title": "✅ Nick!",
                "description": f"**@{name}**\nPattern: {pattern}",
                "color": 0x00FF00,
            }],
        }
        async with session.post(WEBHOOK, json=payload, timeout=aiohttp.ClientTimeout(total=10)):
            pass
    except:
        pass


async def check_one(session, name):
    """Check sem proxy"""
    try:
        async with session.get(
            f"{ENDPOINT}?global_name={name}",
            headers={
                "User-Agent": random.choice(UAS),
                "Accept": "application/json",
                "Referer": "https://discord.com/",
                "Origin": "https://discord.com",
            },
            timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                data = json.loads(await r.text())
                return ("ok", data.get("username") == name)
            elif r.status == 429:
                try:
                    retry = (await r.json()).get("retry_after", 30)
                except:
                    retry = 30
                return ("429", retry)
            return ("err", r.status)
    except Exception:
        return ("err", 0)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", required=True, help="Pattern: 3L, 3C, 4L, 4C")
    parser.add_argument("--chunk", type=int, required=True, help="Chunk ID (0-based)")
    parser.add_argument("--total-chunks", type=int, required=True, help="Total chunks")
    args = parser.parse_args()

    nome, chars, length = PADROES[args.pattern]
    all_combos = ["".join(p) for p in itertools.product(chars, repeat=length)]
    combos = get_chunk(all_combos, args.chunk, args.total_chunks)

    chunk_info = f"chunk {args.chunk}/{args.total_chunks} ({len(combos)} combos)"
    print(f"[{args.pattern}] {chunk_info} — {len(all_combos)} total")

    avail = 0
    taken = 0
    start_time = time.time()
    consecutive_429 = 0
    delay = 0.3

    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Warmup — tenta direto
        for _ in range(10):
            result = await check_one(session, random.choice(string.ascii_lowercase))
            if result[0] == "ok":
                print("Endpoint liberado!")
                break
            elif result[0] == "429":
                wait = min(result[1], 60)
                print(f"429 warmup — aguardando {wait:.0f}s...")
                await asyncio.sleep(wait)
            else:
                await asyncio.sleep(3)
        else:
            print("Warmup falhou, tentando scan mesmo assim...")

        for idx, name in enumerate(combos):
            result = await check_one(session, name)

            if result[0] == "ok":
                consecutive_429 = 0
                delay = max(0.2, delay * 0.9)
                if result[1]:
                    avail += 1
                    print(f"  ✅ @{name} DISPONÍVEL!")
                    os.makedirs(FOUND_DIR, exist_ok=True)
                    with open(os.path.join(FOUND_DIR, f"{nome}.txt"), "a") as f:
                        f.write(f"{name}\n")
                    await send_webhook(session, name, nome)
                else:
                    taken += 1
            elif result[0] == "429":
                consecutive_429 += 1
                retry = result[1]
                if consecutive_429 >= 3:
                    wait = min(retry, 60)
                    print(f"  ⏳ {consecutive_429}x 429 — pausando {wait:.0f}s...")
                    await asyncio.sleep(wait)
                    consecutive_429 = 0
                else:
                    wait = min(retry, 15)
                    await asyncio.sleep(wait)
                delay = min(delay * 1.5, 3.0)
            else:
                consecutive_429 = 0
                taken += 1
                delay = max(0.2, delay * 0.95)

            # Status a cada 50
            if (idx + 1) % 50 == 0:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed if elapsed > 0 else 0
                print(f"  [{idx+1}/{len(combos)}] ✓{avail} ✗{taken} | {rate:.1f}/s | d:{delay:.1f}s")

            await asyncio.sleep(delay)

    elapsed = time.time() - start_time
    rate = len(combos) / elapsed if elapsed > 0 else 0

    # Resultado final
    print(f"\n{'='*50}")
    print(f"[{args.pattern}] {chunk_info} CONCLUIDO!")
    print(f"  ✓{avail} disponíveis | ✗{taken} indisponíveis | {len(combos)} total")
    print(f"  ⏱ {elapsed/60:.1f}m | {rate:.1f}/s")

    # Salva resultado do chunk
    result = {
        "pattern": args.pattern,
        "chunk": args.chunk,
        "total_chunks": args.total_chunks,
        "available": avail,
        "taken": taken,
        "total": len(combos),
        "elapsed_s": round(elapsed, 1),
        "rate": round(rate, 2),
    }
    os.makedirs(FOUND_DIR, exist_ok=True)
    with open(os.path.join(FOUND_DIR, f"{args.pattern}_chunk{args.chunk}.json"), "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    import string
    asyncio.run(main())
