#!/usr/bin/env python3
"""
Discord Rare Nick Checker Bot v2
- Shows every nick being checked in real-time
- Creates channels per pattern
- Posts available nicks to channel + webhook
- Auto-shutdown when done
- Resume from checkpoint
"""

import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import os
import re
import sys
import time
import random

# ─── CONFIG ───────────────────────────────────────────────────────
BLOCOS_FILE = os.environ.get("BLOCOS_FILE", "blocos.txt")
PROGRESS_FILE = os.environ.get("PROGRESS_FILE", "bot_progress.json")
GUILD_ID = int(os.environ.get("GUILD_ID", "1526764581727502346"))  # V&T server
WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK",
    "https://discord.com/api/webhooks/1526764679492538551/HdM8nuu-iV_tnW7BxbETQ-NI5G4auG7wHhkfeMuFoL5lqUPksEqfYwRiJf7HJuI3s3ng",
)
ENDPOINT = "https://discord.com/api/v9/unique-username/username-suggestions-unauthed"
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
]

MAX_CONCURRENT = 1
CHECK_DELAY = 1.8
COOLDOWN_THRESHOLD = 3
COOLDOWN_WAIT = 45

# ─── CHANNEL MAP ──────────────────────────────────────────────────
PATTERN_MAP = {
    "1l3n": ("1l-3n",  "1 Letra + 3 Números"),
    "2l2n": ("2l-2n",  "2 Letras + 2 Números (Alt LNLN)"),
    "3l1n": ("3l-1n",  "3 Letras + 1 Número"),
    "4l":   ("4l",     "4 Letras"),
    "1n3l": ("1n-3l",  "1 Número + 3 Letras"),
    "2n2l": ("2n-2l",  "2 Números + 2 Letras (Alt NLNL)"),
    "3n1l": ("3n-1l",  "3 Números + 1 Letra"),
    "4n":   ("4n",     "4 Números"),
    "other": ("outros", "Outros padrões"),
}


def classify_nick(nick: str) -> str:
    nick = nick.lower().strip()
    if len(nick) != 4:
        return "other"
    letters = sum(1 for c in nick if c.isalpha())
    numbers = sum(1 for c in nick if c.isdigit())
    if letters + numbers != 4:
        return "other"

    if letters == 4: return "4l"
    if numbers == 4: return "4n"
    if letters == 3:
        return "1n3l" if nick[0].isdigit() else "3l1n"
    if numbers == 3:
        return "1l3n" if nick[0].isalpha() else "3n1l"
    if letters == 2 and numbers == 2:
        return "2l2n" if nick[0].isalpha() else "2n2l"
    return "other"


def parse_blocos(filepath: str) -> dict:
    with open(filepath) as f:
        raw = f.read().lower()
    tokens = re.findall(r'[a-z0-9]{4}', raw)
    valid = [t for t in tokens if sum(1 for c in t if c.isalpha()) >= 1
             and sum(1 for c in t if c.isdigit()) >= 1
             and len(t) == 4]
    seen = set()
    unique = []
    for v in valid:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    result = {}
    for nick in unique:
        pat = classify_nick(nick)
        result.setdefault(pat, []).append(nick)
    return result


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


async def check_nick(session: aiohttp.ClientSession, nick: str, sem: asyncio.Semaphore):
    async with sem:
        try:
            headers = {
                "User-Agent": random.choice(UAS),
                "Accept": "application/json",
                "Referer": "https://discord.com/",
                "Origin": "https://discord.com",
            }
            async with session.get(
                f"{ENDPOINT}?global_name={nick}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    available = data.get("username", "").lower() == nick.lower()
                    return {"nick": nick, "available": available, "status": "ok"}
                elif r.status == 429:
                    try:
                        retry = (await r.json()).get("retry_after", 30)
                    except Exception:
                        retry = 30
                    return {"nick": nick, "available": False, "status": "429", "retry_after": retry}
                else:
                    return {"nick": nick, "available": False, "status": "err", "code": r.status}
        except Exception as e:
            return {"nick": nick, "available": False, "status": "err", "error": str(e)}


async def send_webhook(session: aiohttp.ClientSession, text: str):
    try:
        async with session.post(
            WEBHOOK_URL,
            json={"content": text},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            pass
    except Exception:
        pass


async def check_pattern(
    pattern_name: str,
    nicks: list,
    channel: discord.TextChannel,
    progress: dict,
    session: aiohttp.ClientSession,
):
    key = f"checked_{pattern_name}"
    checked_set = set(progress.get(key, []))
    remaining = [n for n in nicks if n not in checked_set]

    if not remaining:
        print(f"  [{pattern_name}] Todos já checados, pulando...")
        return

    total = len(nicks)
    done = len(checked_set)
    found = 0
    taken = 0
    errors = 0
    rate_limit_count = 0
    start_time = time.time()

    print(f"\n{'='*55}")
    print(f"  [{pattern_name.upper()}] {len(remaining)} restantes / {total} total")
    print(f"{'='*55}")

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    batch_size = 10

    for batch_start in range(0, len(remaining), batch_size):
        batch = remaining[batch_start : batch_start + batch_size]
        tasks = [check_nick(session, nick, sem) for nick in batch]
        results = await asyncio.gather(*tasks)

        for r in results:
            nick = r["nick"]
            checked_set.add(nick)
            done += 1

            if r["status"] == "ok":
                rate_limit_count = 0
                if r["available"]:
                    found += 1
                    print(f"  ✅ @{nick} DISPONIVEL!")
                    await channel.send(f"✅ **@{nick}** disponível!")
                    await send_webhook(session, f"✅ **@{nick}** disponível! (`{pattern_name}`)")
                else:
                    taken += 1
                    print(f"  ✗ @{nick}")

            elif r["status"] == "429":
                rate_limit_count += 1
                retry = r.get("retry_after", 30)
                wait = max(retry, COOLDOWN_WAIT) if rate_limit_count >= COOLDOWN_THRESHOLD else min(retry, 10)
                if rate_limit_count >= COOLDOWN_THRESHOLD:
                    print(f"  ⏳ COOLDOWN {wait:.0f}s (retry_after={retry:.0f}s)")
                    await send_webhook(session, f"⏳ `{pattern_name}` cooldown {wait:.0f}s")
                await asyncio.sleep(wait)
            else:
                errors += 1
                print(f"  ⚠ @{nick} ERRO: {r.get('code', r.get('error', '?'))}")

        # Progress every batch
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 0
        pct = done / total * 100
        eta_s = ((total - done) / rate) if rate > 0 else 0
        eta_m = eta_s / 60

        if (batch_start // batch_size) % 10 == 0 or batch_start + batch_size >= len(remaining):
            print(f"\n  📊 [{done}/{total}] {pct:.1f}% | ✅{found} ✗{taken} ⚠{errors} | {rate:.2f}/s | ETA: {eta_m:.0f}min\n")

        progress[key] = list(checked_set)
        save_progress(progress)
        await asyncio.sleep(CHECK_DELAY)

    # Final
    progress[key] = list(checked_set)
    save_progress(progress)
    elapsed = time.time() - start_time

    print(f"\n{'─'*55}")
    print(f"  [{pattern_name.upper()}] ✅ COMPLETO: {found} DISP / {taken} TAKEN / {errors} ERR / {elapsed:.0f}s")
    print(f"{'─'*55}")

    await channel.send(f"📊 Scan `{pattern_name}` completo! **{found}** disponíveis / {total} checados")
    await send_webhook(session, f"📊 `{pattern_name}` completo: **{found}** disponíveis / {total}")


async def main():
    print("=" * 55)
    print("  🔍 Discord Rare Nick Checker Bot v2")
    print("=" * 55)

    if not os.path.exists(BLOCOS_FILE):
        print(f"❌ {BLOCOS_FILE} não encontrado!")
        sys.exit(1)

    nicks_by_pattern = parse_blocos(BLOCOS_FILE)
    total_nicks = sum(len(v) for v in nicks_by_pattern.values())
    print(f"\n📄 {total_nicks} nicks únicos em {len(nicks_by_pattern)} padrões:")
    for pat, nicks in sorted(nicks_by_pattern.items()):
        name, desc = PATTERN_MAP.get(pat, (pat, pat))
        print(f"  #{name}: {len(nicks)} ({desc})")

    progress = load_progress()
    if progress:
        total_done = sum(len(v) for k, v in progress.items() if k.startswith("checked_"))
        print(f"\n📋 Checkpoint: {total_done} já checados, continuando...")

    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    ready_event = asyncio.Event()

    @bot.event
    async def on_ready():
        nonlocal ready_event
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if not guild:
            print(f"❌ Server {GUILD_ID} não encontrado! Servers: {[g.name for g in bot.guilds]}")
            await bot.close()
            return
        print(f"\n🤖 Conectado: {guild.name}")
        ready_event.set()

    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("\n❌ BOT_TOKEN não definido!")
        print("   export BOT_TOKEN=seu_token_aqui")
        sys.exit(1)

    bot_task = asyncio.create_task(bot.start(token))
    await asyncio.wait_for(ready_event.wait(), timeout=30)
    await asyncio.sleep(1)

    guild = discord.utils.get(bot.guilds, id=GUILD_ID)

    # Create channels
    print(f"\n📁 Canais:")
    channels = {}
    for pat, nicks in nicks_by_pattern.items():
        name, desc = PATTERN_MAP.get(pat, (pat, pat))
        existing = discord.utils.get(guild.text_channels, name=name)
        if existing:
            channels[pat] = existing
            print(f"  #{name} (existe)")
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            ch = await guild.create_text_channel(name=name, topic=f"{desc} | Auto-scan", overwrites=overwrites)
            channels[pat] = ch
            print(f"  #{name} (criado)")

    # Run checks
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for pat, nicks in nicks_by_pattern.items():
            if pat in channels:
                await check_pattern(pat, nicks, channels[pat], progress, session)

    # Done
    print(f"\n{'='*55}")
    print("  🎉 TODOS CHECADOS! Desligando...")
    print(f"{'='*55}")

    await send_webhook(session, "🏁 **SCAN COMPLETO!** Todos os nicks checados.")
    save_progress(progress)
    await bot.close()
    print("👋 Bot desconectado.")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
