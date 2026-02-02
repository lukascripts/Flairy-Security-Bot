"""
Ultimate Discord Security Bot - Main Setup
All core imports, configurations, and utilities
"""

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
import random
import asyncpg
from collections import defaultdict
import traceback
import re
from difflib import get_close_matches

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger('DiscordBot')

# Configuration
BOT_PREFIX = "f!"
OWNER_ID = 1029438856069656576
STAFF_ROLE_ID = 1432081794647199895
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Intents
intents = discord.Intents.all()

# Bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None, case_insensitive=True)

# Global storage
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

# Database
db_pool = None
db_manager = None

# Command usage examples
COMMAND_USAGE = {
    "kick": {"usage": "f!kick @user [reason]", "example": "f!kick @BadUser spamming"},
    "ban": {"usage": "f!ban @user [reason]", "example": "f!ban @BadUser raiding"},
    "mute": {"usage": "f!mute @user [time] [reason]", "example": "f!mute @user 1h spamming"},
    "timeout": {"usage": "f!timeout @user <time> [reason]", "example": "f!timeout @user 10m spam"},
    "untimeout": {"usage": "f!untimeout @user [reason]", "example": "f!untimeout @user mistake"},
    "warn": {"usage": "f!warn @user [reason]", "example": "f!warn @user breaking rules"},
    "purge": {"usage": "f!purge <amount>", "example": "f!purge 50"},
    "jail": {"usage": "f!jail @user [reason]", "example": "f!jail @user toxicity"},
    "ai": {"usage": "f!ai <message>", "example": "f!ai What is Python?"},
}

# Database Manager
class DatabaseManager:
    def __init__(self, pool):
        self.pool = pool
    
    async def initialize_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''CREATE TABLE IF NOT EXISTS whitelist (
                id SERIAL PRIMARY KEY, command_name TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id BIGINT NOT NULL, added_by BIGINT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(command_name, entity_type, entity_id))''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS permissions (
                id SERIAL PRIMARY KEY, command_name TEXT NOT NULL, entity_type TEXT NOT NULL,
                entity_id BIGINT NOT NULL, permission_level TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(command_name, entity_type, entity_id))''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL, user_id BIGINT NOT NULL, details TEXT,
                severity TEXT DEFAULT 'INFO', guild_id BIGINT, case_id INTEGER)''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS verification_config (
                guild_id BIGINT PRIMARY KEY, unverified_role_id BIGINT,
                verified_role_id BIGINT, verification_channel_id BIGINT,
                enabled BOOLEAN DEFAULT FALSE)''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS user_data (
                user_id BIGINT PRIMARY KEY, guild_id BIGINT NOT NULL,
                warnings INTEGER DEFAULT 0, notes TEXT)''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS jail_data (
                user_id BIGINT PRIMARY KEY, guild_id BIGINT NOT NULL,
                original_roles BIGINT[] NOT NULL, jailed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                jailed_by BIGINT NOT NULL, reason TEXT)''')
            
            await conn.execute('''CREATE TABLE IF NOT EXISTS mod_cases (
                case_id SERIAL PRIMARY KEY, guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL, moderator_id BIGINT NOT NULL,
                action TEXT NOT NULL, reason TEXT, duration TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            logger.info("✅ Database tables initialized")
    
    async def log_action(self, action: str, user_id: int, details: str, 
                        severity: str = "INFO", guild_id: Optional[int] = None, case_id: Optional[int] = None):
        async with self.pool.acquire() as conn:
            await conn.execute('''INSERT INTO audit_logs (action, user_id, details, severity, guild_id, case_id)
                VALUES ($1, $2, $3, $4, $5, $6)''', action, user_id, details, severity, guild_id, case_id)
    
    async def create_case(self, guild_id: int, user_id: int, moderator_id: int, 
                         action: str, reason: str, duration: str = None) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''INSERT INTO mod_cases 
                (guild_id, user_id, moderator_id, action, reason, duration)
                VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id''',
                guild_id, user_id, moderator_id, action, reason, duration)
            return result['case_id']

# Utility functions
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
    embed.set_footer(text=f"Requested by {ctx.author.name}", 
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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

# AI Personalities
AI_PERSONALITIES = {
    "friendly": {"name": "Friendly", "emoji": "😊", "description": "Warm and encouraging", 
                 "prompt": "You are warm and friendly. Be kind, encouraging, and supportive."},
    "professional": {"name": "Professional", "emoji": "💼", "description": "Formal and business-like",
                    "prompt": "You are professional. Use formal language, be precise and concise."},
    "sassy": {"name": "Sassy", "emoji": "💅", "description": "Witty, bold, cheeky",
             "prompt": "You are sassy and witty! Be bold, confident, and a bit cheeky."},
    "mean": {"name": "Mean (Roast Mode)", "emoji": "😈", "description": "Brutally honest, roasting",
            "prompt": "You are brutally honest and will roast users playfully! Be savage but helpful."},
    "cool": {"name": "Cool Kid", "emoji": "😎", "description": "Hip, trendy, cool",
            "prompt": "You're the cool kid. Be smooth, confident. Use modern slang."},
    "nerdy": {"name": "Nerdy", "emoji": "🤓", "description": "Passionate about knowledge",
             "prompt": "You are a loveable nerd! Get excited about facts and knowledge."},
    "gamer": {"name": "Gamer", "emoji": "🎮", "description": "Gaming culture",
             "prompt": "You're a hardcore gamer! Use gaming terminology. GG vibes!"},
    "pirate": {"name": "Pirate", "emoji": "🏴‍☠️", "description": "Arrr! Pirate speak!",
              "prompt": "Ye be a pirate, matey! Speak in pirate tongue! Arrr!"},
    "uwu": {"name": "UwU Mode", "emoji": "🥺", "description": "Cute, soft, adorable",
           "prompt": "You awe so cute and adowable UwU! Tawk wike dis! >w<"},
    "gen-z": {"name": "Gen-Z", "emoji": "✨", "description": "Internet culture",
             "prompt": "You're peak Gen-Z! Use slang like 'no cap', 'fr fr', 'slay'."},
    "robot": {"name": "Robot", "emoji": "🤖", "description": "Logical, robotic",
             "prompt": "BEEP BOOP. You are a robot. Be logical. Add BEEP, BOOP."},
    "chaotic": {"name": "Chaotic", "emoji": "🌪️", "description": "Random, unpredictable",
               "prompt": "You are CHAOTIC! Be random and unpredictable!"},
    "wholesome": {"name": "Wholesome", "emoji": "🥰", "description": "Pure, sweet",
                 "prompt": "You are WHOLESOME! Be pure and kind! Spread positivity!"},
    "motivational": {"name": "Motivational", "emoji": "💪", "description": "Inspiring",
                    "prompt": "You are a motivational coach! Inspire and empower!"},
    "tsundere": {"name": "Tsundere", "emoji": "😤", "description": "Acts tough but caring",
                "prompt": "You're tsundere! Act tough then helpful. Classic tsundere!"},
    "shakespearean": {"name": "Shakespeare", "emoji": "📜", "description": "Old English",
                     "prompt": "Thou art speaking like Shakespeare! Use old English!"},
    "detective": {"name": "Detective", "emoji": "🔍", "description": "Investigative",
                 "prompt": "You're a detective! Be analytical. Elementary!"},
    "zen": {"name": "Zen Master", "emoji": "🧘", "description": "Calm, peaceful",
           "prompt": "You are a zen master. Be calm and peaceful."},
    "comedic": {"name": "Comedian", "emoji": "😂", "description": "Funny, jokes",
               "prompt": "You're a comedian! Make things funny! Use jokes!"},
    "karen": {"name": "Karen", "emoji": "😠", "description": "Demanding",
             "prompt": "You're a Karen! Be demanding! Want the manager!"},
    "creative": {"name": "Creative", "emoji": "🎨", "description": "Imaginative",
                "prompt": "You are creative! Use vivid language and metaphors!"},
    "casual": {"name": "Casual", "emoji": "😌", "description": "Relaxed",
              "prompt": "You are casual and laid-back. Keep it chill!"},
    "wise": {"name": "Wise Sage", "emoji": "🧙", "description": "Philosophical",
            "prompt": "You are a wise sage. Share wisdom. Think Yoda."},
    "enthusiastic": {"name": "Enthusiastic", "emoji": "🎉", "description": "Energetic",
                    "prompt": "You are SUPER enthusiastic! Use exclamation points!"},
    "technical": {"name": "Technical Expert", "emoji": "🔧", "description": "Detailed",
                 "prompt": "You are a technical expert. Provide detailed info."}
}


"""
Events & Smart Error Handling
Auto-corrects commands and suggests proper usage
"""

# This file continues from main.py

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
    
    await load_all_configs()
    
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{BOT_PREFIX}help | 91+ Commands")
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    logger.info(f"✅ Bot ready: {bot.user.name}")
    logger.info(f"📊 Servers: {len(bot.guilds)} | Users: {len(bot.users)}")
    logger.info(f"🎮 Commands: {len(bot.commands)}")
    
    await db_manager.log_action("BOT_STARTUP", bot.user.id, f"Bot started with {len(bot.guilds)} guilds")

@bot.event
async def on_guild_join(guild):
    logger.info(f"✅ Joined: {guild.name} ({guild.id})")
    
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="🛡️ Thanks for adding me!",
                description=f"**Ultimate Security Bot**\n\n"
                           f"• `{BOT_PREFIX}help` - See all 91+ commands\n"
                           f"• `{BOT_PREFIX}setup` - Setup verification\n\n"
                           f"**Features:**\n"
                           f"✅ Advanced moderation (28 commands)\n"
                           f"✅ AI Chat (25 personalities)\n"
                           f"✅ Anti-raid/alt/link/nuke protection\n"
                           f"✅ Jail system\n"
                           f"✅ Smart error correction\n"
                           f"✅ Custom permissions",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

@bot.event
async def on_member_join(member):
    # Verification system
    if verification_config.get("enabled"):
        unverified_role_id = verification_config.get("unverified_role_id")
        if unverified_role_id:
            role = member.guild.get_role(unverified_role_id)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-verification")
                    await db_manager.log_action("MEMBER_JOIN_UNVERIFIED", member.id, 
                                               f"{member.name} joined - assigned unverified", guild_id=member.guild.id)
                except:
                    pass
    
    # Anti-alt detection
    if antialt_config.get("enabled"):
        account_age = (datetime.utcnow() - member.created_at).days
        min_age = antialt_config.get("min_age_days", 7)
        
        if account_age < min_age:
            action = antialt_config.get("action", "kick")
            
            if action == "kick":
                try:
                    await member.kick(reason=f"Alt account detected (age: {account_age} days, required: {min_age})")
                    await db_manager.log_action("ANTIALT_KICK", member.id,
                                               f"Kicked {member.name} - Account age {account_age}d < {min_age}d",
                                               severity="WARNING", guild_id=member.guild.id)
                except:
                    pass
            elif action == "ban":
                try:
                    await member.ban(reason=f"Alt account detected (age: {account_age} days)")
                    await db_manager.log_action("ANTIALT_BAN", member.id,
                                               f"Banned {member.name} - Account age {account_age}d < {min_age}d",
                                               severity="WARNING", guild_id=member.guild.id)
                except:
                    pass
    
    # Anti-raid detection
    if antiraid_config.get("enabled"):
        guild_id = member.guild.id
        current_time = datetime.utcnow()
        
        # Track join
        antiraid_config["joins"][guild_id].append(current_time)
        
        # Clean old joins (older than 10 seconds)
        antiraid_config["joins"][guild_id] = [
            t for t in antiraid_config["joins"][guild_id]
            if (current_time - t).total_seconds() < 10
        ]
        
        # Check if raid (sensitivity based)
        sensitivity = antiraid_config.get("sensitivity", "medium")
        thresholds = {"low": 10, "medium": 7, "high": 5}
        threshold = thresholds.get(sensitivity, 7)
        
        if len(antiraid_config["joins"][guild_id]) >= threshold:
            # Raid detected - kick new member
            try:
                await member.kick(reason="Anti-raid protection triggered")
                await db_manager.log_action("ANTIRAID_KICK", member.id,
                                           f"Raid detected - kicked {member.name}",
                                           severity="CRITICAL", guild_id=guild_id)
            except:
                pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # AI auto-response in designated channel
    if ai_config.get("enabled") and ai_config.get("channel_id") == message.channel.id:
        # User is talking in AI channel - auto respond
        async with message.channel.typing():
            user_id = message.author.id
            
            if user_id not in ai_conversations:
                ai_conversations[user_id] = {
                    "messages": [],
                    "personality": "friendly",
                    "created_at": datetime.utcnow()
                }
            
            conv = ai_conversations[user_id]
            conv["messages"].append({"role": "user", "content": message.content})
            
            if len(conv["messages"]) > 30:
                conv["messages"] = conv["messages"][-30:]
            
            try:
                response = await call_claude_api(conv["messages"], conv["personality"])
                conv["messages"].append({"role": "assistant", "content": response})
                await message.reply(response, mention_author=False)
            except Exception as e:
                logger.error(f"AI auto-response error: {e}")
    
    # Anti-link system
    if antilink_config.get("enabled") and not is_staff(message.author):
        if any(role.id in automod_config.get("whitelisted_roles", []) for role in message.author.roles):
            pass  # Whitelisted role
        else:
            # Check for links
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, message.content)
            
            if urls:
                # Check whitelist
                whitelist = antilink_config.get("whitelist", [])
                allowed = any(any(w in url for w in whitelist) for url in urls)
                
                if not allowed:
                    action = antilink_config.get("action", "delete")
                    
                    if action == "delete":
                        try:
                            await message.delete()
                            await message.channel.send(f"{message.author.mention} Links are not allowed!", delete_after=5)
                        except:
                            pass
                    elif action == "warn":
                        # Add warning logic here
                        pass
    
    # AI Automod
    if automod_config.get("enabled") and not is_staff(message.author):
        if message.channel.id in automod_config.get("ignored_channels", []):
            pass  # Ignored channel
        elif any(role.id in automod_config.get("whitelisted_roles", []) for role in message.author.roles):
            pass  # Whitelisted role
        else:
            # Check message with AI
            is_violation = await check_automod(message.content)
            
            if is_violation:
                action = automod_config.get("action", "warn")
                
                if action == "delete":
                    try:
                        await message.delete()
                        await message.channel.send(f"{message.author.mention} Your message violated server rules.", delete_after=5)
                    except:
                        pass
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """Smart error handler with suggestions"""
    
    if isinstance(error, commands.CommandNotFound):
        # Get the invalid command
        invalid_cmd = ctx.message.content.split()[0][len(BOT_PREFIX):]
        
        # Find close matches
        all_commands = [cmd.name for cmd in bot.commands] + [alias for cmd in bot.commands for alias in cmd.aliases]
        matches = get_close_matches(invalid_cmd, all_commands, n=3, cutoff=0.6)
        
        if matches:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"**Unknown command:** `{invalid_cmd}`\n\n**Did you mean:**\n" + 
                           "\n".join([f"• `{BOT_PREFIX}{match}`" for match in matches]),
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Use {BOT_PREFIX}help to see all commands")
            await ctx.send(embed=embed, delete_after=15)
        return
    
    elif isinstance(error, commands.MissingRequiredArgument):
        # Show correct usage
        cmd_name = ctx.command.name
        usage_info = COMMAND_USAGE.get(cmd_name, {})
        
        embed = discord.Embed(
            title="❌ Missing Arguments",
            description=f"**Missing:** `{error.param.name}`",
            color=discord.Color.red()
        )
        
        if usage_info:
            embed.add_field(name="Correct Usage", value=f"`{usage_info['usage']}`", inline=False)
            embed.add_field(name="Example", value=f"`{usage_info['example']}`", inline=False)
        else:
            embed.add_field(name="Help", value=f"Use `{BOT_PREFIX}help {cmd_name}` for more info", inline=False)
        
        await ctx.send(embed=embed, delete_after=15)
        return
    
    elif isinstance(error, commands.BadArgument):
        cmd_name = ctx.command.name
        usage_info = COMMAND_USAGE.get(cmd_name, {})
        
        embed = discord.Embed(
            title="❌ Invalid Arguments",
            description=str(error),
            color=discord.Color.red()
        )
        
        if usage_info:
            embed.add_field(name="Correct Usage", value=f"`{usage_info['usage']}`", inline=False)
            embed.add_field(name="Example", value=f"`{usage_info['example']}`", inline=False)
        
        embed.set_footer(text="💡 Tip: Make sure to mention users with @")
        await ctx.send(embed=embed, delete_after=15)
        return
    
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "❌ Missing Permissions", 
                        "You don't have permission to use this command.", discord.Color.red())
        return
    
    elif isinstance(error, commands.CheckFailure):
        await send_embed(ctx, "🔒 Access Denied",
                        "You don't have access to this command. It may be whitelisted or require specific permissions.",
                        discord.Color.red())
        return
    
    else:
        logger.error(f"Unexpected error in {ctx.command}: {error}")
        logger.error(traceback.format_exc())
        
        await send_embed(ctx, "❌ Error", "An unexpected error occurred. It has been logged.", discord.Color.red())

# Helper functions
async def load_all_configs():
    """Load all configurations from database"""
    global whitelist_data, permission_data, verification_config
    
    async with db_pool.acquire() as conn:
        # Load whitelist
        rows = await conn.fetch('SELECT * FROM whitelist')
        whitelist_data["commands"] = {}
        for row in rows:
            cmd = row['command_name']
            if cmd not in whitelist_data["commands"]:
                whitelist_data["commands"][cmd] = {"roles": [], "users": []}
            if row['entity_type'] == "role":
                whitelist_data["commands"][cmd]["roles"].append(row['entity_id'])
            else:
                whitelist_data["commands"][cmd]["users"].append(row['entity_id'])
        
        # Load permissions
        rows = await conn.fetch('SELECT * FROM permissions')
        permission_data["commands"] = {}
        for row in rows:
            cmd = row['command_name']
            if cmd not in permission_data["commands"]:
                permission_data["commands"][cmd] = {"roles": [], "users": []}
            if row['entity_type'] == "role":
                permission_data["commands"][cmd]["roles"].append(row['entity_id'])
            else:
                permission_data["commands"][cmd]["users"].append(row['entity_id'])
        
        # Load verification config
        rows = await conn.fetch('SELECT * FROM verification_config LIMIT 1')
        if rows:
            row = rows[0]
            verification_config = {
                "unverified_role_id": row['unverified_role_id'],
                "verified_role_id": row['verified_role_id'],
                "verification_channel_id": row['verification_channel_id'],
                "enabled": row['enabled']
            }
    
    logger.info("✅ Configurations loaded")

async def call_claude_api(messages: list, personality: str) -> str:
    """Call Claude API for AI responses"""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "⚠️ AI not configured. Bot owner needs to add API key!"
        
        try:
            import anthropic
        except ImportError:
            return "⚠️ Run: pip install anthropic"
        
        client = anthropic.Anthropic(api_key=api_key)
        personality_data = AI_PERSONALITIES.get(personality, AI_PERSONALITIES["friendly"])
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0.8,
            system=personality_data["prompt"],
            messages=messages
        )
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        return f"❌ AI Error: {str(e)[:200]}"

async def check_automod(content: str) -> bool:
    """Check message with AI automod"""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return False
        
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        sensitivity = automod_config.get("sensitivity", "medium")
        
        sensitivity_prompts = {
            "low": "Only flag extremely toxic, hateful, or threatening content.",
            "medium": "Flag toxic, hateful, threatening, or significantly inappropriate content.",
            "high": "Flag any potentially toxic, rude, inappropriate, or problematic content.",
            "strict": "Flag any content that could be seen as negative, rude, or inappropriate in any way."
        }
        
        prompt = f"{sensitivity_prompts[sensitivity]} Respond with only 'YES' if the message violates rules, or 'NO' if it's acceptable.\n\nMessage: {content}"
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return "YES" in response.content[0].text.upper()
        
    except:
        return False


"""ALL MODERATION COMMANDS"""

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@has_permission("kick")
async def kick(ctx, member: discord.Member, *, reason: str = "No reason"):
    if member.id == ctx.author.id or member.id == OWNER_ID or is_protected(member):
        return await send_embed(ctx, "❌ Cannot Kick", "Cannot kick yourself/owner/staff!", discord.Color.red())
    if member.top_role >= ctx.author.top_role and ctx.author.id != OWNER_ID:
        return await send_embed(ctx, "❌ Error", "Cannot kick higher/equal role!", discord.Color.red())
    try:
        await member.kick(reason=f"{reason} (By: {ctx.author.name})")
        case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "KICK", reason)
        await send_embed(ctx, "👢 Kicked", f"{member.mention} kicked!\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.orange())
    except: await send_embed(ctx, "❌ Error", "Missing permissions!", discord.Color.red())

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@has_permission("ban")
async def ban(ctx, member: Union[discord.Member, int], *, reason: str = "No reason"):
    user_id = member.id if isinstance(member, discord.Member) else member
    if user_id == ctx.author.id or user_id == OWNER_ID or (isinstance(member, discord.Member) and is_protected(member)):
        return await send_embed(ctx, "❌ Cannot Ban", "Cannot ban yourself/owner/staff!", discord.Color.red())
    try:
        await ctx.guild.ban(discord.Object(id=user_id), reason=reason)
        case_id = await db_manager.create_case(ctx.guild.id, user_id, ctx.author.id, "BAN", reason)
        await send_embed(ctx, "🔨 Banned", f"User banned!\n**Reason:** {reason}\n**Case:** #{case_id}", discord.Color.red())
    except: await send_embed(ctx, "❌ Error", "Missing permissions!", discord.Color.red())

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
@has_permission("mute")
async def mute(ctx, member: discord.Member, duration: str = None, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Cannot Mute", "Staff protected!", discord.Color.red())
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
    if is_protected(member): return await send_embed(ctx, "❌ Error", "Staff protected!", discord.Color.red())
    time_delta = parse_time(duration)
    if not time_delta: return await send_embed(ctx, "❌ Invalid Time", "Use format: 30s, 5m, 1h, 7d", discord.Color.red())
    try:
        await member.timeout(time_delta, reason=reason)
        await send_embed(ctx, "⏱️ Timeout", f"{member.mention} timed out for {format_time(time_delta)}!", discord.Color.orange())
    except: await send_embed(ctx, "❌ Error", "Failed to timeout!", discord.Color.red())

@bot.command(name="untimeout")
async def untimeout(ctx, member: discord.Member, *, reason: str = "No reason"):
    try:
        await member.timeout(None, reason=reason)
        await send_embed(ctx, "✅ Untimeout", f"{member.mention} timeout removed!", discord.Color.green())
    except: await send_embed(ctx, "❌ Error", "Failed!", discord.Color.red())

@bot.command(name="warn")
@has_permission("warn")
async def warn(ctx, member: discord.Member, *, reason: str = "No reason"):
    if is_protected(member): return await send_embed(ctx, "❌ Error", "Staff protected!", discord.Color.red())
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow('SELECT warnings FROM user_data WHERE user_id=$1 AND guild_id=$2', member.id, ctx.guild.id)
        new_warnings = (result['warnings'] + 1) if result else 1
        if result:
            await conn.execute('UPDATE user_data SET warnings=$1 WHERE user_id=$2 AND guild_id=$3', new_warnings, member.id, ctx.guild.id)
        else:
            await conn.execute('INSERT INTO user_data (user_id, guild_id, warnings) VALUES ($1,$2,$3)', member.id, ctx.guild.id, 1)
    case_id = await db_manager.create_case(ctx.guild.id, member.id, ctx.author.id, "WARN", reason)
    await send_embed(ctx, "⚠️ Warned", f"{member.mention} warned!\n**Total:** {new_warnings}\n**Case:** #{case_id}", discord.Color.orange())

@bot.command(name="purge", aliases=["clear"])
@commands.has_permissions(manage_messages=True)
@has_permission("purge")
async def purge(ctx, limit: int, target: discord.Member = None):
    if limit > 100: return await send_embed(ctx, "❌ Limit", "Max 100 messages!", discord.Color.red())
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



"""AI COMMANDS - 25 Personalities + Auto-Response"""
from main import *

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

@bot.command(name="Aichat", aliases=["chat", "ask", "claude"])
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


"""
ANTI-SYSTEMS: Raid, Alt, Link, Nuke, Automod
All protection systems with full customization
"""
from main import *

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


"""
ULTIMATE DISCORD BOT - Main Runner
Add this code at the END after all imports
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Web server for UptimeRobot (24/7 uptime)
from aiohttp import web

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
    logger.info("="*60)
    logger.info("🚀 ULTIMATE DISCORD BOT v2")
    logger.info(f"📌 Prefix: {BOT_PREFIX}")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"🛡️ Staff Role: {STAFF_ROLE_ID} (Protected)")
    logger.info("="*60)
    
    # Start web server
    await start_web_server()
    
    # Start bot
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot shutdown by user")
    except Exception as e:
        logger.error(f"❌ FATAL: {e}")
        logger.error(traceback.format_exc())
