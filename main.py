# ==================== PART 1 OF 5 - CORE SETUP ====================
# Imports, Config, Database, Helper Functions
# PASTE THIS FIRST

import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
import asyncpg
from collections import defaultdict
import traceback
import re
from difflib import get_close_matches
from aiohttp import web
import json

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('DiscordBot')

class BotConfig:
    def __init__(self):
        self.PREFIX = "f!"
        self.OWNER_ID = 1029438856069656576
        self.STAFF_ROLE_ID = 1432081794647199895
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.LOG_CHANNEL_ID = None
        self.WELCOME_CHANNEL_ID = None
        self.LEAVE_CHANNEL_ID = None
        self.INVITE_CHANNEL_ID = None
        self.WELCOME_MSG = "Welcome {user} to {servername}! You are member #{count}."
        self.LEAVE_MSG = "Goodbye {user}! You were member #{count}."
        self.INVITE_MSG = "{user} has been invited by {inviter} and has now {invites} invites!"
        self.WELCOME_ENABLED = False
        self.LEAVE_ENABLED = False
        self.INVITE_LOG_ENABLED = False
        self.VERIFICATION_CHANNEL_ID = None
        self.VERIFIED_ROLE_ID = None
        self.UNVERIFIED_ROLE_ID = None
        self.VERIFICATION_ENABLED = False
        self.FAKE_INVITE_DAYS = 4
        self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists('bot_config.json'):
                with open('bot_config.json', 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key.upper()):
                            setattr(self, key.upper(), value)
        except: pass
    
    def save_config(self):
        try:
            data = {k.lower(): v for k, v in self.__dict__.items() if not k.startswith('_')}
            with open('bot_config.json', 'w') as f:
                json.dump(data, f, indent=4)
        except: pass

config = BotConfig()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=lambda bot, message: config.PREFIX, intents=intents, help_command=None, case_insensitive=True)

whitelist_data = {"commands": {}}
permission_data = {"commands": {}}
ai_config = {"channel_id": None, "enabled": False}
ai_conversations = defaultdict(lambda: {"messages": [], "personality": "friendly", "created_at": datetime.utcnow()})
antiraid_config = {"enabled": False, "sensitivity": "medium", "joins": defaultdict(list)}
antialt_config = {"enabled": False, "min_age_days": 7, "action": "kick"}
antilink_config = {"enabled": False, "whitelist_domains": [], "bypass_roles": [], "bypass_users": [], "action": "delete"}
antinuke_config = {"enabled": False, "whitelist": [], "actions": {"channel_delete": defaultdict(list), "role_delete": defaultdict(list), "ban": defaultdict(list), "kick": defaultdict(list)}, "bot_adders": {}}
automod_config = {"enabled": False, "sensitivity": "medium", "action": "delete", "ignored_channels": [], "whitelisted_roles": []}
antispam_config = {"enabled": False, "max_messages": 5, "timeframe": 3, "action": "mute", "ignored_channels": [], "whitelisted_roles": [], "user_messages": defaultdict(list)}
invite_tracker = {}
message_tracker = defaultdict(int)
db_pool = None
db_manager = None

AI_PERSONALITIES = {
    "friendly": {"name": "Friendly", "emoji": "😊", "prompt": "You are warm and friendly."},
    "professional": {"name": "Professional", "emoji": "💼", "prompt": "You are professional."},
    "sassy": {"name": "Sassy", "emoji": "💅", "prompt": "You are sassy!"},
    "mean": {"name": "Mean", "emoji": "😈", "prompt": "You roast users!"},
    "cool": {"name": "Cool", "emoji": "😎", "prompt": "You're cool."},
    "nerdy": {"name": "Nerdy", "emoji": "🤓", "prompt": "You're a nerd!"},
    "gamer": {"name": "Gamer", "emoji": "🎮", "prompt": "You're a gamer!"},
    "pirate": {"name": "Pirate", "emoji": "🏴‍☠️", "prompt": "Ye be a pirate!"},
    "uwu": {"name": "UwU", "emoji": "🥺", "prompt": "You awe cute UwU!"},
    "gen-z": {"name": "Gen-Z", "emoji": "✨", "prompt": "You're Gen-Z!"},
    "robot": {"name": "Robot", "emoji": "🤖", "prompt": "BEEP BOOP."},
    "chaotic": {"name": "Chaotic", "emoji": "🌪️", "prompt": "CHAOS!"},
    "wholesome": {"name": "Wholesome", "emoji": "🥰", "prompt": "Wholesome!"},
    "motivational": {"name": "Motivational", "emoji": "💪", "prompt": "Motivate!"},
    "tsundere": {"name": "Tsundere", "emoji": "😤", "prompt": "Tsundere!"},
    "shakespearean": {"name": "Shakespeare", "emoji": "📜", "prompt": "Shakespeare!"},
    "detective": {"name": "Detective", "emoji": "🔍", "prompt": "Detective!"},
    "zen": {"name": "Zen", "emoji": "🧘", "prompt": "Zen."},
    "comedic": {"name": "Comedian", "emoji": "😂", "prompt": "Comedian!"},
    "karen": {"name": "Karen", "emoji": "😠", "prompt": "Karen!"},
    "creative": {"name": "Creative", "emoji": "🎨", "prompt": "Creative!"},
    "casual": {"name": "Casual", "emoji": "😌", "prompt": "Casual."},
    "wise": {"name": "Wise", "emoji": "🧙", "prompt": "Wise."},
    "enthusiastic": {"name": "Enthusiastic", "emoji": "🎉", "prompt": "Enthusiastic!"},
    "technical": {"name": "Technical", "emoji": "🔧", "prompt": "Technical."}
}

class DatabaseManager:
    def __init__(self, pool):
        self.pool = pool
    
    async def initialize_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS whitelist (id SERIAL PRIMARY KEY, command_name TEXT, entity_type TEXT, entity_id BIGINT, added_by BIGINT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(command_name, entity_type, entity_id))''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS permissions (id SERIAL PRIMARY KEY, command_name TEXT, entity_type TEXT, entity_id BIGINT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(command_name, entity_type, entity_id))''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, user_id BIGINT, details TEXT, severity TEXT DEFAULT 'INFO', guild_id BIGINT, case_id INTEGER)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_data (user_id BIGINT PRIMARY KEY, guild_id BIGINT, warnings INTEGER DEFAULT 0, notes TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS jail_data (user_id BIGINT PRIMARY KEY, guild_id BIGINT, original_roles BIGINT[], jailed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, jailed_by BIGINT, reason TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS mod_cases (case_id SERIAL PRIMARY KEY, guild_id BIGINT, user_id BIGINT, moderator_id BIGINT, action TEXT, reason TEXT, duration TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS invites (user_id BIGINT, guild_id BIGINT, inviter_id BIGINT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, account_created_at TIMESTAMP, is_fake BOOLEAN DEFAULT FALSE, is_rejoin BOOLEAN DEFAULT FALSE, left_at TIMESTAMP, PRIMARY KEY(user_id, guild_id, joined_at))''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS messages (user_id BIGINT, guild_id BIGINT, message_count INTEGER DEFAULT 0, last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, guild_id))''')
            logger.info("✅ Database initialized")
    
    async def log_action(self, action: str, user_id: int, details: str, severity: str = "INFO", guild_id: Optional[int] = None, case_id: Optional[int] = None):
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('INSERT INTO audit_logs (action, user_id, details, severity, guild_id, case_id) VALUES ($1, $2, $3, $4, $5, $6)', action, user_id, details, severity, guild_id, case_id)
        except: pass
    
    async def create_case(self, guild_id: int, user_id: int, moderator_id: int, action: str, reason: str, duration: str = None) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('INSERT INTO mod_cases (guild_id, user_id, moderator_id, action, reason, duration) VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id', guild_id, user_id, moderator_id, action, reason, duration)
            return result['case_id']
    
    async def track_invite(self, user_id: int, guild_id: int, inviter_id: int, account_created: datetime, is_rejoin: bool):
        account_age_days = (datetime.utcnow() - account_created).days
        is_fake = account_age_days < config.FAKE_INVITE_DAYS
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO invites (user_id, guild_id, inviter_id, account_created_at, is_fake, is_rejoin) VALUES ($1, $2, $3, $4, $5, $6)', user_id, guild_id, inviter_id, account_created, is_fake, is_rejoin)
    
    async def mark_left(self, user_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE invites SET left_at = CURRENT_TIMESTAMP WHERE user_id = $1 AND guild_id = $2 AND left_at IS NULL', user_id, guild_id)
    
    async def check_rejoin(self, user_id: int, guild_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT COUNT(*) as count FROM invites WHERE user_id = $1 AND guild_id = $2', user_id, guild_id)
            return result['count'] > 0 if result else False
    
    async def get_invites(self, inviter_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''SELECT COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) as total, COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) as real, COUNT(*) FILTER (WHERE left_at IS NOT NULL) as left, COUNT(*) FILTER (WHERE is_fake = TRUE) as fake, COUNT(*) FILTER (WHERE is_rejoin = TRUE) as rejoin FROM invites WHERE inviter_id = $1 AND guild_id = $2''', inviter_id, guild_id)
            return {'total': result['real'] or 0, 'real': result['real'] or 0, 'left': result['left'] or 0, 'fake': result['fake'] or 0, 'rejoin': result['rejoin'] or 0}
    
    async def get_invited_users(self, inviter_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT user_id, joined_at, is_fake, is_rejoin, left_at FROM invites WHERE inviter_id = $1 AND guild_id = $2 ORDER BY joined_at DESC', inviter_id, guild_id)
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''SELECT inviter_id, COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) as real FROM invites WHERE guild_id = $1 GROUP BY inviter_id HAVING COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) > 0 ORDER BY real DESC LIMIT $2''', guild_id, limit)
    
    async def reset_invites_user(self, inviter_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM invites WHERE inviter_id = $1 AND guild_id = $2', inviter_id, guild_id)
    
    async def reset_invites_all(self, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM invites WHERE guild_id = $1', guild_id)
    
    async def track_message(self, user_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('''INSERT INTO messages (user_id, guild_id, message_count, last_message_at) VALUES ($1, $2, 1, CURRENT_TIMESTAMP) ON CONFLICT (user_id, guild_id) DO UPDATE SET message_count = messages.message_count + 1, last_message_at = CURRENT_TIMESTAMP''', user_id, guild_id)
    
    async def get_messages(self, user_id: int, guild_id: int) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT message_count FROM messages WHERE user_id = $1 AND guild_id = $2', user_id, guild_id)
            return result['message_count'] if result else 0

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == config.OWNER_ID
    return commands.check(predicate)

def is_staff(member: discord.Member) -> bool:
    return member.id == config.OWNER_ID or any(role.id == config.STAFF_ROLE_ID for role in member.roles)

async def send_embed(ctx, title: str, description: str, color: discord.Color = discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

async def log_to_channel(guild, title: str, description: str, color: discord.Color = discord.Color.blue()):
    if not config.LOG_CHANNEL_ID:
        return
    try:
        channel = guild.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
            await channel.send(embed=embed)
    except: pass

def parse_time(time_str: str) -> Optional[timedelta]:
    if not time_str: return None
    match = re.match(r'^(\d+)([smhd])$', time_str.lower())
    if not match: return None
    amount, unit = int(match.group(1)), match.group(2)
    units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    return timedelta(**{units[unit]: amount})

def format_time(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    if seconds < 60: return f"{seconds}s"
    elif seconds < 3600: return f"{seconds//60}m"
    elif seconds < 86400: return f"{seconds//3600}h"
    else: return f"{seconds//86400}d"

async def call_claude_api(messages, personality):
    """FIXED - WORKS WITH ANY ANTHROPIC VERSION!"""
    try:
        import anthropic
        if not config.ANTHROPIC_KEY: return "⚠️ AI not configured!"
        
        # Try new version first, fallback to old
        try:
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
        except TypeError:
            # Old version - use different method
            import anthropic as old_anthropic
            old_anthropic.api_key = config.ANTHROPIC_KEY
            client = old_anthropic
        
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        if len(messages) > 20: messages = messages[-20:]
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.7,
            system=p["prompt"],
            messages=messages
        )
        
        return response.content[0].text
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return f"❌ AI Error: {str(e)[:100]}"

def format_msg(template: str, user: discord.Member, inviter: Optional[discord.Member] = None, count: int = 0, invite_count: int = 0) -> str:
    return template.replace("{user}", user.mention).replace("{username}", user.name).replace("{servername}", user.guild.name).replace("{count}", str(count)).replace("{inviter}", inviter.mention if inviter else "Unknown").replace("{invites}", str(invite_count))


# ==================== PART 2 OF 5 - EVENTS & OWNER CONFIG ====================
# Events, Anti-Nuke (5 channels in 15s), Anti-Spam, Owner Commands
# PASTE AFTER PART 1

@bot.event
async def on_ready():
    global db_pool, db_manager, invite_tracker
    try:
        db_pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=10)
        db_manager = DatabaseManager(db_pool)
        await db_manager.initialize_tables()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_tracker[guild.id] = {invite.code: invite for invite in invites}
        except:
            invite_tracker[guild.id] = {}
    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{config.PREFIX}help"), status=discord.Status.online)
    logger.info(f"🚀 Bot Ready | Prefix: {config.PREFIX} | Servers: {len(bot.guilds)}")

@bot.event
async def on_member_join(member):
    # Track who added bots
    if member.bot and antinuke_config.get("enabled"):
        try:
            async for entry in member.guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    antinuke_config["bot_adders"][member.id] = entry.user.id
                    break
        except: pass
    
    # Invite tracking
    inviter = None
    try:
        new_invites = {invite.code: invite for invite in await member.guild.invites()}
        old_invites = invite_tracker.get(member.guild.id, {})
        for code, new_invite in new_invites.items():
            old_invite = old_invites.get(code)
            if old_invite and new_invite.uses > old_invite.uses:
                inviter = new_invite.inviter
                break
        invite_tracker[member.guild.id] = new_invites
        if inviter:
            is_rejoin = await db_manager.check_rejoin(member.id, member.guild.id)
            await db_manager.track_invite(member.id, member.guild.id, inviter.id, member.created_at, is_rejoin)
            stats = await db_manager.get_invites(inviter.id, member.guild.id)
            if config.INVITE_LOG_ENABLED and config.INVITE_CHANNEL_ID:
                channel = member.guild.get_channel(config.INVITE_CHANNEL_ID)
                if channel:
                    await channel.send(format_msg(config.INVITE_MSG, member, inviter, invite_count=stats['total']))
    except: pass
    
    # Verification
    if config.VERIFICATION_ENABLED and config.UNVERIFIED_ROLE_ID:
        try:
            role = member.guild.get_role(config.UNVERIFIED_ROLE_ID)
            if role: await member.add_roles(role)
        except: pass
    
    # Anti-alt
    if antialt_config.get("enabled") and not is_staff(member):
        age = (datetime.utcnow() - member.created_at).days
        if age < antialt_config.get("min_age_days", 7):
            try:
                action = antialt_config.get("action", "kick")
                if action == "kick": await member.kick(reason=f"Alt: {age}d")
                elif action == "ban": await member.ban(reason=f"Alt: {age}d")
                return
            except: pass
    
    # Anti-raid
    if antiraid_config.get("enabled"):
        antiraid_config["joins"][member.guild.id].append(datetime.utcnow())
        antiraid_config["joins"][member.guild.id] = [t for t in antiraid_config["joins"][member.guild.id] if (datetime.utcnow() - t).total_seconds() < 10]
        threshold = {"low": 10, "medium": 7, "high": 5}.get(antiraid_config.get("sensitivity", "medium"), 7)
        if len(antiraid_config["joins"][member.guild.id]) >= threshold:
            try: await member.kick(reason="Raid"); return
            except: pass
    
    # Welcome
    if config.WELCOME_ENABLED and config.WELCOME_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
            if channel: await channel.send(format_msg(config.WELCOME_MSG, member, count=member.guild.member_count))
        except: pass

@bot.event
async def on_member_remove(member):
    try: await db_manager.mark_left(member.id, member.guild.id)
    except: pass
    if config.LEAVE_ENABLED and config.LEAVE_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.LEAVE_CHANNEL_ID)
            if channel: await channel.send(format_msg(config.LEAVE_MSG, member, count=member.guild.member_count))
        except: pass

@bot.event
async def on_guild_channel_delete(channel):
    """ANTI-NUKE: 5 channels in 15 seconds = BAN"""
    if not antinuke_config.get("enabled"): return
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                if deleter.id in antinuke_config.get("whitelist", []) or is_staff(deleter): return
                
                antinuke_config["actions"]["channel_delete"][deleter.id].append(datetime.utcnow())
                antinuke_config["actions"]["channel_delete"][deleter.id] = [t for t in antinuke_config["actions"]["channel_delete"][deleter.id] if (datetime.utcnow() - t).total_seconds() < 15]
                
                if len(antinuke_config["actions"]["channel_delete"][deleter.id]) >= 5:
                    await channel.guild.ban(deleter, reason="🛡️ NUKE: 5 channels deleted in 15s")
                    if deleter.bot:
                        adder_id = antinuke_config["bot_adders"].get(deleter.id)
                        if adder_id:
                            adder = channel.guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await channel.guild.ban(adder, reason=f"🛡️ Added nuke bot: {deleter.name}")
                    antinuke_config["actions"]["channel_delete"][deleter.id] = []
                break
    except: pass

@bot.event
async def on_guild_role_delete(role):
    """ANTI-NUKE: 5 roles in 15 seconds = BAN"""
    if not antinuke_config.get("enabled"): return
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                if deleter.id in antinuke_config.get("whitelist", []) or is_staff(deleter): return
                
                antinuke_config["actions"]["role_delete"][deleter.id].append(datetime.utcnow())
                antinuke_config["actions"]["role_delete"][deleter.id] = [t for t in antinuke_config["actions"]["role_delete"][deleter.id] if (datetime.utcnow() - t).total_seconds() < 15]
                
                if len(antinuke_config["actions"]["role_delete"][deleter.id]) >= 5:
                    await role.guild.ban(deleter, reason="🛡️ NUKE: 5 roles deleted in 15s")
                    if deleter.bot:
                        adder_id = antinuke_config["bot_adders"].get(deleter.id)
                        if adder_id:
                            adder = role.guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await role.guild.ban(adder, reason=f"🛡️ Added nuke bot: {deleter.name}")
                    antinuke_config["actions"]["role_delete"][deleter.id] = []
                break
    except: pass

@bot.event
async def on_member_ban(guild, user):
    """ANTI-NUKE: 5 bans in 60 seconds = BAN"""
    if not antinuke_config.get("enabled"): return
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                banner = entry.user
                if banner.id in antinuke_config.get("whitelist", []) or is_staff(banner): return
                
                antinuke_config["actions"]["ban"][banner.id].append(datetime.utcnow())
                antinuke_config["actions"]["ban"][banner.id] = [t for t in antinuke_config["actions"]["ban"][banner.id] if (datetime.utcnow() - t).total_seconds() < 60]
                
                if len(antinuke_config["actions"]["ban"][banner.id]) >= 5:
                    await guild.ban(banner, reason="🛡️ NUKE: 5 bans in 60s")
                    if banner.bot:
                        adder_id = antinuke_config["bot_adders"].get(banner.id)
                        if adder_id:
                            adder = guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await guild.ban(adder, reason=f"🛡️ Added nuke bot: {banner.name}")
                    antinuke_config["actions"]["ban"][banner.id] = []
                break
    except: pass

@bot.event
async def on_message(message):
    if message.author.bot: return
    try: await db_manager.track_message(message.author.id, message.guild.id)
    except: pass
    
    # Anti-spam
    if antispam_config.get("enabled") and message.channel.id not in antispam_config.get("ignored_channels", []):
        if not is_staff(message.author) and not any(r.id in antispam_config.get("whitelisted_roles", []) for r in message.author.roles):
            antispam_config["user_messages"][message.author.id].append(datetime.utcnow())
            antispam_config["user_messages"][message.author.id] = [t for t in antispam_config["user_messages"][message.author.id] if (datetime.utcnow() - t).total_seconds() < antispam_config.get("timeframe", 3)]
            
            if len(antispam_config["user_messages"][message.author.id]) >= antispam_config.get("max_messages", 5):
                try:
                    action = antispam_config.get("action", "mute")
                    if action == "mute":
                        role = discord.utils.get(message.guild.roles, name="Muted")
                        if not role:
                            role = await message.guild.create_role(name="Muted")
                            for ch in message.guild.channels:
                                await ch.set_permissions(role, send_messages=False, speak=False)
                        await message.author.add_roles(role)
                        await message.channel.send(f"🛡️ {message.author.mention} muted for spam!", delete_after=10)
                    elif action == "kick": await message.author.kick(reason="Spam")
                    elif action == "ban": await message.author.ban(reason="Spam")
                    antispam_config["user_messages"][message.author.id] = []
                except: pass
    
    # AI auto-response
    if ai_config.get("enabled") and ai_config.get("channel_id") == message.channel.id:
        if any(w in message.content.lower() for w in ["invite", "invites", "leaderboard"]):
            try:
                if "leaderboard" in message.content.lower():
                    lb = await db_manager.get_leaderboard(message.guild.id, 5)
                    resp = "📊 **Top Inviters:**\n" + "\n".join([f"{i}. {message.guild.get_member(r['inviter_id']).mention if message.guild.get_member(r['inviter_id']) else 'Unknown'}: **{r['real']}**" for i, r in enumerate(lb, 1)])
                    await message.reply(resp, mention_author=False); return
                else:
                    stats = await db_manager.get_invites(message.author.id, message.guild.id)
                    users = await db_manager.get_invited_users(message.author.id, message.guild.id)
                    resp = f"📊 **Stats:** Total: **{stats['total']}** | Real: **{stats['real']}** | Left: {stats['left']} | Fake: {stats['fake']} | Rejoin: {stats['rejoin']}\n\n"
                    if users:
                        resp += "**Invited:**\n"
                        for i, row in enumerate(users[:10], 1):
                            m = message.guild.get_member(row['user_id'])
                            if m:
                                verified = "✅" if config.VERIFIED_ROLE_ID and any(r.id == config.VERIFIED_ROLE_ID for r in m.roles) else "❌"
                                itype = "FAKE" if row['is_fake'] else "REJOIN" if row['is_rejoin'] else "LEFT" if row['left_at'] else "REAL"
                                resp += f"{i}. {m.mention} ({itype}) {verified}\n"
                    await message.reply(resp, mention_author=False); return
            except: pass
        
        async with message.channel.typing():
            conv = ai_conversations[message.author.id]
            conv["messages"].append({"role": "user", "content": message.content})
            if len(conv["messages"]) > 30: conv["messages"] = conv["messages"][-30:]
            try:
                resp = await call_claude_api(conv["messages"], conv["personality"])
                conv["messages"].append({"role": "assistant", "content": resp})
                await message.reply(resp, mention_author=False)
            except: pass
    
    # Anti-link
    if antilink_config.get("enabled") and not is_staff(message.author):
        if not (any(r.id in antilink_config.get("bypass_roles", []) for r in message.author.roles) or message.author.id in antilink_config.get("bypass_users", [])):
            if re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content):
                try: await message.delete(); await message.channel.send(f"{message.author.mention} Links not allowed!", delete_after=5)
                except: pass
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        cmd = ctx.message.content.split()[0][len(config.PREFIX):]
        matches = get_close_matches(cmd, [c.name for c in bot.commands] + [a for c in bot.commands for a in c.aliases], n=3, cutoff=0.6)
        if matches:
            await send_embed(ctx, "❌ Unknown Command", f"Did you mean: " + ", ".join([f"`{config.PREFIX}{m}`" for m in matches]), discord.Color.red())
        return
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "❌ No Permission", "Missing permissions!", discord.Color.red())
    elif isinstance(error, commands.CheckFailure):
        await send_embed(ctx, "🔒 Access Denied", "You can't use this!", discord.Color.red())

@bot.group(name="config", invoke_without_command=True)
@is_owner()
async def botconfig(ctx):
    await send_embed(ctx, "⚙️ Owner Config", f"`{config.PREFIX}config prefix/owner/staff/logchannel/view/save/reset`", discord.Color.gold())

@botconfig.command(name="prefix")
async def cfg_prefix(ctx, new: str):
    config.PREFIX = new
    config.save_config()
    await send_embed(ctx, "✅ Prefix Changed", f"New: `{new}`", discord.Color.green())

@botconfig.command(name="owner")
async def cfg_owner(ctx, owner_id: int):
    config.OWNER_ID = owner_id
    config.save_config()
    await send_embed(ctx, "✅ Owner Changed", f"New: `{owner_id}`", discord.Color.green())

@botconfig.command(name="staff")
async def cfg_staff(ctx, role_id: int):
    config.STAFF_ROLE_ID = role_id
    config.save_config()
    await send_embed(ctx, "✅ Staff Role", f"New: `{role_id}`", discord.Color.green())

@botconfig.command(name="logchannel")
async def cfg_log(ctx, channel: discord.TextChannel):
    config.LOG_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Log Channel", f"Set: {channel.mention}", discord.Color.green())

@botconfig.command(name="view")
async def cfg_view(ctx):
    embed = discord.Embed(title="⚙️ Config", color=discord.Color.blue())
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    embed.add_field(name="Owner", value=config.OWNER_ID, inline=True)
    embed.add_field(name="Staff", value=config.STAFF_ROLE_ID, inline=True)
    await ctx.send(embed=embed)

@botconfig.command(name="save")
async def cfg_save(ctx):
    config.save_config()
    await send_embed(ctx, "✅ Saved", "Config saved!", discord.Color.green())

@botconfig.command(name="reset")
async def cfg_reset(ctx):
    config.PREFIX = "f!"
    config.save_config()
    await send_embed(ctx, "✅ Reset", "Config reset!", discord.Color.green())



# ==================== PART 3 OF 5 - MODERATION, LOGGING, JAIL, ROLES ====================
# Logging, Moderation, Jail System, Role Commands
# PASTE AFTER PART 2

@bot.command(name="setlog")
@commands.has_permissions(administrator=True)
async def setlog_cmd(ctx, channel: discord.TextChannel):
    config.LOG_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Log Channel", f"Set to {channel.mention}", discord.Color.green())

@bot.group(name="logs", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def logs_cmd(ctx):
    await send_embed(ctx, "📊 Logs", f"`{config.PREFIX}logs view/user`", discord.Color.blue())

@logs_cmd.command(name="view")
async def logs_view(ctx):
    await send_embed(ctx, "📊 Logs", "View recent logs (last 50)", discord.Color.blue())

@logs_cmd.command(name="user")
async def logs_user(ctx, user: discord.Member):
    await send_embed(ctx, "📊 User Logs", f"Logs for {user.mention}", discord.Color.blue())

@bot.command(name="cases")
@commands.has_permissions(manage_guild=True)
async def cases_cmd(ctx, user: discord.Member):
    await send_embed(ctx, "📋 Cases", f"Cases for {user.mention}", discord.Color.blue())

@bot.command(name="case")
@commands.has_permissions(manage_guild=True)
async def case_cmd(ctx, case_id: int):
    await send_embed(ctx, "📋 Case", f"Case #{case_id}", discord.Color.blue())

@bot.command(name="modstats")
@commands.has_permissions(manage_guild=True)
async def modstats_cmd(ctx, mod: discord.Member = None):
    target = mod or ctx.author
    await send_embed(ctx, "📊 Mod Stats", f"Stats for {target.mention}", discord.Color.blue())

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_staff(member):
        return await send_embed(ctx, "❌ Protected", "Can't kick staff!", discord.Color.red())
    try:
        await member.kick(reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "KICK", reason)
        await log_to_channel(ctx.guild, "👢 Kick", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
        await send_embed(ctx, "✅ Kicked", f"{member.mention} kicked!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, target: Union[discord.Member, int], *, reason: str = "No reason"):
    if isinstance(target, discord.Member):
        if is_staff(target):
            return await send_embed(ctx, "❌ Protected", "Can't ban staff!", discord.Color.red())
        user_id = target.id
        await target.ban(reason=reason)
    else:
        user_id = target
        await ctx.guild.ban(discord.Object(id=target), reason=reason)
    
    case_id = await db_manager.create_case(ctx.guild.id, user_id, ctx.author.id, "BAN", reason)
    await log_to_channel(ctx.guild, "🔨 Ban", f"**User:** <@{user_id}>\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.red())
    await send_embed(ctx, "✅ Banned", f"<@{user_id}> banned!", discord.Color.green())

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_cmd(ctx, user_id: int, *, reason: str = "No reason"):
    try:
        await ctx.guild.unban(discord.Object(id=user_id), reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, user_id, ctx.author.id, "UNBAN", reason)
        await log_to_channel(ctx.guild, "✅ Unban", f"**User:** <@{user_id}>\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.green())
        await send_embed(ctx, "✅ Unbanned", f"<@{user_id}> unbanned!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, member: discord.Member, time: str = None, *, reason: str = "No reason"):
    if is_staff(member):
        return await send_embed(ctx, "❌ Protected", "Can't mute staff!", discord.Color.red())
    
    duration = parse_time(time) if time else timedelta(hours=1)
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        
        await member.add_roles(muted_role)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "MUTE", reason, format_time(duration))
        await log_to_channel(ctx.guild, "🔇 Mute", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Duration:** {format_time(duration)}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
        await send_embed(ctx, "✅ Muted", f"{member.mention} muted for {format_time(duration)}!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if muted_role:
            await member.remove_roles(muted_role)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "UNMUTE", reason)
        await log_to_channel(ctx.guild, "🔊 Unmute", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.green())
        await send_embed(ctx, "✅ Unmuted", f"{member.mention} unmuted!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, time: str, *, reason: str = "No reason"):
    if is_staff(member):
        return await send_embed(ctx, "❌ Protected", "Can't timeout staff!", discord.Color.red())
    
    duration = parse_time(time)
    if not duration:
        return await send_embed(ctx, "❌ Invalid Time", "Use: 10m, 1h, 1d", discord.Color.red())
    
    try:
        await member.timeout(duration, reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "TIMEOUT", reason, format_time(duration))
        await log_to_channel(ctx.guild, "⏱️ Timeout", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Duration:** {format_time(duration)}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
        await send_embed(ctx, "✅ Timeout", f"{member.mention} timed out for {format_time(duration)}!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    try:
        await member.timeout(None, reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "UNTIMEOUT", reason)
        await log_to_channel(ctx.guild, "✅ Untimeout", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.green())
        await send_embed(ctx, "✅ Untimeout", f"{member.mention} timeout removed!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_staff(member):
        return await send_embed(ctx, "❌ Protected", "Can't warn staff!", discord.Color.red())
    
    case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "WARN", reason)
    await log_to_channel(ctx.guild, "⚠️ Warn", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
    await send_embed(ctx, "✅ Warned", f"{member.mention} warned!", discord.Color.green())
    try:
        await member.send(f"⚠️ You were warned in **{ctx.guild.name}**\n**Reason:** {reason}")
    except: pass

@bot.command(name="warnings")
@commands.has_permissions(manage_messages=True)
async def warnings_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    await send_embed(ctx, "⚠️ Warnings", f"{target.mention} has warnings", discord.Color.orange())

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clearwarns_cmd(ctx, member: discord.Member):
    await send_embed(ctx, "✅ Cleared", f"Warnings cleared for {member.mention}", discord.Color.green())

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def purge_cmd(ctx, amount: int = None, member: discord.Member = None):
    if amount is None:
        return await send_embed(ctx, "❌ Missing Amount", f"Usage: `{config.PREFIX}purge <amount> [@user]`", discord.Color.red())
    
    try:
        if member:
            deleted = await ctx.channel.purge(limit=amount+1, check=lambda m: m.author == member)
        else:
            deleted = await ctx.channel.purge(limit=amount+1)
        
        msg = await ctx.send(f"✅ Deleted {len(deleted)-1} messages", delete_after=5)
        await log_to_channel(ctx.guild, "🗑️ Purge", f"**Channel:** {ctx.channel.mention}\n**Mod:** {ctx.author.mention}\n**Amount:** {len(deleted)-1}", discord.Color.blue())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await log_to_channel(ctx.guild, "🔒 Lock", f"**Channel:** {channel.mention}\n**Mod:** {ctx.author.mention}", discord.Color.orange())
        await send_embed(ctx, "🔒 Locked", f"{channel.mention} locked!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await log_to_channel(ctx.guild, "🔓 Unlock", f"**Channel:** {channel.mention}\n**Mod:** {ctx.author.mention}", discord.Color.green())
        await send_embed(ctx, "🔓 Unlocked", f"{channel.mention} unlocked!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode_cmd(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    try:
        await channel.edit(slowmode_delay=seconds)
        await log_to_channel(ctx.guild, "⏱️ Slowmode", f"**Channel:** {channel.mention}\n**Mod:** {ctx.author.mention}\n**Delay:** {seconds}s", discord.Color.blue())
        await send_embed(ctx, "✅ Slowmode", f"{channel.mention} slowmode: {seconds}s", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="jail")
@commands.has_permissions(administrator=True)
async def jail_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_staff(member):
        return await send_embed(ctx, "❌ Protected", "Can't jail staff!", discord.Color.red())
    
    try:
        jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
        if not jailed_role:
            jailed_role = await ctx.guild.create_role(name="Jailed", color=discord.Color.dark_gray())
            for channel in ctx.guild.channels:
                await channel.set_permissions(jailed_role, send_messages=False, speak=False, view_channel=False)
        
        original_roles = [role.id for role in member.roles if role != ctx.guild.default_role]
        await member.remove_roles(*member.roles[1:])
        await member.add_roles(jailed_role)
        
        async with db_manager.pool.acquire() as conn:
            await conn.execute('INSERT INTO jail_data (user_id, guild_id, original_roles, jailed_by, reason) VALUES ($1, $2, $3, $4, $5)', member.id, ctx.guild.id, original_roles, ctx.author.id, reason)
        
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "JAIL", reason)
        await log_to_channel(ctx.guild, "🚔 Jail", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.dark_red())
        await send_embed(ctx, "✅ Jailed", f"{member.mention} jailed!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="unjail")
@commands.has_permissions(administrator=True)
async def unjail_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    try:
        async with db_manager.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT original_roles FROM jail_data WHERE user_id = $1 AND guild_id = $2', member.id, ctx.guild.id)
            if not result:
                return await send_embed(ctx, "❌ Not Jailed", f"{member.mention} is not jailed!", discord.Color.red())
            
            jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
            if jailed_role:
                await member.remove_roles(jailed_role)
            
            for role_id in result['original_roles']:
                role = ctx.guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
            
            await conn.execute('DELETE FROM jail_data WHERE user_id = $1 AND guild_id = $2', member.id, ctx.guild.id)
        
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "UNJAIL", reason)
        await log_to_channel(ctx.guild, "✅ Unjail", f"**User:** {member.mention}\n**Mod:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.green())
        await send_embed(ctx, "✅ Unjailed", f"{member.mention} unjailed!", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.command(name="jailed")
@commands.has_permissions(administrator=True)
async def jailed_cmd(ctx):
    try:
        async with db_manager.pool.acquire() as conn:
            results = await conn.fetch('SELECT user_id, jailed_at, reason FROM jail_data WHERE guild_id = $1', ctx.guild.id)
        
        if not results:
            return await send_embed(ctx, "📋 Jailed Users", "No one is jailed!", discord.Color.blue())
        
        embed = discord.Embed(title="🚔 Jailed Users", color=discord.Color.dark_red())
        desc = ""
        for row in results:
            member = ctx.guild.get_member(row['user_id'])
            name = member.mention if member else f"<@{row['user_id']}>"
            desc += f"{name} - *{row['reason']}*\n"
        embed.description = desc
        await ctx.send(embed=embed)
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@bot.group(name="role", invoke_without_command=True)
@commands.has_permissions(manage_roles=True)
async def role_cmd(ctx):
    await send_embed(ctx, "🎭 Role", f"`{config.PREFIX}role add/remove @user @role`", discord.Color.blue())

@role_cmd.command(name="add")
async def role_add(ctx, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await send_embed(ctx, "✅ Role Added", f"Added {role.mention} to {member.mention}", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())

@role_cmd.command(name="remove")
async def role_remove(ctx, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await send_embed(ctx, "✅ Role Removed", f"Removed {role.mention} from {member.mention}", discord.Color.green())
    except Exception as e:
        await send_embed(ctx, "❌ Error", str(e), discord.Color.red())



# ==================== PART 4 OF 5 - AI, PERMS, WHITELIST, ANTI-SYSTEMS, INVITES ====================
# AI Commands, Permission System, Whitelist, All Anti-Systems, Invite Tracker
# PASTE AFTER PART 3

# AI COMMANDS
@bot.command(name="ai", aliases=["chat", "ask", "claude"])
async def ai_cmd(ctx, *, message: str):
    async with ctx.typing():
        conv = ai_conversations[ctx.author.id]
        conv["messages"].append({"role": "user", "content": message})
        if len(conv["messages"]) > 30: conv["messages"] = conv["messages"][-30:]
        resp = await call_claude_api(conv["messages"], conv["personality"])
        conv["messages"].append({"role": "assistant", "content": resp})
        await ctx.reply(resp, mention_author=False)

@bot.command(name="aimood", aliases=["personality", "setmood"])
async def aimood_cmd(ctx, mood: str):
    if mood.lower() not in AI_PERSONALITIES:
        return await send_embed(ctx, "❌ Invalid", "Available: " + ", ".join(AI_PERSONALITIES.keys()), discord.Color.red())
    ai_conversations[ctx.author.id]["personality"] = mood.lower()
    p = AI_PERSONALITIES[mood.lower()]
    await send_embed(ctx, f"{p['emoji']} Mood Changed", f"AI is now **{p['name']}**!", discord.Color.green())

@bot.command(name="personalities", aliases=["moods"])
async def personalities_cmd(ctx):
    embed = discord.Embed(title="🎭 AI Personalities", color=discord.Color.blue())
    desc = "\n".join([f"{p['emoji']} **{p['name']}** - `{k}`" for k, p in AI_PERSONALITIES.items()])
    embed.description = desc
    await ctx.send(embed=embed)

@bot.command(name="aiclear", aliases=["chatclear"])
async def aiclear_cmd(ctx):
    ai_conversations[ctx.author.id]["messages"] = []
    await send_embed(ctx, "✅ Cleared", "Chat history reset!", discord.Color.green())

@bot.command(name="aichannel")
@is_owner()
async def aichannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None or channel.mention == "disable":
        ai_config["enabled"] = False
        ai_config["channel_id"] = None
        return await send_embed(ctx, "❌ Disabled", "Auto-response off!", discord.Color.red())
    ai_config["channel_id"] = channel.id
    ai_config["enabled"] = True
    await send_embed(ctx, "✅ AI Channel", f"Auto-response in {channel.mention}!", discord.Color.green())

# PERMISSION SYSTEM
@bot.group(name="perm", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def perm_cmd(ctx):
    await send_embed(ctx, "🔐 Permissions", f"`{config.PREFIX}perm set/remove/list/reset`", discord.Color.blue())

@perm_cmd.command(name="set")
async def perm_set(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command not in permission_data["commands"]:
        permission_data["commands"][command] = {"roles": [], "users": []}
    etype = "roles" if isinstance(target, discord.Role) else "users"
    if target.id not in permission_data["commands"][command][etype]:
        permission_data["commands"][command][etype].append(target.id)
    await send_embed(ctx, "✅ Permission Set", f"{target.mention} can use `{command}`!", discord.Color.green())

@perm_cmd.command(name="remove")
async def perm_remove(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command in permission_data["commands"]:
        etype = "roles" if isinstance(target, discord.Role) else "users"
        if target.id in permission_data["commands"][command][etype]:
            permission_data["commands"][command][etype].remove(target.id)
    await send_embed(ctx, "✅ Permission Removed", f"{target.mention} removed from `{command}`!", discord.Color.green())

@perm_cmd.command(name="list")
async def perm_list(ctx, command: str = None):
    if command:
        if command not in permission_data["commands"]:
            return await send_embed(ctx, "❌ No Permissions", f"`{command}` has none!", discord.Color.red())
        embed = discord.Embed(title=f"🔐 Permissions: {command}", color=discord.Color.blue())
        roles = [f"<@&{r}>" for r in permission_data["commands"][command].get("roles", [])]
        users = [f"<@{u}>" for u in permission_data["commands"][command].get("users", [])]
        embed.add_field(name="Roles", value=", ".join(roles) or "None", inline=False)
        embed.add_field(name="Users", value=", ".join(users) or "None", inline=False)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🔐 All Permissions", color=discord.Color.blue())
        desc = "\n".join([f"**{cmd}**: {len(data.get('roles', []))} roles, {len(data.get('users', []))} users" for cmd, data in permission_data["commands"].items()]) or "None"
        embed.description = desc
        await ctx.send(embed=embed)

@perm_cmd.command(name="reset")
async def perm_reset(ctx, command: str):
    if command in permission_data["commands"]:
        del permission_data["commands"][command]
    await send_embed(ctx, "✅ Reset", f"`{command}` permissions cleared!", discord.Color.green())

# WHITELIST SYSTEM
@bot.group(name="whitelist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def whitelist_cmd(ctx):
    await send_embed(ctx, "🔐 Whitelist", f"`{config.PREFIX}whitelist add/addall/remove/removeall/list/clear`", discord.Color.blue())

@whitelist_cmd.command(name="add")
async def wl_add(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command not in whitelist_data["commands"]:
        whitelist_data["commands"][command] = {"roles": [], "users": []}
    etype = "roles" if isinstance(target, discord.Role) else "users"
    if target.id not in whitelist_data["commands"][command][etype]:
        whitelist_data["commands"][command][etype].append(target.id)
    await send_embed(ctx, "✅ Whitelist Added", f"{target.mention} can use `{command}`!", discord.Color.green())

@whitelist_cmd.command(name="addall")
async def wl_addall(ctx, target: Union[discord.Role, discord.Member]):
    for cmd in [c.name for c in bot.commands]:
        if cmd not in whitelist_data["commands"]:
            whitelist_data["commands"][cmd] = {"roles": [], "users": []}
        etype = "roles" if isinstance(target, discord.Role) else "users"
        if target.id not in whitelist_data["commands"][cmd][etype]:
            whitelist_data["commands"][cmd][etype].append(target.id)
    await send_embed(ctx, "✅ Full Access", f"{target.mention} can use ALL commands!", discord.Color.green())

@whitelist_cmd.command(name="remove")
async def wl_remove(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command in whitelist_data["commands"]:
        etype = "roles" if isinstance(target, discord.Role) else "users"
        if target.id in whitelist_data["commands"][command][etype]:
            whitelist_data["commands"][command][etype].remove(target.id)
    await send_embed(ctx, "✅ Whitelist Removed", f"{target.mention} removed!", discord.Color.green())

@whitelist_cmd.command(name="removeall")
async def wl_removeall(ctx, target: Union[discord.Role, discord.Member]):
    for cmd in whitelist_data["commands"]:
        etype = "roles" if isinstance(target, discord.Role) else "users"
        if target.id in whitelist_data["commands"][cmd][etype]:
            whitelist_data["commands"][cmd][etype].remove(target.id)
    await send_embed(ctx, "✅ All Access Removed", f"{target.mention} removed from all!", discord.Color.green())

@whitelist_cmd.command(name="list")
async def wl_list(ctx, command: str = None):
    if command:
        if command not in whitelist_data["commands"]:
            return await send_embed(ctx, "❌ No Whitelist", f"`{command}` has none!", discord.Color.red())
        embed = discord.Embed(title=f"🔐 Whitelist: {command}", color=discord.Color.blue())
        roles = [f"<@&{r}>" for r in whitelist_data["commands"][command].get("roles", [])]
        users = [f"<@{u}>" for u in whitelist_data["commands"][command].get("users", [])]
        embed.add_field(name="Roles", value=", ".join(roles) or "None", inline=False)
        embed.add_field(name="Users", value=", ".join(users) or "None", inline=False)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🔐 All Whitelists", color=discord.Color.blue())
        desc = "\n".join([f"**{cmd}**: {len(data.get('roles', []))} roles, {len(data.get('users', []))} users" for cmd, data in whitelist_data["commands"].items()]) or "None"
        embed.description = desc
        await ctx.send(embed=embed)

@whitelist_cmd.command(name="clear")
async def wl_clear(ctx, command: str):
    if command in whitelist_data["commands"]:
        del whitelist_data["commands"][command]
    await send_embed(ctx, "✅ Cleared", f"`{command}` whitelist cleared!", discord.Color.green())

# ANTI-ALT
@bot.group(name="antialt", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antialt_cmd(ctx):
    await send_embed(ctx, "🔰 Anti-Alt", f"`{config.PREFIX}antialt enable/disable/minage/action/status`", discord.Color.blue())

@antialt_cmd.command(name="enable")
async def antialt_enable(ctx):
    antialt_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Checking account age!", discord.Color.green())

@antialt_cmd.command(name="disable")
async def antialt_disable(ctx):
    antialt_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Not checking!", discord.Color.red())

@antialt_cmd.command(name="minage")
async def antialt_minage(ctx, days: int):
    antialt_config["min_age_days"] = days
    await send_embed(ctx, "✅ Min Age", f"Accounts must be **{days}** days old!", discord.Color.green())

@antialt_cmd.command(name="action")
async def antialt_action(ctx, action: str):
    if action.lower() not in ["kick", "ban", "none"]:
        return await send_embed(ctx, "❌ Invalid", "Use: kick, ban, or none", discord.Color.red())
    antialt_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Alts will be **{action}**ed!", discord.Color.green())

@antialt_cmd.command(name="status")
async def antialt_status(ctx):
    embed = discord.Embed(title="🔰 Anti-Alt Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if antialt_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Min Age", value=f"{antialt_config.get('min_age_days', 7)}d", inline=True)
    embed.add_field(name="Action", value=antialt_config.get("action", "kick"), inline=True)
    await ctx.send(embed=embed)

# ANTI-RAID
@bot.group(name="antiraid", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antiraid_cmd(ctx):
    await send_embed(ctx, "🛡️ Anti-Raid", f"`{config.PREFIX}antiraid enable/disable/sensitivity/status`", discord.Color.blue())

@antiraid_cmd.command(name="enable")
async def antiraid_enable(ctx):
    antiraid_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Monitoring joins!", discord.Color.green())

@antiraid_cmd.command(name="disable")
async def antiraid_disable(ctx):
    antiraid_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Not monitoring!", discord.Color.red())

@antiraid_cmd.command(name="sensitivity")
async def antiraid_sensitivity(ctx, level: str):
    if level.lower() not in ["low", "medium", "high"]:
        return await send_embed(ctx, "❌ Invalid", "Use: low, medium, or high", discord.Color.red())
    antiraid_config["sensitivity"] = level.lower()
    thresholds = {"low": "10/10s", "medium": "7/10s", "high": "5/10s"}
    await send_embed(ctx, "✅ Sensitivity", f"**{level}**: {thresholds[level.lower()]}", discord.Color.green())

@antiraid_cmd.command(name="status")
async def antiraid_status(ctx):
    embed = discord.Embed(title="🛡️ Anti-Raid Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if antiraid_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Sensitivity", value=antiraid_config.get("sensitivity", "medium"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="lockdown")
@commands.has_permissions(administrator=True)
async def lockdown_cmd(ctx):
    for channel in ctx.guild.channels:
        try: await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except: pass
    await send_embed(ctx, "🔒 Lockdown", "Server locked!", discord.Color.red())

@bot.command(name="unlockdown")
@commands.has_permissions(administrator=True)
async def unlockdown_cmd(ctx):
    for channel in ctx.guild.channels:
        try: await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        except: pass
    await send_embed(ctx, "🔓 Unlocked", "Server unlocked!", discord.Color.green())

# ANTI-LINK (CONTINUED IN NEXT MESSAGE DUE TO LENGTH)


# ANTI-LINK
@bot.group(name="antilink", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antilink_cmd(ctx):
    await send_embed(ctx, "🔗 Anti-Link", f"`{config.PREFIX}antilink enable/disable/whitelist/bypass/status`", discord.Color.blue())

@antilink_cmd.command(name="enable")
async def antilink_enable(ctx):
    antilink_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Blocking links!", discord.Color.green())

@antilink_cmd.command(name="disable")
async def antilink_disable(ctx):
    antilink_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Links allowed!", discord.Color.red())

@antilink_cmd.command(name="whitelist")
async def antilink_whitelist(ctx, domain: str):
    if domain not in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].append(domain)
    await send_embed(ctx, "✅ Whitelisted", f"**{domain}** allowed!", discord.Color.green())

@antilink_cmd.command(name="unwhitelist")
async def antilink_unwhitelist(ctx, domain: str):
    if domain in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].remove(domain)
    await send_embed(ctx, "✅ Removed", f"**{domain}** removed!", discord.Color.green())

@antilink_cmd.group(name="bypass", invoke_without_command=True)
async def antilink_bypass(ctx):
    await send_embed(ctx, "🔗 Bypass", f"`{config.PREFIX}antilink bypass add/remove/list`", discord.Color.blue())

@antilink_bypass.command(name="add")
async def bypass_add(ctx, target: Union[discord.Role, discord.Member]):
    if isinstance(target, discord.Role):
        if target.id not in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].append(target.id)
    else:
        if target.id not in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].append(target.id)
    await send_embed(ctx, "✅ Bypass Added", f"{target.mention} can post links!", discord.Color.green())

@antilink_bypass.command(name="remove")
async def bypass_remove(ctx, target: Union[discord.Role, discord.Member]):
    if isinstance(target, discord.Role):
        if target.id in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].remove(target.id)
    else:
        if target.id in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].remove(target.id)
    await send_embed(ctx, "✅ Bypass Removed", f"{target.mention} removed!", discord.Color.green())

@antilink_bypass.command(name="list")
async def bypass_list(ctx):
    embed = discord.Embed(title="🔗 Bypasses", color=discord.Color.blue())
    roles = [f"<@&{r}>" for r in antilink_config.get("bypass_roles", [])]
    users = [f"<@{u}>" for u in antilink_config.get("bypass_users", [])]
    embed.add_field(name="Roles", value=", ".join(roles) or "None", inline=False)
    embed.add_field(name="Users", value=", ".join(users) or "None", inline=False)
    await ctx.send(embed=embed)

@antilink_cmd.command(name="status")
async def antilink_status(ctx):
    embed = discord.Embed(title="🔗 Anti-Link Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if antilink_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Whitelisted", value=", ".join(antilink_config.get("whitelist_domains", [])) or "None", inline=False)
    await ctx.send(embed=embed)

# ANTI-NUKE
@bot.group(name="antinuke", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antinuke_cmd(ctx):
    await send_embed(ctx, "🛡️ Anti-Nuke", f"`{config.PREFIX}antinuke enable/disable/whitelist/status`", discord.Color.blue())

@antinuke_cmd.command(name="enable")
async def antinuke_enable(ctx):
    antinuke_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Server protected!", discord.Color.green())

@antinuke_cmd.command(name="disable")
async def antinuke_disable(ctx):
    antinuke_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Protection off!", discord.Color.red())

@antinuke_cmd.command(name="whitelist")
async def antinuke_whitelist(ctx, user: discord.Member):
    if user.id not in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].append(user.id)
    await send_embed(ctx, "✅ Whitelisted", f"{user.mention} trusted!", discord.Color.green())

@antinuke_cmd.command(name="unwhitelist")
async def antinuke_unwhitelist(ctx, user: discord.Member):
    if user.id in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].remove(user.id)
    await send_embed(ctx, "✅ Removed", f"{user.mention} removed!", discord.Color.green())

@antinuke_cmd.command(name="status")
async def antinuke_status(ctx):
    embed = discord.Embed(title="🛡️ Anti-Nuke Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if antinuke_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Thresholds", value="5 channels/15s\n5 roles/15s\n5 bans/60s", inline=True)
    await ctx.send(embed=embed)

# ANTI-SPAM
@bot.group(name="antispam", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antispam_cmd(ctx):
    await send_embed(ctx, "🛡️ Anti-Spam", f"`{config.PREFIX}antispam enable/disable/messages/time/action/status`", discord.Color.blue())

@antispam_cmd.command(name="enable")
async def antispam_enable(ctx):
    antispam_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Monitoring spam!", discord.Color.green())

@antispam_cmd.command(name="disable")
async def antispam_disable(ctx):
    antispam_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Not monitoring!", discord.Color.red())

@antispam_cmd.command(name="messages")
async def antispam_messages(ctx, amount: int):
    antispam_config["max_messages"] = amount
    await send_embed(ctx, "✅ Max Messages", f"Max **{amount}** messages!", discord.Color.green())

@antispam_cmd.command(name="time")
async def antispam_time(ctx, seconds: int):
    antispam_config["timeframe"] = seconds
    await send_embed(ctx, "✅ Timeframe", f"**{seconds}** seconds!", discord.Color.green())

@antispam_cmd.command(name="action")
async def antispam_action(ctx, action: str):
    if action.lower() not in ["mute", "kick", "ban"]:
        return await send_embed(ctx, "❌ Invalid", "Use: mute, kick, or ban", discord.Color.red())
    antispam_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action", f"Spammers will be **{action}**ed!", discord.Color.green())

@antispam_cmd.command(name="ignore")
async def antispam_ignore(ctx, channel: discord.TextChannel):
    if channel.id not in antispam_config["ignored_channels"]:
        antispam_config["ignored_channels"].append(channel.id)
    await send_embed(ctx, "✅ Ignored", f"{channel.mention} exempt!", discord.Color.green())

@antispam_cmd.command(name="whitelist")
async def antispam_whitelist(ctx, role: discord.Role):
    if role.id not in antispam_config["whitelisted_roles"]:
        antispam_config["whitelisted_roles"].append(role.id)
    await send_embed(ctx, "✅ Whitelisted", f"{role.mention} exempt!", discord.Color.green())

@antispam_cmd.command(name="status")
async def antispam_status(ctx):
    embed = discord.Embed(title="🛡️ Anti-Spam Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if antispam_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Max Messages", value=antispam_config.get("max_messages", 5), inline=True)
    embed.add_field(name="Timeframe", value=f"{antispam_config.get('timeframe', 3)}s", inline=True)
    embed.add_field(name="Action", value=antispam_config.get("action", "mute"), inline=True)
    await ctx.send(embed=embed)

# AI AUTOMOD
@bot.group(name="automod", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def automod_cmd(ctx):
    await send_embed(ctx, "🤖 AI Automod", f"`{config.PREFIX}automod enable/disable/sensitivity/action/status`", discord.Color.blue())

@automod_cmd.command(name="enable")
async def automod_enable(ctx):
    automod_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "AI monitoring!", discord.Color.green())

@automod_cmd.command(name="disable")
async def automod_disable(ctx):
    automod_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Not monitoring!", discord.Color.red())

@automod_cmd.command(name="sensitivity")
async def automod_sensitivity(ctx, level: str):
    if level.lower() not in ["low", "medium", "high", "strict"]:
        return await send_embed(ctx, "❌ Invalid", "Use: low, medium, high, or strict", discord.Color.red())
    automod_config["sensitivity"] = level.lower()
    await send_embed(ctx, "✅ Sensitivity", f"**{level}** mode!", discord.Color.green())

@automod_cmd.command(name="action")
async def automod_action(ctx, action: str):
    if action.lower() not in ["delete", "warn", "mute", "kick"]:
        return await send_embed(ctx, "❌ Invalid", "Use: delete, warn, mute, or kick", discord.Color.red())
    automod_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action", f"Violations will **{action}**!", discord.Color.green())

@automod_cmd.command(name="ignore")
async def automod_ignore(ctx, channel: discord.TextChannel):
    if channel.id not in automod_config["ignored_channels"]:
        automod_config["ignored_channels"].append(channel.id)
    await send_embed(ctx, "✅ Ignored", f"{channel.mention} exempt!", discord.Color.green())

@automod_cmd.command(name="whitelist")
async def automod_whitelist(ctx, role: discord.Role):
    if role.id not in automod_config["whitelisted_roles"]:
        automod_config["whitelisted_roles"].append(role.id)
    await send_embed(ctx, "✅ Whitelisted", f"{role.mention} exempt!", discord.Color.green())

@automod_cmd.command(name="status")
async def automod_status(ctx):
    embed = discord.Embed(title="🤖 Automod Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if automod_config.get("enabled") else "❌", inline=True)
    embed.add_field(name="Sensitivity", value=automod_config.get("sensitivity", "medium"), inline=True)
    embed.add_field(name="Action", value=automod_config.get("action", "delete"), inline=True)
    await ctx.send(embed=embed)

# INVITE COMMANDS WITH VERIFICATION
@bot.command(name="invites")
async def invites_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    stats = await db_manager.get_invites(target.id, ctx.guild.id)
    invited = await db_manager.get_invited_users(target.id, ctx.guild.id)
    
    embed = discord.Embed(title=f"📊 {target.name}'s Invites", color=discord.Color.blue())
    embed.add_field(name="Total", value=f"**{stats['total']}**", inline=True)
    embed.add_field(name="Real", value=f"**{stats['real']}**", inline=True)
    embed.add_field(name="Left", value=stats['left'], inline=True)
    embed.add_field(name="Fake", value=stats['fake'], inline=True)
    embed.add_field(name="Rejoin", value=stats['rejoin'], inline=True)
    
    if invited:
        desc = "\n**Invited Users:**\n"
        for i, row in enumerate(invited[:10], 1):
            m = ctx.guild.get_member(row['user_id'])
            if m:
                verified = "✅" if config.VERIFIED_ROLE_ID and any(r.id == config.VERIFIED_ROLE_ID for r in m.roles) else "❌"
                itype = "FAKE" if row['is_fake'] else "REJOIN" if row['is_rejoin'] else "LEFT" if row['left_at'] else "REAL"
                desc += f"{i}. {m.mention} ({itype}) {verified}\n"
        if len(invited) > 10:
            desc += f"\n*...and {len(invited) - 10} more*"
        embed.description = desc
    
    await ctx.send(embed=embed)

@bot.command(name="invited")
async def invited_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    invited = await db_manager.get_invited_users(target.id, ctx.guild.id)
    
    if not invited:
        return await send_embed(ctx, "📊 No Invites", f"{target.mention} hasn't invited anyone!", discord.Color.orange())
    
    embed = discord.Embed(title=f"📊 {target.name}'s Invited Users", color=discord.Color.blue())
    desc = ""
    for i, row in enumerate(invited[:20], 1):
        m = ctx.guild.get_member(row['user_id'])
        if m:
            verified = "✅ VERIFIED" if config.VERIFIED_ROLE_ID and any(r.id == config.VERIFIED_ROLE_ID for r in m.roles) else "❌ NOT VERIFIED"
            itype = "FAKE" if row['is_fake'] else "REJOIN" if row['is_rejoin'] else "LEFT" if row['left_at'] else "REAL"
            desc += f"{i}. {m.mention} ({itype}) ({verified})\n"
    embed.description = desc
    embed.set_footer(text=f"Total: {len(invited)} | ✅ = Verified | ❌ = Not Verified")
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "lbi", "leaderboardinvites"])
async def leaderboard_cmd(ctx):
    lb = await db_manager.get_leaderboard(ctx.guild.id, 10)
    if not lb:
        return await send_embed(ctx, "📊 Empty", "No invites tracked!", discord.Color.orange())
    
    embed = discord.Embed(title="📊 Top Inviters", color=discord.Color.gold())
    desc = ""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, row in enumerate(lb, 1):
        user = ctx.guild.get_member(row['inviter_id'])
        medal = medals.get(i, f"{i}.")
        desc += f"{medal} {user.mention if user else 'Unknown'}: **{row['real']}** invites\n"
    embed.description = desc
    await ctx.send(embed=embed)

@bot.command(name="resetinvites")
@commands.has_permissions(administrator=True)
async def resetinvites_cmd(ctx, target: Union[discord.Member, str] = None):
    if target is None:
        return await send_embed(ctx, "❌ Missing", f"Usage: `{config.PREFIX}resetinvites @user` or `all`", discord.Color.red())
    
    if isinstance(target, str) and target.lower() == "all":
        await db_manager.reset_invites_all(ctx.guild.id)
        await send_embed(ctx, "✅ Reset", "All invites reset!", discord.Color.green())
    else:
        await db_manager.reset_invites_user(target.id, ctx.guild.id)
        await send_embed(ctx, "✅ Reset", f"{target.mention}'s invites reset!", discord.Color.green())

@bot.command(name="messages", aliases=["msgs"])
async def messages_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    count = await db_manager.get_messages(target.id, ctx.guild.id)
    embed = discord.Embed(title=f"💬 {target.name}'s Messages", color=discord.Color.blue())
    embed.add_field(name="Total", value=f"**{count:,}**", inline=False)
    await ctx.send(embed=embed)

# OWNER WELCOME/LEAVE/INVITE CONFIG
@bot.command(name="setwelcomechannel")
@is_owner()
async def setwelcomechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.WELCOME_ENABLED = False
        config.WELCOME_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Disabled", "Welcome off!", discord.Color.red())
    config.WELCOME_CHANNEL_ID = channel.id
    config.WELCOME_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Welcome Channel", f"Set to {channel.mention}", discord.Color.green())

@bot.command(name="setleavechannel")
@is_owner()
async def setleavechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.LEAVE_ENABLED = False
        config.LEAVE_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Disabled", "Leave off!", discord.Color.red())
    config.LEAVE_CHANNEL_ID = channel.id
    config.LEAVE_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Leave Channel", f"Set to {channel.mention}", discord.Color.green())

@bot.command(name="setinvitechannel")
@is_owner()
async def setinvitechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.INVITE_LOG_ENABLED = False
        config.INVITE_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Disabled", "Invite log off!", discord.Color.red())
    config.INVITE_CHANNEL_ID = channel.id
    config.INVITE_LOG_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Invite Channel", f"Set to {channel.mention}", discord.Color.green())

@bot.command(name="setwelcomemsg")
@is_owner()
async def setwelcomemsg_cmd(ctx, *, message: str):
    config.WELCOME_MSG = message
    config.save_config()
    await send_embed(ctx, "✅ Welcome Message", f"Set! Variables: `{{user}}` `{{servername}}` `{{count}}`", discord.Color.green())

@bot.command(name="setleavemsg")
@is_owner()
async def setleavemsg_cmd(ctx, *, message: str):
    config.LEAVE_MSG = message
    config.save_config()
    await send_embed(ctx, "✅ Leave Message", f"Set! Variables: `{{user}}` `{{servername}}` `{{count}}`", discord.Color.green())

@bot.command(name="setinvitemsg")
@is_owner()
async def setinvitemsg_cmd(ctx, *, message: str):
    config.INVITE_MSG = message
    config.save_config()
    await send_embed(ctx, "✅ Invite Message", f"Set! Variables: `{{user}}` `{{inviter}}` `{{invites}}`", discord.Color.green())

@bot.command(name="testwelcome")
@is_owner()
async def testwelcome_cmd(ctx):
    await ctx.send(f"**Preview:**\n{format_msg(config.WELCOME_MSG, ctx.author, count=ctx.guild.member_count)}")

@bot.command(name="testleave")
@is_owner()
async def testleave_cmd(ctx):
    await ctx.send(f"**Preview:**\n{format_msg(config.LEAVE_MSG, ctx.author, count=ctx.guild.member_count)}")

@bot.command(name="testinvite")
@is_owner()
async def testinvite_cmd(ctx):
    stats = await db_manager.get_invites(ctx.author.id, ctx.guild.id)
    await ctx.send(f"**Preview:**\n{format_msg(config.INVITE_MSG, ctx.author, ctx.author, invite_count=stats['total'])}")


# ==================== PART 5 OF 6 - VERIFICATION, UTILITIES, HELP, STARTUP ====================
# Verification System, Utilities, Complete Help Command, Bot Startup
# PASTE AFTER PART 4B - LAST PART!

# VERIFICATION SYSTEM
@bot.group(name="verification", invoke_without_command=True)
@is_owner()
async def verification_cmd(ctx):
    await send_embed(ctx, "✅ Verification", f"`{config.PREFIX}verification enable/disable/channel/verified/unverified/status`", discord.Color.blue())

@verification_cmd.command(name="enable")
async def verif_enable(ctx):
    if not config.VERIFIED_ROLE_ID or not config.UNVERIFIED_ROLE_ID:
        return await send_embed(ctx, "❌ Setup Required", "Set roles first!", discord.Color.red())
    config.VERIFICATION_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Enabled", "Verification active!", discord.Color.green())

@verification_cmd.command(name="disable")
async def verif_disable(ctx):
    config.VERIFICATION_ENABLED = False
    config.save_config()
    await send_embed(ctx, "❌ Disabled", "Verification off!", discord.Color.red())

@verification_cmd.command(name="channel")
async def verif_channel(ctx, channel: discord.TextChannel):
    config.VERIFICATION_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Channel Set", f"Verification → {channel.mention}", discord.Color.green())

@verification_cmd.command(name="verified")
async def verif_verified(ctx, role: discord.Role):
    config.VERIFIED_ROLE_ID = role.id
    config.save_config()
    
    if config.UNVERIFIED_ROLE_ID:
        unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
        if unverified_role:
            locked = 0
            for channel in ctx.guild.channels:
                if channel.id == config.VERIFICATION_CHANNEL_ID: continue
                try:
                    await channel.set_permissions(unverified_role, read_messages=False, send_messages=False, view_channel=False)
                    locked += 1
                except: pass
            
            if config.VERIFICATION_CHANNEL_ID:
                verif_ch = ctx.guild.get_channel(config.VERIFICATION_CHANNEL_ID)
                if verif_ch:
                    await verif_ch.set_permissions(unverified_role, read_messages=True, send_messages=True, view_channel=True)
            
            await send_embed(ctx, "✅ Verified Role", f"Set: {role.mention}\nLocked {locked} channels for unverified!", discord.Color.green())
        else:
            await send_embed(ctx, "✅ Verified Role", f"Set: {role.mention}", discord.Color.green())
    else:
        await send_embed(ctx, "✅ Verified Role", f"Set: {role.mention}\n⚠️ Set unverified role to lock channels!", discord.Color.green())

@verification_cmd.command(name="unverified")
async def verif_unverified(ctx, role: discord.Role):
    config.UNVERIFIED_ROLE_ID = role.id
    config.save_config()
    
    locked = 0
    for channel in ctx.guild.channels:
        if channel.id == config.VERIFICATION_CHANNEL_ID:
            try: await channel.set_permissions(role, read_messages=True, send_messages=True, view_channel=True)
            except: pass
        else:
            try:
                await channel.set_permissions(role, read_messages=False, send_messages=False, view_channel=False)
                locked += 1
            except: pass
    
    await send_embed(ctx, "✅ Unverified Role", f"Set: {role.mention}\nLocked {locked} channels!", discord.Color.green())

@verification_cmd.command(name="status")
async def verif_status(ctx):
    embed = discord.Embed(title="✅ Verification Status", color=discord.Color.blue())
    embed.add_field(name="Enabled", value="✅" if config.VERIFICATION_ENABLED else "❌", inline=True)
    embed.add_field(name="Verified Role", value=f"<@&{config.VERIFIED_ROLE_ID}>" if config.VERIFIED_ROLE_ID else "Not Set", inline=True)
    embed.add_field(name="Unverified Role", value=f"<@&{config.UNVERIFIED_ROLE_ID}>" if config.UNVERIFIED_ROLE_ID else "Not Set", inline=True)
    embed.add_field(name="Channel", value=f"<#{config.VERIFICATION_CHANNEL_ID}>" if config.VERIFICATION_CHANNEL_ID else "Not Set", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="verify")
async def verify_cmd(ctx):
    if not config.VERIFICATION_ENABLED:
        return await send_embed(ctx, "❌ Not Enabled", "Verification disabled!", discord.Color.red())
    
    verified_role = ctx.guild.get_role(config.VERIFIED_ROLE_ID)
    unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
    
    if not verified_role or not unverified_role:
        return await send_embed(ctx, "❌ Not Setup", "Roles missing!", discord.Color.red())
    
    if unverified_role in ctx.author.roles:
        await ctx.author.remove_roles(unverified_role)
        await ctx.author.add_roles(verified_role)
        await send_embed(ctx, "✅ Verified!", f"Welcome to {ctx.guild.name}! You now have access!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Verified", "You're already verified!", discord.Color.orange())

# UTILITIES
@bot.command(name="av", aliases=["avatar", "pfp"])
async def avatar_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="sav", aliases=["serveravatar", "servericon"])
async def serveravatar_cmd(ctx):
    embed = discord.Embed(title=f"{ctx.guild.name}'s Icon", color=discord.Color.blue())
    if ctx.guild.icon:
        embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="si", aliases=["serverinfo"])
async def serverinfo_cmd(ctx):
    embed = discord.Embed(title=f"📊 {ctx.guild.name}", color=discord.Color.blue())
    embed.add_field(name="Owner", value=ctx.guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(ctx.guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(ctx.guild.roles), inline=True)
    embed.add_field(name="Boosts", value=ctx.guild.premium_subscription_count, inline=True)
    embed.add_field(name="Created", value=ctx.guild.created_at.strftime("%Y-%m-%d"), inline=True)
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="ui", aliases=["userinfo", "whois"])
async def userinfo_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"👤 {target.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown", inline=True)
    roles = [r.mention for r in target.roles if r.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_cmd(ctx):
    await send_embed(ctx, "🏓 Pong!", f"Latency: **{round(bot.latency * 1000)}ms**", discord.Color.green())

@bot.command(name="info")
async def info_cmd(ctx):
    embed = discord.Embed(title="🤖 Bot Info", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    await ctx.send(embed=embed)

# COMPLETE HELP COMMAND
class HelpView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.page = 0
        self.pages = [
            {
                "title": "📋 Moderation (14 commands)",
                "description": (
                    f"`{config.PREFIX}kick @user [reason]` - Kick user\n"
                    f"`{config.PREFIX}ban @user [reason]` - Ban user\n"
                    f"`{config.PREFIX}unban <id>` - Unban user\n"
                    f"`{config.PREFIX}mute @user [time] [reason]` - Mute user\n"
                    f"`{config.PREFIX}unmute @user` - Unmute user\n"
                    f"`{config.PREFIX}timeout @user <time>` - Timeout user\n"
                    f"`{config.PREFIX}untimeout @user` - Remove timeout\n"
                    f"`{config.PREFIX}warn @user [reason]` - Warn user\n"
                    f"`{config.PREFIX}warnings [@user]` - View warnings\n"
                    f"`{config.PREFIX}clearwarns @user` - Clear warnings\n"
                    f"`{config.PREFIX}purge <amount>` - Delete messages\n"
                    f"`{config.PREFIX}lock [#channel]` - Lock channel\n"
                    f"`{config.PREFIX}unlock [#channel]` - Unlock channel\n"
                    f"`{config.PREFIX}slowmode <seconds>` - Set slowmode"
                )
            },
            {
                "title": "📊 Logging & Cases (6 commands)",
                "description": (
                    f"`{config.PREFIX}setlog #channel` - Set log channel\n"
                    f"`{config.PREFIX}logs view` - View recent logs\n"
                    f"`{config.PREFIX}logs user @user` - View user logs\n"
                    f"`{config.PREFIX}cases @user` - View user cases\n"
                    f"`{config.PREFIX}case <id>` - View case details\n"
                    f"`{config.PREFIX}modstats [@mod]` - Mod statistics"
                )
            },
            {
                "title": "🚔 Jail System (3 commands)",
                "description": (
                    f"`{config.PREFIX}jail @user [reason]` - Jail user (removes ALL roles)\n"
                    f"`{config.PREFIX}unjail @user [reason]` - Unjail user (restores roles)\n"
                    f"`{config.PREFIX}jailed` - List jailed users"
                )
            },
            {
                "title": "🎭 Roles & Permissions (7 commands)",
                "description": (
                    f"`{config.PREFIX}role add @user @role` - Give role\n"
                    f"`{config.PREFIX}role remove @user @role` - Remove role\n\n"
                    f"**Permissions:**\n"
                    f"`{config.PREFIX}perm set <cmd> @role/@user` - Grant permission\n"
                    f"`{config.PREFIX}perm remove <cmd> @role/@user` - Remove permission\n"
                    f"`{config.PREFIX}perm list [cmd]` - List permissions\n"
                    f"`{config.PREFIX}perm reset <cmd>` - Reset permissions"
                )
            },
            {
                "title": "🔐 Whitelist System (7 commands)",
                "description": (
                    f"`{config.PREFIX}whitelist add <cmd> @role/@user` - Grant access\n"
                    f"`{config.PREFIX}whitelist addall @role/@user` - Grant all access\n"
                    f"`{config.PREFIX}whitelist remove <cmd> @role/@user` - Remove access\n"
                    f"`{config.PREFIX}whitelist removeall @role/@user` - Remove all\n"
                    f"`{config.PREFIX}whitelist list [cmd]` - View whitelists\n"
                    f"`{config.PREFIX}whitelist clear <cmd>` - Clear whitelist"
                )
            },
            {
                "title": "💬 AI Chat (10 commands + 25 personalities)",
                "description": (
                    f"`{config.PREFIX}ai <message>` - Chat with AI\n"
                    f"`{config.PREFIX}aimood <personality>` - Change mood\n"
                    f"`{config.PREFIX}personalities` - List all 25 moods\n"
                    f"`{config.PREFIX}aiclear` - Clear chat history\n"
                    f"`{config.PREFIX}aichannel #channel` - Auto-response\n\n"
                    f"**Personalities:** friendly, professional, sassy, mean, cool, nerdy, gamer, pirate, uwu, gen-z, robot, chaotic, wholesome, motivational, tsundere, shakespearean, detective, zen, comedic, karen, creative, casual, wise, enthusiastic, technical"
                )
            },
            {
                "title": "🛡️ Anti-Systems (35 commands)",
                "description": (
                    f"**Anti-Alt:** enable, disable, minage, action, status\n"
                    f"**Anti-Raid:** enable, disable, sensitivity, status, lockdown, unlockdown\n"
                    f"**Anti-Link:** enable, disable, whitelist, bypass (add/remove/list), status\n"
                    f"**Anti-Nuke:** enable, disable, whitelist, unwhitelist, status\n"
                    f"**Anti-Spam:** enable, disable, messages, time, action, ignore, whitelist, status\n"
                    f"**AI Automod:** enable, disable, sensitivity, action, ignore, whitelist, status"
                )
            },
            {
                "title": "📊 Invite Tracker (9 commands)",
                "description": (
                    f"`{config.PREFIX}invites [@user]` - View invite stats (with ✅/❌ verification)\n"
                    f"`{config.PREFIX}invited [@user]` - List invited users\n"
                    f"`{config.PREFIX}leaderboard` - Top inviters\n"
                    f"`{config.PREFIX}resetinvites @user/all` - Reset invites\n"
                    f"`{config.PREFIX}messages [@user]` - Message count\n\n"
                    f"**Stats:** Total, Real, Left, Fake, Rejoin"
                )
            },
            {
                "title": "✅ Verification System (7 commands)",
                "description": (
                    f"`{config.PREFIX}verification enable` - Turn on\n"
                    f"`{config.PREFIX}verification disable` - Turn off\n"
                    f"`{config.PREFIX}verification channel #channel` - Set channel\n"
                    f"`{config.PREFIX}verification verified @role` - Set verified role\n"
                    f"`{config.PREFIX}verification unverified @role` - Set unverified (AUTO-LOCKS!)\n"
                    f"`{config.PREFIX}verification status` - View settings\n"
                    f"`{config.PREFIX}verify` - User command to verify"
                )
            },
            {
                "title": "⚙️ Owner Config (17 commands)",
                "description": (
                    f"`{config.PREFIX}config prefix/owner/staff/logchannel/view/save/reset`\n\n"
                    f"**Welcome/Leave/Invite:**\n"
                    f"`{config.PREFIX}setwelcomechannel #channel` - Set channel\n"
                    f"`{config.PREFIX}setleavechannel #channel` - Set channel\n"
                    f"`{config.PREFIX}setinvitechannel #channel` - Set channel\n"
                    f"`{config.PREFIX}setwelcomemsg <msg>` - Set message\n"
                    f"`{config.PREFIX}setleavemsg <msg>` - Set message\n"
                    f"`{config.PREFIX}setinvitemsg <msg>` - Set message\n"
                    f"`{config.PREFIX}testwelcome/testleave/testinvite` - Preview\n\n"
                    f"**Variables:** {{user}}, {{inviter}}, {{invites}}, {{count}}, {{servername}}"
                )
            },
            {
                "title": "🔧 Utilities (10 commands)",
                "description": (
                    f"`{config.PREFIX}av [@user]` - View avatar\n"
                    f"`{config.PREFIX}sav` - Server icon\n"
                    f"`{config.PREFIX}si` - Server info\n"
                    f"`{config.PREFIX}ui [@user]` - User info\n"
                    f"`{config.PREFIX}ping` - Bot latency\n"
                    f"`{config.PREFIX}info` - Bot info\n"
                    f"`{config.PREFIX}help` - This menu"
                )
            }
        ]
    
    async def update_message(self, interaction):
        embed = discord.Embed(title=self.pages[self.page]["title"], description=self.pages[self.page]["description"], color=discord.Color.blue())
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)} • Total: 133+ commands")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        self.page = (self.page - 1) % len(self.pages)
        await self.update_message(interaction)
    
    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.page = (self.page + 1) % len(self.pages)
        await self.update_message(interaction)

@bot.command(name="help")
async def help_cmd(ctx):
    view = HelpView()
    embed = discord.Embed(title=view.pages[0]["title"], description=view.pages[0]["description"], color=discord.Color.blue())
    embed.set_footer(text=f"Page 1/{len(view.pages)} • Total: 133+ commands")
    await ctx.send(embed=embed, view=view)

# BOT STARTUP
async def start_web_server():
    async def handle(request):
        return web.Response(text="Bot is running!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Web server started on port {port}")

if __name__ == "__main__":
    async def main():
        async with bot:
            await start_web_server()
            await bot.start(config.TOKEN)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
  
