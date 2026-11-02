"""
GhoSty OwO Dual-Client — Expanded
Controller: discord.py | Workers: raw Gateway+REST
Includes: SPEED_MODES, farm cmds, huntbot, boss (guild channels),
quests, zoo/cash/essence, gems/inventory, image captcha solver hooks,
self-extract note for letter templates.
"""

from __future__ import annotations

import asyncio
import aiohttp
import base64
import json
import logging
import math
import os
import random
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Any

import discord
from discord.ext import commands
from colorama import Fore, Style, init as colorama_init

try:
    from PIL import Image
    import numpy as np
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

colorama_init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("ghosty-dual")

def cprint(msg, color=Fore.WHITE):
    print(f"{color}{msg}{Style.RESET_ALL}")
def log_info(msg): cprint(f"[INFO] {msg}", Fore.CYAN); log.info(msg)
def log_ok(msg): cprint(f"[OK] {msg}", Fore.GREEN); log.info(msg)
def log_warn(msg): cprint(f"[WARN] {msg}", Fore.YELLOW); log.warning(msg)
def log_err(msg): cprint(f"[ERR] {msg}", Fore.RED); log.error(msg)
def log_worker(wid, msg, level="INFO"):
    colors = {"INFO": Fore.CYAN, "OK": Fore.GREEN, "WARN": Fore.YELLOW, "ERR": Fore.RED, "DEBUG": Fore.WHITE, "SUCCESS": Fore.GREEN}
    cprint(f"[{wid}] [{level}] {msg}", colors.get(level, Fore.WHITE))

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
PROXY_URL = os.environ.get("PROXY_URL")
BASE_URL = "https://discord.com/api/v10"
GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
OWO_BOT_ID = 408785106942164992

# Original boss guild / channels
BOSS_GUILD_ID = 420104212895105044
BOSS_PRIMARY_CHANNEL = 1412234015578132511
BOSS_BACKUP_CHANNELS = [1412269279398596728, 1412269382599704691]

RETRY_INITIAL, RETRY_FACTOR, RETRY_MAX = 5, 1.5, 120
BOSS_MIN, BOSS_MAX = 17 * 60, 31 * 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LETTERS_DIR = os.path.join(BASE_DIR, "letters")
QUESTS_FILE = os.path.join(BASE_DIR, "ghostyworkerquests.json")
HB_DATA_FILE = os.path.join(BASE_DIR, "ghostyhbworkers.json")

SPEED_MODES = {
    "efficient": {"name": "Efficient (Fast)", "command_delay": 0.5, "action_delay_min": 5.0, "action_delay_max": 15.0,
        "random_long_delay_min": 200, "random_long_delay_max": 400, "gem_check_interval_min": 200, "gem_check_interval_max": 290,
        "run_duration_min": 3*3600, "run_duration_max": 3.5*3600, "sleep_duration_min": 3.5*3600, "sleep_duration_max": 4.5*3600},
    "fast": {"name": "Fast", "command_delay": 0.3, "action_delay_min": 4.5, "action_delay_max": 10.0,
        "random_long_delay_min": 160, "random_long_delay_max": 200, "gem_check_interval_min": 120, "gem_check_interval_max": 180,
        "run_duration_min": 1.5*3600, "run_duration_max": 2*3600, "sleep_duration_min": 3.5*3600, "sleep_duration_max": 5*3600},
    "durable": {"name": "Durable", "command_delay": 0.35, "action_delay_min": 6.5, "action_delay_max": 21.0,
        "random_long_delay_min": 300, "random_long_delay_max": 600, "gem_check_interval_min": 244, "gem_check_interval_max": 415,
        "run_duration_min": 5*3600, "run_duration_max": 7*3600, "sleep_duration_min": 3.5*3600, "sleep_duration_max": 5*3600},
    "lifetime": {"name": "Lifetime", "command_delay": 0.4, "action_delay_min": 7.0, "action_delay_max": 22.0,
        "random_long_delay_min": 250, "random_long_delay_max": 550, "gem_check_interval_min": 220, "gem_check_interval_max": 380,
        "work_duration_min": 3*3600, "work_duration_max": 5*3600, "break_duration_min": 10*3600, "break_duration_max": 14*3600,
        "day_skip_threshold": 3, "day_skip_duration": 24*3600},
    "humanoid": {"name": "Humanoid", "command_delay": 0.43, "action_delay_min": 8.5, "action_delay_max": 20.55,
        "random_long_delay_min": 250, "random_long_delay_max": 550, "gem_check_interval_min": 220, "gem_check_interval_max": 380,
        "work_duration_min": 3.78*3600, "work_duration_max": 6.4*3600, "break_duration_min": 8*3600, "break_duration_max": 12*3600},
}

_CHROME = list(range(120, 131))
_OS = ["10", "11"]
_LOCALES = ["en-US", "en-GB", "en-CA"]

def build_ua(chrome=None):
    v = chrome or random.choice(_CHROME)
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"

def build_super_properties():
    chrome = random.choice(_CHROME)
    props = {"os": "Windows", "browser": "Chrome", "device": "", "system_locale": random.choice(_LOCALES),
        "browser_user_agent": build_ua(chrome), "browser_version": f"{chrome}.0.0.0", "os_version": random.choice(_OS),
        "referrer": "", "referring_domain": "", "referrer_current": "", "referring_domain_current": "",
        "release_channel": "stable", "client_build_number": random.randint(290000, 320000), "client_event_source": None, "design_id": 0}
    return base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()

def ghostysmarttypo(command):
    if random.random() < 0.12:
        idx = random.randint(0, len(command) - 1)
        return command[:idx] + random.choice("abcdefghijklmnopqrstuvwxyz") + command[idx+1:]
    return command

def calculate_boss_delay():
    u = max(0.0001, random.random()); v = random.random()
    z = math.sqrt(-2.0 * math.log(u)) * math.cos(2.0 * math.pi * v)
    t = max(0.0, min(1.0, (z * 0.2) + 0.4))
    bezier = (1-t)**3*0 + 3*((1-t)**2)*t*0.2 + 3*(1-t)*(t**2)*0.8 + t**3*1
    return BOSS_MIN + bezier * (BOSS_MAX - BOSS_MIN)

def format_value(value):
    if value >= 1_000_000_000: return f"{value/1_000_000_000:.2f}B"
    if value >= 1_000_000: return f"{value/1_000_000:.2f}M"
    if value >= 1_000: return f"{value/1_000:.2f}K"
    return str(value)

# ── Zoo / cash / essence (from modules.py) ────────────────────────────────────

def parse_zoo_message(zoo_messages):
    combined = "\n".join(zoo_messages)
    superscript_map = {c: str(i) for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")}
    value_map = {
        "common": {"cash": 1, "essence": 1}, "uncommon": {"cash": 3, "essence": 5},
        "rare": {"cash": 10, "essence": 20}, "epic": {"cash": 250, "essence": 250},
        "mythic": {"cash": 5000, "essence": 3000}, "legendary": {"cash": 15000, "essence": 10000},
        "fabled": {"cash": 250000, "essence": 100000}, "special": {"cash": 6000, "essence": 5000},
        "hidden": {"cash": 1000000, "essence": 500000}, "patreon": {"cash": 1000, "essence": 500},
        "cpatreon": {"cash": 50000, "essence": 25000}, "gem": {"cash": 30000, "essence": 20000},
        "distorted": {"cash": 300000, "essence": 200000}, "bot": {"cash": 50000, "essence": 10000},
    }
    lines = combined.split("\n")
    tier_counts = {t: 0 for t in value_map}
    current_tier = None
    for line in lines:
        tier_match = re.search(r"<a?:(\w+):\d+>", line)
        if tier_match:
            tier_name = tier_match.group(1).lower()
            if tier_name == "botrank":
                tier_name = "bot"
            if tier_name in value_map:
                current_tier = tier_name
        if current_tier:
            for m in re.finditer(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", line):
                number_str = "".join(superscript_map.get(ch, ch) for ch in m.group(1))
                if number_str.isdigit():
                    tier_counts[current_tier] += int(number_str)
    total_cash = sum(tier_counts[t] * value_map[t]["cash"] for t in value_map)
    total_essence = sum(tier_counts[t] * value_map[t]["essence"] for t in value_map)
    return {"tier_counts": tier_counts, "total_cash": total_cash, "total_essence": total_essence}

def parse_gems(inventory_message):
    rarity_order = ["f", "l", "m", "e", "r", "u", "c"]
    gems_by_tier = {"1": [], "2": [], "3": [], "4": []}
    for line in inventory_message.split("\n"):
        for tier in ["1", "2", "3", "4"]:
            for rarity in rarity_order:
                m = re.search(rf"`(\d+)`<a?:({rarity}gem{tier}):\d+>", line)
                if m:
                    gems_by_tier[tier].append((rarity, m.group(1)))
    for tier in gems_by_tier:
        gems_by_tier[tier].sort(key=lambda x: rarity_order.index(x[0]))
    selected = []
    for tier in ["1", "2", "3", "4"]:
        if gems_by_tier[tier]:
            selected.append(gems_by_tier[tier][0][1])
    return selected

# ── Image captcha solver (from ghostycorehb.py) ───────────────────────────────

def _get_img_paths(directory):
    results = []
    if not os.path.isdir(directory):
        return results
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".png"):
                results.append(os.path.join(root, f))
    return results

def _compare_imgs(large_data, large_w, small_data, small_w, small_h, start_x, start_y):
    for y in range(small_h):
        for x in range(small_w):
            li = ((start_y + y) * large_w + (start_x + x)) * 4
            si = (y * small_w + x) * 4
            if small_data[si + 3] > 0 and (
                small_data[si] != large_data[li] or small_data[si+1] != large_data[li+1] or small_data[si+2] != large_data[li+2]
            ):
                return False
    return True

def _match_letters(large_data, large_w, large_h, checks):
    matches = []
    for check in checks:
        img_data, sw, sh, letter = check["img_data"], check["width"], check["height"], check["letter"]
        for y in range(large_h - sh + 1):
            for x in range(large_w - sw + 1):
                if _compare_imgs(large_data, large_w, img_data, sw, sh, x, y):
                    if not any(abs(m["x"]-x) < sw and abs(m["y"]-y) < sh for m in matches):
                        matches.append({"x": x, "y": y, "letter": letter})
    matches.sort(key=lambda m: m["x"])
    return "".join(m["letter"] for m in matches)

def solve_captcha_image(captcha_url: str) -> Optional[str]:
    """Template-match captcha using letters/*.png. Returns solved string or None."""
    if not HAS_PIL:
        return None
    checks = []
    for path in sorted(_get_img_paths(LETTERS_DIR)):
        with Image.open(path) as img:
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            w, h = img.size
            arr = np.array(img).flatten().astype(np.uint8)
            letter = os.path.splitext(os.path.basename(path))[0]
            checks.append({"img_data": arr, "width": w, "height": h, "letter": letter})
    if not checks:
        return None
    try:
        import requests
        r = requests.get(captcha_url, timeout=15)
        r.raise_for_status()
        with Image.open(BytesIO(r.content)) as large:
            if large.mode != "RGBA":
                large = large.convert("RGBA")
            lw, lh = large.size
            large_data = np.array(large).flatten().astype(np.uint8)
        return _match_letters(large_data, lw, lh, checks) or None
    except Exception:
        return None

# ── Quests persistence ────────────────────────────────────────────────────────

def load_quests(worker_key: str) -> dict:
    if not os.path.exists(QUESTS_FILE):
        return {}
    try:
        with open(QUESTS_FILE) as f:
            data = json.load(f)
        return data.get(str(worker_key), {})
    except Exception:
        return {}

def save_quests(worker_key: str, worker_data: dict):
    try:
        data = {}
        if os.path.exists(QUESTS_FILE):
            with open(QUESTS_FILE) as f:
                try: data = json.load(f)
                except Exception: pass
        data[str(worker_key)] = worker_data
        with open(QUESTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_warn(f"save quests: {e}")

# ── Validation ────────────────────────────────────────────────────────────────

async def validate_user_token(token):
    headers = {"Authorization": token, "User-Agent": build_ua()}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{BASE_URL}/users/@me", headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200: return await r.json()
    except Exception as e: log_warn(f"token validate: {e}")
    return None

async def validate_channel(token, channel_id):
    headers = {"Authorization": token, "User-Agent": build_ua()}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{BASE_URL}/channels/{channel_id}", headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200: return await r.json()
    except Exception as e: log_warn(f"channel validate: {e}")
    return None

# ── Farm Worker ───────────────────────────────────────────────────────────────

class FarmWorker:
    def __init__(self, worker_id, user_token, channel_id, owner_id, speed_mode="efficient", huntbot_enabled=True):
        self.worker_id = worker_id
        self.user_token = user_token
        self.channel_id = str(channel_id)
        self.owner_id = owner_id
        self.speed_mode = speed_mode if speed_mode in SPEED_MODES else "efficient"
        self.huntbot_enabled = huntbot_enabled
        self.username = "Connecting..."
        self.user_id = None
        self.active = True
        self.running = False
        self._gw_task = self._farm_task = self._boss_task = self._hb_task = self._quest_task = None
        self._session = None
        self._sequence = None
        self._session_id = None
        self.paused = False
        self.pause_end_time = None
        self.sleep_mode = False
        self.farming_start_time = None
        self.ghosty_commands_sent = 0
        self.boss_tickets = 3
        self.is_boss_fighting = False
        self.messages_seen = 0
        self.last_command = None
        self.lifetime_work_cycles = 0
        self.lifetime_cycle_start = None
        self.last_gem_check = 0.0
        self.initial_cash = 0
        self.initial_essence = 0
        self.current_cash = 0
        self.current_essence = 0
        self.all_quests_finished = False
        self.next_quest_check = 0.0

    async def start(self):
        self._gw_task = asyncio.create_task(self._gateway_loop(), name=f"gw-{self.worker_id}")

    async def stop(self):
        self.active = False
        self.running = False
        for t in (self._farm_task, self._boss_task, self._hb_task, self._quest_task, self._gw_task):
            if t and not t.done():
                t.cancel()
                try: await t
                except asyncio.CancelledError: pass
        if self._session and not self._session.closed:
            await self._session.close()

    async def _gateway_loop(self):
        attempt = 0
        while self.active:
            try:
                await self._connect(); attempt = 0
            except asyncio.CancelledError: break
            except Exception as exc:
                if not self.active: break
                wait = min(RETRY_INITIAL * (RETRY_FACTOR ** attempt) + random.uniform(0.5, 2), RETRY_MAX)
                log_worker(self.worker_id, f"gateway error ({exc}). retry {wait:.1f}s", "WARN")
                attempt += 1
                try: await asyncio.sleep(wait)
                except asyncio.CancelledError: break

    async def _connect(self):
        super_props = build_super_properties()
        headers = {"User-Agent": build_ua(), "Origin": "https://discord.com"}
        self._session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=True, limit=4))
        ws_kwargs = {"headers": headers, "max_msg_size": 0}
        if PROXY_URL: ws_kwargs["proxy"] = PROXY_URL
        async with self._session.ws_connect(GATEWAY_URL, **ws_kwargs) as ws:
            await self._handle_ws(ws, super_props)

    async def _handle_ws(self, ws, super_props):
        hb_task = None
        async def heartbeat(interval_ms):
            try:
                await asyncio.sleep(random.uniform(0, interval_ms/1000*0.8))
                while True:
                    await ws.send_str(json.dumps({"op": 1, "d": self._sequence}))
                    await asyncio.sleep(interval_ms/1000 + random.uniform(-0.4, 0.4))
            except asyncio.CancelledError: pass
        try:
            async for raw in ws:
                if not self.active: break
                if raw.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR): break
                if raw.type != aiohttp.WSMsgType.TEXT: continue
                payload = json.loads(raw.data)
                op, t, d, s = payload.get("op"), payload.get("t"), payload.get("d") or {}, payload.get("s")
                if s is not None: self._sequence = s
                if op == 10:
                    hb_task = asyncio.create_task(heartbeat(d["heartbeat_interval"]))
                    props_obj = json.loads(base64.b64decode(super_props.encode()).decode())
                    identify = {"op": 2, "d": {
                        "token": self.user_token, "capabilities": 16381, "properties": props_obj,
                        "presence": {"status": "invisible", "since": 0, "activities": [], "afk": False},
                        "compress": False, "client_state": {"guild_versions": {}, "highest_last_message_id": "0",
                            "read_state_version": 0, "user_guild_settings_version": -1, "user_settings_version": -1,
                            "private_channels_version": "0", "api_code_version": 0},
                    }}
                    await ws.send_str(json.dumps(identify))
                elif op == 7:
                    log_worker(self.worker_id, "reconnect requested", "INFO"); break
                elif op == 9:
                    log_worker(self.worker_id, "invalid session", "WARN"); await asyncio.sleep(random.uniform(1, 4)); break
                elif op == 0:
                    if t == "READY":
                        user = d.get("user", {})
                        self.username = user.get("username", "Unknown")
                        self.user_id = str(user.get("id", ""))
                        self._session_id = d.get("session_id")
                        self.running = True
                        log_worker(self.worker_id, f"READY as {self.username} → ch {self.channel_id}", "OK")
                        if not self._farm_task or self._farm_task.done():
                            self._farm_task = asyncio.create_task(self._farm_loop())
                        if not self._boss_task or self._boss_task.done():
                            self._boss_task = asyncio.create_task(self._boss_loop())
                        if self.huntbot_enabled and (not self._hb_task or self._hb_task.done()):
                            self._hb_task = asyncio.create_task(self._huntbot_loop())
                        if not self._quest_task or self._quest_task.done():
                            self._quest_task = asyncio.create_task(self._quest_loop())
                    elif t in ("MESSAGE_CREATE", "MESSAGE_UPDATE"):
                        if str(d.get("channel_id")) == self.channel_id:
                            self.messages_seen += 1
                            await self._on_message(d)
        finally:
            if hb_task and not hb_task.done(): hb_task.cancel()
            self.running = False

    async def _rest(self, method, path, json_body=None):
        if not self._session or self._session.closed: return None
        headers = {"Authorization": self.user_token, "User-Agent": build_ua(), "Content-Type": "application/json"}
        try:
            async with self._session.request(method, f"{BASE_URL}{path}", headers=headers, json=json_body,
                                             timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status in (200, 201): return await resp.json()
                if resp.status == 204: return {}
                text = await resp.text()
                if resp.status == 429:
                    retry = float(resp.headers.get("Retry-After", "3"))
                    log_worker(self.worker_id, f"rate limit {retry}s", "WARN"); await asyncio.sleep(retry + 0.3)
                else:
                    log_worker(self.worker_id, f"REST {resp.status}: {text[:120]}", "WARN")
        except Exception as e:
            log_worker(self.worker_id, f"REST error: {e}", "WARN")
        return None

    async def send_message(self, content):
        return await self._rest("POST", f"/channels/{self.channel_id}/messages", {"content": content})

    async def get_messages(self, limit=30, channel_id=None):
        ch = channel_id or self.channel_id
        data = await self._rest("GET", f"/channels/{ch}/messages?limit={limit}")
        return data if isinstance(data, list) else []

    async def click_button(self, message, custom_id):
        if not self._session or self._session.closed: return False
        payload = {"type": 3, "nonce": str(random.randint(10**17, 10**18-1)), "channel_id": str(message.get("channel_id") or self.channel_id),
            "message_flags": message.get("flags", 0), "message_id": message.get("id"), "application_id": str(OWO_BOT_ID),
            "session_id": self._session_id or "", "data": {"component_type": 2, "custom_id": custom_id}}
        if message.get("guild_id"): payload["guild_id"] = message["guild_id"]
        headers = {"Authorization": self.user_token, "User-Agent": build_ua(), "Content-Type": "application/json"}
        try:
            async with self._session.post(f"{BASE_URL}/interactions", headers=headers, json=payload,
                                          timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status in (200, 204): return True
                body = await resp.text()
                log_worker(self.worker_id, f"button {resp.status}: {body[:100]}", "WARN")
        except Exception as e:
            log_worker(self.worker_id, f"button error: {e}", "WARN")
        return False

    # ── zoo tracking ──────────────────────────────────────────────────────────

    async def fetch_zoo(self):
        await self.send_message("owo zoo")
        await asyncio.sleep(5)
        msgs = await self.get_messages(15)
        zoo_messages = []
        for msg in msgs:
            if str(msg.get("author", {}).get("id")) != str(OWO_BOT_ID): continue
            content = msg.get("content") or ""
            cl = content.lower()
            if any(k in cl for k in ("zoo", "animals", "cowoncy", "points:")) or any(s in content for s in "⁰¹²³⁴⁵⁶⁷⁸⁹"):
                zoo_messages.append(content)
                if "common" in cl: break
        if not zoo_messages: return None
        zoo_messages.reverse()
        data = parse_zoo_message(zoo_messages)
        self.current_cash = data["total_cash"]
        self.current_essence = data["total_essence"]
        log_worker(self.worker_id, f"zoo cash={format_value(self.current_cash)} essence={format_value(self.current_essence)}", "INFO")
        return data

    # ── gems / inventory ──────────────────────────────────────────────────────

    async def check_gems_inventory(self):
        await self.send_message("owo inv")
        await asyncio.sleep(4)
        msgs = await self.get_messages(12)
        inv_text = ""
        for msg in msgs:
            if str(msg.get("author", {}).get("id")) != str(OWO_BOT_ID): continue
            inv_text += (msg.get("content") or "") + "\n"
            for emb in msg.get("embeds") or []:
                inv_text += (emb.get("description") or "") + "\n"
        gems = parse_gems(inv_text)
        if gems:
            # use top gems: owo use <ids>
            use_cmd = "owo use " + " ".join(gems[:4])
            await self.send_message(use_cmd)
            log_worker(self.worker_id, f"gems selected/used: {gems[:4]}", "OK")
        else:
            log_worker(self.worker_id, "no usable gems parsed", "DEBUG")
        self.last_gem_check = time.time()
        return gems

    # ── quests ────────────────────────────────────────────────────────────────

    async def fetch_quests(self):
        await self.send_message("owo q")
        await asyncio.sleep(4)
        msgs = await self.get_messages(20)
        quest_msg = None
        for msg in msgs:
            if str(msg.get("author", {}).get("id")) != str(OWO_BOT_ID): continue
            raw = json.dumps(msg).lower()
            if "quest" in raw:
                quest_msg = msg
                if "you finished all of your quests" in raw:
                    self.all_quests_finished = True
                    log_worker(self.worker_id, "all quests finished — cooldown", "INFO")
                    return None
                break
        if not quest_msg:
            log_worker(self.worker_id, "no quest log found", "DEBUG")
            return None
        # click progress / claim style buttons if present
        for row in quest_msg.get("components") or []:
            for comp in row.get("components") or []:
                if comp.get("type") != 2 or comp.get("disabled"): continue
                label = (comp.get("label") or "").lower()
                cid = comp.get("custom_id") or ""
                if any(k in label for k in ("claim", "reward", "collect", "next")) or any(k in cid.lower() for k in ("claim", "reward")):
                    if await self.click_button(quest_msg, cid):
                        log_worker(self.worker_id, f"quest button {label or cid}", "OK")
        # parse simple progress lines into persistence
        content = (quest_msg.get("content") or "")
        for emb in quest_msg.get("embeds") or []:
            content += "\n" + (emb.get("description") or "")
        qdata = load_quests(self.worker_id)
        qdata["last_check"] = datetime.now(timezone.utc).isoformat()
        qdata["snippet"] = content[:500]
        save_quests(self.worker_id, qdata)
        log_worker(self.worker_id, "quests refreshed", "INFO")
        return content

    async def _quest_loop(self):
        await asyncio.sleep(random.uniform(20, 40))
        while self.active and self.running:
            try:
                if self.sleep_mode or self.paused or self.all_quests_finished:
                    await asyncio.sleep(60); continue
                if time.time() < self.next_quest_check:
                    await asyncio.sleep(15); continue
                await self.fetch_quests()
                self.next_quest_check = time.time() + random.uniform(600, 1200)
            except asyncio.CancelledError: break
            except Exception as e:
                log_worker(self.worker_id, f"quest loop: {e}", "WARN"); await asyncio.sleep(30)

    def _cmd_pool(self):
        return [
            ghostysmarttypo("owoh"), ghostysmarttypo("owo pray"), ghostysmarttypo("owo h"),
            ghostysmarttypo("owo b"), ghostysmarttypo("owob"), ghostysmarttypo("owoh"), ghostysmarttypo("owo h"),
            ghostysmarttypo(random.choice(["owo cf 1", "owoz", "owo s 2", "owo owo", "owoq"])),
            ghostysmarttypo(random.choice(["owo pup", "owo army", "owo piku", "owo run"])),
            ghostysmarttypo(random.choice(["owo punch <@408785106942164992>", "owo roll"])),
        ]

    async def _farm_loop(self):
        cfg = SPEED_MODES[self.speed_mode]
        log_worker(self.worker_id, f"farm loop ({cfg['name']})", "INFO")
        await asyncio.sleep(random.uniform(2, 7))
        self.farming_start_time = datetime.now(timezone.utc)
        self.lifetime_cycle_start = datetime.now(timezone.utc)
        # initial zoo snapshot
        try:
            z = await self.fetch_zoo()
            if z:
                self.initial_cash = z["total_cash"]
                self.initial_essence = z["total_essence"]
        except Exception: pass
        if self.huntbot_enabled:
            await self.send_message("owo hb"); await asyncio.sleep(3)
        while self.active and self.running:
            try:
                if self.paused and self.pause_end_time:
                    if datetime.now(timezone.utc) >= self.pause_end_time:
                        self.paused = False; self.pause_end_time = None
                        self.farming_start_time = datetime.now(timezone.utc)
                        log_worker(self.worker_id, "pause ended", "OK")
                    else:
                        await asyncio.sleep(8); continue
                if self.sleep_mode:
                    await asyncio.sleep(10); continue

                if self.speed_mode in ("lifetime", "humanoid") and self.lifetime_cycle_start:
                    work_for = random.uniform(cfg.get("work_duration_min", 10800), cfg.get("work_duration_max", 18000))
                    if (datetime.now(timezone.utc) - self.lifetime_cycle_start).total_seconds() >= work_for:
                        brk = random.uniform(cfg.get("break_duration_min", 36000), cfg.get("break_duration_max", 50400))
                        self.sleep_mode = True; self.lifetime_work_cycles += 1
                        if self.speed_mode == "lifetime" and self.lifetime_work_cycles >= cfg.get("day_skip_threshold", 3):
                            brk = cfg.get("day_skip_duration", 86400); self.lifetime_work_cycles = 0
                            log_worker(self.worker_id, "lifetime DAY SKIP", "INFO")
                        await self.send_message(f"😴 break {int(brk//3600)}h")
                        await asyncio.sleep(brk)
                        self.sleep_mode = False; self.lifetime_cycle_start = datetime.now(timezone.utc)
                        continue

                if self.speed_mode in ("efficient", "fast", "durable") and self.farming_start_time:
                    run_for = random.uniform(cfg["run_duration_min"], cfg["run_duration_max"])
                    if (datetime.now(timezone.utc) - self.farming_start_time).total_seconds() >= run_for:
                        sleep_for = random.uniform(cfg["sleep_duration_min"], cfg["sleep_duration_max"])
                        self.sleep_mode = True
                        # zoo snapshot before sleep
                        try: await self.fetch_zoo()
                        except Exception: pass
                        await asyncio.sleep(sleep_for)
                        self.sleep_mode = False; self.farming_start_time = datetime.now(timezone.utc)
                        continue

                # gem check interval
                gmin, gmax = cfg.get("gem_check_interval_min", 200), cfg.get("gem_check_interval_max", 290)
                if time.time() - self.last_gem_check >= random.uniform(gmin, gmax):
                    try: await self.check_gems_inventory()
                    except Exception as e: log_worker(self.worker_id, f"gem check: {e}", "WARN")

                cmds = self._cmd_pool()
                command = random.choice(cmds)
                while command == self.last_command and len(cmds) > 1:
                    command = random.choice(cmds)
                self.last_command = command
                await self.send_message(command)
                self.ghosty_commands_sent += 1
                await asyncio.sleep(cfg["command_delay"])
                await asyncio.sleep(random.uniform(cfg["action_delay_min"], cfg["action_delay_max"]))
                if random.random() < 0.05:
                    await asyncio.sleep(random.uniform(cfg["random_long_delay_min"], cfg["random_long_delay_max"]))
            except asyncio.CancelledError: break
            except Exception as e:
                log_worker(self.worker_id, f"farm: {e}", "ERR"); await asyncio.sleep(5)

    async def _huntbot_loop(self):
        await asyncio.sleep(random.uniform(8, 15))
        while self.active and self.running:
            try:
                if self.sleep_mode or self.paused:
                    await asyncio.sleep(20); continue
                await self.send_message("owo hb")
                await asyncio.sleep(random.uniform(280, 420))
            except asyncio.CancelledError: break
            except Exception as e:
                log_worker(self.worker_id, f"hb: {e}", "WARN"); await asyncio.sleep(30)

    async def _boss_loop(self):
        await asyncio.sleep(random.uniform(30, 90))
        first = True
        while self.active and self.running:
            try:
                if self.boss_tickets <= 0:
                    log_worker(self.worker_id, "no boss tickets", "WARN"); return
                delay = random.uniform(120, 300) if first else calculate_boss_delay()
                first = False
                log_worker(self.worker_id, f"next boss in {int(delay//60)}m", "DEBUG")
                slept = 0
                while slept < delay:
                    if not self.active: return
                    await asyncio.sleep(5); slept += 5
                await self._try_boss_fight()
            except asyncio.CancelledError: break
            except Exception as e:
                log_worker(self.worker_id, f"boss: {e}", "WARN"); await asyncio.sleep(30)

    async def _try_boss_fight(self):
        if self.boss_tickets <= 0 or self.is_boss_fighting: return
        self.is_boss_fighting = True
        try:
            # Prefer original guild boss channels, fall back to farm channel
            channels_to_scan = [str(BOSS_PRIMARY_CHANNEL)] + [str(c) for c in BOSS_BACKUP_CHANNELS] + [self.channel_id]
            target_msg = target_cid = None
            for ch in channels_to_scan:
                log_worker(self.worker_id, f"boss scan ch {ch}", "DEBUG")
                try:
                    msgs = await self.get_messages(40, channel_id=ch)
                except Exception:
                    continue
                for msg in msgs:
                    if str(msg.get("author", {}).get("id")) != str(OWO_BOT_ID): continue
                    raw = json.dumps(msg).lower()
                    if "boss" not in raw and "fight" not in raw: continue
                    for row in msg.get("components") or []:
                        for comp in row.get("components") or []:
                            if comp.get("type") != 2: continue
                            label = (comp.get("label") or "").lower()
                            cid = (comp.get("custom_id") or "").lower()
                            if ("fight" in label or "fight" in cid) and not comp.get("disabled"):
                                target_msg, target_cid = msg, comp.get("custom_id")
                                break
                        if target_msg: break
                    if target_msg: break
                if target_msg: break
            if not target_msg or not target_cid:
                log_worker(self.worker_id, "no boss fight", "INFO"); return
            log_worker(self.worker_id, "clicking Fight", "OK")
            if await self.click_button(target_msg, target_cid):
                log_worker(self.worker_id, "boss interaction sent", "OK")
            await asyncio.sleep(3)
            for m in await self.get_messages(8, channel_id=str(target_msg.get("channel_id") or self.channel_id)):
                content = (m.get("content") or "").lower()
                for emb in m.get("embeds") or []:
                    content += " " + (emb.get("description") or "").lower()
                if "boss tickets" in content and ("don't" in content or "do not" in content):
                    self.boss_tickets = 0
                    log_worker(self.worker_id, "out of boss tickets", "WARN")
        finally:
            self.is_boss_fighting = False

    async def _on_message(self, msg):
        author = msg.get("author") or {}
        if str(author.get("id")) != str(OWO_BOT_ID): return
        content = (msg.get("content") or "").lower()
        for emb in msg.get("embeds") or []:
            content += " " + (emb.get("description") or "").lower()
            content += " " + (emb.get("title") or "").lower()

        # image captcha: look for attachment urls on verify-like messages
        if any(k in content for k in ("captcha", "are you a real human", "verify", "please complete", "letter")):
            solved = None
            for att in msg.get("attachments") or []:
                url = att.get("url") or att.get("proxy_url")
                if url and any(url.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
                    log_worker(self.worker_id, "image captcha detected — solving", "WARN")
                    solved = await asyncio.get_event_loop().run_in_executor(None, solve_captcha_image, url)
                    break
            if solved:
                await self.send_message(solved)
                log_worker(self.worker_id, f"captcha answer sent: {solved}", "OK")
            else:
                log_worker(self.worker_id, "captcha — pause 3m (no solve / no templates)", "WARN")
                self.paused = True
                self.pause_end_time = datetime.now(timezone.utc) + timedelta(minutes=3)
            return

        for row in msg.get("components") or []:
            for comp in row.get("components") or []:
                if comp.get("type") != 2 or comp.get("disabled"): continue
                label = (comp.get("label") or "").lower()
                cid = comp.get("custom_id") or ""
                if any(k in label for k in ("fight", "claim", "accept", "yes", "collect")) or any(
                    k in cid.lower() for k in ("fight", "claim", "accept", "collect")
                ):
                    if await self.click_button(msg, cid):
                        log_worker(self.worker_id, f"clicked {label or cid}", "OK")
                    return

# ── Registry ──────────────────────────────────────────────────────────────────

class UserWorkerSlot:
    def __init__(self, num, token, channel_id):
        self.num = num; self.token = token; self.channel_id = channel_id
        self.username = "..."; self.worker = None

class UserConfig:
    def __init__(self, user_id, username):
        self.user_id = user_id; self.username = username
        self.slots = {}; self.next_num = 1
    def add(self, token, channel_id):
        slot = UserWorkerSlot(self.next_num, token, channel_id)
        self.slots[self.next_num] = slot; self.next_num += 1
        return slot

class UserManager:
    def __init__(self):
        self.users = {}; self.lock = threading.Lock()
    def get_or_create(self, user_id, username):
        with self.lock:
            if user_id not in self.users:
                self.users[user_id] = UserConfig(user_id, username)
            return self.users[user_id]

user_manager = UserManager()
live_workers = {}

def parse_pairs(raw):
    if not raw or not raw.strip(): return None
    pairs = []
    for part in raw.split(","):
        part = part.strip()
        if not part or "-" not in part: return None
        token, ch = part.rsplit("-", 1)
        token, ch = token.strip(), ch.strip()
        if len(token) < 50 or not ch.isdigit(): return None
        pairs.append((token, int(ch)))
    return pairs or None

# ── Controller ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

@bot.event
async def on_ready():
    try: await bot.tree.sync()
    except Exception as e: log_warn(f"slash sync: {e}")
    log_ok(f"Controller online as {bot.user}")

class AddWorkersModal(discord.ui.Modal, title="Add Worker Tokens & Channels"):
    workers_input = discord.ui.TextInput(label="TOKEN-CHANNELID pairs", style=discord.TextStyle.paragraph,
        placeholder="TOKEN1-CHANNELID1,TOKEN2-CHANNELID2", required=True, max_length=4000)
    def __init__(self, owner_id, user_config):
        super().__init__(); self.owner_id = owner_id; self.user_config = user_config
    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        pairs = parse_pairs(self.workers_input.value)
        if not pairs:
            await interaction.followup.send("❌ Format: `TOKEN-CHANNELID` comma-separated.", ephemeral=True); return
        results, valid = [], []
        for i, (token, channel_id) in enumerate(pairs, 1):
            ud = await validate_user_token(token)
            if not ud: results.append((i, False, "Invalid token")); continue
            cd = await validate_channel(token, channel_id)
            if not cd: results.append((i, False, "Channel not found / no access")); continue
            results.append((i, True, f"{ud.get('username')} → #{cd.get('name', channel_id)}"))
            valid.append((token, channel_id, ud, cd))
        embed = discord.Embed(title="Verification", color=discord.Color.green() if valid else discord.Color.red())
        for i, ok, msg in results:
            embed.add_field(name=f"{'✅' if ok else '❌'} Pair {i}", value=msg, inline=False)
        embed.add_field(name="Summary", value=f"Valid: {len(valid)} / {len(pairs)}", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        if not valid: return
        started = 0
        for token, channel_id, ud, cd in valid:
            slot = self.user_config.add(token, channel_id)
            wid = f"u{self.owner_id}-w{slot.num}"
            worker = FarmWorker(wid, token, channel_id, self.owner_id, "efficient", True)
            slot.worker = worker; slot.username = ud.get("username", "?")
            live_workers[wid] = worker
            await worker.start(); started += 1
        await interaction.followup.send(
            f"🚀 **{started} worker(s)** started.\nFarm + HB + boss + quests + zoo/gems active.", ephemeral=True)

class PanelView(discord.ui.View):
    def __init__(self, owner_id, user_config):
        super().__init__(timeout=180); self.owner_id = owner_id; self.user_config = user_config
    @discord.ui.button(label="Add Workers", style=discord.ButtonStyle.blurple, emoji="➕")
    async def add_workers(self, interaction, button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Not your panel.", ephemeral=True); return
        await interaction.response.send_modal(AddWorkersModal(self.owner_id, self.user_config))
    @discord.ui.button(label="Stop All Mine", style=discord.ButtonStyle.red, emoji="🛑")
    async def stop_all(self, interaction, button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Not your panel.", ephemeral=True); return
        stopped = 0
        for slot in list(self.user_config.slots.values()):
            if slot.worker and slot.worker.active:
                await slot.worker.stop(); live_workers.pop(slot.worker.worker_id, None); stopped += 1
        await interaction.response.send_message(f"🛑 Stopped {stopped}.", ephemeral=True)

@bot.command(name="panel")
async def cmd_panel(ctx):
    uid, uname = ctx.author.id, str(ctx.author)
    cfg = user_manager.get_or_create(uid, uname)
    embed = discord.Embed(title="🎮 GhoSty Dual-Client — Expanded",
        description=("**Logger pattern + expanded farm**\n"
                     "• Controller = discord.py\n• Workers = raw Gateway+REST\n"
                     "• Quests, zoo/cash/essence, gems, image captcha, boss channels"),
        color=discord.Color.blurple())
    slots = list(cfg.slots.values())
    if slots:
        lines = []
        for s in slots:
            w = s.worker
            status = "🟢 running" if (w and w.running) else "⚪ stopped"
            name = s.username or (w.username if w else "?")
            cmds = w.ghosty_commands_sent if w else 0
            cash = format_value(w.current_cash) if w else "?"
            lines.append(f"**W#{s.num}** — {name}\n└─ <#{s.channel_id}> · {status} · cmds:{cmds} · cash≈{cash}")
        embed.add_field(name=f"Workers ({len(slots)})", value="\n\n".join(lines)[:1000], inline=False)
    else:
        embed.add_field(name="Workers", value="None. Click **Add Workers**.", inline=False)
    embed.add_field(name="Captcha templates", value="Put letter PNGs in `./letters/` (a.png, b.png, …)", inline=False)
    embed.set_footer(text=f"{uname} · dual expanded")
    await ctx.send(embed=embed, view=PanelView(uid, cfg))

@bot.tree.command(name="status", description="Global worker counts")
async def slash_status(interaction):
    total = len(live_workers)
    running = sum(1 for w in live_workers.values() if w.running)
    cmds = sum(w.ghosty_commands_sent for w in live_workers.values())
    await interaction.response.send_message(f"**Workers:** {running}/{total} · **Commands:** {cmds}", ephemeral=True)

def main():
    if not BOT_TOKEN:
        log_err("DISCORD_BOT_TOKEN required"); sys.exit(1)
    if not HAS_PIL:
        log_warn("PIL/numpy not installed — image captcha solver disabled until `pip install pillow numpy`")
    if not os.path.isdir(LETTERS_DIR) or not _get_img_paths(LETTERS_DIR):
        log_warn(f"No letter templates in {LETTERS_DIR} — image captcha will pause instead of solve")
    print(f"""
{Fore.MAGENTA}╔══════════════════════════════════════════════════════════════╗
║  GhoSty Dual-Client EXPANDED                                 ║
║  + Quests  + Zoo/Cash/Essence  + Gems  + Image Captcha       ║
║  + Boss guild channels  + SPEED_MODES farm                   ║
║  Controller=discord.py | Workers=raw gateway                 ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
""")
    bot.run(BOT_TOKEN, log_handler=None)

if __name__ == "__main__":
    main()
