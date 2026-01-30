"""
ADVANCED DISCORD BOT - PART 1 oki/8 (FINAL GEMINI VERSION)
ALL IMPORTS AT TOP | FREE AI | VERIFICATION SYSTEM | EXTENDED PERSONALITIES
COPY THIS FIRST, THEN ADD PARTS 2-8
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import os
import re
from typing import Optional, Set, Dict, List
from dotenv import load_dotenv
import logging
import aiohttp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

class Config:
    """Bot Configuration"""
    OWNER_ID = int(os.getenv('OWNER_ID', '1029438856069656576'))
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    PREFIX = '+'
    PORT = int(os.getenv('PORT', 8080))
    
    COLOR_PRIMARY = 0x5865F2
    COLOR_SUCCESS = 0x57F287
    COLOR_WARNING = 0xFEE75C
    COLOR_ERROR = 0xED4245
    COLOR_INFO = 0x5865F2
    
    SPAM_THRESHOLD = 7
    SPAM_TIMEFRAME = 4
    MESSAGE_TIMEOUT_DURATIONS = {1: 5, 2: 15, 3: 30, 4: 60, 5: 180}
    
    RAID_JOIN_THRESHOLD = 10
    RAID_JOIN_TIMEFRAME = 10
    ACCOUNT_AGE_MINIMUM = 7
    
    PROFANITY_TIMEOUT = 10
    BANNED_WORDS = [
        'nigger', 'nigga', 'n1gger', 'n1gga', 'nigg3r', 'nigg4',
        'faggot', 'f4ggot', 'fag', 'f4g', 'fgt',
        'cunt', 'c*nt', 'pussy', 'puss',
        'dick', 'd1ck', 'cock', 'c0ck',
        'bitch', 'b1tch', 'btch',
        'shit', 'sh1t', 'sht',
        'fuck', 'fck', 'f*ck', 'fuk',
        'ass', '@ss', 'asshole',
        'whore', 'slut', 'hoe',
        'retard', 'retarded', 'ret4rd',
        'kys', 'kms',
        'rape', 'r4pe'
    ]
    
    MENTION_LIMIT = 5
    MENTION_TIMEOUT = 15
    LINK_LIMIT = 3
    LINK_TIMEFRAME = 10
    MAX_PURGE_AMOUNT = 1000
    MAX_REMINDERS_PER_USER = 10
    ITEMS_PER_PAGE = 10
    
    # AI Personalities (Extended)
    AI_PERSONALITIES = {
        'helpful': 'You are a helpful and informative assistant.',
        'friendly': 'You are a friendly, warm, and welcoming assistant.',
        'professional': 'You are a professional and formal assistant.',
        'casual': 'You are a casual, laid-back, and chill assistant.',
        'funny': 'You are a funny, humorous, and entertaining assistant who loves to make people laugh.',
        'sarcastic': 'You are a witty and sarcastic assistant with a sharp sense of humor.',
        'sassy': 'You are a sassy, confident assistant with attitude. You give responses with flair and spice.',
        'flirty': 'You are a playful and flirty assistant. You respond with charm and playful teasing.',
        'mean': 'You are a brutally honest and mean assistant. You roast people and give savage responses.',
        'dumb': 'You are a hilariously dumb assistant who gets confused easily and gives funny silly responses.',
        'uwu': 'You are an overly cute assistant who talks in uwu speak. Use emojis like owo, uwu, >w<',
        'gen-z': 'You are a gen-z assistant. Use slang like "no cap", "fr fr", "bestie", "slay", "periodt"',
        'toxic': 'You are a toxic gamer assistant. Be competitive, trash talk, and act like a toxic player.',
        'simp': 'You are a simp assistant. You compliment the user excessively and act overly nice.',
        'chad': 'You are a sigma chad assistant. Be confident, masculine, give based advice.'
    }

class DataManager:
    def __init__(self):
        self.data_file = 'bot_data.json'
        self.whitelist: Set[int] = set()
        self.role_whitelist: Set[int] = set()
        self.blacklist: Set[int] = set()
        self.antibot_enabled = False
        self.antibot_channel_id: Optional[int] = None
        self.antibot_punishment = 'kick'
        self.bot_whitelist: Set[int] = set()
        self.pending_bots: Dict[int, Dict] = {}
        self.antilink_enabled = False
        self.whitelisted_domains: Set[str] = set()
        self.command_permissions: Dict[str, Dict] = defaultdict(dict)
        self.permits: Dict[int, Dict] = {}
        self.user_warnings: Dict[int, List[Dict]] = defaultdict(list)
        self.user_notes: Dict[int, List[Dict]] = defaultdict(list)
        self.mod_cases: List[Dict] = []
        self.case_counter = 0
        self.antiraid_enabled = True
        self.automod_enabled = True
        self.log_channel_id: Optional[int] = None
        self.modlog_channel_id: Optional[int] = None
        self.memberlog_channel_id: Optional[int] = None
        self.messagelog_channel_id: Optional[int] = None
        self.voicelog_channel_id: Optional[int] = None
        self.serverlog_channel_id: Optional[int] = None
        self.raidlog_channel_id: Optional[int] = None
        self.logs_enabled = False
        self.welcome_channel_id: Optional[int] = None
        self.leave_channel_id: Optional[int] = None
        self.welcome_message = "Welcome {user.mention} to **{server.name}**!"
        self.leave_message = "{user.name} has left the server."
        self.welcome_enabled = False
        self.leave_enabled = False
        self.autoroles: List[int] = []
        self.autonick: Optional[str] = None
        self.muted_role_id: Optional[int] = None
        self.verification_enabled = False
        self.verification_channel_id: Optional[int] = None
        self.verification_role_id: Optional[int] = None
        self.unverified_role_id: Optional[int] = None
        self.verification_message = "Click the button below to verify!"
        self.antiswear_enabled = False
        self.custom_banned_words: Set[str] = set()
        self.custom_prefix: Optional[str] = None
        self.reminders: Dict[int, List[Dict]] = defaultdict(list)
        self.todos: Dict[int, List[str]] = defaultdict(list)
        self.afk_users: Dict[int, Dict] = {}
        self.deleted_messages: Dict[int, Dict] = {}
        self.edited_messages: Dict[int, Dict] = {}
        self.ai_channels: Set[int] = set()
        self.ai_personality = "helpful"
        self.ai_max_length = 1000
        self.backups: List[Dict] = []
        self.timezone = 'UTC'
        self.language = 'en'
        self.voice_banned_users: Set[int] = set()
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.whitelist = set(data.get('whitelist', []))
                    self.role_whitelist = set(data.get('role_whitelist', []))
                    self.blacklist = set(data.get('blacklist', []))
                    self.bot_whitelist = set(data.get('bot_whitelist', []))
                    self.whitelisted_domains = set(data.get('whitelisted_domains', []))
                    self.custom_banned_words = set(data.get('custom_banned_words', []))
                    self.ai_channels = set(data.get('ai_channels', []))
                    self.voice_banned_users = set(data.get('voice_banned_users', []))
                    self.pending_bots = data.get('pending_bots', {})
                    self.command_permissions = defaultdict(dict, data.get('command_permissions', {}))
                    self.permits = data.get('permits', {})
                    self.user_warnings = defaultdict(list, {int(k): v for k, v in data.get('user_warnings', {}).items()})
                    self.user_notes = defaultdict(list, {int(k): v for k, v in data.get('user_notes', {}).items()})
                    self.reminders = defaultdict(list, {int(k): v for k, v in data.get('reminders', {}).items()})
                    self.todos = defaultdict(list, {int(k): v for k, v in data.get('todos', {}).items()})
                    self.afk_users = {int(k): v for k, v in data.get('afk_users', {}).items()}
                    self.mod_cases = data.get('mod_cases', [])
                    self.autoroles = data.get('autoroles', [])
                    self.backups = data.get('backups', [])
                    self.case_counter = data.get('case_counter', 0)
                    self.antibot_enabled = data.get('antibot_enabled', False)
                    self.antibot_channel_id = data.get('antibot_channel_id')
                    self.antibot_punishment = data.get('antibot_punishment', 'kick')
                    self.antilink_enabled = data.get('antilink_enabled', False)
                    self.antiraid_enabled = data.get('antiraid_enabled', True)
                    self.automod_enabled = data.get('automod_enabled', True)
                    self.log_channel_id = data.get('log_channel_id')
                    self.modlog_channel_id = data.get('modlog_channel_id')
                    self.memberlog_channel_id = data.get('memberlog_channel_id')
                    self.messagelog_channel_id = data.get('messagelog_channel_id')
                    self.voicelog_channel_id = data.get('voicelog_channel_id')
                    self.serverlog_channel_id = data.get('serverlog_channel_id')
                    self.raidlog_channel_id = data.get('raidlog_channel_id')
                    self.logs_enabled = data.get('logs_enabled', False)
                    self.welcome_channel_id = data.get('welcome_channel_id')
                    self.leave_channel_id = data.get('leave_channel_id')
                    self.welcome_message = data.get('welcome_message', self.welcome_message)
                    self.leave_message = data.get('leave_message', self.leave_message)
                    self.welcome_enabled = data.get('welcome_enabled', False)
                    self.leave_enabled = data.get('leave_enabled', False)
                    self.autonick = data.get('autonick')
                    self.muted_role_id = data.get('muted_role_id')
                    self.verification_enabled = data.get('verification_enabled', False)
                    self.verification_channel_id = data.get('verification_channel_id')
                    self.verification_role_id = data.get('verification_role_id')
                    self.unverified_role_id = data.get('unverified_role_id')
                    self.verification_message = data.get('verification_message', self.verification_message)
                    self.antiswear_enabled = data.get('antiswear_enabled', False)
                    self.custom_prefix = data.get('custom_prefix')
                    self.ai_personality = data.get('ai_personality', 'helpful')
                    self.ai_max_length = data.get('ai_max_length', 1000)
                    self.timezone = data.get('timezone', 'UTC')
                    self.language = data.get('language', 'en')
                    logging.info("✅ Data loaded")
        except Exception as e:
            logging.error(f"❌ Error loading data: {e}")
    
    def save_data(self):
        try:
            data = {
                'whitelist': list(self.whitelist),
                'role_whitelist': list(self.role_whitelist),
                'blacklist': list(self.blacklist),
                'bot_whitelist': list(self.bot_whitelist),
                'whitelisted_domains': list(self.whitelisted_domains),
                'custom_banned_words': list(self.custom_banned_words),
                'ai_channels': list(self.ai_channels),
                'voice_banned_users': list(self.voice_banned_users),
                'pending_bots': self.pending_bots,
                'command_permissions': dict(self.command_permissions),
                'permits': self.permits,
                'user_warnings': {str(k): v for k, v in self.user_warnings.items()},
                'user_notes': {str(k): v for k, v in self.user_notes.items()},
                'reminders': {str(k): v for k, v in self.reminders.items()},
                'todos': {str(k): v for k, v in self.todos.items()},
                'afk_users': {str(k): v for k, v in self.afk_users.items()},
                'mod_cases': self.mod_cases,
                'autoroles': self.autoroles,
                'backups': self.backups,
                'case_counter': self.case_counter,
                'antibot_enabled': self.antibot_enabled,
                'antibot_channel_id': self.antibot_channel_id,
                'antibot_punishment': self.antibot_punishment,
                'antilink_enabled': self.antilink_enabled,
                'antiraid_enabled': self.antiraid_enabled,
                'automod_enabled': self.automod_enabled,
                'log_channel_id': self.log_channel_id,
                'modlog_channel_id': self.modlog_channel_id,
                'memberlog_channel_id': self.memberlog_channel_id,
                'messagelog_channel_id': self.messagelog_channel_id,
                'voicelog_channel_id': self.voicelog_channel_id,
                'serverlog_channel_id': self.serverlog_channel_id,
                'raidlog_channel_id': self.raidlog_channel_id,
                'logs_enabled': self.logs_enabled,
                'welcome_channel_id': self.welcome_channel_id,
                'leave_channel_id': self.leave_channel_id,
                'welcome_message': self.welcome_message,
                'leave_message': self.leave_message,
                'welcome_enabled': self.welcome_enabled,
                'leave_enabled': self.leave_enabled,
                'autonick': self.autonick,
                'muted_role_id': self.muted_role_id,
                'verification_enabled': self.verification_enabled,
                'verification_channel_id': self.verification_channel_id,
                'verification_role_id': self.verification_role_id,
                'unverified_role_id': self.unverified_role_id,
                'verification_message': self.verification_message,
                'antiswear_enabled': self.antiswear_enabled,
                'custom_prefix': self.custom_prefix,
                'ai_personality': self.ai_personality,
                'ai_max_length': self.ai_max_length,
                'timezone': self.timezone,
                'language': self.language
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ Error saving data: {e}")
    
    def add_mod_case(self, action: str, user_id: int, moderator_id: int, reason: str, guild_id: int) -> int:
        self.case_counter += 1
        case = {
            'case_id': self.case_counter,
            'action': action,
            'user_id': user_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'guild_id': guild_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.mod_cases.append(case)
        self.save_data()
        return self.case_counter
    
    def add_warning(self, user_id: int, reason: str, moderator_id: int, guild_id: int):
        warning = {
            'reason': reason,
            'moderator_id': moderator_id,
            'guild_id': guild_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.user_warnings[user_id].append(warning)
        self.save_data()
    
    def is_whitelisted(self, user_id: int, role_ids: List[int] = None) -> bool:
        if user_id in self.whitelist:
            return True
        if role_ids:
            for role_id in role_ids:
                if role_id in self.role_whitelist:
                    return True
        return False
    
    def has_command_permission(self, command_name: str, user_id: int, role_ids: List[int]) -> Optional[bool]:
        if command_name not in self.command_permissions:
            return None
        perms = self.command_permissions[command_name]
        if 'users' in perms and user_id in perms['users']:
            return True
        if 'roles' in perms:
            for role_id in role_ids:
                if role_id in perms['roles']:
                    return True
        return False

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=lambda bot, message: data_manager.custom_prefix or Config.PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)
data_manager = DataManager()
message_tracking = defaultdict(list)
join_tracking = []
link_tracking = defaultdict(list)

def is_owner():
    async def predicate(ctx):
        return ctx.author.id == Config.OWNER_ID
    return commands.check(predicate)

def has_command_permission():
    async def predicate(ctx):
        if ctx.author.id == Config.OWNER_ID:
            return True
        role_ids = [role.id for role in ctx.author.roles]
        perm_check = data_manager.has_command_permission(ctx.command.name, ctx.author.id, role_ids)
        if perm_check is None:
            return ctx.author.guild_permissions.administrator
        return perm_check
    return commands.check(predicate)

async def log_action(guild: discord.Guild, embed: discord.Embed, log_type: str = 'main'):
    if not data_manager.logs_enabled:
        return
    channel_id = None
    if log_type == 'mod':
        channel_id = data_manager.modlog_channel_id
    elif log_type == 'member':
        channel_id = data_manager.memberlog_channel_id
    elif log_type == 'message':
        channel_id = data_manager.messagelog_channel_id
    elif log_type == 'voice':
        channel_id = data_manager.voicelog_channel_id
    elif log_type == 'server':
        channel_id = data_manager.serverlog_channel_id
    elif log_type == 'raid':
        channel_id = data_manager.raidlog_channel_id
    else:
        channel_id = data_manager.log_channel_id
    if not channel_id:
        channel_id = data_manager.log_channel_id
    if channel_id:
        try:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
        except:
            pass

def create_embed(title: str, description: str, color: int = Config.COLOR_PRIMARY) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())

def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

class Paginator(View):
    def __init__(self, embeds: List[discord.Embed], author: discord.User):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.author = author
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        self.update_buttons()
    
    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == len(self.embeds) - 1
    
    @discord.ui.button(label='⏪ Previous', style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This isn't your menu!", ephemeral=True)
            return
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label='Next ⏩', style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This isn't your menu!", ephemeral=True)
            return
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='✅ Verify', style=discord.ButtonStyle.success, custom_id='verify_button')
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        if not data_manager.verification_role_id:
            return await interaction.response.send_message("❌ Verification role not set!", ephemeral=True)
        
        verified_role = interaction.guild.get_role(data_manager.verification_role_id)
        if not verified_role:
            return await interaction.response.send_message("❌ Verified role not found!", ephemeral=True)
        
        if verified_role in interaction.user.roles:
            return await interaction.response.send_message("✅ You're already verified!", ephemeral=True)
        
        try:
            await interaction.user.add_roles(verified_role, reason="Verification")
            
            if data_manager.unverified_role_id:
                unverified_role = interaction.guild.get_role(data_manager.unverified_role_id)
                if unverified_role and unverified_role in interaction.user.roles:
                    await interaction.user.remove_roles(unverified_role, reason="Verification")
            
            await interaction.response.send_message(f"✅ You've been verified! Welcome to **{interaction.guild.name}**!", ephemeral=True)
            
            if data_manager.memberlog_channel_id:
                channel = interaction.guild.get_channel(data_manager.memberlog_channel_id)
                if channel:
                    embed = create_embed("✅ Member Verified", f"**Member:** {interaction.user.mention}\n**ID:** `{interaction.user.id}`", Config.COLOR_SUCCESS)
                    await channel.send(embed=embed)
        
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to verify you!", ephemeral=True)

"""
END OF PART 1 - PASTE PART 2 BELOW THIS
"""

"""
ADVANCED DISCORD BOT - PART 2/8
PASTE THIS AFTER PART 1 - Bot Events & Auto-Mod
"""

@bot.event
async def on_ready():
    logging.info('=' * 60)
    logging.info(f'Bot: {bot.user.name} (ID: {bot.user.id})')
    logging.info(f'Servers: {len(bot.guilds)}')
    logging.info(f'Users: {len(bot.users)}')
    logging.info(f'Prefix: {Config.PREFIX}')
    logging.info('=' * 60)
    
    bot.add_view(VerificationView())
    
    check_reminders.start()
    check_permits.start()
    update_status.start()
    
    try:
        synced = await bot.tree.sync()
        logging.info(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        logging.error(f'❌ Failed to sync commands: {e}')

@bot.event
async def on_member_join(member: discord.Member):
    if member.bot and data_manager.antibot_enabled:
        if member.id not in data_manager.bot_whitelist:
            data_manager.pending_bots[member.id] = {'added_at': datetime.utcnow().isoformat(), 'added_by': None}
            data_manager.save_data()
            if data_manager.antibot_channel_id:
                channel = member.guild.get_channel(data_manager.antibot_channel_id)
                if channel:
                    embed = create_embed("🤖 Bot Added - Approval Required", f"**Bot:** {member.mention} ({member.name})\n**ID:** `{member.id}`\n**Created:** {discord.utils.format_dt(member.created_at, style='R')}\n\nReact with ✅ to approve or ❌ to {data_manager.antibot_punishment}.", Config.COLOR_WARNING)
                    msg = await channel.send(embed=embed)
                    await msg.add_reaction('✅')
                    await msg.add_reaction('❌')
            return
    
    if data_manager.verification_enabled and not member.bot:
        if data_manager.unverified_role_id:
            unverified_role = member.guild.get_role(data_manager.unverified_role_id)
            if unverified_role:
                try:
                    await member.add_roles(unverified_role, reason="Unverified member")
                except:
                    pass
    
    if data_manager.antiraid_enabled and not member.bot:
        current_time = datetime.utcnow()
        join_tracking.append(current_time)
        cutoff = current_time - timedelta(seconds=Config.RAID_JOIN_TIMEFRAME)
        while join_tracking and join_tracking[0] < cutoff:
            join_tracking.pop(0)
        if len(join_tracking) >= Config.RAID_JOIN_THRESHOLD:
            if data_manager.raidlog_channel_id:
                channel = member.guild.get_channel(data_manager.raidlog_channel_id)
                if channel:
                    embed = create_embed("🚨 POSSIBLE RAID DETECTED", f"**{len(join_tracking)} members** joined in the last {Config.RAID_JOIN_TIMEFRAME} seconds!\n\nLatest member: {member.mention}", Config.COLOR_ERROR)
                    await channel.send(embed=embed, content="@here")
    
    if not member.bot:
        account_age = (datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
        if account_age < Config.ACCOUNT_AGE_MINIMUM:
            if data_manager.raidlog_channel_id:
                channel = member.guild.get_channel(data_manager.raidlog_channel_id)
                if channel:
                    embed = create_embed("⚠️ New Account Joined", f"**Member:** {member.mention}\n**Account Age:** {account_age} days\n**Created:** {discord.utils.format_dt(member.created_at, style='R')}", Config.COLOR_WARNING)
                    await channel.send(embed=embed)
    
    if data_manager.autoroles and not data_manager.verification_enabled:
        for role_id in data_manager.autoroles:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except:
                    pass
    
    if data_manager.autonick and not member.bot:
        try:
            nick = data_manager.autonick.replace('{user}', member.name)
            await member.edit(nick=nick)
        except:
            pass
    
    if data_manager.welcome_enabled and data_manager.welcome_channel_id:
        channel = member.guild.get_channel(data_manager.welcome_channel_id)
        if channel:
            message = data_manager.welcome_message
            message = message.replace('{user}', member.name)
            message = message.replace('{user.mention}', member.mention)
            message = message.replace('{server}', member.guild.name)
            message = message.replace('{server.name}', member.guild.name)
            message = message.replace('{member.count}', str(member.guild.member_count))
            try:
                await channel.send(message)
            except:
                pass
    
    if data_manager.memberlog_channel_id:
        embed = create_embed("📥 Member Joined", f"**Member:** {member.mention}\n**Account Created:** {discord.utils.format_dt(member.created_at, style='R')}\n**Member Count:** {member.guild.member_count}", Config.COLOR_SUCCESS)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_action(member.guild, embed, 'member')

@bot.event
async def on_member_remove(member: discord.Member):
    if data_manager.leave_enabled and data_manager.leave_channel_id:
        channel = member.guild.get_channel(data_manager.leave_channel_id)
        if channel:
            message = data_manager.leave_message
            message = message.replace('{user}', member.name)
            message = message.replace('{user.name}', member.name)
            message = message.replace('{server}', member.guild.name)
            message = message.replace('{server.name}', member.guild.name)
            message = message.replace('{member.count}', str(member.guild.member_count))
            try:
                await channel.send(message)
            except:
                pass
    
    if data_manager.memberlog_channel_id:
        embed = create_embed("📤 Member Left", f"**Member:** {member.mention} ({member.name})\n**Joined:** {discord.utils.format_dt(member.joined_at, style='R') if member.joined_at else 'Unknown'}\n**Member Count:** {member.guild.member_count}", Config.COLOR_ERROR)
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_action(member.guild, embed, 'member')

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    if message.author.id in data_manager.afk_users:
        del data_manager.afk_users[message.author.id]
        data_manager.save_data()
        try:
            await message.channel.send(f"Welcome back {message.author.mention}! I removed your AFK status.", delete_after=5)
        except:
            pass
    
    for mention in message.mentions:
        if mention.id in data_manager.afk_users:
            afk_data = data_manager.afk_users[mention.id]
            afk_msg = afk_data.get('message', 'AFK')
            afk_time = datetime.fromisoformat(afk_data.get('time'))
            time_ago = format_time(int((datetime.utcnow() - afk_time).total_seconds()))
            try:
                await message.channel.send(f"{mention.name} is currently AFK: **{afk_msg}** - {time_ago} ago", delete_after=10)
            except:
                pass
    
    role_ids = [role.id for role in message.author.roles]
    if data_manager.is_whitelisted(message.author.id, role_ids):
        await bot.process_commands(message)
        return
    
    if data_manager.automod_enabled:
        current_time = datetime.utcnow().timestamp()
        user_messages = message_tracking[message.author.id]
        user_messages.append(current_time)
        cutoff = current_time - Config.SPAM_TIMEFRAME
        message_tracking[message.author.id] = [t for t in user_messages if t > cutoff]
        if len(message_tracking[message.author.id]) >= Config.SPAM_THRESHOLD:
            violations = sum(1 for t in user_messages if t > current_time - 60)
            timeout_minutes = Config.MESSAGE_TIMEOUT_DURATIONS.get(min(violations, 5), 180)
            try:
                await message.author.timeout(timedelta(minutes=timeout_minutes), reason="Spam detected")
                await message.channel.send(f"{message.author.mention} has been timed out for **{timeout_minutes} minutes** for spamming.", delete_after=10)
                embed = create_embed("🔇 Auto-Mod: Spam", f"**User:** {message.author.mention}\n**Duration:** {timeout_minutes} minutes\n**Messages:** {len(message_tracking[message.author.id])} in {Config.SPAM_TIMEFRAME}s", Config.COLOR_WARNING)
                await log_action(message.guild, embed, 'mod')
                message_tracking[message.author.id] = []
            except:
                pass
            return
    
    if data_manager.antiswear_enabled:
        content_lower = message.content.lower()
        banned = Config.BANNED_WORDS + list(data_manager.custom_banned_words)
        for word in banned:
            if word in content_lower:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, please watch your language!", delete_after=5)
                    await message.author.timeout(timedelta(minutes=Config.PROFANITY_TIMEOUT), reason="Inappropriate language")
                    embed = create_embed("🔇 Auto-Mod: Profanity", f"**User:** {message.author.mention}\n**Word:** `{word}`\n**Duration:** {Config.PROFANITY_TIMEOUT} minutes", Config.COLOR_WARNING)
                    await log_action(message.guild, embed, 'mod')
                except:
                    pass
                return
    
    if data_manager.antilink_enabled:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, message.content)
        if urls:
            allowed = False
            for url in urls:
                for domain in data_manager.whitelisted_domains:
                    if domain in url:
                        allowed = True
                        break
                if allowed:
                    break
            if not allowed:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, links are not allowed in this server!", delete_after=5)
                except:
                    pass
                return
    
    if len(message.mentions) > Config.MENTION_LIMIT:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=Config.MENTION_TIMEOUT), reason=f"Mention spam ({len(message.mentions)} mentions)")
            await message.channel.send(f"{message.author.mention} has been timed out for mention spam.", delete_after=10)
            embed = create_embed("🔇 Auto-Mod: Mention Spam", f"**User:** {message.author.mention}\n**Mentions:** {len(message.mentions)}\n**Duration:** {Config.MENTION_TIMEOUT} minutes", Config.COLOR_WARNING)
            await log_action(message.guild, embed, 'mod')
        except:
            pass
        return
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    data_manager.deleted_messages[message.channel.id] = {'content': message.content, 'author': message.author.id, 'time': datetime.utcnow().isoformat()}
    if data_manager.messagelog_channel_id and message.content:
        embed = create_embed("🗑️ Message Deleted", f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1000]}", Config.COLOR_ERROR)
        await log_action(message.guild, embed, 'message')

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    data_manager.edited_messages[before.channel.id] = {'before': before.content, 'after': after.content, 'author': before.author.id, 'time': datetime.utcnow().isoformat()}
    if data_manager.messagelog_channel_id:
        embed = create_embed("✏️ Message Edited", f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content[:500]}\n**After:** {after.content[:500]}", Config.COLOR_INFO)
        await log_action(before.guild, embed, 'message')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    if not data_manager.antibot_enabled or not data_manager.antibot_channel_id:
        return
    
    if payload.channel_id != data_manager.antibot_channel_id:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return
    
    if len(message.embeds) == 0:
        return
    
    embed = message.embeds[0]
    if "Bot Added - Approval Required" not in embed.title:
        return
    
    bot_id = None
    for field in embed.fields if embed.fields else []:
        if "ID" in field.name or "ID" in field.value:
            try:
                bot_id = int(field.value.strip('`'))
                break
            except:
                pass
    
    if not bot_id:
        description_lines = embed.description.split('\n')
        for line in description_lines:
            if "ID:" in line:
                try:
                    bot_id = int(line.split('`')[1])
                    break
                except:
                    pass
    
    if not bot_id or bot_id not in data_manager.pending_bots:
        return
    
    member = guild.get_member(bot_id)
    if not member:
        del data_manager.pending_bots[bot_id]
        data_manager.save_data()
        return
    
    user = guild.get_member(payload.user_id)
    if not user or not user.guild_permissions.manage_guild:
        return
    
    if str(payload.emoji) == '✅':
        data_manager.bot_whitelist.add(bot_id)
        del data_manager.pending_bots[bot_id]
        data_manager.save_data()
        
        await message.edit(embed=create_embed("✅ Bot Approved", f"**Bot:** {member.mention}\n**Approved by:** {user.mention}", Config.COLOR_SUCCESS))
        await message.clear_reactions()
    
    elif str(payload.emoji) == '❌':
        del data_manager.pending_bots[bot_id]
        data_manager.save_data()
        
        try:
            if data_manager.antibot_punishment == 'ban':
                await member.ban(reason=f"Unauthorized bot - Denied by {user}")
                await message.edit(embed=create_embed("🔨 Bot Banned", f"**Bot:** {member.mention}\n**Denied by:** {user.mention}", Config.COLOR_ERROR))
            elif data_manager.antibot_punishment == 'kick':
                await member.kick(reason=f"Unauthorized bot - Denied by {user}")
                await message.edit(embed=create_embed("👢 Bot Kicked", f"**Bot:** {member.mention}\n**Denied by:** {user.mention}", Config.COLOR_WARNING))
            await message.clear_reactions()
        except:
            pass

@tasks.loop(seconds=30)
async def check_reminders():
    current_time = datetime.utcnow().timestamp()
    for user_id, reminders in list(data_manager.reminders.items()):
        for reminder in reminders[:]:
            if current_time >= reminder['time']:
                user = bot.get_user(user_id)
                if user:
                    channel = bot.get_channel(reminder['channel_id'])
                    if channel:
                        embed = create_embed("⏰ Reminder", f"{user.mention}, you asked me to remind you:\n\n{reminder['message']}", Config.COLOR_INFO)
                        try:
                            await channel.send(embed=embed)
                        except:
                            pass
                reminders.remove(reminder)
        if not reminders:
            del data_manager.reminders[user_id]
    data_manager.save_data()

@tasks.loop(minutes=5)
async def check_permits():
    current_time = datetime.utcnow().timestamp()
    for user_id, permit_data in list(data_manager.permits.items()):
        if current_time >= permit_data['expires']:
            del data_manager.permits[user_id]
    data_manager.save_data()

@tasks.loop(minutes=5)
async def update_status():
    guild_count = len(bot.guilds)
    user_count = len(bot.users)
    statuses = [f"{Config.PREFIX}help | {guild_count} servers", f"{Config.PREFIX}help | {user_count} users", f"{Config.PREFIX}help | Free AI Bot"]
    status = statuses[int(datetime.utcnow().timestamp()) % len(statuses)]
    await bot.change_presence(activity=discord.Game(name=status))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.", delete_after=10)
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have permission to use this command.", delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: `{error.param.name}`\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", delete_after=15)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided.\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", delete_after=15)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found.", delete_after=10)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"❌ This command is on cooldown. Try again in {error.retry_after:.1f}s", delete_after=10)
    else:
        logging.error(f"Command error in {ctx.command}: {error}")

"""
END OF PART 2 - PASTE PART 3 BELOW THIS
"""

"""
ADVANCED DISCORD BOT - PART 3/8
PASTE THIS AFTER PART 2
"""

@bot.command(name='ban')
@commands.guild_only()
@has_command_permission()
async def ban_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't ban yourself!")
    if member.id == Config.OWNER_ID:
        return await ctx.send("❌ You can't ban the bot owner!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't ban someone with a higher or equal role!")
    try:
        await member.ban(reason=f"{ctx.author}: {reason}")
        case_id = data_manager.add_mod_case('ban', member.id, ctx.author.id, reason, ctx.guild.id)
        embed = create_embed("✅ Member Banned", f"**Member:** {member.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
        log_embed = create_embed("🔨 Member Banned", f"**Member:** {member.mention} ({member})\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_ERROR)
        await log_action(ctx.guild, log_embed, 'mod')
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member!")

@bot.command(name='unban')
@commands.guild_only()
@has_command_permission()
async def unban_user(ctx, user_id: int, *, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
        case_id = data_manager.add_mod_case('unban', user.id, ctx.author.id, reason, ctx.guild.id)
        embed = create_embed("✅ User Unbanned", f"**User:** {user.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("❌ User not found or not banned!")

@bot.command(name='kick')
@commands.guild_only()
@has_command_permission()
async def kick_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't kick yourself!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't kick someone with a higher or equal role!")
    try:
        await member.kick(reason=f"{ctx.author}: {reason}")
        case_id = data_manager.add_mod_case('kick', member.id, ctx.author.id, reason, ctx.guild.id)
        embed = create_embed("✅ Member Kicked", f"**Member:** {member.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this member!")

@bot.command(name='mute')
@commands.guild_only()
@has_command_permission()
async def mute_member(ctx, member: discord.Member, duration: str = "10m", *, reason: str = "No reason provided"):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't mute yourself!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't mute someone with a higher or equal role!")
    try:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1]
        amount = int(duration[:-1])
        seconds = amount * time_units.get(unit, 60)
        if seconds > 2419200:
            return await ctx.send("❌ Maximum timeout duration is 28 days!")
    except:
        return await ctx.send("❌ Invalid duration format! Use: 10s, 5m, 2h, 1d")
    try:
        await member.timeout(timedelta(seconds=seconds), reason=f"{ctx.author}: {reason}")
        case_id = data_manager.add_mod_case('mute', member.id, ctx.author.id, f"{reason} (Duration: {duration})", ctx.guild.id)
        embed = create_embed("✅ Member Muted", f"**Member:** {member.mention}\n**Duration:** {duration}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this member!")

@bot.command(name='unmute')
@commands.guild_only()
@has_command_permission()
async def unmute_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.timeout(None, reason=f"{ctx.author}: {reason}")
        case_id = data_manager.add_mod_case('unmute', member.id, ctx.author.id, reason, ctx.guild.id)
        embed = create_embed("✅ Member Unmuted", f"**Member:** {member.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to remove timeout from this member!")

@bot.command(name='warn')
@commands.guild_only()
@has_command_permission()
async def warn_member(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't warn yourself!")
    if member.id == Config.OWNER_ID:
        return await ctx.send("❌ You can't warn the bot owner!")
    data_manager.add_warning(member.id, reason, ctx.author.id, ctx.guild.id)
    case_id = data_manager.add_mod_case('warn', member.id, ctx.author.id, reason, ctx.guild.id)
    warnings = data_manager.user_warnings.get(member.id, [])
    warn_count = len(warnings)
    embed = create_embed("✅ Member Warned", f"**Member:** {member.mention}\n**Reason:** {reason}\n**Total Warnings:** {warn_count}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='warnings', aliases=['warns'])
@commands.guild_only()
@has_command_permission()
async def view_warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    warnings = data_manager.user_warnings.get(member.id, [])
    if not warnings:
        return await ctx.send(f"✅ {member.mention} has no warnings!")
    embeds = []
    for i in range(0, len(warnings), 5):
        embed = create_embed(f"⚠️ Warnings for {member.name}", f"**Total:** {len(warnings)} warnings", Config.COLOR_WARNING)
        embed.set_thumbnail(url=member.display_avatar.url)
        for idx, warning in enumerate(warnings[i:i+5], start=i+1):
            moderator = ctx.guild.get_member(warning['moderator_id'])
            mod_name = moderator.name if moderator else "Unknown"
            embed.add_field(name=f"Warning #{idx}", value=f"**Reason:** {warning['reason']}\n**Moderator:** {mod_name}", inline=False)
        embed.set_footer(text=f"Page {len(embeds) + 1}/{(len(warnings) + 4) // 5}")
        embeds.append(embed)
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = Paginator(embeds, ctx.author)
        view.message = await ctx.send(embed=embeds[0], view=view)

@bot.command(name='clearwarns')
@commands.guild_only()
@has_command_permission()
async def clear_warnings(ctx, member: discord.Member):
    warnings = data_manager.user_warnings.get(member.id, [])
    if not warnings:
        return await ctx.send(f"✅ {member.mention} has no warnings to clear!")
    warn_count = len(warnings)
    if member.id in data_manager.user_warnings:
        del data_manager.user_warnings[member.id]
        data_manager.save_data()
    embed = create_embed("✅ Warnings Cleared", f"**Member:** {member.mention}\n**Cleared:** {warn_count} warnings", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='tempban')
@commands.guild_only()
@has_command_permission()
async def temp_ban(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    try:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1]
        amount = int(duration[:-1])
        seconds = amount * time_units.get(unit, 60)
    except:
        return await ctx.send("❌ Invalid duration format! Use: 10s, 5m, 2h, 1d")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't ban yourself!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't ban someone with a higher or equal role!")
    try:
        await member.ban(reason=f"{ctx.author}: {reason} (Temp: {duration})")
        case_id = data_manager.add_mod_case('tempban', member.id, ctx.author.id, f"{reason} (Duration: {duration})", ctx.guild.id)
        embed = create_embed("✅ Member Temporarily Banned", f"**Member:** {member.mention}\n**Duration:** {duration}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
        await asyncio.sleep(seconds)
        try:
            await ctx.guild.unban(member, reason=f"Temp ban expired (Case #{case_id})")
        except:
            pass
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member!")

@bot.command(name='softban')
@commands.guild_only()
@has_command_permission()
async def soft_ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't softban yourself!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't softban someone with a higher or equal role!")
    try:
        await member.ban(reason=f"{ctx.author}: {reason} (Softban)", delete_message_days=1)
        await ctx.guild.unban(member, reason=f"{ctx.author}: Softban")
        case_id = data_manager.add_mod_case('softban', member.id, ctx.author.id, reason, ctx.guild.id)
        embed = create_embed("✅ Member Softbanned", f"**Member:** {member.mention}\n**Reason:** {reason}\n**Case:** #{case_id}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member!")

@bot.command(name='timeout', aliases=['to'])
@commands.guild_only()
@has_command_permission()
async def timeout_member(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    await mute_member(ctx, member, duration, reason=reason)

@bot.command(name='tempmute')
@commands.guild_only()
@has_command_permission()
async def temp_mute(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    await mute_member(ctx, member, duration, reason=reason)

@bot.command(name='note')
@commands.guild_only()
@has_command_permission()
async def add_note(ctx, member: discord.Member, *, note: str):
    note_data = {'note': note, 'moderator_id': ctx.author.id, 'timestamp': datetime.utcnow().isoformat()}
    data_manager.user_notes[member.id].append(note_data)
    data_manager.save_data()
    embed = create_embed("✅ Note Added", f"**Member:** {member.mention}\n**Note:** {note}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='case')
@commands.guild_only()
@has_command_permission()
async def view_case(ctx, case_id: int):
    case = next((c for c in data_manager.mod_cases if c['case_id'] == case_id), None)
    if not case or case['guild_id'] != ctx.guild.id:
        return await ctx.send(f"❌ Case #{case_id} not found!")
    user = await bot.fetch_user(case['user_id'])
    moderator = await bot.fetch_user(case['moderator_id'])
    embed = create_embed(f"📋 Case #{case_id}", f"**Action:** {case['action'].title()}\n**User:** {user.mention} ({user})\n**Moderator:** {moderator.mention} ({moderator})\n**Reason:** {case['reason']}\n**Date:** <t:{int(datetime.fromisoformat(case['timestamp']).timestamp())}:F>", Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.command(name='reason')
@commands.guild_only()
@has_command_permission()
async def update_reason(ctx, case_id: int, *, new_reason: str):
    case = next((c for c in data_manager.mod_cases if c['case_id'] == case_id), None)
    if not case or case['guild_id'] != ctx.guild.id:
        return await ctx.send(f"❌ Case #{case_id} not found!")
    for c in data_manager.mod_cases:
        if c['case_id'] == case_id:
            c['reason'] = new_reason
            data_manager.save_data()
            break
    embed = create_embed("✅ Case Updated", f"**Case:** #{case_id}\n**New Reason:** {new_reason}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='history')
@commands.guild_only()
@has_command_permission()
async def member_history(ctx, member: discord.Member):
    cases = [c for c in data_manager.mod_cases if c['user_id'] == member.id and c['guild_id'] == ctx.guild.id]
    if not cases:
        return await ctx.send(f"✅ {member.mention} has no moderation history!")
    embed = create_embed(f"📋 Moderation History for {member.name}", f"**Total Cases:** {len(cases)}", Config.COLOR_INFO)
    embed.set_thumbnail(url=member.display_avatar.url)
    for case in cases[-10:]:
        moderator = await bot.fetch_user(case['moderator_id'])
        embed.add_field(name=f"Case #{case['case_id']} - {case['action'].title()}", value=f"**Moderator:** {moderator.name}\n**Reason:** {case['reason']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='modstats')
@commands.guild_only()
@has_command_permission()
async def mod_stats(ctx):
    guild_cases = [c for c in data_manager.mod_cases if c['guild_id'] == ctx.guild.id]
    action_counts = {}
    for case in guild_cases:
        action = case['action']
        action_counts[action] = action_counts.get(action, 0) + 1
    embed = create_embed("📊 Moderation Statistics", f"**Total Cases:** {len(guild_cases)}", Config.COLOR_INFO)
    if action_counts:
        stats_text = "\n".join([f"**{action.title()}:** {count}" for action, count in sorted(action_counts.items())])
        embed.add_field(name="Actions", value=stats_text, inline=False)
    await ctx.send(embed=embed)

"""
END OF PART 3 - PASTE PART 4 BELOW THIS
"""
"""
ADVANCED DISCORD BOT - PART 4/8
PASTE THIS AFTER PART 3
"""

@bot.command(name='purge', aliases=['p'])
@commands.guild_only()
@has_command_permission()
async def purge_messages(ctx, amount: int):
    if amount < 1 or amount > Config.MAX_PURGE_AMOUNT:
        return await ctx.send(f"❌ Amount must be between 1 and {Config.MAX_PURGE_AMOUNT}!")
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"✅ Deleted {len(deleted) - 1} messages!")
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")

@bot.command(name='purgebots')
@commands.guild_only()
@has_command_permission()
async def purge_bots(ctx, amount: int = 100):
    if amount < 1 or amount > Config.MAX_PURGE_AMOUNT:
        return await ctx.send(f"❌ Amount must be between 1 and {Config.MAX_PURGE_AMOUNT}!")
    try:
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
        msg = await ctx.send(f"✅ Deleted {len(deleted)} bot messages!")
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")

@bot.command(name='purgeuser')
@commands.guild_only()
@has_command_permission()
async def purge_user(ctx, member: discord.Member, amount: int = 100):
    if amount < 1 or amount > Config.MAX_PURGE_AMOUNT:
        return await ctx.send(f"❌ Amount must be between 1 and {Config.MAX_PURGE_AMOUNT}!")
    try:
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == member.id)
        msg = await ctx.send(f"✅ Deleted {len(deleted)} messages from {member.mention}!")
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")

@bot.command(name='purgelinks')
@commands.guild_only()
@has_command_permission()
async def purge_links(ctx, amount: int = 100):
    if amount < 1 or amount > Config.MAX_PURGE_AMOUNT:
        return await ctx.send(f"❌ Amount must be between 1 and {Config.MAX_PURGE_AMOUNT}!")
    try:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: re.search(url_pattern, m.content))
        msg = await ctx.send(f"✅ Deleted {len(deleted)} messages with links!")
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")

@bot.command(name='purgeimages')
@commands.guild_only()
@has_command_permission()
async def purge_images(ctx, amount: int = 100):
    if amount < 1 or amount > Config.MAX_PURGE_AMOUNT:
        return await ctx.send(f"❌ Amount must be between 1 and {Config.MAX_PURGE_AMOUNT}!")
    try:
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: len(m.attachments) > 0 or len(m.embeds) > 0)
        msg = await ctx.send(f"✅ Deleted {len(deleted)} messages with images!")
        await msg.delete(delay=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")

@bot.command(name='lock')
@commands.guild_only()
@has_command_permission()
async def lock_channel(ctx, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"{ctx.author}: {reason}")
        embed = create_embed("🔒 Channel Locked", f"**Channel:** {channel.mention}\n**Reason:** {reason}", Config.COLOR_WARNING)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit channel permissions!")

@bot.command(name='unlock')
@commands.guild_only()
@has_command_permission()
async def unlock_channel(ctx, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"{ctx.author}: {reason}")
        embed = create_embed("🔓 Channel Unlocked", f"**Channel:** {channel.mention}\n**Reason:** {reason}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit channel permissions!")

@bot.command(name='lockdown')
@commands.guild_only()
@has_command_permission()
async def lockdown_server(ctx, *, reason: str = "Lockdown"):
    msg = await ctx.send("🔒 Locking down all channels...")
    locked = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False, reason=f"{ctx.author}: {reason}")
            locked += 1
        except:
            pass
    embed = create_embed("🔒 Server Lockdown", f"Locked {locked}/{len(ctx.guild.text_channels)} channels\n**Reason:** {reason}", Config.COLOR_ERROR)
    await msg.edit(content=None, embed=embed)

@bot.command(name='unlockdown')
@commands.guild_only()
@has_command_permission()
async def unlockdown_server(ctx, *, reason: str = "Lockdown lifted"):
    msg = await ctx.send("🔓 Unlocking all channels...")
    unlocked = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None, reason=f"{ctx.author}: {reason}")
            unlocked += 1
        except:
            pass
    embed = create_embed("🔓 Lockdown Lifted", f"Unlocked {unlocked}/{len(ctx.guild.text_channels)} channels\n**Reason:** {reason}", Config.COLOR_SUCCESS)
    await msg.edit(content=None, embed=embed)

@bot.command(name='slowmode')
@commands.guild_only()
@has_command_permission()
async def set_slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    if seconds < 0 or seconds > 21600:
        return await ctx.send("❌ Slowmode must be between 0 and 21600 seconds (6 hours)!")
    try:
        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            embed = create_embed("✅ Slowmode Disabled", f"**Channel:** {channel.mention}", Config.COLOR_SUCCESS)
        else:
            embed = create_embed("✅ Slowmode Set", f"**Channel:** {channel.mention}\n**Delay:** {seconds} seconds", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel!")

@bot.command(name='addrole')
@commands.guild_only()
@has_command_permission()
async def add_role(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ I can't assign a role higher than or equal to my highest role!")
    if role in member.roles:
        return await ctx.send(f"❌ {member.mention} already has the {role.mention} role!")
    try:
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        embed = create_embed("✅ Role Added", f"**Member:** {member.mention}\n**Role:** {role.mention}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage roles!")

@bot.command(name='removerole')
@commands.guild_only()
@has_command_permission()
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    if role >= ctx.guild.me.top_role:
        return await ctx.send("❌ I can't remove a role higher than or equal to my highest role!")
    if role not in member.roles:
        return await ctx.send(f"❌ {member.mention} doesn't have the {role.mention} role!")
    try:
        await member.remove_roles(role, reason=f"Removed by {ctx.author}")
        embed = create_embed("✅ Role Removed", f"**Member:** {member.mention}\n**Role:** {role.mention}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage roles!")

@bot.command(name='setnick', aliases=['nickname'])
@commands.guild_only()
@has_command_permission()
async def set_nickname(ctx, member: discord.Member, *, nickname: str):
    if len(nickname) > 32:
        return await ctx.send("❌ Nicknames must be 32 characters or less!")
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't change the nickname of someone with a higher or equal role!")
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname, reason=f"Changed by {ctx.author}")
        embed = create_embed("✅ Nickname Changed", f"**Member:** {member.mention}\n**Old:** {old_nick}\n**New:** {nickname}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change nicknames!")

@bot.command(name='resetnick')
@commands.guild_only()
@has_command_permission()
async def reset_nickname(ctx, member: discord.Member):
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ You can't reset the nickname of someone with a higher or equal role!")
    try:
        old_nick = member.display_name
        await member.edit(nick=None, reason=f"Reset by {ctx.author}")
        embed = create_embed("✅ Nickname Reset", f"**Member:** {member.mention}\n**Old Nickname:** {old_nick}", Config.COLOR_SUCCESS)
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change nicknames!")

@bot.command(name='voiceunban')
@commands.guild_only()
@has_command_permission()
async def voice_unban(ctx, member: discord.Member):
    if member.id not in data_manager.voice_banned_users:
        return await ctx.send(f"❌ {member.mention} is not voice banned!")
    data_manager.voice_banned_users.discard(member.id)
    data_manager.save_data()
    for channel in ctx.guild.voice_channels:
        try:
            await channel.set_permissions(member, connect=None, reason=f"Voice unban by {ctx.author}")
        except:
            pass
    embed = create_embed("✅ Voice Unbanned", f"**Member:** {member.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='automod')
@commands.guild_only()
@has_command_permission()
async def toggle_automod(ctx):
    data_manager.automod_enabled = not data_manager.automod_enabled
    data_manager.save_data()
    status = "enabled" if data_manager.automod_enabled else "disabled"
    embed = create_embed(f"✅ Auto-Mod {status.title()}", f"Auto-moderation has been **{status}**", Config.COLOR_SUCCESS if data_manager.automod_enabled else Config.COLOR_ERROR)
    await ctx.send(embed=embed)

@bot.command(name='antiraid')
@commands.guild_only()
@has_command_permission()
async def toggle_antiraid(ctx):
    data_manager.antiraid_enabled = not data_manager.antiraid_enabled
    data_manager.save_data()
    status = "enabled" if data_manager.antiraid_enabled else "disabled"
    embed = create_embed(f"✅ Anti-Raid {status.title()}", f"Anti-raid protection has been **{status}**", Config.COLOR_SUCCESS if data_manager.antiraid_enabled else Config.COLOR_ERROR)
    await ctx.send(embed=embed)

"""
END OF PART 4 - PASTE PART 5 BELOW THIS
"""

"""
ADVANCED DISCORD BOT - PART 5/8
PASTE THIS AFTER PART 4
"""

@bot.group(name='whitelist', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def whitelist(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Usage: `{Config.PREFIX}whitelist <add|remove|list|clear>`")

@whitelist.command(name='add')
async def whitelist_add(ctx, user: discord.User):
    if user.id in data_manager.whitelist:
        return await ctx.send(f"❌ {user.mention} is already whitelisted!")
    data_manager.whitelist.add(user.id)
    data_manager.blacklist.discard(user.id)
    data_manager.save_data()
    embed = create_embed("✅ User Whitelisted", f"**User:** {user.mention}\n{user.mention} can now bypass security checks.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@whitelist.command(name='remove')
async def whitelist_remove(ctx, user: discord.User):
    if user.id not in data_manager.whitelist:
        return await ctx.send(f"❌ {user.mention} is not whitelisted!")
    data_manager.whitelist.discard(user.id)
    data_manager.save_data()
    embed = create_embed("✅ User Removed from Whitelist", f"**User:** {user.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@whitelist.command(name='list')
async def whitelist_list(ctx):
    if not data_manager.whitelist:
        return await ctx.send("✅ No users are whitelisted!")
    users = []
    for user_id in data_manager.whitelist:
        try:
            user = await bot.fetch_user(user_id)
            users.append(f"{user.mention} - `{user.id}`")
        except:
            users.append(f"Unknown User - `{user_id}`")
    embed = create_embed("📋 Whitelisted Users", f"**Total:** {len(users)} users\n\n" + "\n".join(users[:25]), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@whitelist.command(name='clear')
@is_owner()
async def whitelist_clear(ctx):
    count = len(data_manager.whitelist)
    data_manager.whitelist.clear()
    data_manager.save_data()
    embed = create_embed("✅ Whitelist Cleared", f"Removed {count} users from whitelist.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.group(name='rolewhitelist', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def rolewhitelist(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Usage: `{Config.PREFIX}rolewhitelist <add|remove|list>`")

@rolewhitelist.command(name='add')
async def rolewhitelist_add(ctx, role: discord.Role):
    if role.id in data_manager.role_whitelist:
        return await ctx.send(f"❌ {role.mention} is already whitelisted!")
    data_manager.role_whitelist.add(role.id)
    data_manager.save_data()
    embed = create_embed("✅ Role Whitelisted", f"**Role:** {role.mention}\nAll members with this role can bypass security checks.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@rolewhitelist.command(name='remove')
async def rolewhitelist_remove(ctx, role: discord.Role):
    if role.id not in data_manager.role_whitelist:
        return await ctx.send(f"❌ {role.mention} is not whitelisted!")
    data_manager.role_whitelist.discard(role.id)
    data_manager.save_data()
    embed = create_embed("✅ Role Removed from Whitelist", f"**Role:** {role.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@rolewhitelist.command(name='list')
async def rolewhitelist_list(ctx):
    if not data_manager.role_whitelist:
        return await ctx.send("✅ No roles are whitelisted!")
    roles = []
    for role_id in data_manager.role_whitelist:
        role = ctx.guild.get_role(role_id)
        if role:
            roles.append(f"{role.mention} - `{role.id}`")
        else:
            roles.append(f"Unknown Role - `{role_id}`")
    embed = create_embed("📋 Whitelisted Roles", f"**Total:** {len(roles)} roles\n\n" + "\n".join(roles), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.group(name='blacklist', invoke_without_command=True)
@commands.guild_only()
@is_owner()
async def blacklist(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Usage: `{Config.PREFIX}blacklist <add|remove|list>`")

@blacklist.command(name='add')
async def blacklist_add(ctx, user: discord.User):
    if user.id in data_manager.blacklist:
        return await ctx.send(f"❌ {user.mention} is already blacklisted!")
    data_manager.blacklist.add(user.id)
    data_manager.whitelist.discard(user.id)
    data_manager.save_data()
    embed = create_embed("✅ User Blacklisted", f"**User:** {user.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@blacklist.command(name='remove')
async def blacklist_remove(ctx, user: discord.User):
    if user.id not in data_manager.blacklist:
        return await ctx.send(f"❌ {user.mention} is not blacklisted!")
    data_manager.blacklist.discard(user.id)
    data_manager.save_data()
    embed = create_embed("✅ User Removed from Blacklist", f"**User:** {user.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@blacklist.command(name='list')
async def blacklist_list(ctx):
    if not data_manager.blacklist:
        return await ctx.send("✅ No users are blacklisted!")
    users = []
    for user_id in data_manager.blacklist:
        try:
            user = await bot.fetch_user(user_id)
            users.append(f"{user.mention} - `{user.id}`")
        except:
            users.append(f"Unknown User - `{user_id}`")
    embed = create_embed("📋 Blacklisted Users", f"**Total:** {len(users)} users\n\n" + "\n".join(users[:25]), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.group(name='antibot', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def antibot(ctx):
    if ctx.invoked_subcommand is None:
        status = "enabled" if data_manager.antibot_enabled else "disabled"
        embed = create_embed("🤖 Antibot System", f"**Status:** {status.title()}\n**Approval Channel:** {f'<#{data_manager.antibot_channel_id}>' if data_manager.antibot_channel_id else 'Not set'}\n**Punishment:** {data_manager.antibot_punishment.title()}\n**Whitelisted Bots:** {len(data_manager.bot_whitelist)}", Config.COLOR_INFO)
        await ctx.send(embed=embed)

@antibot.command(name='enable')
async def antibot_enable(ctx):
    data_manager.antibot_enabled = True
    data_manager.save_data()
    embed = create_embed("✅ Antibot Enabled", "New bots will require approval before joining.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='disable')
async def antibot_disable(ctx):
    data_manager.antibot_enabled = False
    data_manager.save_data()
    embed = create_embed("✅ Antibot Disabled", "Bots can now join freely.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='setchannel')
async def antibot_setchannel(ctx, channel: discord.TextChannel):
    data_manager.antibot_channel_id = channel.id
    data_manager.save_data()
    embed = create_embed("✅ Approval Channel Set", f"**Channel:** {channel.mention}\nBot approval requests will be sent here.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='setpunishment')
async def antibot_setpunishment(ctx, punishment: str):
    if punishment.lower() not in ['kick', 'ban', 'strip']:
        return await ctx.send("❌ Punishment must be: kick, ban, or strip")
    data_manager.antibot_punishment = punishment.lower()
    data_manager.save_data()
    embed = create_embed("✅ Punishment Set", f"**Punishment:** {punishment.title()}\nUnauthorized bots will be {punishment.lower()}ed.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='whitelist')
async def antibot_whitelist(ctx, bot_user: discord.User):
    if not bot_user.bot:
        return await ctx.send("❌ That user is not a bot!")
    if bot_user.id in data_manager.bot_whitelist:
        return await ctx.send(f"❌ {bot_user.mention} is already whitelisted!")
    data_manager.bot_whitelist.add(bot_user.id)
    data_manager.save_data()
    embed = create_embed("✅ Bot Whitelisted", f"**Bot:** {bot_user.mention}\nThis bot can join freely.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='unwhitelist')
async def antibot_unwhitelist(ctx, bot_user: discord.User):
    if bot_user.id not in data_manager.bot_whitelist:
        return await ctx.send(f"❌ {bot_user.mention} is not whitelisted!")
    data_manager.bot_whitelist.discard(bot_user.id)
    data_manager.save_data()
    embed = create_embed("✅ Bot Removed from Whitelist", f"**Bot:** {bot_user.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antibot.command(name='pending')
async def antibot_pending(ctx):
    if not data_manager.pending_bots:
        return await ctx.send("✅ No pending bot approvals!")
    bots = []
    for bot_id in data_manager.pending_bots.keys():
        try:
            bot_user = await bot.fetch_user(bot_id)
            bots.append(f"{bot_user.mention} - `{bot_id}`")
        except:
            bots.append(f"Unknown Bot - `{bot_id}`")
    embed = create_embed("🤖 Pending Bot Approvals", f"**Total:** {len(bots)} bots\n\n" + "\n".join(bots), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.group(name='antilink', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def antilink(ctx):
    if ctx.invoked_subcommand is None:
        status = "enabled" if data_manager.antilink_enabled else "disabled"
        embed = create_embed("🔗 Anti-Link System", f"**Status:** {status.title()}\n**Whitelisted Domains:** {len(data_manager.whitelisted_domains)}", Config.COLOR_INFO)
        await ctx.send(embed=embed)

@antilink.command(name='enable')
async def antilink_enable(ctx):
    data_manager.antilink_enabled = True
    data_manager.save_data()
    embed = create_embed("✅ Anti-Link Enabled", "Links will now be automatically deleted.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antilink.command(name='disable')
async def antilink_disable(ctx):
    data_manager.antilink_enabled = False
    data_manager.save_data()
    embed = create_embed("✅ Anti-Link Disabled", "Links can now be posted freely.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@antilink.command(name='whitelist')
async def antilink_whitelist_domain(ctx, domain: str):
    domain = domain.lower().replace('http://', '').replace('https://', '').replace('www.', '')
    if domain in data_manager.whitelisted_domains:
        return await ctx.send(f"❌ `{domain}` is already whitelisted!")
    data_manager.whitelisted_domains.add(domain)
    data_manager.save_data()
    embed = create_embed("✅ Domain Whitelisted", f"**Domain:** `{domain}`\nLinks from this domain can now be posted.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.group(name='permit', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def permit(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Usage: `{Config.PREFIX}permit <add|remove|list>`")

@permit.command(name='add')
async def permit_add(ctx, user: discord.User, duration: str = "10m"):
    try:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1]
        amount = int(duration[:-1])
        seconds = amount * time_units.get(unit, 60)
    except:
        return await ctx.send("❌ Invalid duration! Use: 10s, 5m, 2h, 1d")
    expires = datetime.utcnow().timestamp() + seconds
    data_manager.permits[user.id] = {'expires': expires, 'granted_by': ctx.author.id}
    data_manager.save_data()
    embed = create_embed("✅ Permit Granted", f"**User:** {user.mention}\n**Duration:** {duration}\nUser can temporarily bypass security checks.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@permit.command(name='remove')
async def permit_remove(ctx, user: discord.User):
    if user.id not in data_manager.permits:
        return await ctx.send(f"❌ {user.mention} doesn't have a permit!")
    del data_manager.permits[user.id]
    data_manager.save_data()
    embed = create_embed("✅ Permit Removed", f"**User:** {user.mention}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@permit.command(name='list')
async def permit_list(ctx):
    if not data_manager.permits:
        return await ctx.send("✅ No active permits!")
    users = []
    for user_id, permit_data in data_manager.permits.items():
        try:
            user = await bot.fetch_user(user_id)
            users.append(f"{user.mention} - Expires <t:{int(permit_data['expires'])}:R>")
        except:
            pass
    embed = create_embed("📋 Active Permits", f"**Total:** {len(users)} permits\n\n" + "\n".join(users[:10]), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.group(name='perms', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def perms(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"Usage: `{Config.PREFIX}perms <set|view>`")

@perms.command(name='set')
async def perms_set(ctx, command_name: str, *targets):
    command = bot.get_command(command_name)
    if not command:
        return await ctx.send(f"❌ Command `{command_name}` not found!")
    if not targets:
        return await ctx.send(f"❌ Provide at least one role or user!")
    roles = []
    users = []
    for target in targets:
        if target.lower() == 'clear':
            if command_name in data_manager.command_permissions:
                del data_manager.command_permissions[command_name]
                data_manager.save_data()
            return await ctx.send(f"✅ Cleared custom permissions for `{command_name}`")
        try:
            if target.startswith('<@&') and target.endswith('>'):
                role_id = int(target[3:-1])
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role.id)
            elif target.startswith('<@') and target.endswith('>'):
                user_id = int(target[2:-1].replace('!', ''))
                user = await bot.fetch_user(user_id)
                if user:
                    users.append(user.id)
        except:
            pass
    if not roles and not users:
        return await ctx.send("❌ No valid roles or users provided!")
    data_manager.command_permissions[command_name] = {'roles': roles, 'users': users}
    data_manager.save_data()
    role_mentions = [f"<@&{r}>" for r in roles]
    user_mentions = [f"<@{u}>" for u in users]
    embed = create_embed("✅ Permissions Set", f"**Command:** `{command_name}`\n**Allowed Roles:** {', '.join(role_mentions) if roles else 'None'}\n**Allowed Users:** {', '.join(user_mentions) if users else 'None'}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@perms.command(name='view')
async def perms_view(ctx, command_name: str = None):
    if command_name:
        if command_name not in data_manager.command_permissions:
            return await ctx.send(f"✅ No custom permissions set for `{command_name}` (uses default)")
        perms = data_manager.command_permissions[command_name]
        role_mentions = [f"<@&{r}>" for r in perms.get('roles', [])]
        user_mentions = [f"<@{u}>" for u in perms.get('users', [])]
        embed = create_embed(f"🔒 Permissions for {command_name}", f"**Allowed Roles:** {', '.join(role_mentions) if role_mentions else 'None'}\n**Allowed Users:** {', '.join(user_mentions) if user_mentions else 'None'}", Config.COLOR_INFO)
        await ctx.send(embed=embed)
    else:
        if not data_manager.command_permissions:
            return await ctx.send("✅ No custom command permissions set!")
        embed = create_embed("🔒 Custom Command Permissions", f"**Total:** {len(data_manager.command_permissions)} commands", Config.COLOR_INFO)
        for cmd, perms in list(data_manager.command_permissions.items())[:10]:
            role_count = len(perms.get('roles', []))
            user_count = len(perms.get('users', []))
            embed.add_field(name=f"`{cmd}`", value=f"{role_count} roles, {user_count} users", inline=True)
        await ctx.send(embed=embed)

"""
END OF PART 5 - PASTE PART 6 BELOW THIS
"""


"""
ADVANCED DISCORD BOT - PART 6/8 (GOOGLE GEMINI - 100% FREE!)
PASTE THIS AFTER PART 5 - Utility & AI with 15 Personalities
"""

@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = create_embed("🏓 Pong!", f"**Latency:** {latency}ms", Config.COLOR_PRIMARY)
    await ctx.send(embed=embed)

@bot.command(name='serverinfo')
@commands.guild_only()
async def server_info(ctx):
    guild = ctx.guild
    embed = create_embed(f"📊 {guild.name}", f"**ID:** `{guild.id}`", Config.COLOR_PRIMARY)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, style='R'), inline=True)
    embed.add_field(name="Members", value=f"{guild.member_count}", inline=True)
    embed.add_field(name="Channels", value=f"{len(guild.channels)}", inline=True)
    embed.add_field(name="Roles", value=f"{len(guild.roles)}", inline=True)
    embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='userinfo')
@commands.guild_only()
async def user_info(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = create_embed(f"👤 {member.name}", f"**ID:** `{member.id}`", Config.COLOR_PRIMARY)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Nickname", value=member.display_name, inline=True)
    embed.add_field(name="Created", value=discord.utils.format_dt(member.created_at, style='R'), inline=True)
    embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, style='R') if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Roles", value=f"{len(member.roles) - 1}", inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = create_embed(f"🖼️ {member.name}'s Avatar", "", Config.COLOR_PRIMARY)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='afk')
@commands.guild_only()
async def set_afk(ctx, *, message: str = "AFK"):
    data_manager.afk_users[ctx.author.id] = {'message': message, 'time': datetime.utcnow().isoformat()}
    data_manager.save_data()
    await ctx.send(f"✅ You are now AFK: **{message}**")

@bot.command(name='snipe')
@commands.guild_only()
async def snipe(ctx):
    if ctx.channel.id not in data_manager.deleted_messages:
        return await ctx.send("❌ No recently deleted messages!")
    msg_data = data_manager.deleted_messages[ctx.channel.id]
    author = await bot.fetch_user(msg_data['author'])
    embed = create_embed("🎯 Sniped Message", f"**Author:** {author.mention}\n**Content:** {msg_data['content']}", Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.command(name='editsnipe')
@commands.guild_only()
async def edit_snipe(ctx):
    if ctx.channel.id not in data_manager.edited_messages:
        return await ctx.send("❌ No recently edited messages!")
    msg_data = data_manager.edited_messages[ctx.channel.id]
    author = await bot.fetch_user(msg_data['author'])
    embed = create_embed("✏️ Edit Sniped", f"**Author:** {author.mention}\n**Before:** {msg_data['before']}\n**After:** {msg_data['after']}", Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.command(name='remind')
async def set_reminder(ctx, duration: str, *, message: str):
    if len(data_manager.reminders.get(ctx.author.id, [])) >= Config.MAX_REMINDERS_PER_USER:
        return await ctx.send(f"❌ You can only have {Config.MAX_REMINDERS_PER_USER} active reminders!")
    try:
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1]
        amount = int(duration[:-1])
        seconds = amount * time_units.get(unit, 60)
    except:
        return await ctx.send("❌ Invalid duration! Use: 10s, 5m, 2h, 1d")
    reminder_time = datetime.utcnow().timestamp() + seconds
    reminder = {'time': reminder_time, 'message': message, 'channel_id': ctx.channel.id}
    data_manager.reminders[ctx.author.id].append(reminder)
    data_manager.save_data()
    embed = create_embed("⏰ Reminder Set", f"I'll remind you in **{duration}**: {message}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='todo')
async def add_todo(ctx, *, task: str):
    data_manager.todos[ctx.author.id].append(task)
    data_manager.save_data()
    await ctx.send(f"✅ Added to your todo list: **{task}**")

@bot.command(name='todos')
async def view_todos(ctx):
    todos = data_manager.todos.get(ctx.author.id, [])
    if not todos:
        return await ctx.send("✅ Your todo list is empty!")
    embed = create_embed(f"📝 {ctx.author.name}'s Todo List", "\n".join([f"{i+1}. {task}" for i, task in enumerate(todos)]), Config.COLOR_INFO)
    await ctx.send(embed=embed)

@bot.command(name='poll')
@commands.guild_only()
async def create_poll(ctx, question: str, *options):
    if len(options) < 2:
        return await ctx.send("❌ Polls need at least 2 options!")
    if len(options) > 10:
        return await ctx.send("❌ Maximum 10 options!")
    embed = create_embed("📊 Poll", question, Config.COLOR_PRIMARY)
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    for i, option in enumerate(options):
        embed.add_field(name=f"{reactions[i]} {option}", value="\u200b", inline=False)
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(reactions[i])

@bot.command(name='say')
@commands.guild_only()
@has_command_permission()
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name='embedsay')
@commands.guild_only()
@has_command_permission()
async def embed_say(ctx, *, message: str):
    await ctx.message.delete()
    embed = create_embed("", message, Config.COLOR_PRIMARY)
    await ctx.send(embed=embed)

# ==================== AI ASSISTANT (GOOGLE GEMINI - FREE!) ====================

@bot.group(name='ai', invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def ai(ctx):
    """AI Assistant management"""
    if ctx.invoked_subcommand is None:
        ai_channels = [f"<#{ch}>" for ch in data_manager.ai_channels]
        personalities = ', '.join(list(Config.AI_PERSONALITIES.keys())[:5]) + '...'
        embed = create_embed(
            "🤖 AI Assistant Settings (Google Gemini - FREE!)",
            f"**Active Channels:** {', '.join(ai_channels) if ai_channels else 'None'}\n"
            f"**Personality:** {data_manager.ai_personality}\n"
            f"**Max Length:** {data_manager.ai_max_length} tokens\n"
            f"**Available Personalities:** {personalities}\n\n"
            f"**Commands:**\n"
            f"`{Config.PREFIX}ai setup <channel>` - Enable AI\n"
            f"`{Config.PREFIX}ai remove <channel>` - Disable AI\n"
            f"`{Config.PREFIX}ai personality <type>` - Change personality\n"
            f"`{Config.PREFIX}ai list` - List all personalities\n"
            f"`{Config.PREFIX}ask <question>` - Ask AI anywhere",
            Config.COLOR_INFO
        )
        await ctx.send(embed=embed)

@ai.command(name='setup')
async def ai_setup(ctx, channel: discord.TextChannel):
    """Enable AI in a channel"""
    if channel.id in data_manager.ai_channels:
        return await ctx.send(f"❌ AI is already enabled in {channel.mention}!")
    
    data_manager.ai_channels.add(channel.id)
    data_manager.save_data()
    
    embed = create_embed(
        "✅ AI Enabled (Google Gemini - FREE!)",
        f"**Channel:** {channel.mention}\n\n"
        f"Gemini AI will now respond to all messages in this channel!\n"
        f"**Current Personality:** {data_manager.ai_personality}\n"
        f"Change it with `{Config.PREFIX}ai personality <type>`",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@ai.command(name='remove')
async def ai_remove(ctx, channel: discord.TextChannel):
    """Remove AI from a channel"""
    if channel.id not in data_manager.ai_channels:
        return await ctx.send(f"❌ AI is not enabled in {channel.mention}!")
    
    data_manager.ai_channels.discard(channel.id)
    data_manager.save_data()
    
    embed = create_embed(
        "✅ AI Removed",
        f"**Channel:** {channel.mention}\n\nAI has been disabled in this channel.",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@ai.command(name='channels')
async def ai_channels_list(ctx):
    """List AI-enabled channels"""
    if not data_manager.ai_channels:
        return await ctx.send("✅ No channels have AI enabled!")
    
    channels = []
    for channel_id in data_manager.ai_channels:
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            channels.append(f"• {channel.mention}")
        else:
            channels.append(f"• Unknown Channel (`{channel_id}`)")
    
    embed = create_embed(
        "🤖 AI-Enabled Channels (Gemini)",
        "\n".join(channels),
        Config.COLOR_INFO
    )
    await ctx.send(embed=embed)

@ai.command(name='personality')
async def ai_personality(ctx, personality: str):
    """Set AI personality"""
    if personality.lower() not in Config.AI_PERSONALITIES:
        return await ctx.send(f"❌ Invalid personality! Use `{Config.PREFIX}ai list` to see all personalities.")
    
    data_manager.ai_personality = personality.lower()
    data_manager.save_data()
    
    embed = create_embed(
        "✅ AI Personality Updated",
        f"**New Personality:** {personality.title()}\n\n"
        f"**Description:** {Config.AI_PERSONALITIES[personality.lower()]}\n\n"
        f"The AI will now respond with this personality!",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@ai.command(name='list')
async def ai_list_personalities(ctx):
    """List all AI personalities"""
    embed = create_embed(
        "🎭 Available AI Personalities (15 Total)",
        "Change personality with `+ai personality <type>`",
        Config.COLOR_INFO
    )
    
    for name, description in Config.AI_PERSONALITIES.items():
        embed.add_field(
            name=f"**{name}**",
            value=description[:100],
            inline=False
        )
    
    await ctx.send(embed=embed)

@ai.command(name='reset')
async def ai_reset(ctx):
    """Reset AI conversation history"""
    embed = create_embed(
        "✅ AI Reset",
        "Conversation history has been cleared!\nGemini AI will start fresh.",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@ai.command(name='maxlength')
async def ai_maxlength(ctx, length: int):
    """Set max AI response length"""
    if length < 100 or length > 2000:
        return await ctx.send("❌ Max length must be between 100 and 2000!")
    
    data_manager.ai_max_length = length
    data_manager.save_data()
    
    embed = create_embed(
        "✅ Max Length Updated",
        f"**New Max Length:** {length} tokens",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@bot.command(name='ask')
async def ask_ai(ctx, *, question: str):
    """Ask Gemini AI a question anywhere"""
    
    if not os.getenv('GEMINI_API_KEY'):
        return await ctx.send("❌ AI is not configured! The bot owner needs to set GEMINI_API_KEY in environment variables.\n\n**Get a FREE key at:** https://makersuite.google.com/app/apikey")
    
    async with ctx.typing():
        try:
            async with aiohttp.ClientSession() as session:
                api_key = os.getenv('GEMINI_API_KEY')
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
                
                system_prompt = Config.AI_PERSONALITIES.get(data_manager.ai_personality, Config.AI_PERSONALITIES['helpful'])
                full_prompt = f"{system_prompt}\n\nUser question: {question}"
                
                data = {
                    "contents": [{
                        "parts": [{"text": full_prompt}]
                    }],
                    "generationConfig": {
                        "maxOutputTokens": data_manager.ai_max_length,
                        "temperature": 0.7
                    }
                }
                
                headers = {"Content-Type": "application/json"}
                
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logging.error(f"Gemini API Error: {error_text}")
                        return await ctx.send("❌ AI API error! Make sure your GEMINI_API_KEY is valid.\n\n**Get a FREE key at:** https://makersuite.google.com/app/apikey")
                    
                    result = await resp.json()
                    
                    if 'candidates' not in result or not result['candidates']:
                        return await ctx.send("❌ AI couldn't generate a response. Try rephrasing your question!")
                    
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    embed = create_embed(
                        f"🤖 Gemini AI ({data_manager.ai_personality.title()})",
                        ai_response[:4096],
                        Config.COLOR_PRIMARY
                    )
                    embed.set_footer(text=f"Asked by {ctx.author.name} • FREE Gemini API")
                    
                    await ctx.send(embed=embed)
        
        except Exception as e:
            logging.error(f"AI Error: {e}")
            await ctx.send(f"❌ Failed to get AI response: {str(e)}\n\n**Get a FREE Gemini key at:** https://makersuite.google.com/app/apikey")

@bot.command(name='chat')
async def chat_ai(ctx, *, message: str):
    """Chat with Gemini AI (alias for ask)"""
    await ask_ai(ctx, question=message)

"""
END OF PART 6 (GEMINI - FREE!) - PASTE PART 7 BELOW THIS
"""


"""
ADVANCED DISCORD BOT - PART 7/8 (FINAL)
PASTE THIS AFTER PART 6 - Help, Config & Verification Commands
"""

@bot.command(name='help')
async def help_command(ctx):
    embeds = []
    
    page1 = create_embed(
        "🤖 Bot Help - Page 1/5",
        f"**Prefix:** `{Config.PREFIX}`\n\n"
        f"**180+ Commands | FREE AI | 15 Personalities**\n\n"
        f"**Quick Start:**\n"
        f"`{Config.PREFIX}setup` - Setup wizard\n"
        f"`{Config.PREFIX}perms set <cmd> @role` - Set permissions\n"
        f"`{Config.PREFIX}ai setup #channel` - Enable FREE AI\n"
        f"`{Config.PREFIX}ai list` - See 15 personalities!",
        Config.COLOR_PRIMARY
    )
    page1.add_field(name="📋 Moderation", value="`ban, kick, mute, warn, purge, lock`", inline=False)
    page1.add_field(name="🛡️ Security", value="`whitelist, antibot, antilink, perms`", inline=False)
    page1.add_field(name="🤖 AI (FREE!)", value="`ai setup, ask, chat` - 15 Personalities!", inline=False)
    page1.set_footer(text="Page 1/5 • Use ⏪ ⏩ to navigate")
    embeds.append(page1)
    
    page2 = create_embed(
        "🤖 Bot Help - Page 2/5",
        "**Moderation Commands**",
        Config.COLOR_PRIMARY
    )
    page2.add_field(name="Ban/Kick", value="`ban, unban, tempban, softban, kick`", inline=False)
    page2.add_field(name="Mute", value="`mute, unmute, tempmute, timeout`", inline=False)
    page2.add_field(name="Warnings", value="`warn, warnings, clearwarns`", inline=False)
    page2.add_field(name="Cleanup", value="`purge, purgebots, purgeuser, purgelinks, purgeimages`", inline=False)
    page2.add_field(name="Channel", value="`lock, unlock, lockdown, unlockdown, slowmode`", inline=False)
    page2.add_field(name="Roles", value="`addrole, removerole, setnick, resetnick`", inline=False)
    page2.set_footer(text="Page 2/5")
    embeds.append(page2)
    
    page3 = create_embed(
        "🤖 Bot Help - Page 3/5",
        "**Security & Permissions**",
        Config.COLOR_PRIMARY
    )
    page3.add_field(name="Whitelist", value="`whitelist add/remove/list\nrolewhitelist add/remove/list`", inline=False)
    page3.add_field(name="Antibot", value="`antibot enable/disable/setchannel/whitelist`", inline=False)
    page3.add_field(name="Permissions", value="`perms set <cmd> @role` - Per-command control!\n`perms view` - See settings", inline=False)
    page3.add_field(name="Permits", value="`permit add/remove/list` - Temp bypass", inline=False)
    page3.set_footer(text="Page 3/5")
    embeds.append(page3)
    
    page4 = create_embed(
        "🤖 Bot Help - Page 4/5",
        "**AI Assistant (FREE GEMINI!) - 15 PERSONALITIES**",
        Config.COLOR_PRIMARY
    )
    page4.add_field(
        name="AI Commands",
        value="`ai setup #channel` - Enable AI\n"
              "`ai personality <type>` - Change personality\n"
              "`ai list` - See all 15 personalities!\n"
              "`ask <question>` - Ask AI anywhere\n"
              "`chat <message>` - Chat with AI",
        inline=False
    )
    page4.add_field(
        name="🎭 Personalities",
        value="helpful, friendly, sassy, flirty, mean, dumb, uwu, gen-z, toxic, simp, chad, professional, casual, funny, sarcastic",
        inline=False
    )
    page4.add_field(name="Utility", value="`ping, serverinfo, userinfo, avatar, afk, snipe, remind, todo, poll`", inline=False)
    page4.set_footer(text="Page 4/5")
    embeds.append(page4)
    
    page5 = create_embed(
        "🤖 Bot Help - Page 5/5",
        "**Configuration & Verification**",
        Config.COLOR_PRIMARY
    )
    page5.add_field(name="Setup", value="`setup, prefix, setlog, setmodlog`", inline=False)
    page5.add_field(name="Welcome/Leave", value="`setwelcome, welcomemsg, togglewelcome`", inline=False)
    page5.add_field(name="Verification", value="`verification setup` - Button verification!\n`verification panel` - Create verify button", inline=False)
    page5.add_field(name="Auto-Role", value="`autorole, autonick`", inline=False)
    page5.add_field(name="Toggles", value="`automod, antiraid, antiswear`", inline=False)
    page5.set_footer(text="Page 5/5 • 180+ Commands!")
    embeds.append(page5)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = Paginator(embeds, ctx.author)
        view.message = await ctx.send(embed=embeds[0], view=view)

@bot.command(name='prefix')
@commands.guild_only()
@has_command_permission()
async def change_prefix(ctx, new_prefix: str):
    if len(new_prefix) > 5:
        return await ctx.send("❌ Prefix must be 5 characters or less!")
    data_manager.custom_prefix = new_prefix
    data_manager.save_data()
    embed = create_embed("✅ Prefix Changed", f"**New Prefix:** `{new_prefix}`\nExample: `{new_prefix}help`", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@bot.command(name='setup')
@commands.guild_only()
@has_command_permission()
async def setup_wizard(ctx):
    embed = create_embed(
        "🛠️ Bot Setup Wizard",
        "Let's set up your bot!\n\n"
        "**Step 1:** Set log channel\n`+setlog #channel`\n\n"
        "**Step 2:** Set moderator roles\n`+perms set ban @Moderator`\n\n"
        "**Step 3:** Enable security\n`+antibot enable`\n`+antiraid` to toggle\n\n"
        "**Step 4:** Whitelist roles\n`+rolewhitelist add @Role`\n\n"
        "**Step 5:** Enable AI (FREE!)\n`+ai setup #chat`\n`+ai list` for personalities\n\n"
        "**Step 6:** Setup verification (optional)\n`+verification setup`\n\n"
        "**Done!** Your bot is configured!",
        Config.COLOR_PRIMARY
    )
    await ctx.send(embed=embed)

# Verification Commands
@bot.group(name='verification', aliases=['verify'], invoke_without_command=True)
@commands.guild_only()
@has_command_permission()
async def verification(ctx):
    if ctx.invoked_subcommand is None:
        status = "enabled" if data_manager.verification_enabled else "disabled"
        embed = create_embed(
            "✅ Verification System",
            f"**Status:** {status.title()}\n"
            f"**Verify Channel:** {f'<#{data_manager.verification_channel_id}>' if data_manager.verification_channel_id else 'Not set'}\n"
            f"**Verified Role:** {f'<@&{data_manager.verification_role_id}>' if data_manager.verification_role_id else 'Not set'}\n"
            f"**Unverified Role:** {f'<@&{data_manager.unverified_role_id}>' if data_manager.unverified_role_id else 'Not set'}\n\n"
            f"**Commands:**\n"
            f"`{Config.PREFIX}verification setup` - Setup wizard\n"
            f"`{Config.PREFIX}verification panel` - Create verify button\n"
            f"`{Config.PREFIX}verification toggle` - Enable/disable",
            Config.COLOR_INFO
        )
        await ctx.send(embed=embed)

@verification.command(name='setup')
async def verification_setup(ctx):
    embed = create_embed(
        "✅ Verification Setup",
        "**Step 1:** Set verified role\n`+verification role @Verified`\n\n"
        "**Step 2:** Set unverified role (optional)\n`+verification unverified @Unverified`\n\n"
        "**Step 3:** Set verification channel\n`+verification channel #verify`\n\n"
        "**Step 4:** Create verification panel\n`+verification panel`\n\n"
        "**Step 5:** Enable verification\n`+verification toggle`\n\n"
        "**Done!** New members will need to verify!",
        Config.COLOR_SUCCESS
    )
    await ctx.send(embed=embed)

@verification.command(name='role')
async def verification_role(ctx, role: discord.Role):
    data_manager.verification_role_id = role.id
    data_manager.save_data()
    embed = create_embed("✅ Verified Role Set", f"**Role:** {role.mention}\nMembers will get this role after verifying.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@verification.command(name='unverified')
async def verification_unverified(ctx, role: discord.Role):
    data_manager.unverified_role_id = role.id
    data_manager.save_data()
    embed = create_embed("✅ Unverified Role Set", f"**Role:** {role.mention}\nNew members will get this role until they verify.", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@verification.command(name='channel')
async def verification_channel(ctx, channel: discord.TextChannel):
    data_manager.verification_channel_id = channel.id
    data_manager.save_data()
    embed = create_embed("✅ Verification Channel Set", f"**Channel:** {channel.mention}\nCreate the verification panel here with `+verification panel`", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@verification.command(name='message')
async def verification_message(ctx, *, message: str):
    data_manager.verification_message = message
    data_manager.save_data()
    embed = create_embed("✅ Verification Message Set", f"**Message:** {message}", Config.COLOR_SUCCESS)
    await ctx.send(embed=embed)

@verification.command(name='panel')
async def verification_panel(ctx):
    if not data_manager.verification_channel_id:
        return await ctx.send("❌ Set verification channel first with `+verification channel #channel`")
    
    channel = ctx.guild.get_channel(data_manager.verification_channel_id)
    if not channel:
        return await ctx.send("❌ Verification channel not found!")
    
    embed = create_embed(
        "✅ Verification",
        data_manager.verification_message,
        Config.COLOR_SUCCESS
    )
    embed.set_footer(text=f"{ctx.guild.name} Verification")
    
    view = VerificationView()
    await channel.send(embed=embed, view=view)
    await ctx.send(f"✅ Verification panel created in {channel.mention}!")

@verification.command(name='toggle')
async def verification_toggle(ctx):
    data_manager.verification_enabled = not data_manager.verification_enabled
    data_manager.save_data()
    status = "enabled" if data_manager.verification_enabled else "disabled"
    await ctx.send(f"✅ Verification {status}!")

# Config commands from previous version
@bot.command(name='setlog')
@commands.guild_only()
@has_command_permission()
async def set_log(ctx, channel: discord.TextChannel):
    data_manager.log_channel_id = channel.id
    data_manager.save_data()
    await ctx.send(f"✅ Log channel set to {channel.mention}")

@bot.command(name='setmodlog')
@commands.guild_only()
@has_command_permission()
async def set_modlog(ctx, channel: discord.TextChannel):
    data_manager.modlog_channel_id = channel.id
    data_manager.save_data()
    await ctx.send(f"✅ Moderation log set to {channel.mention}")

@bot.command(name='setwelcome')
@commands.guild_only()
@has_command_permission()
async def set_welcome(ctx, channel: discord.TextChannel):
    data_manager.welcome_channel_id = channel.id
    data_manager.save_data()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command(name='welcomemsg')
@commands.guild_only()
@has_command_permission()
async def set_welcome_message(ctx, *, message: str):
    data_manager.welcome_message = message
    data_manager.save_data()
    await ctx.send(f"✅ Welcome message set!\nVariables: `{{user.mention}}`, `{{server.name}}`, `{{member.count}}`")

@bot.command(name='togglewelcome')
@commands.guild_only()
@has_command_permission()
async def toggle_welcome(ctx):
    data_manager.welcome_enabled = not data_manager.welcome_enabled
    data_manager.save_data()
    status = "enabled" if data_manager.welcome_enabled else "disabled"
    await ctx.send(f"✅ Welcome messages {status}!")

@bot.command(name='autorole')
@commands.guild_only()
@has_command_permission()
async def set_autorole(ctx, role: discord.Role):
    if role.id in data_manager.autoroles:
        data_manager.autoroles.remove(role.id)
        data_manager.save_data()
        await ctx.send(f"✅ Removed {role.mention} from auto-roles!")
    else:
        data_manager.autoroles.append(role.id)
        data_manager.save_data()
        await ctx.send(f"✅ Added {role.mention} to auto-roles!")

@bot.command(name='antiswear')
@commands.guild_only()
@has_command_permission()
async def toggle_antiswear(ctx):
    data_manager.antiswear_enabled = not data_manager.antiswear_enabled
    data_manager.save_data()
    status = "enabled" if data_manager.antiswear_enabled else "disabled"
    await ctx.send(f"✅ Anti-swear {status}!")

"""
END OF PART 7 (FINAL) - PASTE PART 8 BELOW THIS
"""
  """
ADVANCED DISCORD BOT - PART 8/8 (FINAL)
PASTE THIS AFTER PART 7 - Web Server & Run Code
"""

async def start_keep_alive():
    """Start web server for Render/UptimeRobot"""
    
    async def health(request):
        return web.Response(text='Bot Online!', status=200)
    
    async def status_page(request):
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Status</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        h1 {{
            font-size: 48px;
            margin: 0 0 20px 0;
        }}
        .status {{
            font-size: 24px;
            margin: 20px 0;
        }}
        .info {{
            font-size: 18px;
            margin: 10px 0;
            opacity: 0.9;
        }}
        .badge {{
            display: inline-block;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            margin: 5px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Discord Bot</h1>
        <div class="status">✅ ONLINE</div>
        <div class="info">Servers: {len(bot.guilds)}</div>
        <div class="info">Prefix: {Config.PREFIX}</div>
        <div class="info">Latency: {round(bot.latency * 1000)}ms</div>
        <div>
            <span class="badge">Anti-Raid {'✅' if data_manager.antiraid_enabled else '❌'}</span>
            <span class="badge">Auto-Mod {'✅' if data_manager.automod_enabled else '❌'}</span>
        </div>
    </div>
</body>
</html>
        '''
        return web.Response(text=html, content_type='text/html')
    
    app = web.Application()
    app.router.add_get('/', status_page)
    app.router.add_get('/health', health)
    app.router.add_get('/ping', health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
    await site.start()
    
    logging.info(f'✅ Web server running on port {Config.PORT}')

async def main():
    """Main bot startup"""
    await start_keep_alive()
    
    try:
        await bot.start(Config.TOKEN)
    except KeyboardInterrupt:
        logging.info('👋 Bot shutdown requested')
        await bot.close()
    except Exception as e:
        logging.error(f'❌ Bot error: {e}')
        await bot.close()

if __name__ == '__main__':
    print('=' * 70)
    print('ADVANCED DISCORD BOT')
    print('=' * 70)
    print(f'Owner ID: {Config.OWNER_ID}')
    print(f'Prefix: {Config.PREFIX}')
    print(f'Port: {Config.PORT}')
    print('=' * 70)
    
    if not Config.TOKEN:
        logging.error('DISCORD_BOT_TOKEN not set in environment variables!')
        print('\nERROR: DISCORD_BOT_TOKEN not found!')
        print('Please set it in your environment variables or .env file')
        exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('👋 Bot stopped by user')
    except Exception as e:
        logging.error(f'❌ Failed to start: {e}')
        print(f'\nFailed to start: {e}')
