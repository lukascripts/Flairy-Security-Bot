# ==================== PART 1 OF 5 - ULTIMATE BOT ====================
# Core Setup, Config, Database, Utils
# PASTE THIS FIRST - COMPLETE VERSION

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

# ==================== CONFIGURATION ====================
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
                    self.PREFIX = data.get('prefix', self.PREFIX)
                    self.OWNER_ID = data.get('owner_id', self.OWNER_ID)
                    self.STAFF_ROLE_ID = data.get('staff_role_id', self.STAFF_ROLE_ID)
                    self.LOG_CHANNEL_ID = data.get('log_channel_id')
                    self.WELCOME_CHANNEL_ID = data.get('welcome_channel_id')
                    self.LEAVE_CHANNEL_ID = data.get('leave_channel_id')
                    self.INVITE_CHANNEL_ID = data.get('invite_channel_id')
                    self.WELCOME_MSG = data.get('welcome_msg', self.WELCOME_MSG)
                    self.LEAVE_MSG = data.get('leave_msg', self.LEAVE_MSG)
                    self.INVITE_MSG = data.get('invite_msg', self.INVITE_MSG)
                    self.WELCOME_ENABLED = data.get('welcome_enabled', False)
                    self.LEAVE_ENABLED = data.get('leave_enabled', False)
                    self.INVITE_LOG_ENABLED = data.get('invite_log_enabled', False)
                    self.VERIFICATION_CHANNEL_ID = data.get('verification_channel_id')
                    self.VERIFIED_ROLE_ID = data.get('verified_role_id')
                    self.UNVERIFIED_ROLE_ID = data.get('unverified_role_id')
                    self.VERIFICATION_ENABLED = data.get('verification_enabled', False)
                    self.FAKE_INVITE_DAYS = data.get('fake_invite_days', 4)
        except: pass
    
    def save_config(self):
        try:
            data = {
                'prefix': self.PREFIX, 'owner_id': self.OWNER_ID, 'staff_role_id': self.STAFF_ROLE_ID,
                'log_channel_id': self.LOG_CHANNEL_ID, 'welcome_channel_id': self.WELCOME_CHANNEL_ID,
                'leave_channel_id': self.LEAVE_CHANNEL_ID, 'invite_channel_id': self.INVITE_CHANNEL_ID,
                'welcome_msg': self.WELCOME_MSG, 'leave_msg': self.LEAVE_MSG, 'invite_msg': self.INVITE_MSG,
                'welcome_enabled': self.WELCOME_ENABLED, 'leave_enabled': self.LEAVE_ENABLED,
                'invite_log_enabled': self.INVITE_LOG_ENABLED, 'verification_channel_id': self.VERIFICATION_CHANNEL_ID,
                'verified_role_id': self.VERIFIED_ROLE_ID, 'unverified_role_id': self.UNVERIFIED_ROLE_ID,
                'verification_enabled': self.VERIFICATION_ENABLED, 'fake_invite_days': self.FAKE_INVITE_DAYS
            }
            with open('bot_config.json', 'w') as f:
                json.dump(data, f, indent=4)
        except: pass

config = BotConfig()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=lambda bot, message: config.PREFIX, intents=intents, help_command=None, case_insensitive=True)

# ==================== GLOBAL DATA ====================
whitelist_data = {"commands": {}}
permission_data = {"commands": {}}
ai_config = {"channel_id": None, "enabled": False}
ai_conversations = defaultdict(lambda: {"messages": [], "personality": "friendly", "created_at": datetime.utcnow()})
antiraid_config = {"enabled": False, "sensitivity": "medium", "joins": defaultdict(list)}
antialt_config = {"enabled": False, "min_age_days": 7, "action": "kick"}
antilink_config = {"enabled": False, "whitelist_domains": [], "bypass_roles": [], "bypass_users": [], "action": "delete"}

# ENHANCED ANTI-NUKE SYSTEM
antinuke_config = {
    "enabled": False,
    "whitelist": [],
    "actions": {
        "channel_delete": defaultdict(list),
        "role_delete": defaultdict(list),
        "ban": defaultdict(list),
        "kick": defaultdict(list),
        "mention_spam": defaultdict(list),
        "webhook_create": defaultdict(list)
    },
    "bot_adders": {}  # Tracks who added which bot
}

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
            results = await conn.fetch('SELECT user_id, joined_at, is_fake, is_rejoin, left_at FROM invites WHERE inviter_id = $1 AND guild_id = $2 ORDER BY joined_at DESC', inviter_id, guild_id)
            return results
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        async with self.pool.acquire() as conn:
            results = await conn.fetch('''SELECT inviter_id, COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) as real FROM invites WHERE guild_id = $1 GROUP BY inviter_id HAVING COUNT(*) FILTER (WHERE left_at IS NULL AND is_fake = FALSE AND is_rejoin = FALSE) > 0 ORDER BY real DESC LIMIT $2''', guild_id, limit)
            return results
    
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

def is_protected(member: discord.Member) -> bool:
    return is_staff(member)

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
    try:
        import anthropic
        if not config.ANTHROPIC_KEY: return "⚠️ AI not configured!"
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        if len(messages) > 20: messages = messages[-20:]
        response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1000, temperature=0.7, system=p["prompt"], messages=messages)
        return response.content[0].text
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return f"❌ AI Error: {str(e)[:100]}"

def format_msg(template: str, user: discord.Member, inviter: Optional[discord.Member] = None, count: int = 0, invite_count: int = 0) -> str:
    return template.replace("{user}", user.mention).replace("{username}", user.name).replace("{servername}", user.guild.name).replace("{count}", str(count)).replace("{inviter}", inviter.mention if inviter else "Unknown").replace("{invites}", str(invite_count))



# ==================== PART 2 OF 5 - EVENTS & TRACKING ====================
# Events, Anti-Spam Detection, Anti-Nuke Events, Invite/Welcome/Leave
# PASTE AFTER PART 1

@bot.event
async def on_ready():
    global db_pool, db_manager, invite_tracker
    
    try:
        db_pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=10)
        db_manager = DatabaseManager(db_pool)
        await db_manager.initialize_tables()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_tracker[guild.id] = {invite.code: invite for invite in invites}
        except:
            invite_tracker[guild.id] = {}
    
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{config.PREFIX}help")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    logger.info("="*60)
    logger.info("🚀 ULTIMATE BOT - FINAL VERSION")
    logger.info(f"📌 Prefix: {config.PREFIX}")
    logger.info(f"👑 Owner: {config.OWNER_ID}")
    logger.info(f"📊 Servers: {len(bot.guilds)}")
    logger.info("="*60)

@bot.event
async def on_guild_join(guild):
    try:
        invites = await guild.invites()
        invite_tracker[guild.id] = {invite.code: invite for invite in invites}
    except:
        invite_tracker[guild.id] = {}

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    
    # TRACK WHO ADDED BOTS (for anti-nuke)
    if member.bot and antinuke_config.get("enabled"):
        try:
            async for entry in member.guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    antinuke_config["bot_adders"][member.id] = entry.user.id
                    logger.info(f"🤖 Bot {member.name} added by {entry.user.name} (ID: {entry.user.id})")
                    break
        except:
            pass
    
    inviter = None
    invite_count = 0
    
    try:
        new_invites = {invite.code: invite for invite in await member.guild.invites()}
        old_invites = invite_tracker.get(guild_id, {})
        
        for code, new_invite in new_invites.items():
            old_invite = old_invites.get(code)
            if old_invite and new_invite.uses > old_invite.uses:
                inviter = new_invite.inviter
                break
        
        invite_tracker[guild_id] = new_invites
        
        if inviter:
            is_rejoin = await db_manager.check_rejoin(member.id, guild_id)
            await db_manager.track_invite(member.id, guild_id, inviter.id, member.created_at, is_rejoin)
            stats = await db_manager.get_invites(inviter.id, guild_id)
            invite_count = stats['total']
    except Exception as e:
        logger.error(f"Invite tracking error: {e}")
    
    if config.INVITE_LOG_ENABLED and config.INVITE_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.INVITE_CHANNEL_ID)
            if channel:
                if inviter:
                    msg = format_msg(config.INVITE_MSG, member, inviter, invite_count=invite_count)
                else:
                    msg = f"I couldn't figure out how {member.mention} joined"
                await channel.send(msg)
        except:
            pass
    
    if config.VERIFICATION_ENABLED and config.UNVERIFIED_ROLE_ID:
        try:
            unverified_role = member.guild.get_role(config.UNVERIFIED_ROLE_ID)
            if unverified_role:
                await member.add_roles(unverified_role)
        except:
            pass
    
    if antialt_config.get("enabled") and not is_staff(member):
        account_age = (datetime.utcnow() - member.created_at).days
        min_age = antialt_config.get("min_age_days", 7)
        
        if account_age < min_age:
            action = antialt_config.get("action", "kick")
            try:
                if action == "kick":
                    await member.kick(reason=f"Alt: {account_age}d < {min_age}d")
                elif action == "ban":
                    await member.ban(reason=f"Alt: {account_age}d")
                return
            except:
                pass
    
    if antiraid_config.get("enabled"):
        current_time = datetime.utcnow()
        antiraid_config["joins"][guild_id].append(current_time)
        antiraid_config["joins"][guild_id] = [t for t in antiraid_config["joins"][guild_id] if (current_time - t).total_seconds() < 10]
        
        sensitivity = antiraid_config.get("sensitivity", "medium")
        thresholds = {"low": 10, "medium": 7, "high": 5}
        
        if len(antiraid_config["joins"][guild_id]) >= thresholds.get(sensitivity, 7):
            try:
                await member.kick(reason="Raid detected")
                return
            except:
                pass
    
    if config.WELCOME_ENABLED and config.WELCOME_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
            if channel:
                msg = format_msg(config.WELCOME_MSG, member, count=member.guild.member_count)
                await channel.send(msg)
        except:
            pass

@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    
    try:
        await db_manager.mark_left(member.id, guild_id)
    except:
        pass
    
    if config.LEAVE_ENABLED and config.LEAVE_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.LEAVE_CHANNEL_ID)
            if channel:
                msg = format_msg(config.LEAVE_MSG, member, count=member.guild.member_count)
                await channel.send(msg)
        except:
            pass

@bot.event
async def on_guild_channel_delete(channel):
    if not antinuke_config.get("enabled"):
        return
    
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                deleter = entry.user
                
                if deleter.id in antinuke_config.get("whitelist", []) or is_staff(deleter):
                    return
                
                current_time = datetime.utcnow()
                antinuke_config["actions"]["channel_delete"][deleter.id].append(current_time)
                antinuke_config["actions"]["channel_delete"][deleter.id] = [t for t in antinuke_config["actions"]["channel_delete"][deleter.id] if (current_time - t).total_seconds() < 30]
                
                if len(antinuke_config["actions"]["channel_delete"][deleter.id]) >= 3:
                    await channel.guild.ban(deleter, reason="🛡️ ANTI-NUKE: 3+ channels deleted")
                    
                    if deleter.bot:
                        adder_id = antinuke_config["bot_adders"].get(deleter.id)
                        if adder_id:
                            adder = channel.guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await channel.guild.ban(adder, reason=f"🛡️ Added nuke bot: {deleter.name}")
                                await log_to_channel(channel.guild, "🛡️ Anti-Nuke", f"**Bot:** {deleter.mention}\n**Adder:** {adder.mention}\n**Reason:** 3+ channels deleted", discord.Color.red())
                    
                    antinuke_config["actions"]["channel_delete"][deleter.id] = []
                break
    except:
        pass

@bot.event
async def on_guild_role_delete(role):
    if not antinuke_config.get("enabled"):
        return
    
    try:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                deleter = entry.user
                
                if deleter.id in antinuke_config.get("whitelist", []) or is_staff(deleter):
                    return
                
                current_time = datetime.utcnow()
                antinuke_config["actions"]["role_delete"][deleter.id].append(current_time)
                antinuke_config["actions"]["role_delete"][deleter.id] = [t for t in antinuke_config["actions"]["role_delete"][deleter.id] if (current_time - t).total_seconds() < 30]
                
                if len(antinuke_config["actions"]["role_delete"][deleter.id]) >= 3:
                    await role.guild.ban(deleter, reason="🛡️ ANTI-NUKE: 3+ roles deleted")
                    
                    if deleter.bot:
                        adder_id = antinuke_config["bot_adders"].get(deleter.id)
                        if adder_id:
                            adder = role.guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await role.guild.ban(adder, reason=f"🛡️ Added nuke bot: {deleter.name}")
                    
                    antinuke_config["actions"]["role_delete"][deleter.id] = []
                break
    except:
        pass

@bot.event
async def on_member_ban(guild, user):
    if not antinuke_config.get("enabled"):
        return
    
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                banner = entry.user
                
                if banner.id in antinuke_config.get("whitelist", []) or is_staff(banner):
                    return
                
                current_time = datetime.utcnow()
                antinuke_config["actions"]["ban"][banner.id].append(current_time)
                antinuke_config["actions"]["ban"][banner.id] = [t for t in antinuke_config["actions"]["ban"][banner.id] if (current_time - t).total_seconds() < 60]
                
                if len(antinuke_config["actions"]["ban"][banner.id]) >= 5:
                    await guild.ban(banner, reason="🛡️ ANTI-NUKE: 5+ bans in 60s")
                    
                    if banner.bot:
                        adder_id = antinuke_config["bot_adders"].get(banner.id)
                        if adder_id:
                            adder = guild.get_member(adder_id)
                            if adder and not is_staff(adder):
                                await guild.ban(adder, reason=f"🛡️ Added nuke bot: {banner.name}")
                    
                    antinuke_config["actions"]["ban"][banner.id] = []
                break
    except:
        pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    try:
        await db_manager.track_message(message.author.id, message.guild.id)
    except:
        pass


    # ANTI-SPAM DETECTION
    if antispam_config.get("enabled") and message.channel.id not in antispam_config.get("ignored_channels", []):
        user_role_ids = [role.id for role in message.author.roles]
        is_whitelisted = any(role_id in antispam_config.get("whitelisted_roles", []) for role_id in user_role_ids)
        
        if not is_staff(message.author) and not is_whitelisted:
            user_id = message.author.id
            current_time = datetime.utcnow()
            
            antispam_config["user_messages"][user_id].append(current_time)
            antispam_config["user_messages"][user_id] = [t for t in antispam_config["user_messages"][user_id] if (current_time - t).total_seconds() < antispam_config.get("timeframe", 3)]
            
            if len(antispam_config["user_messages"][user_id]) >= antispam_config.get("max_messages", 5):
                action = antispam_config.get("action", "mute")
                
                try:
                    if action == "mute":
                        muted_role = discord.utils.get(message.guild.roles, name="Muted")
                        if not muted_role:
                            muted_role = await message.guild.create_role(name="Muted")
                            for channel in message.guild.channels:
                                await channel.set_permissions(muted_role, send_messages=False, speak=False)
                        
                        await message.author.add_roles(muted_role)
                        await message.channel.send(f"🛡️ {message.author.mention} muted for spam!", delete_after=10)
                        
                    elif action == "kick":
                        await message.author.kick(reason="Spam")
                        await message.channel.send(f"🛡️ {message.author.mention} kicked for spam!", delete_after=10)
                        
                    elif action == "ban":
                        await message.author.ban(reason="Spam")
                        await message.channel.send(f"🛡️ {message.author.mention} banned for spam!", delete_after=10)
                    
                    antispam_config["user_messages"][user_id] = []
                    
                    if db_manager:
                        await db_manager.log_action("ANTISPAM", message.author.id, f"Action: {action}", "WARNING", message.guild.id)
                
                except Exception as e:
                    logger.error(f"Anti-spam error: {e}")
    
    # AI auto-response
    if ai_config.get("enabled") and ai_config.get("channel_id") == message.channel.id:
        lower_msg = message.content.lower()
        
        if any(word in lower_msg for word in ["invite", "invites", "how many", "leaderboard"]):
            try:
                if "leaderboard" in lower_msg or "most" in lower_msg or "top" in lower_msg:
                    lb = await db_manager.get_leaderboard(message.guild.id, 5)
                    response = "📊 **Top Inviters:**\n"
                    for idx, row in enumerate(lb, 1):
                        user = message.guild.get_member(row['inviter_id'])
                        response += f"{idx}. {user.mention if user else 'Unknown'}: **{row['real']}** invites\n"
                    await message.reply(response, mention_author=False)
                    return
                else:
                    stats = await db_manager.get_invites(message.author.id, message.guild.id)
                    invited_users = await db_manager.get_invited_users(message.author.id, message.guild.id)
                    
                    response = f"📊 **Your Invite Stats:**\nTotal: **{stats['total']}** | Real: **{stats['real']}** | Left: {stats['left']} | Fake: {stats['fake']} | Rejoin: {stats['rejoin']}\n\n"
                    
                    if invited_users:
                        response += "**Invited Users:**\n"
                        verified_role_id = config.VERIFIED_ROLE_ID
                        
                        for idx, row in enumerate(invited_users[:10], 1):
                            member = message.guild.get_member(row['user_id'])
                            
                            if member:
                                is_verified = verified_role_id and any(role.id == verified_role_id for role in member.roles)
                                verification = "✅ VERIFIED" if is_verified else "❌ NOT VERIFIED"
                                
                                if row['is_fake']:
                                    invite_type = "FAKE"
                                elif row['is_rejoin']:
                                    invite_type = "REJOIN"
                                elif row['left_at']:
                                    invite_type = "LEFT"
                                else:
                                    invite_type = "REAL"
                                
                                response += f"{idx}. {member.mention} ({invite_type}) ({verification})\n"
                            else:
                                response += f"{idx}. <@{row['user_id']}> (LEFT)\n"
                        
                        if len(invited_users) > 10:
                            response += f"\n*...and {len(invited_users) - 10} more*"
                    
                    await message.reply(response, mention_author=False)
                    return
            except Exception as e:
                logger.error(f"AI invite response error: {e}")
        
        async with message.channel.typing():
            user_id = message.author.id
            conv = ai_conversations[user_id]
            conv["messages"].append({"role": "user", "content": message.content})
            if len(conv["messages"]) > 30:
                conv["messages"] = conv["messages"][-30:]
            
            try:
                response = await call_claude_api(conv["messages"], conv["personality"])
                conv["messages"].append({"role": "assistant", "content": response})
                await message.reply(response, mention_author=False)
            except:
                pass
    
    # Anti-link
    if antilink_config.get("enabled") and not is_staff(message.author):
        user_role_ids = [role.id for role in message.author.roles]
        bypassed = any(role_id in antilink_config.get("bypass_roles", []) for role_id in user_role_ids)
        bypassed = bypassed or message.author.id in antilink_config.get("bypass_users", [])
        
        if not bypassed:
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, message.content)
            
            if urls:
                whitelist = antilink_config.get("whitelist_domains", [])
                allowed = any(any(domain in url for domain in whitelist) for url in urls)
                
                if not allowed:
                    try:
                        await message.delete()
                        await message.channel.send(f"{message.author.mention} Links not allowed!", delete_after=5)
                    except:
                        pass
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        invalid_cmd = ctx.message.content.split()[0][len(config.PREFIX):]
        all_commands = [cmd.name for cmd in bot.commands] + [alias for cmd in bot.commands for alias in cmd.aliases]
        matches = get_close_matches(invalid_cmd, all_commands, n=3, cutoff=0.6)
        
        if matches:
            embed = discord.Embed(title="❌ Command Not Found", description=f"**Unknown:** `{invalid_cmd}`\n\n**Did you mean:**\n" + "\n".join([f"• `{config.PREFIX}{m}`" for m in matches]), color=discord.Color.red())
            await ctx.send(embed=embed, delete_after=10)
        return
    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title="❌ Missing Arguments", description=f"Missing: `{error.param.name}`", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=10)
        return
    
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "❌ No Permission", "You don't have permission!", discord.Color.red())
        return
    
    elif isinstance(error, commands.CheckFailure):
        await send_embed(ctx, "🔒 Access Denied", "You don't have access!", discord.Color.red())
        return

# Owner config commands
@bot.group(name="config", invoke_without_command=True)
@is_owner()
async def botconfig(ctx):
    embed = discord.Embed(title="⚙️ Bot Configuration (Owner)", color=discord.Color.gold())
    embed.add_field(name="Commands", value=f"`{config.PREFIX}config prefix/owner/staff/logchannel/view/save/reset`", inline=False)
    await ctx.send(embed=embed)

@botconfig.command(name="prefix")
async def cfg_prefix(ctx, new_prefix: str):
    config.PREFIX = new_prefix
    await send_embed(ctx, "✅ Prefix Changed", f"New prefix: `{new_prefix}`", discord.Color.green())

@botconfig.command(name="owner")
async def cfg_owner(ctx, owner_id: int):
    config.OWNER_ID = owner_id
    await send_embed(ctx, "✅ Owner Changed", f"New owner: `{owner_id}`", discord.Color.green())

@botconfig.command(name="staff")
async def cfg_staff(ctx, role_id: int):
    config.STAFF_ROLE_ID = role_id
    await send_embed(ctx, "✅ Staff Role Changed", f"New staff role: `{role_id}`", discord.Color.green())

@botconfig.command(name="logchannel")
async def cfg_logchannel(ctx, channel: discord.TextChannel):
    config.LOG_CHANNEL_ID = channel.id
    await send_embed(ctx, "✅ Log Channel Set", f"Logs → {channel.mention}", discord.Color.green())

@botconfig.command(name="view")
async def cfg_view(ctx):
    embed = discord.Embed(title="⚙️ Configuration", color=discord.Color.blue())
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    embed.add_field(name="Owner", value=config.OWNER_ID, inline=True)
    embed.add_field(name="Staff Role", value=config.STAFF_ROLE_ID, inline=True)
    await ctx.send(embed=embed)

@botconfig.command(name="save")
async def cfg_save(ctx):
    config.save_config()
    await send_embed(ctx, "✅ Config Saved", "Saved to `bot_config.json`!", discord.Color.green())

@botconfig.command(name="reset")
async def cfg_reset(ctx):
    config.PREFIX = "f!"
    config.OWNER_ID = 1029438856069656576
    config.STAFF_ROLE_ID = 1432081794647199895
    config.save_config()
    await send_embed(ctx, "✅ Config Reset", "Reset to defaults!", discord.Color.green())


# ==================== PART 3 OF 5 ====================
# Moderation Commands ONLY
# Paste AFTER Part 2

# ==================== MODERATION COMMANDS ====================
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot kick staff!", discord.Color.red())
    
    try:
        await member.kick(reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "KICK", reason)
        await send_embed(ctx, "👢 Kicked", f"{member.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
    except:
        await send_embed(ctx, "❌ Error", "Failed to kick!", discord.Color.red())

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: Union[discord.Member, int], *, reason: str = "No reason"):
    user_id = member.id if isinstance(member, discord.Member) else member
    if isinstance(member, discord.Member) and is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot ban staff!", discord.Color.red())
    
    try:
        await ctx.guild.ban(discord.Object(id=user_id), reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, user_id, ctx.author.id, "BAN", reason)
        await send_embed(ctx, "🔨 Banned", f"User banned!\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.red())
    except:
        await send_embed(ctx, "❌ Error", "Failed to ban!", discord.Color.red())

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_cmd(ctx, user_id: int, *, reason: str = "No reason"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await send_embed(ctx, "✅ Unbanned", f"{user.name} unbanned!", discord.Color.green())
    except:
        await send_embed(ctx, "❌ Error", "User not banned or not found!", discord.Color.red())

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute_cmd(ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason"):
    if is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot mute staff!", discord.Color.red())
    
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    
    await member.add_roles(muted_role, reason=reason)
    time_delta = parse_time(duration) if duration else None
    
    await send_embed(ctx, "🔇 Muted", f"{member.mention} muted{' for ' + format_time(time_delta) if time_delta else ''}!", discord.Color.orange())
    
    if time_delta:
        await asyncio.sleep(time_delta.total_seconds())
        if muted_role in member.roles:
            await member.remove_roles(muted_role)

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute_cmd(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role)
        await send_embed(ctx, "🔊 Unmuted", f"{member.mention} unmuted!", discord.Color.green())

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration: str, *, reason: str = "No reason"):
    if is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot timeout staff!", discord.Color.red())
    
    time_delta = parse_time(duration)
    if not time_delta:
        return await send_embed(ctx, "❌ Invalid Time", "Use: 30s, 5m, 1h, 7d", discord.Color.red())
    
    try:
        await member.timeout(time_delta, reason=reason)
        await send_embed(ctx, "⏱️ Timeout", f"{member.mention} timed out for {format_time(time_delta)}!", discord.Color.orange())
    except:
        await send_embed(ctx, "❌ Error", "Failed to timeout!", discord.Color.red())

@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout_cmd(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await send_embed(ctx, "✅ Timeout Removed", f"{member.mention} timeout removed!", discord.Color.green())
    except:
        await send_embed(ctx, "❌ Error", "Failed!", discord.Color.red())

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot warn staff!", discord.Color.red())
    
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT warnings FROM user_data WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
        new_warnings = (result['warnings'] + 1) if result else 1
        
        if result:
            await conn.execute('UPDATE user_data SET warnings=$1 WHERE user_id=$2 AND guild_id=$3', new_warnings, member.id, ctx.guild.id)
        else:
            await conn.execute('INSERT INTO user_data (user_id, guild_id, warnings) VALUES ($1,$2,$3)', member.id, ctx.guild.id, 1)
    
    case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "WARN", reason)
    await send_embed(ctx, "⚠️ Warned", f"{member.mention}\n**Total:** {new_warnings}\n**Case:** #{case_id}", discord.Color.orange())

@bot.command(name="warnings")
async def warnings_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT warnings FROM user_data WHERE user_id=$1 AND guild_id=$2', target.id, ctx.guild.id)
    
    warnings = result['warnings'] if result else 0
    await send_embed(ctx, f"⚠️ Warnings - {target.name}", f"**Total:** {warnings}", discord.Color.orange() if warnings > 0 else discord.Color.green())

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns_cmd(ctx, member: discord.Member):
    async with db_pool.acquire() as conn:
        await conn.execute('UPDATE user_data SET warnings=0 WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
    
    await send_embed(ctx, "✅ Cleared", f"Warnings cleared for {member.mention}", discord.Color.green())

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
async def purge_cmd(ctx, limit: int, target: discord.Member = None):
    if limit > 100:
        return await send_embed(ctx, "❌ Limit", "Max 100 messages!", discord.Color.red())
    
    def check(m):
        return target is None or m.author == target
    
    deleted = await ctx.channel.purge(limit=limit+1, check=check)
    await ctx.send(f"✅ Deleted {len(deleted)-1} messages!", delete_after=5)

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await send_embed(ctx, "🔒 Locked", f"{channel.mention} locked!", discord.Color.orange())

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await send_embed(ctx, "🔓 Unlocked", f"{channel.mention} unlocked!", discord.Color.green())

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode_cmd(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await send_embed(ctx, "⏱️ Slowmode", f"Set to {seconds}s in {channel.mention}", discord.Color.blue())

# ==================== JAIL SYSTEM ====================
@bot.command(name="jail")
@commands.has_permissions(administrator=True)
async def jail_cmd(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member):
        return await send_embed(ctx, "❌ Protected", "Cannot jail staff!", discord.Color.red())
    
    jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if not jailed_role:
        jailed_role = await ctx.guild.create_role(name="Jailed", color=discord.Color.dark_gray())
    
    original_roles = [role.id for role in member.roles if role.name != "@everyone"]
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            'INSERT INTO jail_data (user_id, guild_id, original_roles, jailed_by, reason) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (user_id) DO UPDATE SET original_roles=$3, jailed_by=$4, reason=$5',
            member.id, ctx.guild.id, original_roles, ctx.author.id, reason
        )
    
    for role in member.roles:
        if role.name != "@everyone":
            try:
                await member.remove_roles(role)
            except:
                pass
    
    await member.add_roles(jailed_role)
    await send_embed(ctx, "🚔 Jailed", f"{member.mention} jailed!\n**Reason:** {reason}", discord.Color.dark_gray())

@bot.command(name="unjail")
@commands.has_permissions(administrator=True)
async def unjail_cmd(ctx, member: discord.Member):
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT original_roles FROM jail_data WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
    
    if not result:
        return await send_embed(ctx, "❌ Not Jailed", f"{member.mention} is not jailed!", discord.Color.red())
    
    jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if jailed_role:
        await member.remove_roles(jailed_role)
    
    for role_id in result['original_roles']:
        role = ctx.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    
    async with db_pool.acquire() as conn:
        await conn.execute('DELETE FROM jail_data WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
    
    await send_embed(ctx, "✅ Unjailed", f"{member.mention} released from jail!", discord.Color.green())

@bot.command(name="jailed")
async def jailed_cmd(ctx):
    async with db_pool.acquire() as conn:
        results = await conn.fetch('SELECT user_id FROM jail_data WHERE guild_id=$1', ctx.guild.id)
    
    if not results:
        return await send_embed(ctx, "🚔 Jailed Users", "No one is jailed!", discord.Color.blue())
    
    users = [f"<@{r['user_id']}>" for r in results]
    await send_embed(ctx, "🚔 Jailed Users", "\n".join(users), discord.Color.dark_gray())



# ==================== PART 4 OF 5 - AI + ANTI-SYSTEMS + INVITES ====================
# AI Chat, Anti-Systems, Whitelist, Invite Commands
# PASTE AFTER PART 3

# ==================== AI COMMANDS ====================
@bot.command(name="ai", aliases=["chat", "ask", "claude"])
async def ai_cmd(ctx, *, message: str):
    async with ctx.typing():
        user_id = ctx.author.id
        conv = ai_conversations[user_id]
        conv["messages"].append({"role": "user", "content": message})
        if len(conv["messages"]) > 30:
            conv["messages"] = conv["messages"][-30:]
        
        response = await call_claude_api(conv["messages"], conv["personality"])
        conv["messages"].append({"role": "assistant", "content": response})
        await ctx.reply(response, mention_author=False)

@bot.command(name="aimood", aliases=["personality", "setmood"])
async def aimood_cmd(ctx, mood: str):
    mood = mood.lower()
    if mood not in AI_PERSONALITIES:
        available = ", ".join(AI_PERSONALITIES.keys())
        return await send_embed(ctx, "❌ Invalid Mood", f"Available: {available}", discord.Color.red())
    
    ai_conversations[ctx.author.id]["personality"] = mood
    p = AI_PERSONALITIES[mood]
    await send_embed(ctx, f"{p['emoji']} Mood Changed", f"AI is now **{p['name']}**!", discord.Color.green())

@bot.command(name="personalities", aliases=["moods"])
async def personalities_cmd(ctx):
    embed = discord.Embed(title="🎭 AI Personalities", color=discord.Color.blue())
    description = ""
    for key, p in AI_PERSONALITIES.items():
        description += f"{p['emoji']} **{p['name']}** - `{key}`\n"
    embed.description = description
    await ctx.send(embed=embed)

@bot.command(name="aiclear", aliases=["chatclear"])
async def aiclear_cmd(ctx):
    ai_conversations[ctx.author.id]["messages"] = []
    await send_embed(ctx, "✅ Chat Cleared", "Conversation history reset!", discord.Color.green())

@bot.command(name="aichannel")
@is_owner()
async def aichannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None or channel.mention == "disable":
        ai_config["enabled"] = False
        ai_config["channel_id"] = None
        return await send_embed(ctx, "❌ AI Channel Disabled", "Auto-response turned off!", discord.Color.red())
    
    ai_config["channel_id"] = channel.id
    ai_config["enabled"] = True
    await send_embed(ctx, "✅ AI Channel Set", f"Auto-response in {channel.mention}!", discord.Color.green())

# ==================== ANTI-ALT ====================
@bot.group(name="antialt", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antialt(ctx):
    await send_embed(ctx, "🔰 Anti-Alt", f"`{config.PREFIX}antialt enable/disable/minage/action/status`", discord.Color.blue())

@antialt.command(name="enable")
async def antialt_enable(ctx):
    antialt_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Alt Enabled", "Checking account age on join!", discord.Color.green())

@antialt.command(name="disable")
async def antialt_disable(ctx):
    antialt_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Alt Disabled", "No longer checking accounts!", discord.Color.red())

@antialt.command(name="minage")
async def antialt_minage(ctx, days: int):
    antialt_config["min_age_days"] = days
    await send_embed(ctx, "✅ Min Age Set", f"Accounts must be **{days}** days old!", discord.Color.green())

@antialt.command(name="action")
async def antialt_action(ctx, action: str):
    if action.lower() not in ["kick", "ban", "none"]:
        return await send_embed(ctx, "❌ Invalid Action", "Use: kick, ban, or none", discord.Color.red())
    antialt_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Alts will be **{action}**ed!", discord.Color.green())

@antialt.command(name="status")
async def antialt_status(ctx):
    status = "Enabled ✅" if antialt_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🔰 Anti-Alt Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Min Age", value=f"{antialt_config.get('min_age_days', 7)} days", inline=True)
    embed.add_field(name="Action", value=antialt_config.get("action", "kick"), inline=True)
    await ctx.send(embed=embed)

# ==================== ANTI-RAID ====================
@bot.group(name="antiraid", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antiraid(ctx):
    await send_embed(ctx, "🛡️ Anti-Raid", f"`{config.PREFIX}antiraid enable/disable/sensitivity/status`", discord.Color.blue())

@antiraid.command(name="enable")
async def antiraid_enable(ctx):
    antiraid_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Raid Enabled", "Monitoring joins!", discord.Color.green())

@antiraid.command(name="disable")
async def antiraid_disable(ctx):
    antiraid_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Raid Disabled", "Not monitoring joins!", discord.Color.red())

@antiraid.command(name="sensitivity")
async def antiraid_sensitivity(ctx, level: str):
    if level.lower() not in ["low", "medium", "high"]:
        return await send_embed(ctx, "❌ Invalid", "Use: low, medium, or high", discord.Color.red())
    antiraid_config["sensitivity"] = level.lower()
    thresholds = {"low": "10 joins/10s", "medium": "7 joins/10s", "high": "5 joins/10s"}
    await send_embed(ctx, "✅ Sensitivity Set", f"**{level}**: {thresholds[level.lower()]}", discord.Color.green())

@antiraid.command(name="status")
async def antiraid_status(ctx):
    status = "Enabled ✅" if antiraid_config.get("enabled") else "Disabled ❌"
    sensitivity = antiraid_config.get("sensitivity", "medium")
    thresholds = {"low": "10/10s", "medium": "7/10s", "high": "5/10s"}
    embed = discord.Embed(title="🛡️ Anti-Raid Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Sensitivity", value=f"{sensitivity} ({thresholds[sensitivity]})", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="lockdown")
@commands.has_permissions(administrator=True)
async def lockdown_cmd(ctx):
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    await send_embed(ctx, "🔒 Lockdown Active", "Server locked!", discord.Color.red())

@bot.command(name="unlockdown")
@commands.has_permissions(administrator=True)
async def unlockdown_cmd(ctx):
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        except:
            pass
    await send_embed(ctx, "🔓 Lockdown Lifted", "Server unlocked!", discord.Color.green())

# ==================== ANTI-LINK ====================
@bot.group(name="antilink", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antilink(ctx):
    await send_embed(ctx, "🔗 Anti-Link", f"`{config.PREFIX}antilink enable/disable/whitelist/bypass/status`", discord.Color.blue())

@antilink.command(name="enable")
async def antilink_enable(ctx):
    antilink_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Link Enabled", "Blocking links!", discord.Color.green())

@antilink.command(name="disable")
async def antilink_disable(ctx):
    antilink_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Link Disabled", "Links allowed!", discord.Color.red())

@antilink.command(name="whitelist")
async def antilink_whitelist(ctx, domain: str):
    if domain not in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].append(domain)
    await send_embed(ctx, "✅ Domain Whitelisted", f"**{domain}** is allowed!", discord.Color.green())

@antilink.command(name="unwhitelist")
async def antilink_unwhitelist(ctx, domain: str):
    if domain in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].remove(domain)
    await send_embed(ctx, "✅ Domain Removed", f"**{domain}** removed!", discord.Color.green())

@antilink.group(name="bypass", invoke_without_command=True)
async def antilink_bypass(ctx):
    await send_embed(ctx, "🔗 Link Bypass", f"`{config.PREFIX}antilink bypass add/remove/list`", discord.Color.blue())

@antilink_bypass.command(name="add")
async def bypass_add(ctx, target: Union[discord.Role, discord.Member]):
    if isinstance(target, discord.Role):
        if target.id not in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].append(target.id)
        await send_embed(ctx, "✅ Role Bypass Added", f"{target.mention} can post links!", discord.Color.green())
    else:
        if target.id not in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].append(target.id)
        await send_embed(ctx, "✅ User Bypass Added", f"{target.mention} can post links!", discord.Color.green())

@antilink_bypass.command(name="remove")
async def bypass_remove(ctx, target: Union[discord.Role, discord.Member]):
    if isinstance(target, discord.Role):
        if target.id in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].remove(target.id)
        await send_embed(ctx, "✅ Role Bypass Removed", f"{target.mention} removed!", discord.Color.green())
    else:
        if target.id in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].remove(target.id)
        await send_embed(ctx, "✅ User Bypass Removed", f"{target.mention} removed!", discord.Color.green())

@antilink_bypass.command(name="list")
async def bypass_list(ctx):
    embed = discord.Embed(title="🔗 Link Bypasses", color=discord.Color.blue())
    roles = [f"<@&{rid}>" for rid in antilink_config.get("bypass_roles", [])]
    users = [f"<@{uid}>" for uid in antilink_config.get("bypass_users", [])]
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
    embed.add_field(name="Users", value=", ".join(users) if users else "None", inline=False)
    await ctx.send(embed=embed)

@antilink.command(name="action")
async def antilink_action(ctx, action: str):
    if action.lower() not in ["delete", "warn", "mute"]:
        return await send_embed(ctx, "❌ Invalid", "Use: delete, warn, or mute", discord.Color.red())
    antilink_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Links will **{action}**!", discord.Color.green())

@antilink.command(name="status")
async def antilink_status(ctx):
    status = "Enabled ✅" if antilink_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🔗 Anti-Link Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Action", value=antilink_config.get("action", "delete"), inline=True)
    domains = ", ".join(antilink_config.get("whitelist_domains", [])) or "None"
    embed.add_field(name="Whitelisted Domains", value=domains, inline=False)
    await ctx.send(embed=embed)

# ==================== ANTI-NUKE ====================
@bot.group(name="antinuke", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antinuke(ctx):
    await send_embed(ctx, "🛡️ Anti-Nuke", f"`{config.PREFIX}antinuke enable/disable/whitelist/status`", discord.Color.blue())

@antinuke.command(name="enable")
async def antinuke_enable(ctx):
    antinuke_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Nuke Enabled", "Server protected!", discord.Color.green())

@antinuke.command(name="disable")
async def antinuke_disable(ctx):
    antinuke_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Nuke Disabled", "Protection off!", discord.Color.red())

@antinuke.command(name="whitelist")
async def antinuke_whitelist(ctx, user: discord.Member):
    if user.id not in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].append(user.id)
    await send_embed(ctx, "✅ User Whitelisted", f"{user.mention} trusted!", discord.Color.green())

@antinuke.command(name="unwhitelist")
async def antinuke_unwhitelist(ctx, user: discord.Member):
    if user.id in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].remove(user.id)
    await send_embed(ctx, "✅ User Removed", f"{user.mention} removed!", discord.Color.green())

@antinuke.command(name="status")
async def antinuke_status(ctx):
    status = "Enabled ✅" if antinuke_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🛡️ Anti-Nuke Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    whitelist = [f"<@{uid}>" for uid in antinuke_config.get("whitelist", [])]
    embed.add_field(name="Whitelisted", value=", ".join(whitelist) if whitelist else "None", inline=False)
    await ctx.send(embed=embed)


# ==================== AI AUTOMOD ====================
@bot.group(name="automod", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def automod(ctx):
    await send_embed(ctx, "🤖 AI Automod", f"`{config.PREFIX}automod enable/disable/sensitivity/action/status`", discord.Color.blue())

@automod.command(name="enable")
async def automod_enable(ctx):
    automod_config["enabled"] = True
    await send_embed(ctx, "✅ Automod Enabled", "AI monitoring messages!", discord.Color.green())

@automod.command(name="disable")
async def automod_disable(ctx):
    automod_config["enabled"] = False
    await send_embed(ctx, "❌ Automod Disabled", "Not monitoring!", discord.Color.red())

@automod.command(name="sensitivity")
async def automod_sensitivity(ctx, level: str):
    if level.lower() not in ["low", "medium", "high", "strict"]:
        return await send_embed(ctx, "❌ Invalid", "Use: low, medium, high, or strict", discord.Color.red())
    automod_config["sensitivity"] = level.lower()
    await send_embed(ctx, "✅ Sensitivity Set", f"**{level}** mode active!", discord.Color.green())

@automod.command(name="action")
async def automod_action(ctx, action: str):
    if action.lower() not in ["delete", "warn", "mute", "kick"]:
        return await send_embed(ctx, "❌ Invalid", "Use: delete, warn, mute, or kick", discord.Color.red())
    automod_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Violations will **{action}**!", discord.Color.green())

@automod.command(name="ignore")
async def automod_ignore(ctx, channel: discord.TextChannel):
    if channel.id not in automod_config["ignored_channels"]:
        automod_config["ignored_channels"].append(channel.id)
    await send_embed(ctx, "✅ Channel Ignored", f"{channel.mention} exempt!", discord.Color.green())

@automod.command(name="whitelist")
async def automod_whitelist(ctx, role: discord.Role):
    if role.id not in automod_config["whitelisted_roles"]:
        automod_config["whitelisted_roles"].append(role.id)
    await send_embed(ctx, "✅ Role Whitelisted", f"{role.mention} exempt!", discord.Color.green())

@automod.command(name="status")
async def automod_status(ctx):
    status = "Enabled ✅" if automod_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🤖 Automod Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Sensitivity", value=automod_config.get("sensitivity", "medium"), inline=True)
    embed.add_field(name="Action", value=automod_config.get("action", "delete"), inline=True)
    await ctx.send(embed=embed)

# ==================== WHITELIST SYSTEM ====================
@bot.group(name="whitelist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def whitelist(ctx):
    await send_embed(ctx, "🔐 Whitelist", f"`{config.PREFIX}whitelist add/addall/remove/removeall/list`", discord.Color.blue())

@whitelist.command(name="add")
async def whitelist_add(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command not in whitelist_data["commands"]:
        whitelist_data["commands"][command] = {"roles": [], "users": []}
    
    if isinstance(target, discord.Role):
        if target.id not in whitelist_data["commands"][command]["roles"]:
            whitelist_data["commands"][command]["roles"].append(target.id)
    else:
        if target.id not in whitelist_data["commands"][command]["users"]:
            whitelist_data["commands"][command]["users"].append(target.id)
    
    await send_embed(ctx, "✅ Whitelist Added", f"{target.mention} can use `{command}`!", discord.Color.green())

@whitelist.command(name="addall")
async def whitelist_addall(ctx, target: Union[discord.Role, discord.Member]):
    all_commands = [cmd.name for cmd in bot.commands]
    for cmd in all_commands:
        if cmd not in whitelist_data["commands"]:
            whitelist_data["commands"][cmd] = {"roles": [], "users": []}
        
        if isinstance(target, discord.Role):
            if target.id not in whitelist_data["commands"][cmd]["roles"]:
                whitelist_data["commands"][cmd]["roles"].append(target.id)
        else:
            if target.id not in whitelist_data["commands"][cmd]["users"]:
                whitelist_data["commands"][cmd]["users"].append(target.id)
    
    await send_embed(ctx, "✅ Full Access Granted", f"{target.mention} can use ALL commands!", discord.Color.green())

@whitelist.command(name="remove")
async def whitelist_remove(ctx, command: str, target: Union[discord.Role, discord.Member]):
    if command in whitelist_data["commands"]:
        if isinstance(target, discord.Role):
            if target.id in whitelist_data["commands"][command]["roles"]:
                whitelist_data["commands"][command]["roles"].remove(target.id)
        else:
            if target.id in whitelist_data["commands"][command]["users"]:
                whitelist_data["commands"][command]["users"].remove(target.id)
    
    await send_embed(ctx, "✅ Whitelist Removed", f"{target.mention} removed from `{command}`!", discord.Color.green())

@whitelist.command(name="removeall")
async def whitelist_removeall(ctx, target: Union[discord.Role, discord.Member]):
    for cmd in whitelist_data["commands"]:
        if isinstance(target, discord.Role):
            if target.id in whitelist_data["commands"][cmd]["roles"]:
                whitelist_data["commands"][cmd]["roles"].remove(target.id)
        else:
            if target.id in whitelist_data["commands"][cmd]["users"]:
                whitelist_data["commands"][cmd]["users"].remove(target.id)
    
    await send_embed(ctx, "✅ All Access Removed", f"{target.mention} removed from all commands!", discord.Color.green())

@whitelist.command(name="list")
async def whitelist_list(ctx, command: str = None):
    if command:
        if command not in whitelist_data["commands"]:
            return await send_embed(ctx, "❌ No Whitelist", f"`{command}` has no whitelist!", discord.Color.red())
        
        embed = discord.Embed(title=f"🔐 Whitelist: {command}", color=discord.Color.blue())
        roles = [f"<@&{rid}>" for rid in whitelist_data["commands"][command].get("roles", [])]
        users = [f"<@{uid}>" for uid in whitelist_data["commands"][command].get("users", [])]
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        embed.add_field(name="Users", value=", ".join(users) if users else "None", inline=False)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🔐 All Whitelists", color=discord.Color.blue())
        description = ""
        for cmd, data in whitelist_data["commands"].items():
            if data.get("roles") or data.get("users"):
                description += f"**{cmd}**: {len(data.get('roles', []))} roles, {len(data.get('users', []))} users\n"
        embed.description = description if description else "No whitelists set!"
        await ctx.send(embed=embed)

@whitelist.command(name="clear")
async def whitelist_clear(ctx, command: str):
    if command in whitelist_data["commands"]:
        del whitelist_data["commands"][command]
    await send_embed(ctx, "✅ Whitelist Cleared", f"`{command}` whitelist cleared!", discord.Color.green())

# ==================== INVITE COMMANDS (NO DUPLICATES!) ====================
@bot.command(name="invites")
async def invites_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    stats = await db_manager.get_invites(target.id, ctx.guild.id)
    
    embed = discord.Embed(title=f"📊 {target.name}'s Invites", color=discord.Color.blue())
    embed.add_field(name="Total", value=f"**{stats['total']}**", inline=True)
    embed.add_field(name="Real", value=f"**{stats['real']}**", inline=True)
    embed.add_field(name="Left", value=stats['left'], inline=True)
    embed.add_field(name="Fake", value=stats['fake'], inline=True)
    embed.add_field(name="Rejoin", value=stats['rejoin'], inline=True)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="invited")
async def invited_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    results = await db_manager.get_invited_users(target.id, ctx.guild.id)
    
    if not results:
        return await send_embed(ctx, "📊 No Invites", f"{target.mention} hasn't invited anyone!", discord.Color.orange())
    
    embed = discord.Embed(title=f"📊 {target.name}'s Invited Users", color=discord.Color.blue())
    description = ""
    
    for idx, row in enumerate(results[:20], 1):
        member = ctx.guild.get_member(row['user_id'])
        user_mention = member.mention if member else f"<@{row['user_id']}>"
        
        status = ""
        if row['is_fake']:
            status = " [FAKE]"
        elif row['is_rejoin']:
            status = " [REJOIN]"
        elif row['left_at']:
            status = " [LEFT]"
        
        description += f"{idx}. {user_mention}{status}\n"
    
    if len(results) > 20:
        description += f"\n*...and {len(results) - 20} more*"
    
    embed.description = description
    embed.set_footer(text=f"Total: {len(results)} users")
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "lbi", "leaderboardinvites"])
async def leaderboard_cmd(ctx):
    lb = await db_manager.get_leaderboard(ctx.guild.id, 10)
    
    if not lb:
        return await send_embed(ctx, "📊 Leaderboard Empty", "No invites tracked!", discord.Color.orange())
    
    embed = discord.Embed(title="📊 Top Inviters", color=discord.Color.gold())
    description = ""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    for idx, row in enumerate(lb, 1):
        user = ctx.guild.get_member(row['inviter_id'])
        medal = medals.get(idx, f"{idx}.")
        description += f"{medal} {user.mention if user else 'Unknown'}: **{row['real']}** invites\n"
    
    embed.description = description
    await ctx.send(embed=embed)

@bot.command(name="resetinvites")
@commands.has_permissions(administrator=True)
async def resetinvites_cmd(ctx, target: Union[discord.Member, str] = None):
    if target is None:
        return await send_embed(ctx, "❌ Missing Argument", f"Usage: `{config.PREFIX}resetinvites @user` or `{config.PREFIX}resetinvites all`", discord.Color.red())
    
    if isinstance(target, str) and target.lower() == "all":
        await db_manager.reset_invites_all(ctx.guild.id)
        await send_embed(ctx, "✅ All Invites Reset", "Everyone's invites reset to 0!", discord.Color.green())
    else:
        await db_manager.reset_invites_user(target.id, ctx.guild.id)
        await send_embed(ctx, "✅ Invites Reset", f"{target.mention}'s invites reset to 0!", discord.Color.green())

@bot.command(name="messages", aliases=["msgs"])
async def messages_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    count = await db_manager.get_messages(target.id, ctx.guild.id)
    
    embed = discord.Embed(title=f"💬 {target.name}'s Messages", color=discord.Color.blue())
    embed.add_field(name="Total Messages", value=f"**{count:,}**", inline=False)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

# ==================== OWNER CONFIG - WELCOME/LEAVE/INVITE (NO DUPLICATES!) ====================
@bot.command(name="setwelcomechannel")
@is_owner()
async def setwelcomechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.WELCOME_ENABLED = False
        config.WELCOME_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Welcome Disabled", "Welcome messages turned off!", discord.Color.red())
    
    config.WELCOME_CHANNEL_ID = channel.id
    config.WELCOME_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Welcome Channel Set", f"Welcome messages → {channel.mention}", discord.Color.green())

@bot.command(name="setleavechannel")
@is_owner()
async def setleavechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.LEAVE_ENABLED = False
        config.LEAVE_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Leave Disabled", "Leave messages turned off!", discord.Color.red())
    
    config.LEAVE_CHANNEL_ID = channel.id
    config.LEAVE_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Leave Channel Set", f"Leave messages → {channel.mention}", discord.Color.green())

@bot.command(name="setinvitechannel")
@is_owner()
async def setinvitechannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        config.INVITE_LOG_ENABLED = False
        config.INVITE_CHANNEL_ID = None
        config.save_config()
        return await send_embed(ctx, "❌ Invite Log Disabled", "Invite logging turned off!", discord.Color.red())
    
    config.INVITE_CHANNEL_ID = channel.id
    config.INVITE_LOG_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Invite Channel Set", f"Invite logs → {channel.mention}", discord.Color.green())

@bot.command(name="setwelcomemsg")
@is_owner()
async def setwelcomemsg_cmd(ctx, *, message: str):
    config.WELCOME_MSG = message
    config.WELCOME_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Welcome Message Set", f"**Message:** {message}\n\n**Variables:** `{{user}}` `{{username}}` `{{servername}}` `{{count}}`", discord.Color.green())

@bot.command(name="setleavemsg")
@is_owner()
async def setleavemsg_cmd(ctx, *, message: str):
    config.LEAVE_MSG = message
    config.LEAVE_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Leave Message Set", f"**Message:** {message}\n\n**Variables:** `{{user}}` `{{username}}` `{{servername}}` `{{count}}`", discord.Color.green())

@bot.command(name="setinvitemsg")
@is_owner()
async def setinvitemsg_cmd(ctx, *, message: str):
    config.INVITE_MSG = message
    config.INVITE_LOG_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Invite Message Set", f"**Message:** {message}\n\n**Variables:** `{{user}}` `{{inviter}}` `{{invites}}`", discord.Color.green())

@bot.command(name="testwelcome")
@is_owner()
async def testwelcome_cmd(ctx):
    msg = format_msg(config.WELCOME_MSG, ctx.author, count=ctx.guild.member_count)
    await ctx.send(f"**Preview:**\n{msg}")

@bot.command(name="testleave")
@is_owner()
async def testleave_cmd(ctx):
    msg = format_msg(config.LEAVE_MSG, ctx.author, count=ctx.guild.member_count)
    await ctx.send(f"**Preview:**\n{msg}")

@bot.command(name="testinvite")
@is_owner()
async def testinvite_cmd(ctx):
    stats = await db_manager.get_invites(ctx.author.id, ctx.guild.id)
    msg = format_msg(config.INVITE_MSG, ctx.author, ctx.author, invite_count=stats['total'])
    await ctx.send(f"**Preview:**\n{msg}")


# ==================== ANTI-SPAM SYSTEM ====================
@bot.group(name="antispam", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antispam(ctx):
    await send_embed(ctx, "🛡️ Anti-Spam", f"`{config.PREFIX}antispam enable/disable/messages/time/action/ignore/whitelist/status`", discord.Color.blue())

antispam_config = {
    "enabled": False,
    "max_messages": 5,
    "timeframe": 3,
    "action": "mute",
    "ignored_channels": [],
    "whitelisted_roles": [],
    "user_messages": defaultdict(list)
}

@antispam.command(name="enable")
async def antispam_enable(ctx):
    antispam_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Spam Enabled", "Monitoring message spam!", discord.Color.green())

@antispam.command(name="disable")
async def antispam_disable(ctx):
    antispam_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Spam Disabled", "Not monitoring spam!", discord.Color.red())

@antispam.command(name="messages")
async def antispam_messages(ctx, amount: int):
    antispam_config["max_messages"] = amount
    await send_embed(ctx, "✅ Max Messages Set", f"Max **{amount}** messages in timeframe!", discord.Color.green())

@antispam.command(name="time")
async def antispam_time(ctx, seconds: int):
    antispam_config["timeframe"] = seconds
    await send_embed(ctx, "✅ Timeframe Set", f"Timeframe: **{seconds}** seconds!", discord.Color.green())

@antispam.command(name="action")
async def antispam_action(ctx, action: str):
    if action.lower() not in ["mute", "kick", "ban"]:
        return await send_embed(ctx, "❌ Invalid", "Use: mute, kick, or ban", discord.Color.red())
    antispam_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Spammers will be **{action}**ed!", discord.Color.green())

@antispam.command(name="ignore")
async def antispam_ignore(ctx, channel: discord.TextChannel):
    if channel.id not in antispam_config["ignored_channels"]:
        antispam_config["ignored_channels"].append(channel.id)
    await send_embed(ctx, "✅ Channel Ignored", f"{channel.mention} exempt from spam detection!", discord.Color.green())

@antispam.command(name="whitelist")
async def antispam_whitelist(ctx, role: discord.Role):
    if role.id not in antispam_config["whitelisted_roles"]:
        antispam_config["whitelisted_roles"].append(role.id)
    await send_embed(ctx, "✅ Role Whitelisted", f"{role.mention} exempt from spam detection!", discord.Color.green())

@antispam.command(name="status")
async def antispam_status(ctx):
    status = "Enabled ✅" if antispam_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🛡️ Anti-Spam Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Max Messages", value=antispam_config.get("max_messages", 5), inline=True)
    embed.add_field(name="Timeframe", value=f"{antispam_config.get('timeframe', 3)}s", inline=True)
    embed.add_field(name="Action", value=antispam_config.get("action", "mute"), inline=True)
    await ctx.send(embed=embed)

# UPDATE INVITES COMMANDS WITH VERIFICATION STATUS
# (Replace the existing invites and invited commands with these enhanced versions)


# ==================== PART 5 OF 5 - UTILITIES + VERIFICATION + STARTUP ====================
# Utilities, Help, Verification, Bot Startup
# PASTE AFTER PART 4 - LAST PART!

# ==================== UTILITY COMMANDS ====================
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
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="ui", aliases=["userinfo", "whois"])
async def userinfo_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    embed = discord.Embed(title=f"👤 {target.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown", inline=True)
    roles = [role.mention for role in target.roles if role.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_cmd(ctx):
    latency = round(bot.latency * 1000)
    await send_embed(ctx, "🏓 Pong!", f"Latency: **{latency}ms**", discord.Color.green())

@bot.command(name="info")
async def info_cmd(ctx):
    embed = discord.Embed(title="🤖 Bot Info", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    await ctx.send(embed=embed)

# ==================== HELP SYSTEM ====================
class HelpView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.page = 0
        self.pages = [
            {
                "title": "📋 Moderation Commands",
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
                "title": "📊 Invite Tracker",
                "description": (
                    f"`{config.PREFIX}invites [@user]` - View invite stats\n"
                    f"`{config.PREFIX}invited [@user]` - List invited users\n"
                    f"`{config.PREFIX}leaderboard` - Top inviters\n"
                    f"`{config.PREFIX}resetinvites <@user|all>` - Reset invites\n"
                    f"`{config.PREFIX}messages [@user]` - Message count\n\n"
                    "**Stats Shown:**\n"
                    "Total - Real invites only\n"
                    "Real - Valid invites\n"
                    "Left - People who left\n"
                    "Fake - Accounts < 4 days\n"
                    "Rejoin - People who rejoined"
                )
            },
            {
                "title": "💬 AI Chat (25 Personalities)",
                "description": (
                    f"`{config.PREFIX}ai <message>` - Chat with AI\n"
                    f"`{config.PREFIX}aimood <personality>` - Change mood\n"
                    f"`{config.PREFIX}personalities` - List all moods\n"
                    f"`{config.PREFIX}aiclear` - Clear chat history\n"
                    f"`{config.PREFIX}aichannel #channel` - Auto-response\n\n"
                    "**Personalities:**\n"
                    "😊 friendly, 💼 professional, 💅 sassy, 😈 mean\n"
                    "😎 cool, 🤓 nerdy, 🎮 gamer, 🏴‍☠️ pirate\n"
                    "🥺 uwu, ✨ gen-z, 🤖 robot, 🌪️ chaotic\n"
                    "And 13 more! Use `f!personalities`"
                )
            },
            {
                "title": "🛡️ Anti-Systems",
                "description": (
                    f"`{config.PREFIX}antialt enable/disable` - Alt detection\n"
                    f"`{config.PREFIX}antiraid enable/disable` - Raid protection\n"
                    f"`{config.PREFIX}antilink enable/disable` - Link blocking\n"
                    f"`{config.PREFIX}antilink bypass add @role/@user` - Bypass links\n"
                    f"`{config.PREFIX}antinuke enable/disable` - Nuke protection\n"
                    f"`{config.PREFIX}automod enable/disable` - AI moderation\n"
                    f"`{config.PREFIX}lockdown` - Lock entire server\n"
                    f"`{config.PREFIX}unlockdown` - Unlock server"
                )
            },
            {
                "title": "⚙️ Owner Config (Owner Only)",
                "description": (
                    f"`{config.PREFIX}config prefix <new>` - Change prefix\n"
                    f"`{config.PREFIX}setwelcomechannel #channel` - Welcome channel\n"
                    f"`{config.PREFIX}setleavechannel #channel` - Leave channel\n"
                    f"`{config.PREFIX}setinvitechannel #channel` - Invite log channel\n"
                    f"`{config.PREFIX}setwelcomemsg <msg>` - Welcome message\n"
                    f"`{config.PREFIX}setleavemsg <msg>` - Leave message\n"
                    f"`{config.PREFIX}setinvitemsg <msg>` - Invite message\n"
                    f"`{config.PREFIX}testwelcome` - Preview messages\n\n"
                    "**Variables:** {user}, {inviter}, {invites}, {count}, {servername}"
                )
            }
        ]
    
    async def update_message(self, interaction):
        embed = discord.Embed(
            title=self.pages[self.page]["title"],
            description=self.pages[self.page]["description"],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)} • {config.PREFIX}help")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if self.page > 0:
            self.page -= 1
        else:
            self.page = len(self.pages) - 1
        await self.update_message(interaction)
    
    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
        else:
            self.page = 0
        await self.update_message(interaction)

@bot.command(name="help")
async def help_cmd(ctx):
    view = HelpView()
    embed = discord.Embed(
        title=view.pages[0]["title"],
        description=view.pages[0]["description"],
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Page 1/{len(view.pages)} • {config.PREFIX}help")
    await ctx.send(embed=embed, view=view)

# ==================== VERIFICATION SYSTEM ====================
@bot.group(name="verification", invoke_without_command=True)
@is_owner()
async def verification(ctx):
    embed = discord.Embed(title="✅ Verification System", color=discord.Color.blue())
    embed.add_field(name="Commands", value=(
        f"`{config.PREFIX}verification enable` - Turn on\n"
        f"`{config.PREFIX}verification disable` - Turn off\n"
        f"`{config.PREFIX}verification channel #channel` - Set channel\n"
        f"`{config.PREFIX}verification verified @role` - Set verified role\n"
        f"`{config.PREFIX}verification unverified @role` - Set unverified role\n"
        f"`{config.PREFIX}verification status` - View settings"
    ), inline=False)
    await ctx.send(embed=embed)

@verification.command(name="enable")
async def verif_enable(ctx):
    if not config.VERIFIED_ROLE_ID or not config.UNVERIFIED_ROLE_ID:
        return await send_embed(ctx, "❌ Setup Required", "Set verified and unverified roles first!", discord.Color.red())
    
    config.VERIFICATION_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Verification Enabled", "New members get unverified role!", discord.Color.green())

@verification.command(name="disable")
async def verif_disable(ctx):
    config.VERIFICATION_ENABLED = False
    config.save_config()
    await send_embed(ctx, "❌ Verification Disabled", "Auto-verification off!", discord.Color.red())

@verification.command(name="channel")
async def verif_channel(ctx, channel: discord.TextChannel):
    config.VERIFICATION_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Verification Channel Set", f"Verification → {channel.mention}", discord.Color.green())

@verification.command(name="verified")
async def verif_verified(ctx, role: discord.Role):
    config.VERIFIED_ROLE_ID = role.id
    config.save_config()
    
    # Lock ALL channels for unverified role if set
    if config.UNVERIFIED_ROLE_ID:
        unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
        if unverified_role:
            locked_count = 0
            for channel in ctx.guild.channels:
                if channel.id == config.VERIFICATION_CHANNEL_ID:
                    continue
                try:
                    await channel.set_permissions(unverified_role, read_messages=False, send_messages=False, view_channel=False)
                    locked_count += 1
                except:
                    pass
            
            # Allow unverified to see verification channel
            if config.VERIFICATION_CHANNEL_ID:
                verif_channel = ctx.guild.get_channel(config.VERIFICATION_CHANNEL_ID)
                if verif_channel:
                    await verif_channel.set_permissions(unverified_role, read_messages=True, send_messages=True, view_channel=True)
            
            await send_embed(ctx, "✅ Verified Role Set", f"Verified role: {role.mention}\nLocked {locked_count} channels for unverified!", discord.Color.green())
        else:
            await send_embed(ctx, "✅ Verified Role Set", f"Verified role: {role.mention}", discord.Color.green())
    else:
        await send_embed(ctx, "✅ Verified Role Set", f"Verified role: {role.mention}\n\n⚠️ Set unverified role to lock channels!", discord.Color.green())

@verification.command(name="unverified")
async def verif_unverified(ctx, role: discord.Role):
    config.UNVERIFIED_ROLE_ID = role.id
    config.save_config()
    
    # Lock ALL channels for this role
    locked_count = 0
    for channel in ctx.guild.channels:
        if channel.id == config.VERIFICATION_CHANNEL_ID:
            # Allow in verification channel
            try:
                await channel.set_permissions(role, read_messages=True, send_messages=True, view_channel=True)
            except:
                pass
        else:
            # Block everywhere else
            try:
                await channel.set_permissions(role, read_messages=False, send_messages=False, view_channel=False)
                locked_count += 1
            except:
                pass
    
    await send_embed(ctx, "✅ Unverified Role Set", f"Unverified role: {role.mention}\nLocked {locked_count} channels!\nOnly {f'<#{config.VERIFICATION_CHANNEL_ID}>' if config.VERIFICATION_CHANNEL_ID else 'verification channel'} visible!", discord.Color.green())

@verification.command(name="status")
async def verif_status(ctx):
    status = "Enabled ✅" if config.VERIFICATION_ENABLED else "Disabled ❌"
    embed = discord.Embed(title="✅ Verification Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    
    if config.VERIFIED_ROLE_ID:
        embed.add_field(name="Verified Role", value=f"<@&{config.VERIFIED_ROLE_ID}>", inline=True)
    else:
        embed.add_field(name="Verified Role", value="Not Set ❌", inline=True)
    
    if config.UNVERIFIED_ROLE_ID:
        embed.add_field(name="Unverified Role", value=f"<@&{config.UNVERIFIED_ROLE_ID}>", inline=True)
    else:
        embed.add_field(name="Unverified Role", value="Not Set ❌", inline=True)
    
    if config.VERIFICATION_CHANNEL_ID:
        embed.add_field(name="Channel", value=f"<#{config.VERIFICATION_CHANNEL_ID}>", inline=True)
    else:
        embed.add_field(name="Channel", value="Not Set ❌", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="verify")
async def verify_cmd(ctx):
    if not config.VERIFICATION_ENABLED:
        return await send_embed(ctx, "❌ Not Enabled", "Verification system disabled!", discord.Color.red())
    
    if not config.VERIFIED_ROLE_ID or not config.UNVERIFIED_ROLE_ID:
        return await send_embed(ctx, "❌ Not Setup", "Verification not configured!", discord.Color.red())
    
    verified_role = ctx.guild.get_role(config.VERIFIED_ROLE_ID)
    unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
    
    if not verified_role or not unverified_role:
        return await send_embed(ctx, "❌ Roles Missing", "Verification roles don't exist!", discord.Color.red())
    
    if unverified_role in ctx.author.roles:
        await ctx.author.remove_roles(unverified_role)
        await ctx.author.add_roles(verified_role)
        await send_embed(ctx, "✅ Verified!", f"Welcome to {ctx.guild.name}! You now have access!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Verified", "You're already verified!", discord.Color.orange())

# ==================== BOT STARTUP (AT THE BOTTOM!) ====================
async def start_web_server():
    """Start web server for UptimeRobot"""
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

@bot.event
async def on_connect():
    logger.info("🔗 Bot connected to Discord")

if __name__ == "__main__":
    async def main():
        async with bot:
            await start_web_server()
            await bot.start(config.TOKEN)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        traceback.print_exc()
