# ==================== PART 1 OF 5 ====================
# Core Setup, Configuration, Database, Utilities
# Paste this FIRST into main.py

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

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DiscordBot')

# ==================== CONFIGURATION ====================
BOT_PREFIX = "f!"
OWNER_ID = 1029438856069656576
STAFF_ROLE_ID = 1432081794647199895
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None, case_insensitive=True)

# ==================== GLOBAL DATA STORAGE ====================
whitelist_data = {"commands": {}}
ai_config = {"channel_id": None, "enabled": False}
ai_conversations = defaultdict(lambda: {"messages": [], "personality": "friendly", "created_at": datetime.utcnow()})
antiraid_config = {"enabled": False, "sensitivity": "medium", "joins": defaultdict(list)}
antialt_config = {"enabled": False, "min_age_days": 7, "action": "kick"}
antilink_config = {"enabled": False, "whitelist_domains": [], "bypass_roles": [], "bypass_users": [], "action": "delete"}
antinuke_config = {"enabled": False, "whitelist": []}
automod_config = {"enabled": False, "sensitivity": "medium", "action": "delete", "ignored_channels": [], "whitelisted_roles": []}

db_pool = None
db_manager = None

# ==================== ERROR MESSAGES ====================
COMMAND_USAGE = {
    "kick": {"usage": "f!kick @user [reason]", "example": "f!kick @BadUser spamming"},
    "ban": {"usage": "f!ban @user [reason]", "example": "f!ban @BadUser raiding"},
    "mute": {"usage": "f!mute @user [time] [reason]", "example": "f!mute @user 1h spamming"},
    "timeout": {"usage": "f!timeout @user <time> [reason]", "example": "f!timeout @user 10m spam"},
    "untimeout": {"usage": "f!untimeout @user [reason]", "example": "f!untimeout @user mistake"},
    "warn": {"usage": "f!warn @user [reason]", "example": "f!warn @user breaking rules"},
    "purge": {"usage": "f!purge <amount>", "example": "f!purge 50"},
    "jail": {"usage": "f!jail @user [reason]", "example": "f!jail @user toxicity"},
}

# ==================== AI PERSONALITIES ====================
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

# ==================== DATABASE MANAGER ====================
class DatabaseManager:
    def __init__(self, pool):
        self.pool = pool
    
    async def initialize_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    id SERIAL PRIMARY KEY,
                    command_name TEXT,
                    entity_type TEXT,
                    entity_id BIGINT,
                    added_by BIGINT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(command_name, entity_type, entity_id)
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    user_id BIGINT,
                    details TEXT,
                    severity TEXT DEFAULT 'INFO',
                    guild_id BIGINT,
                    case_id INTEGER
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id BIGINT PRIMARY KEY,
                    guild_id BIGINT,
                    warnings INTEGER DEFAULT 0,
                    notes TEXT
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS jail_data (
                    user_id BIGINT PRIMARY KEY,
                    guild_id BIGINT,
                    original_roles BIGINT[],
                    jailed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    jailed_by BIGINT,
                    reason TEXT
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS mod_cases (
                    case_id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    user_id BIGINT,
                    moderator_id BIGINT,
                    action TEXT,
                    reason TEXT,
                    duration TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info("✅ Database tables initialized")
    
    async def log_action(self, action: str, user_id: int, details: str, severity: str = "INFO", guild_id: Optional[int] = None, case_id: Optional[int] = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO audit_logs (action, user_id, details, severity, guild_id, case_id) VALUES ($1, $2, $3, $4, $5, $6)',
                action, user_id, details, severity, guild_id, case_id
            )
    
    async def create_case(self, guild_id: int, user_id: int, moderator_id: int, action: str, reason: str, duration: str = None) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                'INSERT INTO mod_cases (guild_id, user_id, moderator_id, action, reason, duration) VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id',
                guild_id, user_id, moderator_id, action, reason, duration
            )
            return result['case_id']

# ==================== UTILITY FUNCTIONS ====================
def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_staff(member: discord.Member) -> bool:
    return member.id == OWNER_ID or any(role.id == STAFF_ROLE_ID for role in member.roles)

def is_protected(member: discord.Member) -> bool:
    return is_staff(member)

async def send_embed(ctx, title: str, description: str, color: discord.Color = discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

def parse_time(time_str: str) -> Optional[timedelta]:
    if not time_str:
        return None
    match = re.match(r'^(\d+)([smhd])$', time_str.lower())
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2)
    units = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    return timedelta(**{units[unit]: amount})

def format_time(td: timedelta) -> str:
    seconds = int(td.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m"
    elif seconds < 86400:
        return f"{seconds//3600}h"
    else:
        return f"{seconds//86400}d"

async def call_claude_api(messages, personality):
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "⚠️ AI not configured!"
        
        client = anthropic.Anthropic(api_key=api_key)
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0.8,
            system=p["prompt"],
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ AI Error: {str(e)[:100]}"


# ==================== PART 2 OF 5 ====================
# Events & Smart Error Handling
# Paste AFTER Part 1

# ==================== BOT EVENTS ====================
@bot.event
async def on_ready():
    global db_pool, db_manager
    
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        db_manager = DatabaseManager(db_pool)
        await db_manager.initialize_tables()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{BOT_PREFIX}help")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    logger.info(f"✅ Bot ready: {bot.user.name}")
    logger.info(f"📊 Servers: {len(bot.guilds)} | Users: {len(bot.users)}")

@bot.event
async def on_guild_join(guild):
    logger.info(f"✅ Joined server: {guild.name}")

@bot.event
async def on_member_join(member):
    # Anti-alt check
    if antialt_config.get("enabled"):
        account_age = (datetime.utcnow() - member.created_at).days
        min_age = antialt_config.get("min_age_days", 7)
        
        if account_age < min_age and not is_staff(member):
            action = antialt_config.get("action", "kick")
            try:
                if action == "kick":
                    await member.kick(reason=f"Account too new: {account_age} days < {min_age} days")
                elif action == "ban":
                    await member.ban(reason=f"Alt account detected: {account_age} days old")
                await db_manager.log_action("ANTIALT_ACTION", member.id, f"Account age: {account_age}d", severity="WARNING", guild_id=member.guild.id)
            except:
                pass
    
    # Anti-raid check
    if antiraid_config.get("enabled"):
        guild_id = member.guild.id
        current_time = datetime.utcnow()
        
        antiraid_config["joins"][guild_id].append(current_time)
        antiraid_config["joins"][guild_id] = [t for t in antiraid_config["joins"][guild_id] if (current_time - t).total_seconds() < 10]
        
        sensitivity = antiraid_config.get("sensitivity", "medium")
        thresholds = {"low": 10, "medium": 7, "high": 5}
        
        if len(antiraid_config["joins"][guild_id]) >= thresholds.get(sensitivity, 7):
            try:
                await member.kick(reason="Raid detected")
                await db_manager.log_action("ANTIRAID_KICK", member.id, "Raid protection triggered", severity="CRITICAL", guild_id=guild_id)
            except:
                pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI auto-response channel
    if ai_config.get("enabled") and ai_config.get("channel_id") == message.channel.id:
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
    
    # Anti-link check
    if antilink_config.get("enabled") and not is_staff(message.author):
        # Check role bypass
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
                    action = antilink_config.get("action", "delete")
                    if action == "delete":
                        try:
                            await message.delete()
                            await message.channel.send(f"{message.author.mention} Links are not allowed!", delete_after=5)
                        except:
                            pass
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        invalid_cmd = ctx.message.content.split()[0][len(BOT_PREFIX):]
        all_commands = [cmd.name for cmd in bot.commands] + [alias for cmd in bot.commands for alias in cmd.aliases]
        matches = get_close_matches(invalid_cmd, all_commands, n=3, cutoff=0.6)
        
        if matches:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"**Unknown:** `{invalid_cmd}`\n\n**Did you mean:**\n" + "\n".join([f"• `{BOT_PREFIX}{m}`" for m in matches]),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
        return
    
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd_name = ctx.command.name
        usage_info = COMMAND_USAGE.get(cmd_name, {})
        
        embed = discord.Embed(title="❌ Missing Arguments", description=f"Missing: `{error.param.name}`", color=discord.Color.red())
        
        if usage_info:
            embed.add_field(name="Usage", value=f"`{usage_info['usage']}`", inline=False)
            embed.add_field(name="Example", value=f"`{usage_info['example']}`", inline=False)
        
        await ctx.send(embed=embed, delete_after=10)
        return
    
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "❌ No Permission", "You don't have permission for this command.", discord.Color.red())
        return
    
    elif isinstance(error, commands.CheckFailure):
        await send_embed(ctx, "🔒 Access Denied", "You don't have access to this command.", discord.Color.red())
        return
    
    else:
        logger.error(f"Error in {ctx.command}: {error}")


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
        return await send_embed(ctx, "🤖 Claude AI", f"Use `{BOT_PREFIX}ai <message>` to chat!", discord.Color.blue())
    
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
    await send_embed(ctx, "🔰 Anti-Alt", f"`{BOT_PREFIX}antialt enable/disable/minage/action/status`", discord.Color.blue())

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
    await send_embed(ctx, "🛡️ Anti-Raid", f"`{BOT_PREFIX}antiraid enable/disable/sensitivity/status`", discord.Color.blue())

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
    await send_embed(ctx, "🔗 Anti-Link", f"`{BOT_PREFIX}antilink enable/disable/whitelist/bypass/status`", discord.Color.blue())

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
    await send_embed(ctx, "🔗 Link Bypass", f"`{BOT_PREFIX}antilink bypass add/remove/list`", discord.Color.blue())

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
    await send_embed(ctx, "🔐 Whitelist", f"`{BOT_PREFIX}whitelist add/addall/remove/removeall/list`", discord.Color.blue())

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
    embed.add_field(name="Prefix", value=f"`{BOT_PREFIX}`", inline=True)
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
            f"`{BOT_PREFIX}kick @user [reason]`\n"
            f"`{BOT_PREFIX}ban @user [reason]`\n"
            f"`{BOT_PREFIX}mute @user [time] [reason]`\n"
            f"`{BOT_PREFIX}timeout @user <time> [reason]`\n"
            f"`{BOT_PREFIX}untimeout @user [reason]`\n"
            f"`{BOT_PREFIX}warn @user [reason]`\n"
            f"`{BOT_PREFIX}purge <amount>`", inline=False)
        embed1.set_footer(text="Page 1/5")
        pages.append(embed1)
        
        # Page 2: Jail
        embed2 = discord.Embed(title="🚔 Jail System", color=discord.Color.dark_gray())
        embed2.add_field(name="Commands", value=
            f"`{BOT_PREFIX}jail @user [reason]`\n"
            f"`{BOT_PREFIX}unjail @user`\n"
            f"`{BOT_PREFIX}jailed`", inline=False)
        embed2.set_footer(text="Page 2/5")
        pages.append(embed2)
        
        # Page 3: AI
        embed3 = discord.Embed(title="💬 AI Chat", color=discord.Color.gold())
        embed3.add_field(name="Commands", value=
            f"`{BOT_PREFIX}ai <message>`\n"
            f"`{BOT_PREFIX}aimood <personality>`\n"
            f"`{BOT_PREFIX}personalities`\n"
            f"`{BOT_PREFIX}aiclear`\n"
            f"`{BOT_PREFIX}aichannel #channel`", inline=False)
        embed3.set_footer(text="Page 3/5")
        pages.append(embed3)
        
        # Page 4: Anti-Systems
        embed4 = discord.Embed(title="🛡️ Anti-Systems", color=discord.Color.red())
        embed4.add_field(name="Commands", value=
            f"`{BOT_PREFIX}antialt enable/disable/minage/action/status`\n"
            f"`{BOT_PREFIX}antiraid enable/disable/sensitivity/status`\n"
            f"`{BOT_PREFIX}antilink enable/disable/whitelist/bypass/status`", inline=False)
        embed4.set_footer(text="Page 4/5")
        pages.append(embed4)
        
        # Page 5: Utility
        embed5 = discord.Embed(title="🔧 Utility", color=discord.Color.blue())
        embed5.add_field(name="Commands", value=
            f"`{BOT_PREFIX}av [@user]` - Avatar\n"
            f"`{BOT_PREFIX}sav` - Server avatar\n"
            f"`{BOT_PREFIX}si` - Server info\n"
            f"`{BOT_PREFIX}ui [@user]` - User info\n"
            f"`{BOT_PREFIX}ping` - Latency\n"
            f"`{BOT_PREFIX}info` - Bot info", inline=False)
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
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        db_manager = DatabaseManager(db_pool)
        await db_manager.initialize_tables()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    logger.info("="*60)
    logger.info("🚀 ULTIMATE DISCORD BOT")
    logger.info(f"📌 Prefix: {BOT_PREFIX}")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"🛡️ Staff Role: {STAFF_ROLE_ID}")
    logger.info("="*60)
    
    await start_web_server()
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot shutdown by user")
    except Exception as e:
        logger.error(f"❌ FATAL: {e}")
