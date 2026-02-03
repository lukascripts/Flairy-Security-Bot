# ==================== PART 1 OF 5 ====================
# PASTE THIS FIRST - Core Setup, Database, Utilities

"""
ULTIMATE DISCORD BOT - ALL IN ONE FILE
PART 1 OF 5 - Paste into main.py
"""
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()])
logger = logging.getLogger('DiscordBot')

BOT_PREFIX = "f!"
OWNER_ID = 1029438856069656576
STAFF_ROLE_ID = 1432081794647199895
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None, case_insensitive=True)

whitelist_data = {"commands": {}}
permission_data = {"commands": {}}
verification_config = {"unverified_role_id": None, "verified_role_id": None, "verification_channel_id": None, "enabled": False}
ai_config = {"channel_id": None, "enabled": False}
ai_conversations = defaultdict(lambda: {"messages": [], "personality": "friendly", "created_at": datetime.utcnow()})
antiraid_config = {"enabled": False, "sensitivity": "medium", "joins": defaultdict(list)}
antialt_config = {"enabled": False, "min_age_days": 7, "action": "kick"}
antilink_config = {"enabled": False, "whitelist_domains": [], "bypass_roles": [], "bypass_users": [], "action": "delete"}
antinuke_config = {"enabled": False, "whitelist": [], "actions": defaultdict(list)}
automod_config = {"enabled": False, "sensitivity": "medium", "action": "warn", "ignored_channels": [], "whitelisted_roles": []}
db_pool = None
db_manager = None

COMMAND_USAGE = {
    "kick": {"usage": "f!kick @user [reason]", "example": "f!kick @BadUser spamming"},
    "ban": {"usage": "f!ban @user [reason]", "example": "f!ban @BadUser raiding"},
    "mute": {"usage": "f!mute @user [time] [reason]", "example": "f!mute @user 1h spamming"},
    "timeout": {"usage": "f!timeout @user <time> [reason]", "example": "f!timeout @user 10m spam"},
    "warn": {"usage": "f!warn @user [reason]", "example": "f!warn @user breaking rules"},
    "purge": {"usage": "f!purge <amount>", "example": "f!purge 50"},
    "jail": {"usage": "f!jail @user [reason]", "example": "f!jail @user toxicity"},
}

AI_PERSONALITIES = {
    "friendly": {"name": "Friendly", "emoji": "😊", "prompt": "You are warm and friendly."},
    "professional": {"name": "Professional", "emoji": "💼", "prompt": "You are professional."},
    "sassy": {"name": "Sassy", "emoji": "💅", "prompt": "You are sassy and witty!"},
    "mean": {"name": "Mean", "emoji": "😈", "prompt": "You roast users playfully!"},
    "cool": {"name": "Cool", "emoji": "😎", "prompt": "You're the cool kid."},
    "nerdy": {"name": "Nerdy", "emoji": "🤓", "prompt": "You're a loveable nerd!"},
    "gamer": {"name": "Gamer", "emoji": "🎮", "prompt": "You're a hardcore gamer!"},
    "pirate": {"name": "Pirate", "emoji": "🏴‍☠️", "prompt": "Ye be a pirate, matey!"},
    "uwu": {"name": "UwU", "emoji": "🥺", "prompt": "You awe so cute UwU!"},
    "gen-z": {"name": "Gen-Z", "emoji": "✨", "prompt": "You're peak Gen-Z!"},
    "robot": {"name": "Robot", "emoji": "🤖", "prompt": "BEEP BOOP."},
    "chaotic": {"name": "Chaotic", "emoji": "🌪️", "prompt": "You are CHAOTIC!"},
    "wholesome": {"name": "Wholesome", "emoji": "🥰", "prompt": "You are WHOLESOME!"},
    "motivational": {"name": "Motivational", "emoji": "💪", "prompt": "You inspire!"},
    "tsundere": {"name": "Tsundere", "emoji": "😤", "prompt": "You're tsundere!"},
    "shakespearean": {"name": "Shakespeare", "emoji": "📜", "prompt": "Thou art Shakespeare!"},
    "detective": {"name": "Detective", "emoji": "🔍", "prompt": "You're a detective!"},
    "zen": {"name": "Zen", "emoji": "🧘", "prompt": "You are zen."},
    "comedic": {"name": "Comedian", "emoji": "😂", "prompt": "You're funny!"},
    "karen": {"name": "Karen", "emoji": "😠", "prompt": "You're a Karen!"},
    "creative": {"name": "Creative", "emoji": "🎨", "prompt": "You are creative!"},
    "casual": {"name": "Casual", "emoji": "😌", "prompt": "You are casual."},
    "wise": {"name": "Wise", "emoji": "🧙", "prompt": "You are wise."},
    "enthusiastic": {"name": "Enthusiastic", "emoji": "🎉", "prompt": "Super enthusiastic!"},
    "technical": {"name": "Technical", "emoji": "🔧", "prompt": "Technical expert."}
}

class DatabaseManager:
    def __init__(self, pool):
        self.pool = pool
    async def initialize_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS whitelist (id SERIAL PRIMARY KEY, command_name TEXT, entity_type TEXT, entity_id BIGINT, added_by BIGINT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(command_name, entity_type, entity_id))''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, user_id BIGINT, details TEXT, severity TEXT DEFAULT 'INFO', guild_id BIGINT, case_id INTEGER)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS verification_config (guild_id BIGINT PRIMARY KEY, unverified_role_id BIGINT, verified_role_id BIGINT, verification_channel_id BIGINT, enabled BOOLEAN)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_data (user_id BIGINT PRIMARY KEY, guild_id BIGINT, warnings INTEGER DEFAULT 0, notes TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS jail_data (user_id BIGINT PRIMARY KEY, guild_id BIGINT, original_roles BIGINT[], jailed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, jailed_by BIGINT, reason TEXT)''')
            await conn.execute('''CREATE TABLE IF NOT EXISTS mod_cases (case_id SERIAL PRIMARY KEY, guild_id BIGINT, user_id BIGINT, moderator_id BIGINT, action TEXT, reason TEXT, duration TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            logger.info("✅ Database initialized")
    async def log_action(self, action: str, user_id: int, details: str, severity: str = "INFO", guild_id: Optional[int] = None, case_id: Optional[int] = None):
        async with self.pool.acquire() as conn:
            await conn.execute('''INSERT INTO audit_logs (action, user_id, details, severity, guild_id, case_id) VALUES ($1, $2, $3, $4, $5, $6)''', action, user_id, details, severity, guild_id, case_id)
    async def create_case(self, guild_id: int, user_id: int, moderator_id: int, action: str, reason: str, duration: str = None) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''INSERT INTO mod_cases (guild_id, user_id, moderator_id, action, reason, duration) VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id''', guild_id, user_id, moderator_id, action, reason, duration)
            return result['case_id']

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

def is_staff(member: discord.Member) -> bool:
    if member.id == OWNER_ID:
        return True
    return any(role.id == STAFF_ROLE_ID for role in member.roles)

def is_protected(member: discord.Member) -> bool:
    return is_staff(member)

def has_permission(command_name: str):
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        if command_name in permission_data.get("commands", {}):
            perms = permission_data["commands"][command_name]
            if ctx.author.id in perms.get("users", []):
                return True
            user_role_ids = [role.id for role in ctx.author.roles]
            if any(role_id in perms.get("roles", []) for role_id in user_role_ids):
                return True
            return False
        return True
    return commands.check(predicate)

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
    if seconds < 60: return f"{seconds}s"
    elif seconds < 3600: return f"{seconds//60}m"
    elif seconds < 86400: return f"{seconds//3600}h"
    else: return f"{seconds//86400}d"

async def call_claude_api(messages, personality):
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key: return "⚠️ AI not configured!"
        client = anthropic.Anthropic(api_key=api_key)
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1500, temperature=0.8, system=p["prompt"], messages=messages)
        return response.content[0].text
    except: return "❌ AI Error!"

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
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{BOT_PREFIX}help | 100+ Commands")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    logger.info(f"✅ Bot ready: {bot.user.name}")
    logger.info(f"📊 Servers: {len(bot.guilds)} | Users: {len(bot.users)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        invalid_cmd = ctx.message.content.split()[0][len(BOT_PREFIX):]
        all_commands = [cmd.name for cmd in bot.commands] + [alias for cmd in bot.commands for alias in cmd.aliases]
        matches = get_close_matches(invalid_cmd, all_commands, n=3, cutoff=0.6)
        if matches:
            embed = discord.Embed(title="❌ Command Not Found", description=f"**Unknown:** `{invalid_cmd}`\n\n**Did you mean:**\n" + "\n".join([f"• `{BOT_PREFIX}{match}`" for match in matches]), color=discord.Color.red())
            embed.set_footer(text=f"Use {BOT_PREFIX}help")
            await ctx.send(embed=embed, delete_after=15)
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        cmd_name = ctx.command.name
        usage_info = COMMAND_USAGE.get(cmd_name, {})
        embed = discord.Embed(title="❌ Missing Arguments", description=f"**Missing:** `{error.param.name}`", color=discord.Color.red())
        if usage_info:
            embed.add_field(name="Usage", value=f"`{usage_info['usage']}`", inline=False)
            embed.add_field(name="Example", value=f"`{usage_info['example']}`", inline=False)
        await ctx.send(embed=embed, delete_after=15)
        return
    elif isinstance(error, commands.BadArgument):
        await send_embed(ctx, "❌ Invalid Arguments", str(error), discord.Color.red())
        return


# ==================== PART 2 OF 5 ====================
# PASTE AFTER PART 1 - Events & Smart Error Handling

# ==================== MODERATION COMMANDS (PART 2) ====================

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@has_permission("kick")
async def kick(ctx, member: discord.Member, *, reason: str = "No reason"):
    if member.id == ctx.author.id or member.id == OWNER_ID or is_protected(member):
        return await send_embed(ctx, "❌ Cannot Kick", "Protected!", discord.Color.red())
    if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        return await send_embed(ctx, "❌ Error", "Cannot kick higher/equal role!", discord.Color.red())
    try:
        await member.kick(reason=f"{reason} (By: {ctx.author.name})")
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "KICK", reason)
        await send_embed(ctx, "👢 Kicked", f"{member.mention} kicked!\n**Case:** #{case_id}", discord.Color.orange())
    except: await send_embed(ctx, "❌ Error", "Missing permissions!", discord.Color.red())

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@has_permission("ban")
async def ban(ctx, member: Union[discord.Member, int], *, reason: str = "No reason"):
    user_id = member.id if isinstance(member, discord.Member) else member
    if user_id == ctx.author.id or user_id == OWNER_ID or (isinstance(member, discord.Member) and is_protected(member)):
        return await send_embed(ctx, "❌ Cannot Ban", "Protected!", discord.Color.red())
    try:
        await ctx.guild.ban(discord.Object(id=user_id), reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, user_id, ctx.author.id, "BAN", reason)
        await send_embed(ctx, "🔨 Banned", f"User banned!\n**Case:** #{case_id}", discord.Color.red())
    except: await send_embed(ctx, "❌ Error", "Failed!", discord.Color.red())

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason: str = "No reason"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await send_embed(ctx, "✅ Unbanned", f"{user.name} unbanned!", discord.Color.green())
    except: await send_embed(ctx, "❌ Error", "Not banned!", discord.Color.red())

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
@has_permission("mute")
async def mute(ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Protected", "Staff protected!", discord.Color.red())
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
        if muted_role in member.roles: await member.remove_roles(muted_role)

@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member, *, reason: str = "No reason"):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role in member.roles:
        await member.remove_roles(muted_role, reason=reason)
        await send_embed(ctx, "🔊 Unmuted", f"{member.mention} unmuted!", discord.Color.green())

@bot.command(name="timeout")
@has_permission("timeout")
async def timeout(ctx, member: discord.Member, duration: str, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Protected", "Staff protected!", discord.Color.red())
    time_delta = parse_time(duration)
    if not time_delta: return await send_embed(ctx, "❌ Invalid Time", "Use: 30s, 5m, 1h, 7d", discord.Color.red())
    try:
        await member.timeout(time_delta, reason=reason)
        await send_embed(ctx, "⏱️ Timeout", f"{member.mention} timed out for {format_time(time_delta)}!", discord.Color.orange())
    except: await send_embed(ctx, "❌ Error", "Failed!", discord.Color.red())

@bot.command(name="untimeout")
async def untimeout(ctx, member: discord.Member, *, reason: str = "No reason"):
    try:
        await member.timeout(None, reason=reason)
        await send_embed(ctx, "✅ Timeout Removed", f"{member.mention} timeout removed!", discord.Color.green())
    except: await send_embed(ctx, "❌ Error", "Failed!", discord.Color.red())

@bot.command(name="warn")
@has_permission("warn")
async def warn(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Protected", "Staff protected!", discord.Color.red())
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT warnings FROM user_data WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
        new_warnings = (result['warnings'] + 1) if result else 1
        if result:
            await conn.execute('UPDATE user_data SET warnings=$1 WHERE user_id=$2 AND guild_id=$3', new_warnings, member.id, ctx.guild.id)
        else:
            await conn.execute('INSERT INTO user_data (user_id, guild_id, warnings) VALUES ($1,$2,$3)', member.id, ctx.guild.id, 1)
    case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "WARN", reason)
    await send_embed(ctx, "⚠️ Warned", f"{member.mention} warned!\n**Total:** {new_warnings}\n**Case:** #{case_id}", discord.Color.orange())

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member = None):
    target = member or ctx.author
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT warnings FROM user_data WHERE user_id=$1 AND guild_id=$2', target.id, ctx.guild.id)
    warnings = result['warnings'] if result else 0
    await send_embed(ctx, f"⚠️ Warnings - {target.name}", f"**Total:** {warnings}", discord.Color.orange() if warnings > 0 else discord.Color.green())

@bot.command(name="clearwarns")
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member):
    async with db_pool.acquire() as conn:
        await conn.execute('UPDATE user_data SET warnings=0 WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
    await send_embed(ctx, "✅ Cleared", f"Warnings cleared for {member.mention}", discord.Color.green())

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
@has_permission("purge")
async def purge(ctx, limit: int, target: discord.Member = None):
    if limit > 100: return await send_embed(ctx, "❌ Limit", "Max 100!", discord.Color.red())
    def check(m): return target is None or m.author == target
    deleted = await ctx.channel.purge(limit=limit+1, check=check)
    await ctx.send(f"✅ Deleted {len(deleted)-1} messages!", delete_after=5)

@bot.command(name="lock")
@has_permission("lock")
async def lock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await send_embed(ctx, "🔒 Locked", f"{channel.mention} locked!", discord.Color.orange())

@bot.command(name="unlock")
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await send_embed(ctx, "🔓 Unlocked", f"{channel.mention} unlocked!", discord.Color.green())

@bot.command(name="slowmode")
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    await channel.edit(slowmode_delay=seconds)
    await send_embed(ctx, "⏱️ Slowmode", f"Set to {seconds}s in {channel.mention}", discord.Color.blue())

@bot.group(name="role")
async def role(ctx): pass

@role.command(name="add")
async def role_add(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        return await send_embed(ctx, "❌ Error", "Cannot assign higher role!", discord.Color.red())
    await member.add_roles(role)
    await send_embed(ctx, "✅ Role Added", f"Gave {role.mention} to {member.mention}", discord.Color.green())

@role.command(name="remove")
async def role_remove(ctx, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await send_embed(ctx, "✅ Role Removed", f"Removed {role.mention} from {member.mention}", discord.Color.green())

@bot.command(name="jail")
@has_permission("jail")
async def jail(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Protected", "Staff protected!", discord.Color.red())
    jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if not jailed_role:
        jailed_role = await ctx.guild.create_role(name="Jailed", color=discord.Color.dark_gray())
    jailed_channel = discord.utils.get(ctx.guild.text_channels, name="jailed-chat")
    if not jailed_channel:
        jailed_channel = await ctx.guild.create_text_channel("jailed-chat")
        await jailed_channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await jailed_channel.set_permissions(jailed_role, view_channel=True, send_messages=True)
    original_roles = [role.id for role in member.roles if role != ctx.guild.default_role]
    async with db_pool.acquire() as conn:
        await conn.execute('INSERT INTO jail_data (user_id, guild_id, original_roles, jailed_by, reason) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (user_id) DO UPDATE SET original_roles=$3, jailed_by=$4, reason=$5', member.id, ctx.guild.id, original_roles, ctx.author.id, reason)
    await member.remove_roles(*[role for role in member.roles if role != ctx.guild.default_role])
    await member.add_roles(jailed_role)
    await send_embed(ctx, "🚔 Jailed", f"{member.mention} has been jailed!\n**Reason:** {reason}", discord.Color.dark_gray())

@bot.command(name="unjail")
@has_permission("unjail")
async def unjail(ctx, member: discord.Member, *, reason: str = "No reason"):
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT original_roles FROM jail_data WHERE user_id=$1', member.id)
        if not result:
            return await send_embed(ctx, "❌ Not Jailed", f"{member.mention} is not jailed!", discord.Color.red())
        original_role_ids = result['original_roles']
        await conn.execute('DELETE FROM jail_data WHERE user_id=$1', member.id)
    jailed_role = discord.utils.get(ctx.guild.roles, name="Jailed")
    if jailed_role in member.roles:
        await member.remove_roles(jailed_role)
    for role_id in original_role_ids:
        role = ctx.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
    await send_embed(ctx, "✅ Unjailed", f"{member.mention} has been unjailed!\n**Reason:** {reason}", discord.Color.green())

@bot.command(name="jailed")
async def jailed(ctx):
    async with db_pool.acquire() as conn:
        results = await conn.fetch('SELECT user_id, reason, jailed_at FROM jail_data WHERE guild_id=$1', ctx.guild.id)
    if not results:
        return await send_embed(ctx, "ℹ️ No Jailed Members", "No one is currently jailed", discord.Color.blue())
    embed = discord.Embed(title="🚔 Jailed Members", color=discord.Color.dark_gray())
    for row in results[:10]:
        member = ctx.guild.get_member(row['user_id'])
        if member:
            embed.add_field(name=member.name, value=f"**Reason:** {row['reason']}\n**Since:** {row['jailed_at'].strftime('%Y-%m-%d')}", inline=False)
    await ctx.send(embed=embed)



# ==================== PART 3 OF 5 ====================
# PASTE AFTER PART 2 - AI Commands & Anti-Systems

"""AI COMMANDS - 25 Personalities + Auto-Response"""

async def call_claude_api(messages, personality):
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key: return "⚠️ AI not configured!"
        client = anthropic.Anthropic(api_key=api_key)
        p = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1500, temperature=0.8, system=p["prompt"], messages=messages)
        return response.content[0].text
    except: return "❌ AI Error!"

@bot.command(name="ai", aliases=["chat", "ask", "claude"])
async def ai(ctx, *, message: str = None):
    """Chat with Claude AI"""
    if not message: return await send_embed(ctx, "🤖 Claude AI", f"Use `{BOT_PREFIX}ai <message>` to chat!\n`{BOT_PREFIX}personalities` to see all personalities", discord.Color.blue())
    async with ctx.typing():
        user_id = ctx.author.id
        if user_id not in ai_conversations:
            ai_conversations[user_id] = {"messages": [], "personality": "friendly", "created_at": datetime.utcnow()}
        conv = ai_conversations[user_id]
        conv["messages"].append({"role": "user", "content": message})
        if len(conv["messages"]) > 30: conv["messages"] = conv["messages"][-30:]
        response = await call_claude_api(conv["messages"], conv["personality"])
        conv["messages"].append({"role": "assistant", "content": response})
        p = AI_PERSONALITIES[conv["personality"]]
        embed = discord.Embed(title=f"{p['emoji']} Claude - {p['name']}", color=discord.Color.blue())
        embed.add_field(name="💬 You", value=message[:1024], inline=False)
        embed.add_field(name="🤖 Response", value=response[:1024], inline=False)
        await ctx.send(embed=embed)

@bot.command(name="aimood", aliases=["personality", "setmood"])
async def aimood(ctx, *, mood: str):
    """Switch AI personality"""
    mood = mood.lower().replace(" ", "")
    matched = None
    for key, data in AI_PERSONALITIES.items():
        if mood in key.lower() or mood in data["name"].lower():
            matched = key
            break
    if not matched: return await send_embed(ctx, "❌ Not Found", f"Try: {', '.join(list(AI_PERSONALITIES.keys())[:10])}...", discord.Color.red())
    if ctx.author.id not in ai_conversations:
        ai_conversations[ctx.author.id] = {"messages": [], "personality": matched, "created_at": datetime.utcnow()}
    else:
        ai_conversations[ctx.author.id]["personality"] = matched
    p = AI_PERSONALITIES[matched]
    await send_embed(ctx, f"{p['emoji']} Personality Set!", f"**{p['name']}** - {p['description']}", discord.Color.green())

@bot.command(name="personalities", aliases=["moods", "persona"])
async def personalities(ctx):
    """See all AI personalities"""
    embed = discord.Embed(title="🎭 25 AI Personalities", description="Switch with `f!aimood <name>`", color=discord.Color.purple())
    text = ", ".join([f"{AI_PERSONALITIES[k]['emoji']}{k}" for k in list(AI_PERSONALITIES.keys())[:25]])
    embed.add_field(name="Available", value=text, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="aiclear", aliases=["chatclear"])
async def aiclear(ctx):
    """Clear AI conversation"""
    if ctx.author.id in ai_conversations:
        ai_conversations[ctx.author.id]["messages"] = []
        await send_embed(ctx, "✅ Cleared", "AI conversation cleared!", discord.Color.green())

@bot.command(name="aichannel")
@is_owner()
async def aichannel(ctx, channel: discord.TextChannel = None):
    """Set AI auto-response channel"""
    if channel is None or channel == "disable":
        ai_config["enabled"] = False
        ai_config["channel_id"] = None
        await send_embed(ctx, "✅ Disabled", "AI auto-response disabled!", discord.Color.green())
    else:
        ai_config["enabled"] = True
        ai_config["channel_id"] = channel.id
        await send_embed(ctx, "✅ AI Channel Set", f"Users can chat naturally in {channel.mention} without using `{BOT_PREFIX}ai`!", discord.Color.green())
"""
ANTI-SYSTEMS: Raid, Alt, Link, Nuke, Automod
All protection systems with full customization
"""

# ========== ANTI-ALT SYSTEM ==========

@bot.group(name="antialt", invoke_without_command=True)
@is_owner()
async def antialt(ctx):
    """Anti-alt detection system"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🔰 Anti-Alt System", 
            f"`{BOT_PREFIX}antialt enable/disable`\n"
            f"`{BOT_PREFIX}antialt minage <days>` - Set minimum account age\n"
            f"`{BOT_PREFIX}antialt action <kick/ban/none>`\n"
            f"`{BOT_PREFIX}antialt status`", discord.Color.blue())

@antialt.command(name="enable")
async def antialt_enable(ctx):
    antialt_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Alt Enabled", "New accounts will be checked!", discord.Color.green())

@antialt.command(name="disable")
async def antialt_disable(ctx):
    antialt_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Alt Disabled", "Alt detection turned off.", discord.Color.red())

@antialt.command(name="minage")
async def antialt_minage(ctx, days: int):
    """Set minimum account age in days"""
    antialt_config["min_age_days"] = days
    await send_embed(ctx, "✅ Minimum Age Set", f"Accounts must be **{days}+ days old** to join!", discord.Color.green())

@antialt.command(name="action")
async def antialt_action(ctx, action: str):
    """Set action for detected alts"""
    if action.lower() not in ["kick", "ban", "none"]:
        return await send_embed(ctx, "❌ Invalid Action", "Use: kick, ban, or none", discord.Color.red())
    antialt_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Alt accounts will be **{action}ed**!", discord.Color.green())

@antialt.command(name="status")
async def antialt_status(ctx):
    """Check anti-alt settings"""
    status = "Enabled ✅" if antialt_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🔰 Anti-Alt Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Minimum Age", value=f"{antialt_config.get('min_age_days', 7)} days", inline=True)
    embed.add_field(name="Action", value=antialt_config.get("action", "kick").title(), inline=True)
    await ctx.send(embed=embed)

# ========== ANTI-RAID SYSTEM ==========

@bot.group(name="antiraid", invoke_without_command=True)
@is_owner()
async def antiraid(ctx):
    """Anti-raid protection"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🛡️ Anti-Raid System",
            f"`{BOT_PREFIX}antiraid enable/disable`\n"
            f"`{BOT_PREFIX}antiraid sensitivity <low/medium/high>`\n"
            f"`{BOT_PREFIX}antiraid status`", discord.Color.blue())

@antiraid.command(name="enable")
async def antiraid_enable(ctx):
    antiraid_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Raid Enabled", "Server protected from raids!", discord.Color.green())

@antiraid.command(name="disable")
async def antiraid_disable(ctx):
    antiraid_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Raid Disabled", "Raid protection turned off.", discord.Color.red())

@antiraid.command(name="sensitivity")
async def antiraid_sensitivity(ctx, level: str):
    """Set raid detection sensitivity"""
    if level.lower() not in ["low", "medium", "high"]:
        return await send_embed(ctx, "❌ Invalid Level", "Use: low, medium, or high", discord.Color.red())
    antiraid_config["sensitivity"] = level.lower()
    thresholds = {"low": "10 joins/10s", "medium": "7 joins/10s", "high": "5 joins/10s"}
    await send_embed(ctx, "✅ Sensitivity Set", f"**{level.title()}** - Triggers at {thresholds[level.lower()]}", discord.Color.green())

@antiraid.command(name="status")
async def antiraid_status(ctx):
    """Check anti-raid settings"""
    status = "Enabled ✅" if antiraid_config.get("enabled") else "Disabled ❌"
    embed = discord.Embed(title="🛡️ Anti-Raid Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Sensitivity", value=antiraid_config.get("sensitivity", "medium").title(), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="lockdown")
@is_owner()
async def lockdown(ctx):
    """Lock entire server"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False, connect=False)
        except:
            pass
    await send_embed(ctx, "🔒 LOCKDOWN ACTIVE", "Server is now locked!", discord.Color.red())

@bot.command(name="unlockdown")
@is_owner()
async def unlockdown(ctx):
    """Unlock server"""
    for channel in ctx.guild.channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None, connect=None)
        except:
            pass
    await send_embed(ctx, "🔓 Lockdown Lifted", "Server is now unlocked!", discord.Color.green())

# ========== ANTI-LINK SYSTEM (ENHANCED!) ==========

@bot.group(name="antilink", invoke_without_command=True)
@is_owner()
async def antilink(ctx):
    """Anti-link system with role/user bypass"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🔗 Anti-Link System",
            f"`{BOT_PREFIX}antilink enable/disable`\n"
            f"`{BOT_PREFIX}antilink whitelist <domain>` - Allow domain\n"
            f"`{BOT_PREFIX}antilink unwhitelist <domain>`\n"
            f"`{BOT_PREFIX}antilink bypass add @role/@user` - **Bypass link filter**\n"
            f"`{BOT_PREFIX}antilink bypass remove @role/@user`\n"
            f"`{BOT_PREFIX}antilink bypass list` - **See who can post links**\n"
            f"`{BOT_PREFIX}antilink action <delete/warn/mute>`\n"
            f"`{BOT_PREFIX}antilink status`", discord.Color.blue())

@antilink.command(name="enable")
async def antilink_enable(ctx):
    antilink_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Link Enabled", "Links will be blocked!", discord.Color.green())

@antilink.command(name="disable")
async def antilink_disable(ctx):
    antilink_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Link Disabled", "Links are now allowed.", discord.Color.red())

@antilink.command(name="whitelist")
async def antilink_whitelist_domain(ctx, domain: str):
    """Whitelist a domain"""
    if "whitelist_domains" not in antilink_config:
        antilink_config["whitelist_domains"] = []
    
    domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    
    if domain not in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].append(domain)
        await send_embed(ctx, "✅ Domain Whitelisted", f"**{domain}** links are now allowed!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Whitelisted", f"{domain} is already whitelisted!", discord.Color.orange())

@antilink.command(name="unwhitelist")
async def antilink_unwhitelist_domain(ctx, domain: str):
    """Remove domain from whitelist"""
    domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    
    if "whitelist_domains" in antilink_config and domain in antilink_config["whitelist_domains"]:
        antilink_config["whitelist_domains"].remove(domain)
        await send_embed(ctx, "✅ Domain Removed", f"**{domain}** removed from whitelist!", discord.Color.green())
    else:
        await send_embed(ctx, "❌ Not Whitelisted", f"{domain} is not in whitelist!", discord.Color.red())

@antilink.group(name="bypass", invoke_without_command=True)
async def antilink_bypass(ctx):
    """Manage link bypass permissions"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🔗 Link Bypass",
            f"`{BOT_PREFIX}antilink bypass add @role/@user`\n"
            f"`{BOT_PREFIX}antilink bypass remove @role/@user`\n"
            f"`{BOT_PREFIX}antilink bypass list`", discord.Color.blue())

@antilink_bypass.command(name="add")
async def bypass_add(ctx, target: Union[discord.Role, discord.Member]):
    """Add role or user to link bypass"""
    if "bypass_roles" not in antilink_config:
        antilink_config["bypass_roles"] = []
    if "bypass_users" not in antilink_config:
        antilink_config["bypass_users"] = []
    
    if isinstance(target, discord.Role):
        if target.id not in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].append(target.id)
            await send_embed(ctx, "✅ Role Added", f"{target.mention} can now post links!", discord.Color.green())
        else:
            await send_embed(ctx, "⚠️ Already Bypassed", f"{target.mention} already has link permissions!", discord.Color.orange())
    else:
        if target.id not in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].append(target.id)
            await send_embed(ctx, "✅ User Added", f"{target.mention} can now post links!", discord.Color.green())
        else:
            await send_embed(ctx, "⚠️ Already Bypassed", f"{target.mention} already has link permissions!", discord.Color.orange())

@antilink_bypass.command(name="remove")
async def bypass_remove(ctx, target: Union[discord.Role, discord.Member]):
    """Remove role or user from link bypass"""
    if isinstance(target, discord.Role):
        if "bypass_roles" in antilink_config and target.id in antilink_config["bypass_roles"]:
            antilink_config["bypass_roles"].remove(target.id)
            await send_embed(ctx, "✅ Role Removed", f"{target.mention} can no longer post links!", discord.Color.green())
        else:
            await send_embed(ctx, "❌ Not Bypassed", f"{target.mention} doesn't have link bypass!", discord.Color.red())
    else:
        if "bypass_users" in antilink_config and target.id in antilink_config["bypass_users"]:
            antilink_config["bypass_users"].remove(target.id)
            await send_embed(ctx, "✅ User Removed", f"{target.mention} can no longer post links!", discord.Color.green())
        else:
            await send_embed(ctx, "❌ Not Bypassed", f"{target.mention} doesn't have link bypass!", discord.Color.red())

@antilink_bypass.command(name="list")
async def bypass_list(ctx):
    """List all bypassed roles and users"""
    embed = discord.Embed(title="🔗 Link Bypass List", color=discord.Color.blue())
    
    # Roles
    if "bypass_roles" in antilink_config and antilink_config["bypass_roles"]:
        roles = [ctx.guild.get_role(r).mention for r in antilink_config["bypass_roles"] if ctx.guild.get_role(r)]
        embed.add_field(name=f"Roles ({len(roles)})", value="\n".join(roles) or "None", inline=False)
    else:
        embed.add_field(name="Roles", value="None", inline=False)
    
    # Users
    if "bypass_users" in antilink_config and antilink_config["bypass_users"]:
        users = [f"<@{u}>" for u in antilink_config["bypass_users"]]
        embed.add_field(name=f"Users ({len(users)})", value="\n".join(users) or "None", inline=False)
    else:
        embed.add_field(name="Users", value="None", inline=False)
    
    await ctx.send(embed=embed)

@antilink.command(name="action")
async def antilink_action(ctx, action: str):
    """Set action for link violations"""
    if action.lower() not in ["delete", "warn", "mute"]:
        return await send_embed(ctx, "❌ Invalid Action", "Use: delete, warn, or mute", discord.Color.red())
    antilink_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Links will trigger: **{action}**", discord.Color.green())

@antilink.command(name="status")
async def antilink_status(ctx):
    """Check anti-link settings"""
    status = "Enabled ✅" if antilink_config.get("enabled") else "Disabled ❌"
    
    embed = discord.Embed(title="🔗 Anti-Link Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Action", value=antilink_config.get("action", "delete").title(), inline=True)
    
    # Whitelisted domains
    domains = antilink_config.get("whitelist_domains", [])
    domain_text = ", ".join(domains[:5]) if domains else "None"
    if len(domains) > 5:
        domain_text += f" (+{len(domains)-5} more)"
    embed.add_field(name="Whitelisted Domains", value=domain_text, inline=False)
    
    # Bypassed roles/users count
    bypass_roles = len(antilink_config.get("bypass_roles", []))
    bypass_users = len(antilink_config.get("bypass_users", []))
    embed.add_field(name="Bypass Permissions", value=f"**Roles:** {bypass_roles}\n**Users:** {bypass_users}", inline=False)
    
    await ctx.send(embed=embed)

# ========== ANTI-NUKE SYSTEM ==========

@bot.group(name="antinuke", invoke_without_command=True)
@is_owner()
async def antinuke(ctx):
    """Anti-nuke protection"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🛡️ Anti-Nuke System",
            f"`{BOT_PREFIX}antinuke enable/disable`\n"
            f"`{BOT_PREFIX}antinuke whitelist @user`\n"
            f"`{BOT_PREFIX}antinuke unwhitelist @user`\n"
            f"`{BOT_PREFIX}antinuke status`", discord.Color.blue())

@antinuke.command(name="enable")
async def antinuke_enable(ctx):
    antinuke_config["enabled"] = True
    await send_embed(ctx, "✅ Anti-Nuke Enabled", "Server protected from mass actions!", discord.Color.green())

@antinuke.command(name="disable")
async def antinuke_disable(ctx):
    antinuke_config["enabled"] = False
    await send_embed(ctx, "❌ Anti-Nuke Disabled", "Protection turned off.", discord.Color.red())

@antinuke.command(name="whitelist")
async def antinuke_whitelist(ctx, user: discord.Member):
    """Whitelist trusted user"""
    if "whitelist" not in antinuke_config:
        antinuke_config["whitelist"] = []
    
    if user.id not in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].append(user.id)
        await send_embed(ctx, "✅ User Whitelisted", f"{user.mention} is now trusted!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Whitelisted", f"{user.mention} is already trusted!", discord.Color.orange())

@antinuke.command(name="unwhitelist")
async def antinuke_unwhitelist(ctx, user: discord.Member):
    """Remove user from whitelist"""
    if "whitelist" in antinuke_config and user.id in antinuke_config["whitelist"]:
        antinuke_config["whitelist"].remove(user.id)
        await send_embed(ctx, "✅ User Removed", f"{user.mention} removed from whitelist!", discord.Color.green())
    else:
        await send_embed(ctx, "❌ Not Whitelisted", f"{user.mention} is not whitelisted!", discord.Color.red())

@antinuke.command(name="status")
async def antinuke_status(ctx):
    """Check anti-nuke settings"""
    status = "Enabled ✅" if antinuke_config.get("enabled") else "Disabled ❌"
    
    embed = discord.Embed(title="🛡️ Anti-Nuke Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    
    whitelist = antinuke_config.get("whitelist", [])
    if whitelist:
        users = [f"<@{u}>" for u in whitelist]
        embed.add_field(name="Whitelisted Users", value="\n".join(users), inline=False)
    else:
        embed.add_field(name="Whitelisted Users", value="None", inline=False)
    
    embed.add_field(name="Protection", value="• Mass channel deletion\n• Mass role deletion\n• Mass bans/kicks", inline=False)
    
    await ctx.send(embed=embed)

 # ========== AI AUTOMOD ==========

@bot.group(name="automod", invoke_without_command=True)
@is_owner()
async def automod(ctx):
    """AI-powered automod"""
    if ctx.invoked_subcommand is None:
        await send_embed(ctx, "🤖 AI Automod",
            f"`{BOT_PREFIX}automod enable/disable`\n"
            f"`{BOT_PREFIX}automod sensitivity <low/medium/high/strict>`\n"
            f"`{BOT_PREFIX}automod action <delete/warn/mute/kick>`\n"
            f"`{BOT_PREFIX}automod ignore #channel`\n"
            f"`{BOT_PREFIX}automod whitelist @role`\n"
            f"`{BOT_PREFIX}automod status`", discord.Color.blue())

@automod.command(name="enable")
async def automod_enable(ctx):
    automod_config["enabled"] = True
    await send_embed(ctx, "✅ AI Automod Enabled", "Claude is now monitoring messages!", discord.Color.green())

@automod.command(name="disable")
async def automod_disable(ctx):
    automod_config["enabled"] = False
    await send_embed(ctx, "❌ AI Automod Disabled", "Automatic moderation turned off.", discord.Color.red())

@automod.command(name="sensitivity")
async def automod_sensitivity(ctx, level: str):
    """Set detection sensitivity"""
    if level.lower() not in ["low", "medium", "high", "strict"]:
        return await send_embed(ctx, "❌ Invalid Level", "Use: low, medium, high, or strict", discord.Color.red())
    automod_config["sensitivity"] = level.lower()
    await send_embed(ctx, "✅ Sensitivity Set", f"Detection level: **{level.title()}**", discord.Color.green())

@automod.command(name="action")
async def automod_action(ctx, action: str):
    """Set punishment for violations"""
    if action.lower() not in ["delete", "warn", "mute", "kick"]:
        return await send_embed(ctx, "❌ Invalid Action", "Use: delete, warn, mute, or kick", discord.Color.red())
    automod_config["action"] = action.lower()
    await send_embed(ctx, "✅ Action Set", f"Violations will: **{action}**", discord.Color.green())

@automod.command(name="ignore")
async def automod_ignore(ctx, channel: discord.TextChannel):
    """Ignore channel from automod"""
    if "ignored_channels" not in automod_config:
        automod_config["ignored_channels"] = []
    
    if channel.id not in automod_config["ignored_channels"]:
        automod_config["ignored_channels"].append(channel.id)
        await send_embed(ctx, "✅ Channel Ignored", f"{channel.mention} will be ignored by automod!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Ignored", f"{channel.mention} is already ignored!", discord.Color.orange())

@automod.command(name="whitelist")
async def automod_whitelist_role(ctx, role: discord.Role):
    """Whitelist role from automod"""
    if "whitelisted_roles" not in automod_config:
        automod_config["whitelisted_roles"] = []
    
    if role.id not in automod_config["whitelisted_roles"]:
        automod_config["whitelisted_roles"].append(role.id)
        await send_embed(ctx, "✅ Role Whitelisted", f"{role.mention} exempt from automod!", discord.Color.green())
    else:
        await send_embed(ctx, "⚠️ Already Whitelisted", f"{role.mention} is already whitelisted!", discord.Color.orange())

@automod.command(name="status")
async def automod_status(ctx):
    """Check automod settings"""
    status = "Enabled ✅" if automod_config.get("enabled") else "Disabled ❌"
    
    embed = discord.Embed(title="🤖 AI Automod Status", color=discord.Color.blue())
    embed.add_field(name="Status", value=status, inline=False)
    embed.add_field(name="Sensitivity", value=automod_config.get("sensitivity", "medium").title(), inline=True)
    embed.add_field(name="Action", value=automod_config.get("action", "warn").title(), inline=True)
    
    ignored = len(automod_config.get("ignored_channels", []))
    whitelisted = len(automod_config.get("whitelisted_roles", []))
    embed.add_field(name="Exemptions", value=f"**Channels:** {ignored}\n**Roles:** {whitelisted}", inline=False)
    
    await ctx.send(embed=embed)

# ==================== PART 4 OF 5 ====================
# PASTE AFTER PART 3 - Whitelist & Moderation

"""
COMPLETE WHITELIST SYSTEM
Owner can whitelist users/roles for specific commands OR everything at once
"""

@bot.group(name="whitelist", invoke_without_command=True)
@is_owner()
async def whitelist(ctx):
    """Whitelist management system (Owner only)"""
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(title="🔐 Whitelist System", color=discord.Color.blue())
        embed.add_field(
            name="Commands",
            value=f"`{BOT_PREFIX}whitelist add <command> @role/@user` - Whitelist for specific command\n"
                  f"`{BOT_PREFIX}whitelist addall @role/@user` - **Whitelist for EVERYTHING**\n"
                  f"`{BOT_PREFIX}whitelist remove <command> @role/@user` - Remove whitelist\n"
                  f"`{BOT_PREFIX}whitelist removeall @role/@user` - Remove ALL whitelists\n"
                  f"`{BOT_PREFIX}whitelist list [command]` - View whitelists\n"
                  f"`{BOT_PREFIX}whitelist clear <command>` - Clear command whitelist",
            inline=False
        )
        await ctx.send(embed=embed)

@whitelist.command(name="add")
async def whitelist_add(ctx, command_name: str, target: Union[discord.Role, discord.Member]):
    """Whitelist role/user for specific command"""
    # Check if command exists
    cmd = bot.get_command(command_name)
    if not cmd:
        return await send_embed(ctx, "❌ Command Not Found", f"No command named `{command_name}`", discord.Color.red())
    
    # Initialize command whitelist if not exists
    if command_name not in whitelist_data["commands"]:
        whitelist_data["commands"][command_name] = {"roles": [], "users": []}
    
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    entity_list = whitelist_data["commands"][command_name]["roles" if entity_type == "role" else "users"]
    
    # Check if already whitelisted
    if target.id in entity_list:
        return await send_embed(ctx, "⚠️ Already Whitelisted", 
            f"{target.mention} already has access to `{command_name}`", discord.Color.orange())
    
    # Add to whitelist
    entity_list.append(target.id)
    
    # Save to database
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO whitelist (command_name, entity_type, entity_id, added_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (command_name, entity_type, entity_id) DO NOTHING
        ''', command_name, entity_type, target.id, ctx.author.id)
    
    await send_embed(ctx, "✅ Whitelisted", 
        f"{target.mention} can now use `{BOT_PREFIX}{command_name}`!", discord.Color.green())
    
    await db_manager.log_action("WHITELIST_ADD", ctx.author.id,
        f"Whitelisted {target.name} for {command_name}", guild_id=ctx.guild.id)

@whitelist.command(name="addall")
async def whitelist_addall(ctx, target: Union[discord.Role, discord.Member]):
    """Whitelist role/user for ALL COMMANDS"""
    added_count = 0
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    
    # Get all bot commands
    all_commands = [cmd.name for cmd in bot.commands if cmd.name not in ["help", "info", "ping"]]
    
    async with db_pool.acquire() as conn:
        for command_name in all_commands:
            # Initialize if not exists
            if command_name not in whitelist_data["commands"]:
                whitelist_data["commands"][command_name] = {"roles": [], "users": []}
            
            entity_list = whitelist_data["commands"][command_name]["roles" if entity_type == "role" else "users"]
            
            # Add if not already whitelisted
            if target.id not in entity_list:
                entity_list.append(target.id)
                
                # Save to database
                await conn.execute('''
                    INSERT INTO whitelist (command_name, entity_type, entity_id, added_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (command_name, entity_type, entity_id) DO NOTHING
                ''', command_name, entity_type, target.id, ctx.author.id)
                
                added_count += 1
    
    embed = discord.Embed(
        title="✅ Full Access Granted!",
        description=f"{target.mention} now has access to **ALL COMMANDS**!",
        color=discord.Color.green()
    )
    embed.add_field(name="Commands Whitelisted", value=f"{added_count} commands", inline=False)
    await ctx.send(embed=embed)
    
    await db_manager.log_action("WHITELIST_ADDALL", ctx.author.id,
        f"Whitelisted {target.name} for ALL commands ({added_count})", guild_id=ctx.guild.id)

@whitelist.command(name="remove")
async def whitelist_remove(ctx, command_name: str, target: Union[discord.Role, discord.Member]):
    """Remove whitelist for specific command"""
    if command_name not in whitelist_data["commands"]:
        return await send_embed(ctx, "❌ Not Whitelisted", 
            f"`{command_name}` has no whitelist entries", discord.Color.red())
    
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    entity_list = whitelist_data["commands"][command_name]["roles" if entity_type == "role" else "users"]
    
    if target.id not in entity_list:
        return await send_embed(ctx, "❌ Not Found", 
            f"{target.mention} doesn't have access to `{command_name}`", discord.Color.red())
    
    # Remove from whitelist
    entity_list.remove(target.id)
    
    # Remove from database
    async with db_pool.acquire() as conn:
        await conn.execute('''
            DELETE FROM whitelist
            WHERE command_name = $1 AND entity_type = $2 AND entity_id = $3
        ''', command_name, entity_type, target.id)
    
    await send_embed(ctx, "✅ Removed", 
        f"{target.mention} can no longer use `{BOT_PREFIX}{command_name}`", discord.Color.green())
    
    await db_manager.log_action("WHITELIST_REMOVE", ctx.author.id,
        f"Removed {target.name} from {command_name} whitelist", guild_id=ctx.guild.id)

@whitelist.command(name="removeall")
async def whitelist_removeall(ctx, target: Union[discord.Role, discord.Member]):
    """Remove ALL whitelists for a user/role"""
    removed_count = 0
    entity_type = "role" if isinstance(target, discord.Role) else "user"
    
    async with db_pool.acquire() as conn:
        for command_name, data in list(whitelist_data["commands"].items()):
            entity_list = data["roles" if entity_type == "role" else "users"]
            
            if target.id in entity_list:
                entity_list.remove(target.id)
                
                # Remove from database
                await conn.execute('''
                    DELETE FROM whitelist
                    WHERE command_name = $1 AND entity_type = $2 AND entity_id = $3
                ''', command_name, entity_type, target.id)
                
                removed_count += 1
    
    if removed_count == 0:
        return await send_embed(ctx, "ℹ️ No Whitelists", 
            f"{target.mention} has no whitelist entries", discord.Color.blue())
    
    embed = discord.Embed(
        title="✅ All Whitelists Removed",
        description=f"{target.mention} access revoked from all commands",
        color=discord.Color.green()
    )
    embed.add_field(name="Removed From", value=f"{removed_count} commands", inline=False)
    await ctx.send(embed=embed)
    
    await db_manager.log_action("WHITELIST_REMOVEALL", ctx.author.id,
        f"Removed all whitelists for {target.name} ({removed_count})", guild_id=ctx.guild.id)

@whitelist.command(name="list")
async def whitelist_list(ctx, command_name: str = None):
    """List whitelisted commands"""
    if command_name:
        # Show whitelist for specific command
        if command_name not in whitelist_data["commands"]:
            return await send_embed(ctx, "ℹ️ No Whitelist", 
                f"`{command_name}` has no whitelist entries", discord.Color.blue())
        
        data = whitelist_data["commands"][command_name]
        
        embed = discord.Embed(
            title=f"🔒 Whitelist: {command_name}",
            color=discord.Color.blue()
        )
        
        # Roles
        if data["roles"]:
            role_mentions = []
            for role_id in data["roles"]:
                role = ctx.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            
            if role_mentions:
                embed.add_field(name=f"Roles ({len(role_mentions)})", 
                              value="\n".join(role_mentions), inline=False)
        
        # Users
        if data["users"]:
            user_mentions = [f"<@{user_id}>" for user_id in data["users"]]
            embed.add_field(name=f"Users ({len(user_mentions)})", 
                          value="\n".join(user_mentions), inline=False)
        
        if not data["roles"] and not data["users"]:
            embed.description = "No entries"
        
        await ctx.send(embed=embed)
    
    else:
        # Show all whitelisted commands
        if not whitelist_data["commands"]:
            return await send_embed(ctx, "ℹ️ No Whitelists", 
                "No commands have whitelist entries", discord.Color.blue())
        
        embed = discord.Embed(
            title="🔒 All Whitelisted Commands",
            description=f"Total: {len(whitelist_data['commands'])} commands",
            color=discord.Color.blue()
        )
        
        for cmd, data in list(whitelist_data["commands"].items())[:25]:
            roles_count = len(data.get("roles", []))
            users_count = len(data.get("users", []))
            
            if roles_count > 0 or users_count > 0:
                embed.add_field(
                    name=f"`{cmd}`",
                    value=f"Roles: {roles_count} | Users: {users_count}",
                    inline=True
                )
        
        if len(whitelist_data["commands"]) > 25:
            embed.set_footer(text=f"Showing 25 of {len(whitelist_data['commands'])} commands")
        
        await ctx.send(embed=embed)

@whitelist.command(name="clear")
async def whitelist_clear(ctx, command_name: str):
    """Clear all whitelist entries for a command"""
    if command_name not in whitelist_data["commands"]:
        return await send_embed(ctx, "ℹ️ No Whitelist", 
            f"`{command_name}` has no whitelist entries", discord.Color.blue())
    
    # Count entries
    data = whitelist_data["commands"][command_name]
    total = len(data.get("roles", [])) + len(data.get("users", []))
    
    # Clear from memory
    del whitelist_data["commands"][command_name]
    
    # Clear from database
    async with db_pool.acquire() as conn:
        await conn.execute('DELETE FROM whitelist WHERE command_name = $1', command_name)
    
    await send_embed(ctx, "✅ Whitelist Cleared", 
        f"Removed {total} entries from `{command_name}`", discord.Color.green())
    
    await db_manager.log_action("WHITELIST_CLEAR", ctx.author.id,
        f"Cleared whitelist for {command_name} ({total} entries)", guild_id=ctx.guild.id)
"""
ALL COMMANDS - Complete System
91+ commands: Moderation, Utility, Help, Anti-systems, AI, etc.
"""

# This continues from previous files

# ========== PAGINATED HELP SYSTEM ==========

class HelpView(View):
    """Paginated help with ◀️▶️ navigation"""
    
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.current_page = 0
        self.pages = self.create_pages()
    
    def create_pages(self):
        """Create all help pages"""
        pages = []
        
        # Page 1: Security & Verification
        embed1 = discord.Embed(title="🛡️ Security & Verification", color=discord.Color.blue())
        embed1.add_field(name=f"{BOT_PREFIX}setup", value="Setup verification system", inline=False)
        embed1.add_field(name=f"{BOT_PREFIX}verification [enable/disable/status]", value="Manage verification", inline=False)
        embed1.set_footer(text="Page 1/10 | Use arrows to navigate")
        pages.append(embed1)
        
        # Page 2: Moderation
        embed2 = discord.Embed(title="⚖️ Moderation Commands", color=discord.Color.orange())
        embed2.add_field(name="Kicks & Bans", value=
                        f"`{BOT_PREFIX}kick @user [reason]`\n"
                        f"`{BOT_PREFIX}softban @user [reason]`\n"
                        f"`{BOT_PREFIX}ban @user [reason]`\n"
                        f"`{BOT_PREFIX}unban <id> [reason]`\n"
                        f"`{BOT_PREFIX}tempban @user <time> [reason]`", inline=False)
        embed2.add_field(name="Mutes & Timeouts", value=
                        f"`{BOT_PREFIX}mute @user [time] [reason]`\n"
                        f"`{BOT_PREFIX}unmute @user [reason]`\n"
                        f"`{BOT_PREFIX}timeout @user <time> [reason]`\n"
                        f"`{BOT_PREFIX}untimeout @user [reason]`", inline=False)
        embed2.add_field(name="Warnings", value=
                        f"`{BOT_PREFIX}warn @user [reason]`\n"
                        f"`{BOT_PREFIX}warnings [@user]`\n"
                        f"`{BOT_PREFIX}clearwarns @user`", inline=False)
        embed2.set_footer(text="Page 2/10")
        pages.append(embed2)
        
        # Page 3: Message & Channel Management
        embed3 = discord.Embed(title="💬 Message & Channel Management", color=discord.Color.green())
        embed3.add_field(name="Message Purge", value=
                        f"`{BOT_PREFIX}purge <amount>`\n"
                        f"`{BOT_PREFIX}purge @user <amount>`\n"
                        f"`{BOT_PREFIX}purge bots <amount>`\n"
                        f"`{BOT_PREFIX}purge contains <word> <amount>`\n"
                        f"`{BOT_PREFIX}purge embeds/links/images <amount>`\n"
                        f"`{BOT_PREFIX}clear <amount>` (alias)", inline=False)
        embed3.add_field(name="Channel Control", value=
                        f"`{BOT_PREFIX}lock [#channel]`\n"
                        f"`{BOT_PREFIX}unlock [#channel]`\n"
                        f"`{BOT_PREFIX}slowmode [#channel] <seconds>`\n"
                        f"`{BOT_PREFIX}nick @user <nickname>`\n"
                        f"`{BOT_PREFIX}resetnick @user`", inline=False)
        embed3.set_footer(text="Page 3/10")
        pages.append(embed3)
        
        # Page 4: Role Management
        embed4 = discord.Embed(title="👥 Role Management", color=discord.Color.purple())
        embed4.add_field(name="Role Commands", value=
                        f"`{BOT_PREFIX}role add @user @role`\n"
                        f"`{BOT_PREFIX}role remove @user @role`\n"
                        f"`{BOT_PREFIX}role create <name> [color]`\n"
                        f"`{BOT_PREFIX}role delete @role`\n"
                        f"`{BOT_PREFIX}role info @role`", inline=False)
        embed4.set_footer(text="Page 4/10")
        pages.append(embed4)
        
        # Page 5: Jail System
        embed5 = discord.Embed(title="🚔 Jail System", color=discord.Color.dark_gray())
        embed5.add_field(name="Jail Commands", value=
                        f"`{BOT_PREFIX}jail @user [reason]` - Saves roles, restricts access\n"
                        f"`{BOT_PREFIX}unjail @user [reason]` - Restores original roles\n"
                        f"`{BOT_PREFIX}jailed` - List all jailed members", inline=False)
        embed5.set_footer(text="Page 5/10")
        pages.append(embed5)
        
        # Page 6: Anti-Systems
        embed6 = discord.Embed(title="🛡️ Anti-Raid/Alt/Link/Nuke", color=discord.Color.red())
        embed6.add_field(name="Anti-Raid", value=
                        f"`{BOT_PREFIX}antiraid enable/disable/status`\n"
                        f"`{BOT_PREFIX}antiraid sensitivity <low/medium/high>`\n"
                        f"`{BOT_PREFIX}lockdown` / `{BOT_PREFIX}unlockdown`", inline=False)
        embed6.add_field(name="Anti-Alt", value=
                        f"`{BOT_PREFIX}antialt enable/disable/status`\n"
                        f"`{BOT_PREFIX}antialt minage <days>`\n"
                        f"`{BOT_PREFIX}antialt action <kick/ban/none>`", inline=False)
        embed6.add_field(name="Anti-Link", value=
                        f"`{BOT_PREFIX}antilink enable/disable/status`\n"
                        f"`{BOT_PREFIX}antilink whitelist/unwhitelist <url>`", inline=False)
        embed6.add_field(name="Anti-Nuke", value=
                        f"`{BOT_PREFIX}antinuke enable/disable/status`\n"
                        f"`{BOT_PREFIX}antinuke whitelist/unwhitelist @user`", inline=False)
        embed6.set_footer(text="Page 6/10")
        pages.append(embed6)
        
        # Page 7: AI Automod
        embed7 = discord.Embed(title="🤖 AI Automod (Claude-Powered)", color=discord.Color.blue())
        embed7.add_field(name="AI Automod Commands", value=
                        f"`{BOT_PREFIX}automod enable/disable/status`\n"
                        f"`{BOT_PREFIX}automod sensitivity <low/medium/high/strict>`\n"
                        f"`{BOT_PREFIX}automod action <delete/warn/mute/kick>`\n"
                        f"`{BOT_PREFIX}automod ignore/unignore #channel`\n"
                        f"`{BOT_PREFIX}automod whitelist @role`\n"
                        f"`{BOT_PREFIX}automod test <message>`", inline=False)
        embed7.add_field(name="Detects", value="Profanity, Toxicity, Spam, NSFW, Threats, Hate Speech", inline=False)
        embed7.set_footer(text="Page 7/10")
        pages.append(embed7)
        
        # Page 8: AI Chat (25 Personalities)
        embed8 = discord.Embed(title="💬 AI Chat System", color=discord.Color.gold())
        embed8.add_field(name="AI Commands", value=
                        f"`{BOT_PREFIX}ai <message>` (aliases: chat, ask, claude)\n"
                        f"`{BOT_PREFIX}aimood <personality>` (aliases: personality, setmood)\n"
                        f"`{BOT_PREFIX}personalities` (aliases: moods, persona)\n"
                        f"`{BOT_PREFIX}aiclear` (aliases: chatclear)\n"
                        f"`{BOT_PREFIX}aichannel #channel` - Auto-response channel\n"
                        f"`{BOT_PREFIX}aichannel disable` - Disable auto-response", inline=False)
        embed8.add_field(name="25 Personalities", value=
                        "friendly, sassy, mean, cool, nerdy, gamer, pirate, uwu, gen-z, robot, chaotic, wholesome, motivational, tsundere, shakespearean, detective, zen, comedic, karen, creative, casual, wise, enthusiastic, technical, professional",
                        inline=False)
        embed8.set_footer(text="Page 8/10")
        pages.append(embed8)
        
        # Page 9: Permissions & Logging
        embed9 = discord.Embed(title="🔐 Permissions & Logging", color=discord.Color.teal())
        embed9.add_field(name="Custom Permissions", value=
                        f"`{BOT_PREFIX}perm set <command> @role/@user`\n"
                        f"`{BOT_PREFIX}perm remove <command> @role/@user`\n"
                        f"`{BOT_PREFIX}perm list [command]`\n"
                        f"`{BOT_PREFIX}perm reset <command>`", inline=False)
        embed9.add_field(name="Whitelisting (Owner)", value=
                        f"`{BOT_PREFIX}whitelist add/remove <cmd> @role/@user`\n"
                        f"`{BOT_PREFIX}whitelist list [command]`", inline=False)
        embed9.add_field(name="Logging", value=
                        f"`{BOT_PREFIX}logs view/search/export`\n"
                        f"`{BOT_PREFIX}logs user/modlogs @user`\n"
                        f"`{BOT_PREFIX}modstats [@mod]`\n"
                        f"`{BOT_PREFIX}cases @user` | `{BOT_PREFIX}case <id>`", inline=False)
        embed9.set_footer(text="Page 9/10")
        pages.append(embed9)

    
        # Page 10: Utility Commands
        embed10 = discord.Embed(title="🔧 Utility Commands", color=discord.Color.light_grey())
        embed10.add_field(name="Server Info", value=
                         f"`{BOT_PREFIX}serverinfo` (alias: si)\n"
                         f"`{BOT_PREFIX}sav` - Server avatar (aliases: serveravatar)\n"
                         f"`{BOT_PREFIX}membercount` (alias: mc)\n"
                         f"`{BOT_PREFIX}roles` - List all roles", inline=False)
        embed10.add_field(name="User Info", value=
                         f"`{BOT_PREFIX}userinfo [@user]` (aliases: ui, whois)\n"
                         f"`{BOT_PREFIX}av [@user]` - Avatar (aliases: avatar, pfp)\n"
                         f"`{BOT_PREFIX}banner [@user]` - User banner\n"
                         f"`{BOT_PREFIX}roleinfo @role` (alias: ri)", inline=False)
        embed10.add_field(name="Channel Info", value=
                         f"`{BOT_PREFIX}channelinfo [#channel]` (alias: ci)", inline=False)
        embed10.add_field(name="General", value=
                         f"`{BOT_PREFIX}help` - This menu\n"
                         f"`{BOT_PREFIX}info` - Bot info\n"
                         f"`{BOT_PREFIX}ping` - Bot latency", inline=False)
        embed10.set_footer(text="Page 10/10")
        pages.append(embed10)
        
        return pages
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Not your help menu!", ephemeral=True)
            return
        
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Not your help menu!", ephemeral=True)
            return
        
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

@bot.command(name="help")
async def help_command(ctx, *, command_name: str = None):
    """
    Show help menu with navigation
    Usage: f!help [command]
    """
    if command_name:
        cmd = bot.get_command(command_name)
        if not cmd:
            await send_embed(ctx, "❌ Command Not Found", f"No command named `{command_name}`", discord.Color.red())
            return
        
        usage = COMMAND_USAGE.get(command_name, {})
        
        embed = discord.Embed(title=f"📖 {BOT_PREFIX}{cmd.name}", color=discord.Color.blue())
        embed.add_field(name="Description", value=cmd.help or "No description", inline=False)
        
        if usage:
            embed.add_field(name="Usage", value=f"`{usage['usage']}`", inline=False)
            embed.add_field(name="Example", value=f"`{usage['example']}`", inline=False)
        
        if cmd.aliases:
            embed.add_field(name="Aliases", value=", ".join([f"`{a}`" for a in cmd.aliases]), inline=False)
        
        await ctx.send(embed=embed)
    else:
        view = HelpView(ctx)
        await ctx.send(embed=view.pages[0], view=view)

# ========== UTILITY COMMANDS ==========

@bot.command(name="av", aliases=["avatar", "pfp"])
async def avatar(ctx, member: discord.Member = None):
    """Show user's avatar"""
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
    avatar_url = target.avatar.url if target.avatar else target.default_avatar.url
    embed.set_image(url=avatar_url)
    embed.add_field(name="Download", value=f"[Click Here]({avatar_url})")
    await ctx.send(embed=embed)

@bot.command(name="sav", aliases=["serveravatar", "servericon"])
async def server_avatar(ctx):
    """Show server's avatar/icon"""
    if not ctx.guild.icon:
        await send_embed(ctx, "❌ No Icon", "This server has no icon set.", discord.Color.red())
        return
    
    embed = discord.Embed(title=f"{ctx.guild.name}'s Icon", color=discord.Color.blue())
    embed.set_image(url=ctx.guild.icon.url)
    embed.add_field(name="Download", value=f"[Click Here]({ctx.guild.icon.url})")
    await ctx.send(embed=embed)

@bot.command(name="si", aliases=["serverinfo"])
async def server_info(ctx):
    """Show server information"""
    g = ctx.guild
    embed = discord.Embed(title=f"📊 {g.name}", color=discord.Color.blue(), timestamp=datetime.utcnow())
    
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    
    embed.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
    embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Members", value=f"{g.member_count:,}", inline=True)
    embed.add_field(name="Channels", value=f"{len(g.channels)}", inline=True)
    embed.add_field(name="Roles", value=f"{len(g.roles)}", inline=True)
    embed.add_field(name="Boost Level", value=f"Level {g.premium_tier}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="ui", aliases=["userinfo", "whois"])
async def user_info(ctx, member: discord.Member = None):
    """Show user information"""
    target = member or ctx.author
    embed = discord.Embed(title=f"👤 {target.name}", color=target.color, timestamp=datetime.utcnow())
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "Unknown", inline=True)
    embed.add_field(name="Roles", value=f"{len(target.roles)-1}", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    color = discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
    await send_embed(ctx, "🏓 Pong!", f"**Latency:** {latency}ms", color)

@bot.command(name="info")
async def bot_info(ctx):
    """Bot information"""
    embed = discord.Embed(title="🤖 Bot Information", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Commands", value=len(bot.commands), inline=True)
    embed.add_field(name="Prefix", value=f"`{BOT_PREFIX}`", inline=True)
    embed.add_field(name="Features", value=
                   "✅ 91+ Commands\n"
                   "✅ AI Chat (25 personalities)\n"
                   "✅ Anti-Raid/Alt/Link/Nuke\n"
                   "✅ Smart Error Correction\n"
                   "✅ Custom Permissions", inline=False)
    await ctx.send(embed=embed)

# Note: Due to length, I'll continue with moderation commands in the next artifact
# This file needs to be combined with moderation.py, ai_commands.py, etc.


# ==================== PART 5 OF 5 ====================
# PASTE LAST - Help, Utilities & Startup Code

# ==================== UTILITY COMMANDS (PART 5) ====================

@bot.command(name="skin", aliases=["skinav", "ownpfp"])
async def avatar(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"{target.name}'s Avatar", color=discord.Color.blue())
    avatar_url = target.avatar.url if target.avatar else target.default_avatar.url
    embed.set_image(url=avatar_url)
    embed.add_field(name="Download", value=f"[Click Here]({avatar_url})")
    await ctx.send(embed=embed)

@bot.command(name="spfp", aliases=["serverpfp", "pfpserver"])
async def server_avatar(ctx):
    if not ctx.guild.icon:
        return await send_embed(ctx, "❌ No Icon", "No server icon!", discord.Color.red())
    embed = discord.Embed(title=f"{ctx.guild.name}'s Icon", color=discord.Color.blue())
    embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)

@bot.command(name="is", aliases=["infoserver"])
async def server_info(ctx):
    g = ctx.guild
    embed = discord.Embed(title=f"📊 {g.name}", color=discord.Color.blue())
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner", value=g.owner.mention if g.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=f"{g.member_count:,}", inline=True)
    embed.add_field(name="Channels", value=f"{len(g.channels)}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="iu", aliases=["infouser", "whois"])
async def user_info(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"👤 {target.name}", color=target.color)
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="ID", value=target.id, inline=True)
    embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Roles", value=f"{len(target.roles)-1}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    color = discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
    await send_embed(ctx, "🏓 Pong!", f"**Latency:** {latency}ms", color)

@bot.command(name="info")
async def bot_info(ctx):
    embed = discord.Embed(title="🤖 Bot Info", color=discord.Color.blue())
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Commands", value=len(bot.commands), inline=True)
    embed.add_field(name="Prefix", value=f"`{BOT_PREFIX}`", inline=True)
    await ctx.send(embed=embed)

# ==================== STARTUP CODE (END OF PART 5) ====================
async def handle(request):
    return web.Response(text="Bot alive! 🤖")

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
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    logger.info("="*60)
    logger.info("🚀 ULTIMATE DISCORD BOT - STARTING")
    logger.info(f"📌 Prefix: {BOT_PREFIX}")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"🛡️ Staff Protected: {STAFF_ROLE_ID}")
    logger.info("="*60)
    
    await start_web_server()
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot shutdown")
    except Exception as e:
        logger.error(f"❌ FATAL: {e}")
        logger.error(traceback.format_exc())
