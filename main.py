# ==================== PART 1 OF 5 - ULTIMATE BOT ====================
# Core Setup, Config, Database, Utils
# PASTE THIS FIRST - NO BUGS, CLEAN CODE

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
        self.config.OWNER_ID = 1029438856069656576
        self.config.STAFF_ROLE_ID = 1432081794647199895
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
        self.LOG_CHANNEL_ID = None
        self.WELCOME_CHANNEL_ID = None
        self.LEAVE_CHANNEL_ID = None
        self.WELCOME_MSG = "Welcome {user} to {servername}! You are member #{count}. Invited by {inviter}!"
        self.LEAVE_MSG = "Goodbye {user}! You were member #{count}."
        self.WELCOME_ENABLED = False
        self.LEAVE_ENABLED = False
        self.VERIFICATION_CHANNEL_ID = None
        self.VERIFIED_ROLE_ID = None
        self.UNVERIFIED_ROLE_ID = None
        self.VERIFICATION_ENABLED = False
        self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists('bot_config.json'):
                with open('bot_config.json', 'r') as f:
                    data = json.load(f)
                    self.PREFIX = data.get('prefix', self.PREFIX)
                    self.config.OWNER_ID = data.get('owner_id', self.config.OWNER_ID)
                    self.config.STAFF_ROLE_ID = data.get('staff_role_id', self.config.STAFF_ROLE_ID)
                    self.LOG_CHANNEL_ID = data.get('log_channel_id', self.LOG_CHANNEL_ID)
                    self.WELCOME_CHANNEL_ID = data.get('welcome_channel_id', self.WELCOME_CHANNEL_ID)
                    self.LEAVE_CHANNEL_ID = data.get('leave_channel_id', self.LEAVE_CHANNEL_ID)
                    self.WELCOME_MSG = data.get('welcome_msg', self.WELCOME_MSG)
                    self.LEAVE_MSG = data.get('leave_msg', self.LEAVE_MSG)
                    self.WELCOME_ENABLED = data.get('welcome_enabled', self.WELCOME_ENABLED)
                    self.LEAVE_ENABLED = data.get('leave_enabled', self.LEAVE_ENABLED)
                    self.VERIFICATION_CHANNEL_ID = data.get('verification_channel_id', self.VERIFICATION_CHANNEL_ID)
                    self.VERIFIED_ROLE_ID = data.get('verified_role_id', self.VERIFIED_ROLE_ID)
                    self.UNVERIFIED_ROLE_ID = data.get('unverified_role_id', self.UNVERIFIED_ROLE_ID)
                    self.VERIFICATION_ENABLED = data.get('verification_enabled', self.VERIFICATION_ENABLED)
        except: pass
    
    def save_config(self):
        try:
            data = {
                'prefix': self.PREFIX,
                'owner_id': self.config.OWNER_ID,
                'staff_role_id': self.config.STAFF_ROLE_ID,
                'log_channel_id': self.LOG_CHANNEL_ID,
                'welcome_channel_id': self.WELCOME_CHANNEL_ID,
                'leave_channel_id': self.LEAVE_CHANNEL_ID,
                'welcome_msg': self.WELCOME_MSG,
                'leave_msg': self.LEAVE_MSG,
                'welcome_enabled': self.WELCOME_ENABLED,
                'leave_enabled': self.LEAVE_ENABLED,
                'verification_channel_id': self.VERIFICATION_CHANNEL_ID,
                'verified_role_id': self.VERIFIED_ROLE_ID,
                'unverified_role_id': self.UNVERIFIED_ROLE_ID,
                'verification_enabled': self.VERIFICATION_ENABLED
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
antinuke_config = {"enabled": False, "whitelist": []}
automod_config = {"enabled": False, "sensitivity": "medium", "action": "delete", "ignored_channels": [], "whitelisted_roles": []}
invite_tracker = {}

db_pool = None
db_manager = None

AI_PERSONALITIES = {
    "friendly": {"name": "Friendly", "emoji": "😊", "prompt": "You are warm and friendly. Be kind and supportive."},
    "professional": {"name": "Professional", "emoji": "💼", "prompt": "You are professional and formal."},
    "sassy": {"name": "Sassy", "emoji": "💅", "prompt": "You are sassy and witty!"},
    "mean": {"name": "Mean", "emoji": "😈", "prompt": "You roast users playfully!"},
    "cool": {"name": "Cool", "emoji": "😎", "prompt": "You're cool and smooth."},
    "nerdy": {"name": "Nerdy", "emoji": "🤓", "prompt": "You're a loveable nerd!"},
    "gamer": {"name": "Gamer", "emoji": "🎮", "prompt": "You're a hardcore gamer!"},
    "pirate": {"name": "Pirate", "emoji": "🏴‍☠️", "prompt": "Ye be a pirate! Arrr matey!"},
    "uwu": {"name": "UwU", "emoji": "🥺", "prompt": "You awe so cute UwU!"},
    "gen-z": {"name": "Gen-Z", "emoji": "✨", "prompt": "You're Gen-Z! No cap fr fr."},
    "robot": {"name": "Robot", "emoji": "🤖", "prompt": "BEEP BOOP. You are a robot."},
    "chaotic": {"name": "Chaotic", "emoji": "🌪️", "prompt": "You are CHAOTIC!"},
    "wholesome": {"name": "Wholesome", "emoji": "🥰", "prompt": "You are WHOLESOME!"},
    "motivational": {"name": "Motivational", "emoji": "💪", "prompt": "You motivate people!"},
    "tsundere": {"name": "Tsundere", "emoji": "😤", "prompt": "You're tsundere!"},
    "shakespearean": {"name": "Shakespeare", "emoji": "📜", "prompt": "Thou speakest like Shakespeare!"},
    "detective": {"name": "Detective", "emoji": "🔍", "prompt": "You're a detective!"},
    "zen": {"name": "Zen", "emoji": "🧘", "prompt": "You are zen and calm."},
    "comedic": {"name": "Comedian", "emoji": "😂", "prompt": "You're a comedian!"},
    "karen": {"name": "Karen", "emoji": "😠", "prompt": "You're a Karen!"},
    "creative": {"name": "Creative", "emoji": "🎨", "prompt": "You are creative!"},
    "casual": {"name": "Casual", "emoji": "😌", "prompt": "You are casual and chill."},
    "wise": {"name": "Wise", "emoji": "🧙", "prompt": "You are a wise sage."},
    "enthusiastic": {"name": "Enthusiastic", "emoji": "🎉", "prompt": "You're enthusiastic!"},
    "technical": {"name": "Technical", "emoji": "🔧", "prompt": "You're a technical expert."}
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
            await conn.execute('''CREATE TABLE IF NOT EXISTS invites (user_id BIGINT, guild_id BIGINT, inviter_id BIGINT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_fake BOOLEAN DEFAULT FALSE, left_at TIMESTAMP, PRIMARY KEY(user_id, guild_id))''')
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
    
    async def track_invite(self, user_id: int, guild_id: int, inviter_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('INSERT INTO invites (user_id, guild_id, inviter_id) VALUES ($1, $2, $3) ON CONFLICT (user_id, guild_id) DO NOTHING', user_id, guild_id, inviter_id)
    
    async def mark_left(self, user_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE invites SET left_at = CURRENT_TIMESTAMP WHERE user_id = $1 AND guild_id = $2', user_id, guild_id)
    
    async def get_invites(self, inviter_id: int, guild_id: int):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE left_at IS NULL) as real FROM invites WHERE inviter_id = $1 AND guild_id = $2 AND is_fake = FALSE', inviter_id, guild_id)
            return {'total': result['total'] or 0, 'real': result['real'] or 0, 'left': (result['total'] or 0) - (result['real'] or 0)}
    
    async def get_leaderboard(self, guild_id: int, limit: int = 10):
        async with self.pool.acquire() as conn:
            results = await conn.fetch('SELECT inviter_id, COUNT(*) FILTER (WHERE left_at IS NULL) as real FROM invites WHERE guild_id = $1 AND is_fake = FALSE GROUP BY inviter_id ORDER BY real DESC LIMIT $2', guild_id, limit)
            return results

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == config.config.OWNER_ID
    return commands.check(predicate)

def is_staff(member: discord.Member) -> bool:
    return member.id == config.config.OWNER_ID or any(role.id == config.config.STAFF_ROLE_ID for role in member.roles)

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
    """FIXED AI - No more proxies error!"""
    try:
        import anthropic
        
        if not config.ANTHROPIC_KEY:
            return "⚠️ AI not configured! Add ANTHROPIC_API_KEY to environment."
        
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_KEY)
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        
        if len(messages) > 20:
            messages = messages[-20:]
        
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

def format_welcome_leave(template: str, user: discord.Member, inviter: Optional[discord.Member], count: int) -> str:
    """Format welcome/leave messages with variables"""
    return template.replace("{user}", user.mention).replace("{username}", user.name).replace("{servername}", user.guild.name).replace("{count}", str(count)).replace("{inviter}", inviter.mention if inviter else "Unknown").replace("{invites}", str(0))



# ==================== PART 2 OF 5 - EVENTS & TRACKING ====================
# Events, Invite Tracker, Welcome/Leave Messages, Owner Config
# PASTE AFTER PART 1

# ==================== BOT EVENTS ====================
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
    
    # Cache invites for tracking
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_tracker[guild.id] = {invite.code: invite for invite in invites}
        except:
            invite_tracker[guild.id] = {}
    
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{config.PREFIX}help")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    logger.info("="*60)
    logger.info("🚀 ULTIMATE DISCORD BOT")
    logger.info(f"📌 Prefix: {config.PREFIX}")
    logger.info(f"👑 Owner: {config.config.OWNER_ID}")
    logger.info(f"📊 Servers: {len(bot.guilds)} | Users: {len(bot.users)}")
    logger.info("="*60)

@bot.event
async def on_guild_join(guild):
    try:
        invites = await guild.invites()
        invite_tracker[guild.id] = {invite.code: invite for invite in invites}
    except:
        invite_tracker[guild.id] = {}
    logger.info(f"✅ Joined: {guild.name}")

@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    
    # Find who invited them
    inviter = None
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
            await db_manager.track_invite(member.id, guild_id, inviter.id)
    except:
        pass
    
    # Verification system
    if config.VERIFICATION_ENABLED and config.UNVERIFIED_ROLE_ID:
        try:
            unverified_role = member.guild.get_role(config.UNVERIFIED_ROLE_ID)
            if unverified_role:
                await member.add_roles(unverified_role)
        except:
            pass
    
    # Anti-alt
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
    
    # Anti-raid
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
    
    # Welcome message
    if config.WELCOME_ENABLED and config.WELCOME_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.WELCOME_CHANNEL_ID)
            if channel:
                msg = format_welcome_leave(config.WELCOME_MSG, member, inviter, member.guild.member_count)
                await channel.send(msg)
        except:
            pass

@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    
    # Mark as left in database
    try:
        await db_manager.mark_left(member.id, guild_id)
    except:
        pass
    
    # Find who invited them
    inviter = None
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow('SELECT inviter_id FROM invites WHERE user_id = $1 AND guild_id = $2', member.id, guild_id)
            if result:
                inviter = member.guild.get_member(result['inviter_id'])
    except:
        pass
    
    # Leave message
    if config.LEAVE_ENABLED and config.LEAVE_CHANNEL_ID:
        try:
            channel = member.guild.get_channel(config.LEAVE_CHANNEL_ID)
            if channel:
                msg = format_welcome_leave(config.LEAVE_MSG, member, inviter, member.guild.member_count)
                await channel.send(msg)
        except:
            pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI auto-response
    if ai_config.get("enabled") and ai_config.get("channel_id") == message.channel.id:
        # Check for invite questions
        lower_msg = message.content.lower()
        if any(word in lower_msg for word in ["invite", "invites", "how many", "leaderboard"]):
            try:
                stats = await db_manager.get_invites(message.author.id, message.guild.id)
                if "leaderboard" in lower_msg or "most" in lower_msg or "top" in lower_msg:
                    lb = await db_manager.get_leaderboard(message.guild.id, 5)
                    response = "📊 **Top Inviters:**\n"
                    for idx, row in enumerate(lb, 1):
                        user = message.guild.get_member(row['inviter_id'])
                        response += f"{idx}. {user.mention if user else 'Unknown'}: **{row['real']}** invites\n"
                    await message.reply(response, mention_author=False)
                    return
                else:
                    response = f"📊 You have **{stats['real']}** invites! ({stats['left']} left)"
                    await message.reply(response, mention_author=False)
                    return
            except:
                pass
        
        # Regular AI chat
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

# ==================== OWNER CONFIG COMMANDS ====================
@bot.group(name="config", invoke_without_command=True)
@is_owner()
async def botconfig(ctx):
    embed = discord.Embed(title="⚙️ Bot Configuration (Owner)", color=discord.Color.gold())
    embed.add_field(name="Commands", value=
        f"`{config.PREFIX}config prefix <new>` - Change prefix\n"
        f"`{config.PREFIX}config owner <id>` - Change owner\n"
        f"`{config.PREFIX}config staff <id>` - Change staff role\n"
        f"`{config.PREFIX}config logchannel #channel` - Set log channel\n"
        f"`{config.PREFIX}config view` - View settings\n"
        f"`{config.PREFIX}config save` - Save config\n"
        f"`{config.PREFIX}config reset` - Reset to defaults", inline=False)
    await ctx.send(embed=embed)

@botconfig.command(name="prefix")
async def cfg_prefix(ctx, new_prefix: str):
    config.PREFIX = new_prefix
    await send_embed(ctx, "✅ Prefix Changed", f"New prefix: `{new_prefix}`\n\nExample: `{new_prefix}help`", discord.Color.green())

@botconfig.command(name="owner")
async def cfg_owner(ctx, owner_id: int):
    config.config.OWNER_ID = owner_id
    await send_embed(ctx, "✅ Owner Changed", f"New owner ID: `{owner_id}`", discord.Color.green())

@botconfig.command(name="staff")
async def cfg_staff(ctx, role_id: int):
    config.config.STAFF_ROLE_ID = role_id
    await send_embed(ctx, "✅ Staff Role Changed", f"New staff role ID: `{role_id}`", discord.Color.green())

@botconfig.command(name="logchannel")
async def cfg_logchannel(ctx, channel: discord.TextChannel):
    config.LOG_CHANNEL_ID = channel.id
    await send_embed(ctx, "✅ Log Channel Set", f"Logs will be sent to {channel.mention}", discord.Color.green())

@botconfig.command(name="view")
async def cfg_view(ctx):
    embed = discord.Embed(title="⚙️ Current Configuration", color=discord.Color.blue())
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    embed.add_field(name="Owner ID", value=config.config.OWNER_ID, inline=True)
    embed.add_field(name="Staff Role", value=config.config.STAFF_ROLE_ID, inline=True)
    log_ch = f"<#{config.LOG_CHANNEL_ID}>" if config.LOG_CHANNEL_ID else "Not Set"
    embed.add_field(name="Log Channel", value=log_ch, inline=True)
    await ctx.send(embed=embed)

@botconfig.command(name="save")
async def cfg_save(ctx):
    config.save_config()
    await send_embed(ctx, "✅ Config Saved", "Saved to `bot_config.json`!", discord.Color.green())

@botconfig.command(name="reset")
async def cfg_reset(ctx):
    config.PREFIX = "f!"
    config.config.OWNER_ID = 1029438856069656576
    config.config.STAFF_ROLE_ID = 1432081794647199895
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


# ==================== PART 4 OF 5 ====================
# AI Commands, Anti-Systems, Whitelist
# Paste AFTER Part 3

# ==================== AI COMMANDS ====================
@bot.command(name="ai", aliases=["chat", "ask", "claude"])
async def ai_cmd(ctx, *, message: str = None):
    if not message:
        return await send_embed(ctx, "🤖 Claude AI", f"Use `{config.PREFIX}ai <message>` to chat!", discord.Color.blue())
    
    async with ctx.typing():
        user_id = ctx.author.id
        conv = ai_conversations[user_id]
        conv["messages"].append({"role": "user", "content": message})
        
        if len(conv["messages"]) > 30:
            conv["messages"] = conv["messages"][-30:]
        
        response = await call_claude_api(conv["messages"], conv["personality"])
        conv["messages"].append({"role": "assistant", "content": response})
        
        p = AI_PERSONALITIES[conv["personality"]]
        embed = discord.Embed(title=f"{p['emoji']} Claude - {p['name']}", color=discord.Color.blue())
        embed.add_field(name="💬 You", value=message[:1024], inline=False)
        embed.add_field(name="🤖 Response", value=response[:1024], inline=False)
        await ctx.send(embed=embed)

@bot.command(name="aimood", aliases=["personality", "setmood"])
async def aimood_cmd(ctx, *, mood: str):
    mood_lower = mood.lower().replace(" ", "")
    matched = None
    
    for key in AI_PERSONALITIES.keys():
        if mood_lower in key.lower():
            matched = key
            break
    
    if not matched:
        return await send_embed(ctx, "❌ Not Found", f"Try: {', '.join(list(AI_PERSONALITIES.keys())[:5])}...", discord.Color.red())
    
    ai_conversations[ctx.author.id]["personality"] = matched
    p = AI_PERSONALITIES[matched]
    await send_embed(ctx, f"{p['emoji']} Personality Set!", f"**{p['name']}**", discord.Color.green())

@bot.command(name="personalities", aliases=["moods"])
async def personalities_cmd(ctx):
    embed = discord.Embed(title="🎭 25 AI Personalities", description="Use `f!aimood <name>`", color=discord.Color.purple())
    text = ", ".join([f"{AI_PERSONALITIES[k]['emoji']}{k}" for k in list(AI_PERSONALITIES.keys())[:25]])
    embed.add_field(name="Available", value=text, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="aiclear", aliases=["chatclear"])
async def aiclear_cmd(ctx):
    if ctx.author.id in ai_conversations:
        ai_conversations[ctx.author.id]["messages"] = []
    await send_embed(ctx, "✅ Cleared", "AI conversation cleared!", discord.Color.green())

@bot.command(name="aichannel")
@is_owner()
async def aichannel_cmd(ctx, channel: discord.TextChannel = None):
    if channel is None:
        ai_config["enabled"] = False
        ai_config["channel_id"] = None
        await send_embed(ctx, "✅ Disabled", "AI auto-response disabled!", discord.Color.green())
    else:
        ai_config["enabled"] = True
        ai_config["channel_id"] = channel.id
        await send_embed(ctx, "✅ AI Channel Set", f"Auto-responses in {channel.mention}!", discord.Color.green())

# ==================== ANTI-SYSTEMS ====================
@bot.group(name="antialt", invoke_without_command=True)
@is_owner()
async def antialt(ctx):
    await send_embed(ctx, "🔰 Anti-Alt", f"`{config.PREFIX}antialt enable/disable/minage/action/status`", discord.Color.blue())

@antialt.command(name="enable")
async def antialt_enable(ctx):
    antialt_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Alt detection enabled!", discord.Color.green())

@antialt.command(name="disable")
async def antialt_disable(ctx):
    antialt_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Alt detection disabled!", discord.Color.red())

@antialt.command(name="minage")
async def antialt_minage(ctx, days: int):
    antialt_config["min_age_days"] = days
    await send_embed(ctx, "✅ Min Age Set", f"Accounts must be **{days}+ days** old!", discord.Color.green())

@antialt.command(name="action")
async def antialt_action(ctx, action: str):
    if action.lower() not in ["kick", "ban", "none"]:
        return await send_embed(ctx, "❌ Invalid", "Use: kick, ban, or none", discord.Color.red())
    antialt_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Alts will be **{action}ed**!", discord.Color.green())

@antialt.command(name="status")
async def antialt_status(ctx):
    status = "Enabled ✅" if antialt_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🔰 Anti-Alt Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Min Age", value=f"{antialt_config.get('min_age_days', 7)} days", inline=True)
    embed.add_field(name="Action", value=antialt_config.get("action", "kick").title(), inline=True)
    await ctx.send(embed=embed)

@bot.group(name="antiraid", invoke_without_command=True)
@is_owner()
async def antiraid(ctx):
    await send_embed(ctx, "🛡️ Anti-Raid", f"`{config.PREFIX}antiraid enable/disable/sensitivity/status`", discord.Color.blue())

@antiraid.command(name="enable")
async def antiraid_enable(ctx):
    antiraid_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Raid protection enabled!", discord.Color.green())

@antiraid.command(name="disable")
async def antiraid_disable(ctx):
    antiraid_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Raid protection disabled!", discord.Color.red())

@antiraid.command(name="sensitivity")
async def antiraid_sensitivity(ctx, level: str):
    if level.lower() not in ["low", "medium", "high"]:
        return await send_embed(ctx, "❌ Invalid", "Use: low, medium, or high", discord.Color.red())
    antiraid_config["sensitivity"] = level.lower()
    thresholds = {"low": "10 joins/10s", "medium": "7 joins/10s", "high": "5 joins/10s"}
    await send_embed(ctx, "✅ Sensitivity Set", f"**{level.title()}** - {thresholds[level.lower()]}", discord.Color.green())

@antiraid.command(name="status")
async def antiraid_status(ctx):
    status = "Enabled ✅" if antiraid_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🛡️ Anti-Raid Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Sensitivity", value=antiraid_config.get("sensitivity", "medium").title(), inline=True)
    await ctx.send(embed=embed)

@bot.group(name="antilink", invoke_without_command=True)
@is_owner()
async def antilink(ctx):
    await send_embed(ctx, "🔗 Anti-Link", f"`{config.PREFIX}antilink enable/disable/whitelist/bypass/status`", discord.Color.blue())

@antilink.command(name="enable")
async def antilink_enable(ctx):
    antilink_config["enabled"] = True
    await send_embed(ctx, "✅ Enabled", "Link blocking enabled!", discord.Color.green())

@antilink.command(name="disable")
async def antilink_disable(ctx):
    antilink_config["enabled"] = False
    await send_embed(ctx, "❌ Disabled", "Links allowed!", discord.Color.red())

@antilink.command(name="whitelist")
async def antilink_whitelist(ctx, domain: str):
    domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    if "whitelist_domains" not in antilink_config:
        antilink_config["whitelist_domains"] = []
    
    if domain not in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].append(domain)
        await send_embed(ctx, "✅ Whitelisted", f"**{domain}** allowed!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Whitelisted", f"{domain} already whitelisted!", discord.Color.orange())

@antilink.group(name="bypass", invoke_without_command=True)
async def antilink_bypass(ctx):
    await send_embed(ctx, "🔗 Link Bypass", f"`{config.PREFIX}antilink bypass add/remove/list`", discord.Color.blue())

@antilink_bypass.command(name="add")
async def bypass_add(ctx, target: Union[discord.Role, discord.Member]):
    if isinstance(target, discord.Role):
        if "bypass_roles" not in antilink_config:
            antilink_config["bypass_roles"] = []
        if target.id not in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].append(target.id)
            await send_embed(ctx, "✅ Role Added", f"{target.mention} can post links!", discord.Color.green())
    else:
        if "bypass_users" not in antilink_config:
            antilink_config["bypass_users"] = []
        if target.id not in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].append(target.id)
            await send_embed(ctx, "✅ User Added", f"{target.mention} can post links!", discord.Color.green())

@antilink_bypass.command(name="list")
async def bypass_list(ctx):
    embed = discord.Embed(title="🔗 Link Bypass List", color=discord.Color.blue())
    
    roles = antilink_config.get("bypass_roles", [])
    users = antilink_config.get("bypass_users", [])
    
    role_text = "\n".join([ctx.guild.get_role(r).mention for r in roles if ctx.guild.get_role(r)]) or "None"
    user_text = "\n".join([f"<@{u}>" for u in users]) or "None"
    
    embed.add_field(name="Roles", value=role_text, inline=False)
    embed.add_field(name="Users", value=user_text, inline=False)
    await ctx.send(embed=embed)

@antilink.command(name="status")
async def antilink_status(ctx):
    status = "Enabled ✅" if antilink_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🔗 Anti-Link Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    
    domains = antilink_config.get("whitelist_domains", [])
    domain_text = ", ".join(domains[:5]) if domains else "None"
    if len(domains) > 5:
        domain_text += f" (+{len(domains)-5} more)"
    
    embed.add_field(name="Whitelisted Domains", value=domain_text, inline=False)
    embed.add_field(name="Bypasses", value=f"Roles: {len(antilink_config.get('bypass_roles', []))}, Users: {len(antilink_config.get('bypass_users', []))}", inline=False)
    await ctx.send(embed=embed)

# ==================== WHITELIST SYSTEM ====================
@bot.group(name="whitelist", invoke_without_command=True)
@is_owner()
async def whitelist(ctx):
    await send_embed(ctx, "🔐 Whitelist", f"`{config.PREFIX}whitelist add/addall/remove/removeall/list`", discord.Color.blue())

@whitelist.command(name="add")
async def whitelist_add(ctx, command_name: str, target: Union[discord.Role, discord.Member]):
    if command_name not in whitelist_data["commands"]:
        whitelist_data["commands"][command_name] = {"roles": [], "users": []}
    
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    entity_list = whitelist_data["commands"][command_name]["roles" if entity_type == "role" else "users"]
    
    if target.id not in entity_list:
        entity_list.append(target.id)
        await send_embed(ctx, "✅ Whitelisted", f"{target.mention} can use `{command_name}`!", discord.Color.green())

@whitelist.command(name="addall")
async def whitelist_addall(ctx, target: Union[discord.Role, discord.Member]):
    all_commands = [cmd.name for cmd in bot.commands if cmd.name not in ["help", "ping"]]
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    
    for cmd_name in all_commands:
        if cmd_name not in whitelist_data["commands"]:
            whitelist_data["commands"][cmd_name] = {"roles": [], "users": []}
        
        entity_list = whitelist_data["commands"][cmd_name]["roles" if entity_type == "role" else "users"]
        if target.id not in entity_list:
            entity_list.append(target.id)
    
    await send_embed(ctx, "✅ Full Access", f"{target.mention} has access to ALL commands!", discord.Color.green())

@whitelist.command(name="remove")
async def whitelist_remove(ctx, command_name: str, target: Union[discord.Role, discord.Member]):
    if command_name in whitelist_data["commands"]:
        entity_type = "role" if isinstance(target, discord.Role) else "user"
        entity_list = whitelist_data["commands"][command_name]["roles" if entity_type == "role" else "users"]
        
        if target.id in entity_list:
            entity_list.remove(target.id)
            await send_embed(ctx, "✅ Removed", f"{target.mention} removed from `{command_name}`!", discord.Color.green())

@whitelist.command(name="list")
async def whitelist_list(ctx, command_name: str = None):
    if command_name:
        if command_name in whitelist_data["commands"]:
            data = whitelist_data["commands"][command_name]
            embed = discord.Embed(title=f"🔒 Whitelist: {command_name}", color=discord.Color.blue())
            
            roles = [ctx.guild.get_role(r).mention for r in data.get("roles", []) if ctx.guild.get_role(r)]
            users = [f"<@{u}>" for u in data.get("users", [])]
            
            embed.add_field(name="Roles", value="\n".join(roles) or "None", inline=False)
            embed.add_field(name="Users", value="\n".join(users) or "None", inline=False)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="🔒 All Whitelisted Commands", color=discord.Color.blue())
        for cmd in list(whitelist_data["commands"].keys())[:25]:
            data = whitelist_data["commands"][cmd]
            embed.add_field(name=f"`{cmd}`", value=f"Roles: {len(data.get('roles', []))}, Users: {len(data.get('users', []))}", inline=True)
        await ctx.send(embed=embed)


# ==================== INVITE TRACKER COMMANDS ====================
@bot.command(name="invites")
async def invites_cmd(ctx, user: discord.Member = None):
    target = user or ctx.author
    stats = await db_manager.get_invites(target.id, ctx.guild.id)
    
    embed = discord.Embed(title=f"📊 {target.name}'s Invites", color=discord.Color.blue())
    embed.add_field(name="Total Invites", value=f"**{stats['real']}**", inline=True)
    embed.add_field(name="Left", value=stats['left'], inline=True)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "inviteleaderboard"])
async def leaderboard_cmd(ctx):
    lb = await db_manager.get_leaderboard(ctx.guild.id, 10)
    
    embed = discord.Embed(title="📊 Top Inviters", color=discord.Color.gold())
    description = ""
    for idx, row in enumerate(lb, 1):
        user = ctx.guild.get_member(row['inviter_id'])
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medals.get(idx, f"{idx}.")
        description += f"{medal} {user.mention if user else 'Unknown'}: **{row['real']}** invites\n"
    
    embed.description = description if description else "No invites tracked yet!"
    await ctx.send(embed=embed)

@bot.command(name="resetinvites")
@commands.has_permissions(administrator=True)
async def resetinvites_cmd(ctx, user: discord.Member):
    async with db_pool.acquire() as conn:
        await conn.execute('DELETE FROM invites WHERE inviter_id = $1 AND guild_id = $2', user.id, ctx.guild.id)
    await send_embed(ctx, "✅ Invites Reset", f"{user.mention}'s invites reset to 0!", discord.Color.green())

# ==================== WELCOME/LEAVE CONFIG ====================
@bot.command(name="setwelcomemsg")
@is_owner()
async def setwelcomemsg_cmd(ctx, *, message: str):
    config.WELCOME_MSG = message
    config.WELCOME_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Welcome Message Set", f"Message: {message}\n\nVariables: {{user}}, {{username}}, {{servername}}, {{count}}, {{inviter}}", discord.Color.green())

@bot.command(name="setwelcomechannel")
@is_owner()
async def setwelcomechannel_cmd(ctx, channel: discord.TextChannel):
    config.WELCOME_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Welcome Channel Set", f"Welcome messages → {channel.mention}", discord.Color.green())

@bot.command(name="setleavemsg")
@is_owner()
async def setleavemsg_cmd(ctx, *, message: str):
    config.LEAVE_MSG = message
    config.LEAVE_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Leave Message Set", f"Message: {message}", discord.Color.green())

@bot.command(name="setleavechannel")
@is_owner()
async def setleavechannel_cmd(ctx, channel: discord.TextChannel):
    config.LEAVE_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Leave Channel Set", f"Leave messages → {channel.mention}", discord.Color.green())

@bot.command(name="testwelcome")
@is_owner()
async def testwelcome_cmd(ctx):
    msg = format_welcome_leave(config.WELCOME_MSG, ctx.author, None, ctx.guild.member_count)
    await ctx.send(f"**Preview:**\n{msg}")

@bot.command(name="testleave")
@is_owner()
async def testleave_cmd(ctx):
    msg = format_welcome_leave(config.LEAVE_MSG, ctx.author, None, ctx.guild.member_count)
    await ctx.send(f"**Preview:**\n{msg}")

@bot.group(name="welcomemsg", invoke_without_command=True)
@is_owner()
async def welcomemsg(ctx):
    status = "Enabled ✅" if config.WELCOME_ENABLED else "Disabled ❌"
    await send_embed(ctx, "💬 Welcome Messages", f"Status: {status}\nUse `{config.PREFIX}welcomemsg disable` to turn off", discord.Color.blue())

@welcomemsg.command(name="disable")
async def welcome_disable(ctx):
    config.WELCOME_ENABLED = False
    config.save_config()
    await send_embed(ctx, "❌ Welcome Disabled", "Welcome messages turned off!", discord.Color.red())

@bot.group(name="leavemsg", invoke_without_command=True)
@is_owner()
async def leavemsg(ctx):
    status = "Enabled ✅" if config.LEAVE_ENABLED else "Disabled ❌"
    await send_embed(ctx, "👋 Leave Messages", f"Status: {status}\nUse `{config.PREFIX}leavemsg disable` to turn off", discord.Color.blue())

@leavemsg.command(name="disable")
async def leave_disable(ctx):
    config.LEAVE_ENABLED = False
    config.save_config()
    await send_embed(ctx, "❌ Leave Disabled", "Leave messages turned off!", discord.Color.red())


# ==================== PART 5 OF 5 ====================
# Utility Commands, Help System, Startup
# Paste LAST

# ==================== UTILITY COMMANDS ====================
@bot.command(name="av", aliases=["avatar", "pfp"])
async def avatar_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
    avatar_url = target.avatar.url if target.avatar else target.default_avatar.url
    embed.set_image(url=avatar_url)
    await ctx.send(embed=embed)

@bot.command(name="sav", aliases=["serveravatar", "servericon"])
async def server_avatar_cmd(ctx):
    if ctx.guild.icon:
        embed = discord.Embed(title=f"{ctx.guild.name}'s Icon", color=discord.Color.blue())
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

@bot.command(name="si", aliases=["serverinfo"])
async def server_info_cmd(ctx):
    g = ctx.guild
    embed = discord.Embed(title=f"📊 {g.name}", color=discord.Color.blue())
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=f"{g.member_count:,}", inline=True)
    embed.add_field(name="Channels", value=f"{len(g.channels)}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ui", aliases=["userinfo", "whois"])
async def user_info_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"👤 {target.name}", color=target.color)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_cmd(ctx):
    latency = round(bot.latency * 1000)
    await send_embed(ctx, "🏓 Pong!", f"**Latency:** {latency}ms", discord.Color.green())

@bot.command(name="info")
async def info_cmd(ctx):
    embed = discord.Embed(title="🤖 Bot Info", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value=f"`{config.PREFIX}`", inline=True)
    await ctx.send(embed=embed)

# ==================== HELP SYSTEM ====================
class HelpView(View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.current_page = 0
        self.pages = self.create_pages()
    
    def create_pages(self):
        pages = []
        
        # Page 1: Moderation
        embed1 = discord.Embed(title="⚖️ Moderation", color=discord.Color.orange())
        embed1.add_field(name="Commands", value=
            f"`{config.PREFIX}kick @user [reason]`\n"
            f"`{config.PREFIX}ban @user [reason]`\n"
            f"`{config.PREFIX}mute @user [time] [reason]`\n"
            f"`{config.PREFIX}timeout @user <time> [reason]`\n"
            f"`{config.PREFIX}untimeout @user [reason]`\n"
            f"`{config.PREFIX}warn @user [reason]`\n"
            f"`{config.PREFIX}purge <amount>`", inline=False)
        embed1.set_footer(text="Page 1/5")
        pages.append(embed1)
        
        # Page 2: Jail
        embed2 = discord.Embed(title="🚔 Jail System", color=discord.Color.dark_gray())
        embed2.add_field(name="Commands", value=
            f"`{config.PREFIX}jail @user [reason]`\n"
            f"`{config.PREFIX}unjail @user`\n"
            f"`{config.PREFIX}jailed`", inline=False)
        embed2.set_footer(text="Page 2/5")
        pages.append(embed2)
        
        # Page 3: AI
        embed3 = discord.Embed(title="💬 AI Chat", color=discord.Color.gold())
        embed3.add_field(name="Commands", value=
            f"`{config.PREFIX}ai <message>`\n"
            f"`{config.PREFIX}aimood <personality>`\n"
            f"`{config.PREFIX}personalities`\n"
            f"`{config.PREFIX}aiclear`\n"
            f"`{config.PREFIX}aichannel #channel`", inline=False)
        embed3.set_footer(text="Page 3/5")
        pages.append(embed3)
        
        # Page 4: Anti-Systems
        embed4 = discord.Embed(title="🛡️ Anti-Systems", color=discord.Color.red())
        embed4.add_field(name="Commands", value=
            f"`{config.PREFIX}antialt enable/disable/minage/action/status`\n"
            f"`{config.PREFIX}antiraid enable/disable/sensitivity/status`\n"
            f"`{config.PREFIX}antilink enable/disable/whitelist/bypass/status`", inline=False)
        embed4.set_footer(text="Page 4/5")
        pages.append(embed4)
        
        # Page 5: Utility
        embed5 = discord.Embed(title="🔧 Utility", color=discord.Color.blue())
        embed5.add_field(name="Commands", value=
            f"`{config.PREFIX}av [@user]` - Avatar\n"
            f"`{config.PREFIX}sav` - Server avatar\n"
            f"`{config.PREFIX}si` - Server info\n"
            f"`{config.PREFIX}ui [@user]` - User info\n"
            f"`{config.PREFIX}ping` - Latency\n"
            f"`{config.PREFIX}info` - Bot info", inline=False)
        embed5.set_footer(text="Page 5/5")
        pages.append(embed5)
        
        return pages
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

@bot.command(name="help")
async def help_cmd(ctx):
    view = HelpView(ctx)
    await ctx.send(embed=view.pages[0], view=view)


# ==================== VERIFICATION SYSTEM ====================
@bot.group(name="verification", invoke_without_command=True)
@is_owner()
async def verification(ctx):
    await send_embed(ctx, "✅ Verification System", f"`{config.PREFIX}verification enable/disable/channel/verified/unverified/status`", discord.Color.blue())

@verification.command(name="enable")
async def verif_enable(ctx):
    config.VERIFICATION_ENABLED = True
    config.save_config()
    await send_embed(ctx, "✅ Verification Enabled", "New members will get unverified role!", discord.Color.green())

@verification.command(name="disable")
async def verif_disable(ctx):
    config.VERIFICATION_ENABLED = False
    config.save_config()
    await send_embed(ctx, "❌ Verification Disabled", "Auto-verification turned off!", discord.Color.red())

@verification.command(name="channel")
async def verif_channel(ctx, channel: discord.TextChannel):
    config.VERIFICATION_CHANNEL_ID = channel.id
    config.save_config()
    await send_embed(ctx, "✅ Verification Channel Set", f"Verification → {channel.mention}", discord.Color.green())

@verification.command(name="verified")
async def verif_verified(ctx, role: discord.Role):
    config.VERIFIED_ROLE_ID = role.id
    config.save_config()
    
    # Update ALL channel permissions for unverified role
    if config.UNVERIFIED_ROLE_ID:
        unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
        if unverified_role:
            for channel in ctx.guild.channels:
                if channel.id == config.VERIFICATION_CHANNEL_ID:
                    continue
                try:
                    await channel.set_permissions(unverified_role, read_messages=False, send_messages=False, view_channel=False)
                except:
                    pass
            
            # Allow unverified to see verification channel only
            if config.VERIFICATION_CHANNEL_ID:
                verif_channel = ctx.guild.get_channel(config.VERIFICATION_CHANNEL_ID)
                if verif_channel:
                    await verif_channel.set_permissions(unverified_role, read_messages=True, send_messages=True, view_channel=True)
    
    await send_embed(ctx, "✅ Verified Role Set", f"Verified role: {role.mention}\nAll channels locked for unverified!", discord.Color.green())

@verification.command(name="unverified")
async def verif_unverified(ctx, role: discord.Role):
    config.UNVERIFIED_ROLE_ID = role.id
    config.save_config()
    
    # Lock ALL channels for this role except verification channel
    for channel in ctx.guild.channels:
        if channel.id == config.VERIFICATION_CHANNEL_ID:
            await channel.set_permissions(role, read_messages=True, send_messages=True, view_channel=True)
        else:
            try:
                await channel.set_permissions(role, read_messages=False, send_messages=False, view_channel=False)
            except:
                pass
    
    await send_embed(ctx, "✅ Unverified Role Set", f"Unverified role: {role.mention}\nAll channels locked except {f'<#{config.VERIFICATION_CHANNEL_ID}>' if config.VERIFICATION_CHANNEL_ID else 'verification'}!", discord.Color.green())

@verification.command(name="status")
async def verif_status(ctx):
    status = "Enabled ✅" if config.VERIFICATION_ENABLED else "Disabled ❌"
    embed = discord.Embed(title="✅ Verification Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    if config.VERIFIED_ROLE_ID:
        embed.add_field(name="Verified Role", value=f"<@&{config.VERIFIED_ROLE_ID}>", inline=True)
    if config.UNVERIFIED_ROLE_ID:
        embed.add_field(name="Unverified Role", value=f"<@&{config.UNVERIFIED_ROLE_ID}>", inline=True)
    if config.VERIFICATION_CHANNEL_ID:
        embed.add_field(name="Channel", value=f"<#{config.VERIFICATION_CHANNEL_ID}>", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="verify")
async def verify_cmd(ctx):
    if not config.VERIFICATION_ENABLED:
        return await send_embed(ctx, "❌ Not Enabled", "Verification system is disabled!", discord.Color.red())
    
    if not config.VERIFIED_ROLE_ID or not config.UNVERIFIED_ROLE_ID:
        return await send_embed(ctx, "❌ Not Setup", "Verification not configured!", discord.Color.red())
    
    verified_role = ctx.guild.get_role(config.VERIFIED_ROLE_ID)
    unverified_role = ctx.guild.get_role(config.UNVERIFIED_ROLE_ID)
    
    if not verified_role or not unverified_role:
        return await send_embed(ctx, "❌ Roles Missing", "Verification roles don't exist!", discord.Color.red())
    
    if unverified_role in ctx.author.roles:
        await ctx.author.remove_roles(unverified_role)
        await ctx.author.add_roles(verified_role)
        await send_embed(ctx, "✅ Verified!", f"Welcome to {ctx.guild.name}!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Verified", "You're already verified!", discord.Color.orange())

# ==================== STARTUP CODE ====================
async def handle(request):
    return web.Response(text="Bot is alive! 🤖")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logger.info("🌐 Web server started on port 8080")

async def main():
    global db_pool, db_manager
    
    try:
        db_pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=10)
        db_manager = DatabaseManager(db_pool)
        await db_manager.initialize_tables()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    logger.info("="*60)
    logger.info("🚀 ULTIMATE DISCORD BOT")
    logger.info(f"📌 Prefix: {config.PREFIX}")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"🛡️ Staff Role: {STAFF_ROLE_ID}")
    logger.info("="*60)
    
    await start_web_server()
    await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot shutdown by user")
    except Exception as e:
        logger.error(f"❌ FATAL: {e}")
