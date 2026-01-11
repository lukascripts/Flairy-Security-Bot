"""
Elite Discord Security Bot - Part 1: Core Setup & Configuration
Production-Grade Security System
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
from typing import Optional, Set, Dict, List, Tuple
import re
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Config:
    """Bot Configuration"""
    OWNER_ID = 1029438856069656576
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    PREFIX = '+'
    PORT = int(os.getenv('PORT', 8080))
    STAFF_ROLE_ID = 1432081794647199895
    
    # Anti-Spam Settings
    SPAM_THRESHOLD = 7
    SPAM_TIMEFRAME = 4
    SPAM_TIMEOUTS = {1: 5, 2: 15, 3: 30, 4: 60, 5: 180}
    
    # Anti-Raid Settings
    RAID_JOIN_THRESHOLD = 10
    RAID_JOIN_TIMEFRAME = 10
    ACCOUNT_AGE_MINIMUM = 7
    
    # Content Moderation
    PROFANITY_TIMEOUT = 10
    BANNED_WORDS = ['nigger', 'nigga', 'n1gger', 'n1gga', 'faggot', 'f4ggot']
    BANNED_PATTERNS = [r'n[i1!]gg[ae]r', r'f[a4@]gg[o0]t']
    
    # Mention & Link Spam
    MENTION_LIMIT = 5
    MENTION_TIMEOUT = 15
    LINK_LIMIT = 3
    LINK_TIMEFRAME = 10
    
    # Anti-Nuke Thresholds
    CHANNEL_DELETE_THRESHOLD = 3
    CHANNEL_DELETE_TIMEFRAME = 30
    ROLE_DELETE_THRESHOLD = 3
    ROLE_DELETE_TIMEFRAME = 30
    BAN_THRESHOLD = 3
    BAN_TIMEFRAME = 30
    KICK_THRESHOLD = 5
    KICK_TIMEFRAME = 60
    
    # Dangerous Permissions
    DANGEROUS_PERMISSIONS = [
        'administrator',
        'kick_members',
        'ban_members',
        'manage_channels',
        'manage_guild',
        'manage_roles',
        'manage_webhooks',
        'manage_messages',
        'mention_everyone'
    ]

class DataManager:
    """Advanced Data Management System"""
    
    def __init__(self):
        self.data_file = 'security_data.json'
        self.whitelist: Set[int] = set()
        self.blacklist: Set[int] = set()
        self.user_violations: Dict[int, int] = defaultdict(int)
        self.user_warnings: Dict[int, List[Dict]] = defaultdict(list)
        self.message_history: Dict[int, List[float]] = defaultdict(list)
        self.link_history: Dict[int, List[float]] = defaultdict(list)
        self.action_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Verification System
        self.verified_role_id: Optional[int] = None
        self.unverified_role_id: Optional[int] = None
        self.verification_channel_id: Optional[int] = None
        
        # Logging
        self.log_channel_id: Optional[int] = None
        
        # Auto-Moderation
        self.automod_enabled = True
        self.anti_raid_enabled = True
        self.anti_nuke_enabled = True
        
        self.load_data()
    
    def load_data(self):
        """Load persistent data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.whitelist = set(data.get('whitelist', []))
                    self.blacklist = set(data.get('blacklist', []))
                    self.user_violations = defaultdict(int, {int(k): v for k, v in data.get('violations', {}).items()})
                    self.user_warnings = defaultdict(list, {int(k): v for k, v in data.get('warnings', {}).items()})
                    self.verified_role_id = data.get('verified_role_id')
                    self.unverified_role_id = data.get('unverified_role_id')
                    self.verification_channel_id = data.get('verification_channel_id')
                    self.log_channel_id = data.get('log_channel_id')
                    self.automod_enabled = data.get('automod_enabled', True)
                    self.anti_raid_enabled = data.get('anti_raid_enabled', True)
                    self.anti_nuke_enabled = data.get('anti_nuke_enabled', True)
                    logging.info("Data loaded successfully")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
    
    def save_data(self):
        """Save persistent data to file"""
        try:
            data = {
                'whitelist': list(self.whitelist),
                'blacklist': list(self.blacklist),
                'violations': {str(k): v for k, v in self.user_violations.items()},
                'warnings': {str(k): v for k, v in self.user_warnings.items()},
                'verified_role_id': self.verified_role_id,
                'unverified_role_id': self.unverified_role_id,
                'verification_channel_id': self.verification_channel_id,
                'log_channel_id': self.log_channel_id,
                'automod_enabled': self.automod_enabled,
                'anti_raid_enabled': self.anti_raid_enabled,
                'anti_nuke_enabled': self.anti_nuke_enabled
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving data: {e}")
    
    def add_to_whitelist(self, user_id: int):
        """Add user to whitelist"""
        self.whitelist.add(user_id)
        self.blacklist.discard(user_id)
        self.save_data()
    
    def remove_from_whitelist(self, user_id: int):
        """Remove user from whitelist"""
        self.whitelist.discard(user_id)
        self.save_data()
    
    def is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return user_id in self.whitelist
    
    def add_to_blacklist(self, user_id: int):
        """Add user to blacklist"""
        self.blacklist.add(user_id)
        self.whitelist.discard(user_id)
        self.save_data()
    
    def remove_from_blacklist(self, user_id: int):
        """Remove user from blacklist"""
        self.blacklist.discard(user_id)
        self.save_data()
    
    def is_blacklisted(self, user_id: int) -> bool:
        """Check if user is blacklisted"""
        return user_id in self.blacklist
    
    def add_warning(self, user_id: int, reason: str, moderator_id: int):
        """Add warning to user"""
        warning = {
            'reason': reason,
            'moderator': moderator_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.user_warnings[user_id].append(warning)
        self.save_data()
    
    def get_warnings(self, user_id: int) -> List[Dict]:
        """Get all warnings for a user"""
        return self.user_warnings.get(user_id, [])
    
    def clear_warnings(self, user_id: int):
        """Clear all warnings for a user"""
        if user_id in self.user_warnings:
            del self.user_warnings[user_id]
            self.save_data()
    
    def track_action(self, action_type: str, user_id: int, guild_id: int):
        """Track moderation actions for anti-nuke detection"""
        current_time = datetime.utcnow().timestamp()
        key = f"{guild_id}:{user_id}:{action_type}"
        
        self.action_history[key].append({
            'timestamp': current_time,
            'user_id': user_id
        })
        
        # Clean old entries
        timeframe = Config.CHANNEL_DELETE_TIMEFRAME
        self.action_history[key] = [
            entry for entry in self.action_history[key]
            if current_time - entry['timestamp'] <= timeframe
        ]
    
    def get_action_count(self, action_type: str, user_id: int, guild_id: int, timeframe: int) -> int:
        """Get count of recent actions"""
        key = f"{guild_id}:{user_id}:{action_type}"
        current_time = datetime.utcnow().timestamp()
        
        recent = [
            entry for entry in self.action_history.get(key, [])
            if current_time - entry['timestamp'] <= timeframe
        ]
        return len(recent)

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=Config.PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)
data_manager = DataManager()

# Utility Functions
def is_owner():
    """Check if user is bot owner"""
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id != Config.OWNER_ID:
            await interaction.response.send_message(
                "Only the bot owner can use this command.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

def is_owner_or_admin():
    """Check if user is owner or admin"""
    async def predicate(ctx):
        return ctx.author.id == Config.OWNER_ID or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_moderator():
    """Check if user has moderator permissions"""
    async def predicate(ctx):
        if ctx.author.id == Config.OWNER_ID:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        if ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members:
            return True
        return False
    return commands.check(predicate)

async def get_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Get or create log channel"""
    if data_manager.log_channel_id:
        channel = guild.get_channel(data_manager.log_channel_id)
        if channel:
            return channel
    
    log_channel = discord.utils.get(guild.text_channels, name='security-logs')
    if not log_channel:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            log_channel = await guild.create_text_channel(
                'security-logs',
                reason='Security logging channel',
                overwrites=overwrites
            )
            data_manager.log_channel_id = log_channel.id
            data_manager.save_data()
        except Exception as e:
            logging.error(f"Failed to create log channel: {e}")
            return None
    
    return log_channel

async def log_action(guild: discord.Guild, title: str, description: str, color: discord.Color, fields: List[Tuple[str, str]] = None):
    """Log security action to log channel"""
    log_channel = await get_log_channel(guild)
    if not log_channel:
        return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=True)
    
    try:
        await log_channel.send(embed=embed)
    except Exception as e:
        logging.error(f"Failed to send log: {e}")

def calculate_timeout(violation_count: int) -> int:
    """Calculate timeout duration based on violations"""
    return Config.SPAM_TIMEOUTS.get(violation_count, 180)

def contains_profanity(content: str) -> Tuple[bool, str]:
    """Check if content contains profanity"""
    content_lower = content.lower()
    
    for word in Config.BANNED_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', content_lower):
            return True, word
    
    for pattern in Config.BANNED_PATTERNS:
        match = re.search(pattern, content_lower, re.IGNORECASE)
        if match:
            return True, match.group(0)
    
    return False, ''

def extract_links(content: str) -> List[str]:
    """Extract URLs from content"""
    url_pattern = r'https?://[^\s]+'
    return re.findall(url_pattern, content)

def is_suspicious_account(member: discord.Member) -> Tuple[bool, str]:
    """Check if account is suspicious"""
    account_age = (datetime.utcnow() - member.created_at).days
    
    if account_age < Config.ACCOUNT_AGE_MINIMUM:
        return True, f"Account age: {account_age} days (minimum: {Config.ACCOUNT_AGE_MINIMUM})"
    
    if member.avatar is None:
        return True, "No profile picture"
    
    return False, ""

"""
Elite Discord Security Bot - Part 2: Verification System
Add this after Part 1
"""

# Verification Button View
class VerificationView(View):
    """Verification button interface"""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        custom_id="verify_button",
        emoji="✅"
    )
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = interaction.user
        
        verified_role = guild.get_role(data_manager.verified_role_id) if data_manager.verified_role_id else None
        unverified_role = guild.get_role(data_manager.unverified_role_id) if data_manager.unverified_role_id else None
        
        if not verified_role:
            await interaction.response.send_message(
                "Verification system not configured. Contact an administrator.",
                ephemeral=True
            )
            return
        
        if verified_role in member.roles:
            await interaction.response.send_message(
                "You are already verified.",
                ephemeral=True
            )
            return
        
        # Check if blacklisted
        if data_manager.is_blacklisted(member.id):
            await interaction.response.send_message(
                "You are not eligible for verification. Contact an administrator.",
                ephemeral=True
            )
            return
        
        try:
            await member.add_roles(verified_role, reason="User verified")
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason="User verified")
            
            await interaction.response.send_message(
                f"Welcome to {guild.name}! You have been verified and now have full access to the server.",
                ephemeral=True
            )
            
            await log_action(
                guild,
                'User Verified',
                f'{member.mention} verified successfully',
                discord.Color.green(),
                [('User ID', str(member.id)), ('Account Created', member.created_at.strftime('%Y-%m-%d'))]
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Verification failed: {str(e)}",
                ephemeral=True
            )
            logging.error(f"Verification error: {e}")

# Bot Events
@bot.event
async def on_ready():
    """Bot startup event"""
    print('=' * 70)
    print(f'Bot Online: {bot.user}')
    print(f'Servers: {len(bot.guilds)}')
    print(f'Users: {len(bot.users)}')
    print(f'Prefix: {Config.PREFIX}')
    print('=' * 70)
    
    bot.add_view(VerificationView())
    
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        logging.error(f'Command sync failed: {e}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{Config.PREFIX}help | Elite Security"
        ),
        status=discord.Status.online
    )
    
    # Start background tasks
    if not cleanup_task.is_running():
        cleanup_task.start()
    
    print('All systems active')
    print('=' * 70)

@tasks.loop(hours=1)
async def cleanup_task():
    """Cleanup old data periodically"""
    try:
        current_time = datetime.utcnow().timestamp()
        
        # Clean message history
        for user_id in list(data_manager.message_history.keys()):
            data_manager.message_history[user_id] = [
                ts for ts in data_manager.message_history[user_id]
                if current_time - ts <= 3600
            ]
            if not data_manager.message_history[user_id]:
                del data_manager.message_history[user_id]
        
        # Clean link history
        for user_id in list(data_manager.link_history.keys()):
            data_manager.link_history[user_id] = [
                ts for ts in data_manager.link_history[user_id]
                if current_time - ts <= 3600
            ]
            if not data_manager.link_history[user_id]:
                del data_manager.link_history[user_id]
        
        logging.info("Cleanup task completed")
    except Exception as e:
        logging.error(f"Cleanup task error: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    """Handle member join events"""
    guild = member.guild
    
    # Check if blacklisted
    if data_manager.is_blacklisted(member.id):
        try:
            await member.kick(reason="Blacklisted user")
            await log_action(
                guild,
                'Blacklisted User Kicked',
                f'{member.mention} attempted to join but is blacklisted',
                discord.Color.red(),
                [('User ID', str(member.id))]
            )
        except Exception as e:
            logging.error(f"Failed to kick blacklisted user: {e}")
        return
    
    # Auto-assign unverified role
    if data_manager.unverified_role_id:
        unverified_role = guild.get_role(data_manager.unverified_role_id)
        if unverified_role:
            try:
                await member.add_roles(unverified_role, reason="Auto-assign unverified")
            except Exception as e:
                logging.error(f"Failed to assign unverified role: {e}")
    
    # Check for suspicious account
    is_suspicious, reason = is_suspicious_account(member)
    if is_suspicious and data_manager.anti_raid_enabled:
        await log_action(
            guild,
            'Suspicious Account Detected',
            f'{member.mention} joined with suspicious profile',
            discord.Color.orange(),
            [('User ID', str(member.id)), ('Reason', reason)]
        )
    
    # Bot addition protection
    if member.bot:
        await asyncio.sleep(1)
        
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                inviter = entry.user
                
                if inviter.id == Config.OWNER_ID or data_manager.is_whitelisted(inviter.id):
                    await log_action(
                        guild,
                        'Bot Addition Authorized',
                        f'{inviter.mention} added {member.mention}',
                        discord.Color.green(),
                        [('Bot', member.mention), ('Added By', inviter.mention)]
                    )
                    return
                
                if data_manager.anti_nuke_enabled:
                    try:
                        await member.kick(reason=f'Unauthorized bot addition by {inviter}')
                        
                        inviter_member = guild.get_member(inviter.id)
                        if inviter_member and inviter_member != guild.owner:
                            roles_to_remove = [
                                r for r in inviter_member.roles
                                if r != guild.default_role and r.position < guild.me.top_role.position
                            ]
                            if roles_to_remove:
                                await inviter_member.remove_roles(*roles_to_remove, reason='Unauthorized bot addition')
                        
                        await log_action(
                            guild,
                            'Anti-Nuke: Unauthorized Bot Blocked',
                            f'Bot: {member.mention}\nAdded by: {inviter.mention}',
                            discord.Color.red(),
                            [('Action', 'Bot kicked, roles stripped')]
                        )
                    except Exception as e:
                        logging.error(f"Failed to handle unauthorized bot: {e}")
                break
    
    # Raid detection
    if not data_manager.anti_raid_enabled:
        return
    
    current_time = datetime.utcnow().timestamp()
    
    if not hasattr(bot, 'recent_joins'):
        bot.recent_joins = defaultdict(list)
    
    bot.recent_joins[guild.id].append(current_time)
    bot.recent_joins[guild.id] = [
        ts for ts in bot.recent_joins[guild.id]
        if current_time - ts <= Config.RAID_JOIN_TIMEFRAME
    ]
    
    if len(bot.recent_joins[guild.id]) >= Config.RAID_JOIN_THRESHOLD:
        try:
            await guild.edit(
                verification_level=discord.VerificationLevel.highest,
                reason='Raid detected - automatic protection'
            )
            await log_action(
                guild,
                'Anti-Raid: Mass Join Detected',
                f'Detected {len(bot.recent_joins[guild.id])} joins in {Config.RAID_JOIN_TIMEFRAME} seconds',
                discord.Color.red(),
                [('Action', 'Verification level raised to HIGHEST')]
            )
            bot.recent_joins[guild.id].clear()
        except Exception as e:
            logging.error(f"Failed to activate raid protection: {e}")

@bot.event
async def on_member_remove(member: discord.Member):
    """Log member leaves"""
    await log_action(
        member.guild,
        'Member Left',
        f'{member.mention} left the server',
        discord.Color.orange(),
        [('User', str(member)), ('ID', str(member.id))]
    )

# Verification Commands
@bot.tree.command(name="setup_verification", description="Setup verification system")
@app_commands.describe(
    verified_role="Role to give when verified",
    unverified_role="Role for unverified members",
    channel="Channel for verification panel"
)
@is_owner()
async def setup_verification(
    interaction: discord.Interaction,
    verified_role: discord.Role,
    unverified_role: discord.Role,
    channel: discord.TextChannel
):
    """Setup the verification system"""
    data_manager.verified_role_id = verified_role.id
    data_manager.unverified_role_id = unverified_role.id
    data_manager.verification_channel_id = channel.id
    data_manager.save_data()
    
    embed = discord.Embed(
        title='Verification System Configured',
        description='Verification system has been set up successfully.',
        color=discord.Color.green()
    )
    embed.add_field(name='Verified Role', value=verified_role.mention, inline=True)
    embed.add_field(name='Unverified Role', value=unverified_role.mention, inline=True)
    embed.add_field(name='Channel', value=channel.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    await log_action(
        interaction.guild,
        'Verification System Configured',
        f'Setup by {interaction.user.mention}',
        discord.Color.blue(),
        [
            ('Verified Role', verified_role.mention),
            ('Unverified Role', unverified_role.mention),
            ('Channel', channel.mention)
        ]
    )

@bot.tree.command(name="send_verification", description="Send verification panel")
@app_commands.describe(channel="Channel to send panel (optional)")
@is_owner()
async def send_verification(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Send the verification panel"""
    target_channel = channel or interaction.channel
    
    if not data_manager.verified_role_id:
        await interaction.response.send_message(
            "Setup verification first with `/setup_verification`",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title='Server Verification',
        description=(
            'Welcome to the server!\n\n'
            'To gain access to all channels, please verify yourself by clicking the button below.\n\n'
            'This helps us keep the server safe and secure for everyone.'
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text='Click the Verify button to get started')
    
    view = VerificationView()
    await target_channel.send(embed=embed, view=view)
    
    await interaction.response.send_message(
        f'Verification panel sent to {target_channel.mention}',
        ephemeral=True
    )

@bot.tree.command(name="verify_user", description="Manually verify a user")
@app_commands.describe(member="Member to verify")
async def verify_user(interaction: discord.Interaction, member: discord.Member):
    """Manually verify a user"""
    if interaction.user.id != Config.OWNER_ID and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "You need administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    if not data_manager.verified_role_id:
        await interaction.response.send_message(
            "Setup verification first with `/setup_verification`",
            ephemeral=True
        )
        return
    
    verified_role = interaction.guild.get_role(data_manager.verified_role_id)
    unverified_role = interaction.guild.get_role(data_manager.unverified_role_id)
    
    try:
        await member.add_roles(verified_role, reason=f'Manually verified by {interaction.user}')
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        
        await interaction.response.send_message(
            f'{member.mention} has been verified.',
            ephemeral=True
        )
        
        await log_action(
            interaction.guild,
            'Manual Verification',
            f'{member.mention} verified by {interaction.user.mention}',
            discord.Color.green(),
            [('User', member.mention), ('Verified By', interaction.user.mention)]
        )
    except Exception as e:
        await interaction.response.send_message(
            f'Failed to verify user: {e}',
            ephemeral=True
      )

  """
Elite Discord Security Bot - Part 3: Anti-Nuke Protection
Add this after Part 2
"""

@bot.event
async def on_guild_role_create(role: discord.Role):
    """Monitor role creation for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    guild = role.guild
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.target.id == role.id:
            creator = entry.user
            
            if creator.id == Config.OWNER_ID or data_manager.is_whitelisted(creator.id):
                break
            
            # Track action
            data_manager.track_action('role_create', creator.id, guild.id)
            count = data_manager.get_action_count('role_create', creator.id, guild.id, Config.ROLE_DELETE_TIMEFRAME)
            
            if count >= Config.ROLE_DELETE_THRESHOLD:
                try:
                    await role.delete(reason='Anti-nuke: Mass role creation detected')
                    
                    member = guild.get_member(creator.id)
                    if member and member != guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != guild.default_role and r.position < guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Mass role creation')
                        
                        try:
                            await member.timeout(timedelta(days=7), reason='Anti-nuke: Mass role creation')
                        except:
                            pass
                    
                    await log_action(
                        guild,
                        'Anti-Nuke: Mass Role Creation',
                        f'User: {creator.mention}\nRoles created: {count}',
                        discord.Color.red(),
                        [('Action', 'Role deleted, user roles stripped, 7-day timeout')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke role creation failed: {e}")
            break

@bot.event
async def on_guild_role_delete(role: discord.Role):
    """Monitor role deletion for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    guild = role.guild
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        if entry.target.id == role.id:
            deleter = entry.user
            
            if deleter.id == Config.OWNER_ID or data_manager.is_whitelisted(deleter.id):
                break
            
            data_manager.track_action('role_delete', deleter.id, guild.id)
            count = data_manager.get_action_count('role_delete', deleter.id, guild.id, Config.ROLE_DELETE_TIMEFRAME)
            
            if count >= Config.ROLE_DELETE_THRESHOLD:
                try:
                    member = guild.get_member(deleter.id)
                    if member and member != guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != guild.default_role and r.position < guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Mass role deletion')
                        
                        try:
                            await member.timeout(timedelta(days=7), reason='Anti-nuke: Mass role deletion')
                        except:
                            pass
                    
                    await log_action(
                        guild,
                        'Anti-Nuke: Mass Role Deletion',
                        f'User: {deleter.mention}\nRoles deleted: {count}',
                        discord.Color.red(),
                        [('Action', 'User roles stripped, 7-day timeout')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke role deletion failed: {e}")
            break

@bot.event
async def on_guild_channel_create(channel):
    """Monitor channel creation for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    guild = channel.guild
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        if entry.target.id == channel.id:
            creator = entry.user
            
            if creator.id == Config.OWNER_ID or data_manager.is_whitelisted(creator.id):
                break
            
            data_manager.track_action('channel_create', creator.id, guild.id)
            count = data_manager.get_action_count('channel_create', creator.id, guild.id, Config.CHANNEL_DELETE_TIMEFRAME)
            
            if count >= Config.CHANNEL_DELETE_THRESHOLD:
                try:
                    await channel.delete(reason='Anti-nuke: Mass channel creation detected')
                    
                    member = guild.get_member(creator.id)
                    if member and member != guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != guild.default_role and r.position < guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Mass channel creation')
                        
                        try:
                            await member.timeout(timedelta(days=7), reason='Anti-nuke: Mass channel creation')
                        except:
                            pass
                    
                    await log_action(
                        guild,
                        'Anti-Nuke: Mass Channel Creation',
                        f'User: {creator.mention}\nChannels created: {count}',
                        discord.Color.red(),
                        [('Action', 'Channel deleted, user roles stripped, 7-day timeout')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke channel creation failed: {e}")
            break

@bot.event
async def on_guild_channel_delete(channel):
    """Monitor channel deletion for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    guild = channel.guild
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.target.id == channel.id:
            deleter = entry.user
            
            if deleter.id == Config.OWNER_ID or data_manager.is_whitelisted(deleter.id):
                break
            
            data_manager.track_action('channel_delete', deleter.id, guild.id)
            count = data_manager.get_action_count('channel_delete', deleter.id, guild.id, Config.CHANNEL_DELETE_TIMEFRAME)
            
            if count >= Config.CHANNEL_DELETE_THRESHOLD:
                try:
                    member = guild.get_member(deleter.id)
                    if member and member != guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != guild.default_role and r.position < guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Mass channel deletion')
                        
                        try:
                            await member.timeout(timedelta(days=7), reason='Anti-nuke: Mass channel deletion')
                        except:
                            pass
                    
                    await log_action(
                        guild,
                        'Anti-Nuke: Mass Channel Deletion',
                        f'User: {deleter.mention}\nChannels deleted: {count}',
                        discord.Color.red(),
                        [('Action', 'User roles stripped, 7-day timeout')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke channel deletion failed: {e}")
            break

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    """Monitor bans for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.target.id == user.id:
            banner = entry.user
            
            if banner.id == Config.OWNER_ID or data_manager.is_whitelisted(banner.id):
                break
            
            data_manager.track_action('ban', banner.id, guild.id)
            count = data_manager.get_action_count('ban', banner.id, guild.id, Config.BAN_TIMEFRAME)
            
            if count >= Config.BAN_THRESHOLD:
                try:
                    member = guild.get_member(banner.id)
                    if member and member != guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != guild.default_role and r.position < guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Mass ban detected')
                        
                        try:
                            await member.timeout(timedelta(days=7), reason='Anti-nuke: Mass ban')
                        except:
                            pass
                    
                    await log_action(
                        guild,
                        'Anti-Nuke: Mass Ban Detected',
                        f'User: {banner.mention}\nBans issued: {count}',
                        discord.Color.red(),
                        [('Action', 'User roles stripped, 7-day timeout')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke ban protection failed: {e}")
            break

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Monitor role changes for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    added_roles = set(after.roles) - set(before.roles)
    if not added_roles:
        return
    
    await asyncio.sleep(0.5)
    
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
        if entry.target.id == after.id:
            moderator = entry.user
            
            if moderator.id == Config.OWNER_ID or data_manager.is_whitelisted(moderator.id):
                break
            
            # Check for dangerous permissions
            dangerous_granted = False
            for role in added_roles:
                role_perms = role.permissions
                for perm in Config.DANGEROUS_PERMISSIONS:
                    if getattr(role_perms, perm, False):
                        dangerous_granted = True
                        break
            
            if dangerous_granted:
                try:
                    member = after.guild.get_member(moderator.id)
                    if member and member != after.guild.owner:
                        roles_to_remove = [
                            r for r in member.roles
                            if r != after.guild.default_role and r.position < after.guild.me.top_role.position
                        ]
                        if roles_to_remove:
                            await member.remove_roles(*roles_to_remove, reason='Anti-nuke: Unauthorized dangerous permissions')
                        
                        # Remove dangerous roles from target
                        await after.remove_roles(*added_roles, reason='Anti-nuke: Dangerous permissions granted')
                    
                    await log_action(
                        after.guild,
                        'Anti-Nuke: Dangerous Permissions Granted',
                        f'Moderator: {moderator.mention}\nTarget: {after.mention}',
                        discord.Color.red(),
                        [('Action', 'Roles stripped from both users')]
                    )
                except Exception as e:
                    logging.error(f"Anti-nuke permission protection failed: {e}")
            break

@bot.event
async def on_webhooks_update(channel: discord.TextChannel):
    """Monitor webhook creation for anti-nuke"""
    if not data_manager.anti_nuke_enabled:
        return
    
    guild = channel.guild
    await asyncio.sleep(0.5)
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        creator = entry.user
        
        if creator.id == Config.OWNER_ID or data_manager.is_whitelisted(creator.id):
            break
        
        await log_action(
            guild,
            'Webhook Created',
            f'User: {creator.mention}\nChannel: {channel.mention}',
            discord.Color.orange(),
            [('Status', 'Monitoring')]
        )
        break

  """
Elite Discord Security Bot - Part 4: Auto-Moderation System
Add this after Part 3
"""

@bot.event
async def on_message(message: discord.Message):
    """Auto-moderation message handler"""
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    # Whitelist bypass
    if data_manager.is_whitelisted(message.author.id) or message.author.id == Config.OWNER_ID:
        await bot.process_commands(message)
        return
    
    # Blacklist check
    if data_manager.is_blacklisted(message.author.id):
        try:
            await message.delete()
            await message.author.timeout(timedelta(hours=1), reason='Blacklisted user')
        except:
            pass
        return
    
    if not data_manager.automod_enabled:
        await bot.process_commands(message)
        return
    
    user_id = message.author.id
    current_time = datetime.utcnow().timestamp()
    
    # Spam Detection
    data_manager.message_history[user_id].append(current_time)
    data_manager.message_history[user_id] = [
        ts for ts in data_manager.message_history[user_id]
        if current_time - ts <= Config.SPAM_TIMEFRAME
    ]
    
    message_count = len(data_manager.message_history[user_id])
    
    if message_count >= Config.SPAM_THRESHOLD:
        data_manager.user_violations[user_id] += 1
        violation_count = data_manager.user_violations[user_id]
        data_manager.save_data()
        
        timeout_minutes = calculate_timeout(violation_count)
        
        try:
            await message.channel.purge(limit=20, check=lambda m: m.author.id == user_id)
            await message.author.timeout(timedelta(minutes=timeout_minutes), reason=f'Spam: {message_count} messages')
            
            warning = await message.channel.send(
                f'{message.author.mention} has been timed out for {timeout_minutes} minutes for spamming.'
            )
            await asyncio.sleep(5)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                'Anti-Spam Action',
                f'User: {message.author.mention}\nMessages: {message_count}\nTimeout: {timeout_minutes} minutes',
                discord.Color.orange(),
                [('Violations', str(violation_count))]
            )
        except Exception as e:
            logging.error(f"Spam protection failed: {e}")
        
        data_manager.message_history[user_id].clear()
        return
    
    # Profanity Filter
    is_profane, matched_word = contains_profanity(message.content)
    if is_profane:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=Config.PROFANITY_TIMEOUT), reason=f'Profanity: {matched_word}')
            
            warning = await message.channel.send(
                f'{message.author.mention} has been timed out for {Config.PROFANITY_TIMEOUT} minutes for using inappropriate language.'
            )
            await asyncio.sleep(5)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                'Profanity Filter',
                f'User: {message.author.mention}\nWord: ||{matched_word}||',
                discord.Color.red(),
                [('Action', f'{Config.PROFANITY_TIMEOUT}min timeout')]
            )
        except Exception as e:
            logging.error(f"Profanity filter failed: {e}")
        return
    
    # Mention Spam
    mention_count = len(message.mentions) + len(message.role_mentions)
    if mention_count >= Config.MENTION_LIMIT:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=Config.MENTION_TIMEOUT), reason=f'Mention spam: {mention_count} mentions')
            
            warning = await message.channel.send(
                f'{message.author.mention} has been timed out for {Config.MENTION_TIMEOUT} minutes for mention spam.'
            )
            await asyncio.sleep(5)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                'Mention Spam',
                f'User: {message.author.mention}\nMentions: {mention_count}',
                discord.Color.red(),
                [('Action', f'{Config.MENTION_TIMEOUT}min timeout')]
            )
        except Exception as e:
            logging.error(f"Mention spam protection failed: {e}")
        return
    
    # Link Spam Detection
    links = extract_links(message.content)
    if links:
        data_manager.link_history[user_id].append(current_time)
        data_manager.link_history[user_id] = [
            ts for ts in data_manager.link_history[user_id]
            if current_time - ts <= Config.LINK_TIMEFRAME
        ]
        
        link_count = len(data_manager.link_history[user_id])
        
        if link_count >= Config.LINK_LIMIT:
            try:
                await message.delete()
                await message.author.timeout(timedelta(minutes=15), reason=f'Link spam: {link_count} links')
                
                warning = await message.channel.send(
                    f'{message.author.mention} has been timed out for 15 minutes for link spam.'
                )
                await asyncio.sleep(5)
                try:
                    await warning.delete()
                except:
                    pass
                
                await log_action(
                    message.guild,
                    'Link Spam',
                    f'User: {message.author.mention}\nLinks posted: {link_count}',
                    discord.Color.red(),
                    [('Action', '15min timeout')]
                )
                
                data_manager.link_history[user_id].clear()
            except Exception as e:
                logging.error(f"Link spam protection failed: {e}")
            return
    
    # Caps Lock Detection
    if len(message.content) >= 20:
        caps_count = sum(1 for c in message.content if c.isupper())
        caps_ratio = caps_count / len(message.content)
        
        if caps_ratio >= 0.7:
            try:
                await message.delete()
                warning = await message.channel.send(
                    f'{message.author.mention}, please avoid excessive caps lock.'
                )
                await asyncio.sleep(4)
                try:
                    await warning.delete()
                except:
                    pass
            except Exception as e:
                logging.error(f"Caps lock filter failed: {e}")
            return
    
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    """Monitor message edits"""
    if after.author.bot or not after.guild:
        return
    
    if before.content == after.content:
        return
    
    # Check edited message for profanity
    is_profane, matched_word = contains_profanity(after.content)
    if is_profane and data_manager.automod_enabled:
        try:
            await after.delete()
            await after.author.timeout(timedelta(minutes=Config.PROFANITY_TIMEOUT), reason=f'Profanity in edit: {matched_word}')
            
            await log_action(
                after.guild,
                'Profanity in Edited Message',
                f'User: {after.author.mention}\nWord: ||{matched_word}||',
                discord.Color.red(),
                [('Action', f'{Config.PROFANITY_TIMEOUT}min timeout')]
            )
        except Exception as e:
            logging.error(f"Edit profanity check failed: {e}")

@bot.event
async def on_message_delete(message: discord.Message):
    """Log message deletions"""
    if message.author.bot or not message.guild:
        return
    
    await asyncio.sleep(0.5)
    
    async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
        if entry.target.id == message.author.id:
            deleter = entry.user
            
            await log_action(
                message.guild,
                'Message Deleted',
                f'Author: {message.author.mention}\nDeleted by: {deleter.mention}\nChannel: {message.channel.mention}',
                discord.Color.orange(),
                [('Content', message.content[:100] if message.content else 'No content')]
            )
            break

@bot.event
async def on_bulk_message_delete(messages):
    """Log bulk message deletions"""
    if not messages:
        return
    
    guild = messages[0].guild
    await log_action(
        guild,
        'Bulk Message Delete',
        f'Channel: {messages[0].channel.mention}\nMessages deleted: {len(messages)}',
        discord.Color.orange(),
        [('Count', str(len(messages)))]
  )

"""
Elite Discord Security Bot - Part 5: Moderation Commands
Add this after Part 4
"""

# Moderation Commands
@bot.command(name='kick')
@is_owner_or_admin()
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member from the server"""
    if member.top_role >= ctx.author.top_role and ctx.author.id != Config.OWNER_ID:
        await ctx.send("You cannot kick someone with equal or higher role.")
        return
    
    try:
        await member.kick(reason=f'{reason} | By {ctx.author}')
        
        embed = discord.Embed(
            title='Member Kicked',
            description=f'{member.mention} has been kicked from the server.',
            color=discord.Color.orange()
        )
        embed.add_field(name='Reason', value=reason, inline=False)
        embed.add_field(name='Moderator', value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
        await log_action(
            ctx.guild,
            'Member Kicked',
            f'User: {member.mention}\nModerator: {ctx.author.mention}',
            discord.Color.orange(),
            [('Reason', reason)]
        )
    except Exception as e:
        await ctx.send(f'Failed to kick member: {e}')

@bot.command(name='ban')
@is_owner_or_admin()
async def ban_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member from the server"""
    if member.top_role >= ctx.author.top_role and ctx.author.id != Config.OWNER_ID:
        await ctx.send("You cannot ban someone with equal or higher role.")
        return
    
    try:
        await member.ban(reason=f'{reason} | By {ctx.author}', delete_message_days=1)
        
        embed = discord.Embed(
            title='Member Banned',
            description=f'{member.mention} has been banned from the server.',
            color=discord.Color.red()
        )
        embed.add_field(name='Reason', value=reason, inline=False)
        embed.add_field(name='Moderator', value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
        await log_action(
            ctx.guild,
            'Member Banned',
            f'User: {member.mention}\nModerator: {ctx.author.mention}',
            discord.Color.red(),
            [('Reason', reason)]
        )
    except Exception as e:
        await ctx.send(f'Failed to ban member: {e}')

@bot.command(name='unban')
@is_owner_or_admin()
async def unban_cmd(ctx, user_id: int, *, reason: str = "No reason provided"):
    """Unban a user by their ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f'{reason} | By {ctx.author}')
        
        await ctx.send(f'Unbanned {user} (ID: {user_id})')
        
        await log_action(
            ctx.guild,
            'Member Unbanned',
            f'User: {user} (ID: {user_id})\nModerator: {ctx.author.mention}',
            discord.Color.green(),
            [('Reason', reason)]
        )
    except Exception as e:
        await ctx.send(f'Failed to unban user: {e}')

@bot.command(name='softban')
@is_owner_or_admin()
async def softban_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Softban a member (ban then unban to delete messages)"""
    if member.top_role >= ctx.author.top_role and ctx.author.id != Config.OWNER_ID:
        await ctx.send("You cannot softban someone with equal or higher role.")
        return
    
    try:
        await member.ban(reason=f'Softban: {reason} | By {ctx.author}', delete_message_days=7)
        await ctx.guild.unban(member, reason=f'Softban unban | By {ctx.author}')
        
        await ctx.send(f'Softbanned {member.mention} (messages deleted)')
        
        await log_action(
            ctx.guild,
            'Member Softbanned',
            f'User: {member.mention}\nModerator: {ctx.author.mention}',
            discord.Color.orange(),
            [('Reason', reason)]
        )
    except Exception as e:
        await ctx.send(f'Failed to softban member: {e}')

@bot.command(name='timeout')
@is_owner_or_admin()
async def timeout_cmd(ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
    """Timeout a member (duration in minutes)"""
    if member.top_role >= ctx.author.top_role and ctx.author.id != Config.OWNER_ID:
        await ctx.send("You cannot timeout someone with equal or higher role.")
        return
    
    if duration > 40320:  # 28 days in minutes
        await ctx.send("Maximum timeout duration is 40320 minutes (28 days)")
        return
    
    try:
        await member.timeout(timedelta(minutes=duration), reason=f'{reason} | By {ctx.author}')
        
        embed = discord.Embed(
            title='Member Timed Out',
            description=f'{member.mention} has been timed out.',
            color=discord.Color.orange()
        )
        embed.add_field(name='Duration', value=f'{duration} minutes', inline=True)
        embed.add_field(name='Reason', value=reason, inline=False)
        
        await ctx.send(embed=embed)
        
        await log_action(
            ctx.guild,
            'Member Timed Out',
            f'User: {member.mention}\nDuration: {duration} minutes\nModerator: {ctx.author.mention}',
            discord.Color.orange(),
            [('Reason', reason)]
        )
    except Exception as e:
        await ctx.send(f'Failed to timeout member: {e}')

@bot.command(name='untimeout')
@is_owner_or_admin()
async def untimeout_cmd(ctx, member: discord.Member):
    """Remove timeout from a member"""
    try:
        await member.timeout(None, reason=f'Timeout removed by {ctx.author}')
        await ctx.send(f'Timeout removed from {member.mention}')
        
        await log_action(
            ctx.guild,
            'Timeout Removed',
            f'User: {member.mention}\nModerator: {ctx.author.mention}',
            discord.Color.green()
        )
    except Exception as e:
        await ctx.send(f'Failed to remove timeout: {e}')

@bot.command(name='warn')
@is_moderator()
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Warn a member"""
    data_manager.add_warning(member.id, reason, ctx.author.id)
    warning_count = len(data_manager.get_warnings(member.id))
    
    try:
        await member.send(
            f'**Warning from {ctx.guild.name}**\n\n'
            f'You have been warned by {ctx.author}.\n'
            f'Reason: {reason}\n'
            f'Total warnings: {warning_count}'
        )
        dm_sent = True
    except:
        dm_sent = False
    
    embed = discord.Embed(
        title='Member Warned',
        description=f'{member.mention} has been warned.',
        color=discord.Color.gold()
    )
    embed.add_field(name='Reason', value=reason, inline=False)
    embed.add_field(name='Total Warnings', value=str(warning_count), inline=True)
    embed.add_field(name='DM Sent', value='Yes' if dm_sent else 'No', inline=True)
    
    await ctx.send(embed=embed)
    
    await log_action(
        ctx.guild,
        'Warning Issued',
        f'User: {member.mention}\nModerator: {ctx.author.mention}\nTotal warnings: {warning_count}',
        discord.Color.gold(),
        [('Reason', reason)]
    )

@bot.command(name='warnings')
@is_moderator()
async def warnings_cmd(ctx, member: discord.Member):
    """View warnings for a member"""
    warnings = data_manager.get_warnings(member.id)
    
    if not warnings:
        await ctx.send(f'{member.mention} has no warnings.')
        return
    
    embed = discord.Embed(
        title=f'Warnings for {member}',
        description=f'Total warnings: {len(warnings)}',
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    for i, warning in enumerate(warnings[:10], 1):
        moderator = await bot.fetch_user(warning['moderator'])
        timestamp = datetime.fromisoformat(warning['timestamp']).strftime('%Y-%m-%d %H:%M')
        embed.add_field(
            name=f'Warning {i}',
            value=f"Reason: {warning['reason']}\nModerator: {moderator.mention}\nDate: {timestamp}",
            inline=False
        )
    
    if len(warnings) > 10:
        embed.set_footer(text=f'Showing 10 of {len(warnings)} warnings')
    
    await ctx.send(embed=embed)

@bot.command(name='clearwarnings')
@is_owner_or_admin()
async def clearwarnings_cmd(ctx, member: discord.Member):
    """Clear all warnings for a member"""
    warnings = data_manager.get_warnings(member.id)
    
    if not warnings:
        await ctx.send(f'{member.mention} has no warnings to clear.')
        return
    
    warning_count = len(warnings)
    data_manager.clear_warnings(member.id)
    
    await ctx.send(f'Cleared {warning_count} warnings for {member.mention}')
    
    await log_action(
        ctx.guild,
        'Warnings Cleared',
        f'User: {member.mention}\nCleared by: {ctx.author.mention}\nWarnings removed: {warning_count}',
        discord.Color.blue()
    )

@bot.command(name='purge')
@is_owner_or_admin()
async def purge_cmd(ctx, amount: int):
    """Delete messages (max 100)"""
    if amount <= 0:
        await ctx.send("Amount must be greater than 0")
        return
    
    if amount > 100:
        await ctx.send("Maximum 100 messages at once")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        
        msg = await ctx.send(f'Deleted {len(deleted) - 1} messages')
        await asyncio.sleep(3)
        await msg.delete()
        
        await log_action(
            ctx.guild,
            'Messages Purged',
            f'Channel: {ctx.channel.mention}\nAmount: {len(deleted) - 1}\nModerator: {ctx.author.mention}',
            discord.Color.blue()
        )
    except Exception as e:
        await ctx.send(f'Failed to purge messages: {e}')

@bot.command(name='purgeuser')
@is_owner_or_admin()
async def purgeuser_cmd(ctx, member: discord.Member, amount: int = 100):
    """Delete messages from a specific user"""
    if amount > 100:
        amount = 100
    
    try:
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.id == member.id)
        
        msg = await ctx.send(f'Deleted {len(deleted)} messages from {member.mention}')
        await asyncio.sleep(3)
        await msg.delete()
        
        await log_action(
            ctx.guild,
            'User Messages Purged',
            f'User: {member.mention}\nChannel: {ctx.channel.mention}\nAmount: {len(deleted)}\nModerator: {ctx.author.mention}',
            discord.Color.blue()
        )
    except Exception as e:
        await ctx.send(f'Failed to purge user messages: {e}')

@bot.command(name='slowmode')
@is_owner_or_admin()
async def slowmode_cmd(ctx, seconds: int):
    """Set slowmode for a channel (0 to disable)"""
    if seconds < 0 or seconds > 21600:
        await ctx.send("Slowmode must be between 0 and 21600 seconds (6 hours)")
        return
    
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send(f'Slowmode disabled in {ctx.channel.mention}')
        else:
            await ctx.send(f'Slowmode set to {seconds} seconds in {ctx.channel.mention}')
        
        await log_action(
            ctx.guild,
            'Slowmode Updated',
            f'Channel: {ctx.channel.mention}\nDelay: {seconds} seconds\nModerator: {ctx.author.mention}',
            discord.Color.blue()
        )
    except Exception as e:
        await ctx.send(f'Failed to set slowmode: {e}')

  """
Elite Discord Security Bot - Part 6: Advanced Commands
Add this after Part 5
"""

# Lock/Unlock Commands
@bot.command(name='lock')
@is_owner_or_admin()
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    """Lock a channel"""
    channel = channel or ctx.channel
    
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        
        # Allow staff to still talk
        if Config.STAFF_ROLE_ID:
            staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID)
            if staff_role:
                await channel.set_permissions(staff_role, send_messages=True)
        
        await ctx.send(f'{channel.mention} has been locked.')
        
        await log_action(
            ctx.guild,
            'Channel Locked',
            f'Channel: {channel.mention}\nModerator: {ctx.author.mention}',
            discord.Color.red()
        )
    except Exception as e:
        await ctx.send(f'Failed to lock channel: {e}')

@bot.command(name='unlock')
@is_owner_or_admin()
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    """Unlock a channel"""
    channel = channel or ctx.channel
    
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f'{channel.mention} has been unlocked.')
        
        await log_action(
            ctx.guild,
            'Channel Unlocked',
            f'Channel: {channel.mention}\nModerator: {ctx.author.mention}',
            discord.Color.green()
        )
    except Exception as e:
        await ctx.send(f'Failed to unlock channel: {e}')

@bot.command(name='lockdown')
@is_owner_or_admin()
async def lockdown_cmd(ctx):
    """Lockdown entire server"""
    locked_count = 0
    staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID) if Config.STAFF_ROLE_ID else None
    
    try:
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                
                if staff_role:
                    await channel.set_permissions(staff_role, send_messages=True)
                
                locked_count += 1
            except:
                pass
        
        embed = discord.Embed(
            title='Server Lockdown Active',
            description=f'Locked {locked_count} text channels',
            color=discord.Color.dark_red()
        )
        embed.add_field(name='Moderator', value=ctx.author.mention)
        if staff_role:
            embed.add_field(name='Staff Access', value='Staff can still send messages')
        
        await ctx.send(embed=embed)
        
        await log_action(
            ctx.guild,
            'Server Lockdown',
            f'Channels locked: {locked_count}\nModerator: {ctx.author.mention}',
            discord.Color.dark_red(),
            [('Staff Role', staff_role.mention if staff_role else 'None')]
        )
    except Exception as e:
        await ctx.send(f'Failed to lockdown server: {e}')

@bot.command(name='unlockdown')
@is_owner_or_admin()
async def unlockdown_cmd(ctx):
    """Remove server lockdown"""
    unlocked_count = 0
    
    try:
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                unlocked_count += 1
            except:
                pass
        
        embed = discord.Embed(
            title='Server Lockdown Ended',
            description=f'Unlocked {unlocked_count} text channels',
            color=discord.Color.green()
        )
        embed.add_field(name='Moderator', value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
        await log_action(
            ctx.guild,
            'Server Lockdown Ended',
            f'Channels unlocked: {unlocked_count}\nModerator: {ctx.author.mention}',
            discord.Color.green()
        )
    except Exception as e:
        await ctx.send(f'Failed to end lockdown: {e}')

# Anti-Raid Commands
@bot.command(name='antiraid')
@is_owner_or_admin()
async def antiraid_cmd(ctx, mode: str):
    """Toggle anti-raid mode (on/off)"""
    mode = mode.lower()
    
    if mode == 'on':
        try:
            await ctx.guild.edit(verification_level=discord.VerificationLevel.highest)
            data_manager.anti_raid_enabled = True
            data_manager.save_data()
            
            await ctx.send('Anti-raid mode enabled. Verification level set to HIGHEST.')
            
            await log_action(
                ctx.guild,
                'Anti-Raid Enabled',
                f'Moderator: {ctx.author.mention}',
                discord.Color.green()
            )
        except Exception as e:
            await ctx.send(f'Failed to enable anti-raid: {e}')
    
    elif mode == 'off':
        try:
            await ctx.guild.edit(verification_level=discord.VerificationLevel.low)
            data_manager.anti_raid_enabled = False
            data_manager.save_data()
            
            await ctx.send('Anti-raid mode disabled. Verification level restored.')
            
            await log_action(
                ctx.guild,
                'Anti-Raid Disabled',
                f'Moderator: {ctx.author.mention}',
                discord.Color.orange()
            )
        except Exception as e:
            await ctx.send(f'Failed to disable anti-raid: {e}')
    
    else:
        await ctx.send('Use `+antiraid on` or `+antiraid off`')

@bot.command(name='antinuke')
@is_owner_or_admin()
async def antinuke_cmd(ctx, mode: str):
    """Toggle anti-nuke protection (on/off)"""
    mode = mode.lower()
    
    if mode == 'on':
        data_manager.anti_nuke_enabled = True
        data_manager.save_data()
        await ctx.send('Anti-nuke protection enabled.')
        
        await log_action(
            ctx.guild,
            'Anti-Nuke Enabled',
            f'Moderator: {ctx.author.mention}',
            discord.Color.green()
        )
    
    elif mode == 'off':
        data_manager.anti_nuke_enabled = False
        data_manager.save_data()
        await ctx.send('Anti-nuke protection disabled.')
        
        await log_action(
            ctx.guild,
            'Anti-Nuke Disabled',
            f'Moderator: {ctx.author.mention}',
            discord.Color.orange()
        )
    
    else:
        await ctx.send('Use `+antinuke on` or `+antinuke off`')

@bot.command(name='automod')
@is_owner_or_admin()
async def automod_cmd(ctx, mode: str):
    """Toggle auto-moderation (on/off)"""
    mode = mode.lower()
    
    if mode == 'on':
        data_manager.automod_enabled = True
        data_manager.save_data()
        await ctx.send('Auto-moderation enabled.')
        
        await log_action(
            ctx.guild,
            'Auto-Moderation Enabled',
            f'Moderator: {ctx.author.mention}',
            discord.Color.green()
        )
    
    elif mode == 'off':
        data_manager.automod_enabled = False
        data_manager.save_data()
        await ctx.send('Auto-moderation disabled.')
        
        await log_action(
            ctx.guild,
            'Auto-Moderation Disabled',
            f'Moderator: {ctx.author.mention}',
            discord.Color.orange()
        )
    
    else:
        await ctx.send('Use `+automod on` or `+automod off`')

# Role Management
@bot.command(name='roleall')
@is_owner_or_admin()
async def roleall_cmd(ctx, role: discord.Role):
    """Give role to all members"""
    added = 0
    msg = await ctx.send(f'Adding {role.mention} to all members...')
    
    for member in ctx.guild.members:
        if role not in member.roles and not member.bot:
            try:
                await member.add_roles(role, reason=f'Role all by {ctx.author}')
                added += 1
            except:
                pass
    
    await msg.edit(content=f'Added {role.mention} to {added} members.')
    
    await log_action(
        ctx.guild,
        'Role Added to All',
        f'Role: {role.mention}\nMembers affected: {added}\nModerator: {ctx.author.mention}',
        discord.Color.blue()
    )

@bot.command(name='unroleall')
@is_owner_or_admin()
async def unroleall_cmd(ctx, role: discord.Role):
    """Remove role from all members"""
    removed = 0
    msg = await ctx.send(f'Removing {role.mention} from all members...')
    
    for member in role.members:
        try:
            await member.remove_roles(role, reason=f'Unrole all by {ctx.author}')
            removed += 1
        except:
            pass
    
    await msg.edit(content=f'Removed {role.mention} from {removed} members.')
    
    await log_action(
        ctx.guild,
        'Role Removed from All',
        f'Role: {role.mention}\nMembers affected: {removed}\nModerator: {ctx.author.mention}',
        discord.Color.blue()
    )

# Staff Role Commands
@bot.command(name='setstaffrole')
@is_owner_or_admin()
async def setstaffrole_cmd(ctx, role: discord.Role):
    """Set the staff role"""
    Config.STAFF_ROLE_ID = role.id
    data_manager.save_data()
    
    embed = discord.Embed(
        title='Staff Role Set',
        description=f'Staff role set to {role.mention}',
        color=discord.Color.green()
    )
    embed.add_field(
        name='Permissions',
        value='Can send messages in locked channels\nCan send messages during lockdown',
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    await log_action(
        ctx.guild,
        'Staff Role Configured',
        f'Staff role: {role.mention}\nSet by: {ctx.author.mention}',
        discord.Color.blue()
    )

@bot.command(name='viewstaffrole')
async def viewstaffrole_cmd(ctx):
    """View the current staff role"""
    if not Config.STAFF_ROLE_ID:
        await ctx.send('No staff role has been set.')
        return
    
    staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID)
    
    if staff_role:
        embed = discord.Embed(
            title='Staff Role',
            description=f'Current staff role: {staff_role.mention}',
            color=discord.Color.blue()
        )
        embed.add_field(name='Role ID', value=str(Config.STAFF_ROLE_ID), inline=True)
        embed.add_field(name='Members', value=str(len(staff_role.members)), inline=True)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send('Staff role not found. It may have been deleted.')

@bot.command(name='removestaffrole')
@is_owner_or_admin()
async def removestaffrole_cmd(ctx):
    """Remove the staff role setting"""
    if not Config.STAFF_ROLE_ID:
        await ctx.send('No staff role is set.')
        return
    
    Config.STAFF_ROLE_ID = None
    data_manager.save_data()
    
    await ctx.send('Staff role setting removed.')
    
    await log_action(
        ctx.guild,
        'Staff Role Removed',
        f'Removed by: {ctx.author.mention}',
        discord.Color.orange()
      )

"""
Elite Discord Security Bot - Part 7: Whitelist & Security Commands
Add this after Part 6
"""

# Whitelist Commands
@bot.tree.command(name="whitelist_add", description="Add user to whitelist")
@app_commands.describe(user="User to add to whitelist")
@is_owner()
async def whitelist_add(interaction: discord.Interaction, user: discord.User):
    """Add a user to whitelist"""
    if data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(
            f'{user.mention} is already whitelisted.',
            ephemeral=True
        )
        return
    
    data_manager.add_to_whitelist(user.id)
    
    if user.id in data_manager.user_violations:
        del data_manager.user_violations[user.id]
        data_manager.save_data()
    
    embed = discord.Embed(
        title='User Whitelisted',
        description=f'{user.mention} has been added to the whitelist.',
        color=discord.Color.green()
    )
    embed.add_field(
        name='Permissions',
        value='Bypass spam detection\nBypass auto-moderation\nAuthorized bot additions\nGrant roles without restrictions',
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        'User Whitelisted',
        f'User: {user.mention}\nAdded by: {interaction.user.mention}',
        discord.Color.green()
    )

@bot.tree.command(name="whitelist_remove", description="Remove user from whitelist")
@app_commands.describe(user="User to remove from whitelist")
@is_owner()
async def whitelist_remove(interaction: discord.Interaction, user: discord.User):
    """Remove user from whitelist"""
    if not data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(
            f'{user.mention} is not whitelisted.',
            ephemeral=True
        )
        return
    
    data_manager.remove_from_whitelist(user.id)
    
    embed = discord.Embed(
        title='User Removed from Whitelist',
        description=f'{user.mention} has been removed from the whitelist.',
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        'User Removed from Whitelist',
        f'User: {user.mention}\nRemoved by: {interaction.user.mention}',
        discord.Color.orange()
    )

@bot.tree.command(name="whitelist_list", description="View whitelisted users")
@is_owner()
async def whitelist_list(interaction: discord.Interaction):
    """List all whitelisted users"""
    if not data_manager.whitelist:
        await interaction.response.send_message(
            'The whitelist is empty.',
            ephemeral=True
        )
        return
    
    user_list = []
    for user_id in data_manager.whitelist:
        user = bot.get_user(user_id)
        if user:
            user_list.append(f'{user.mention} (ID: {user_id})')
        else:
            user_list.append(f'Unknown User (ID: {user_id})')
    
    embed = discord.Embed(
        title='Whitelisted Users',
        description='\n'.join(user_list),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f'Total: {len(data_manager.whitelist)} users')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Blacklist Commands
@bot.tree.command(name="blacklist_add", description="Add user to blacklist")
@app_commands.describe(user="User to add to blacklist", reason="Reason for blacklisting")
@is_owner()
async def blacklist_add(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
    """Add a user to blacklist"""
    if data_manager.is_blacklisted(user.id):
        await interaction.response.send_message(
            f'{user.mention} is already blacklisted.',
            ephemeral=True
        )
        return
    
    data_manager.add_to_blacklist(user.id)
    
    embed = discord.Embed(
        title='User Blacklisted',
        description=f'{user.mention} has been added to the blacklist.',
        color=discord.Color.dark_red()
    )
    embed.add_field(name='Reason', value=reason, inline=False)
    embed.add_field(
        name='Effects',
        value='Cannot verify\nMessages auto-deleted\nAuto-timeout on message\nAuto-kick on join',
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        'User Blacklisted',
        f'User: {user.mention}\nAdded by: {interaction.user.mention}',
        discord.Color.dark_red(),
        [('Reason', reason)]
    )

@bot.tree.command(name="blacklist_remove", description="Remove user from blacklist")
@app_commands.describe(user="User to remove from blacklist")
@is_owner()
async def blacklist_remove(interaction: discord.Interaction, user: discord.User):
    """Remove user from blacklist"""
    if not data_manager.is_blacklisted(user.id):
        await interaction.response.send_message(
            f'{user.mention} is not blacklisted.',
            ephemeral=True
        )
        return
    
    data_manager.remove_from_blacklist(user.id)
    
    embed = discord.Embed(
        title='User Removed from Blacklist',
        description=f'{user.mention} has been removed from the blacklist.',
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        'User Removed from Blacklist',
        f'User: {user.mention}\nRemoved by: {interaction.user.mention}',
        discord.Color.green()
    )

@bot.tree.command(name="blacklist_list", description="View blacklisted users")
@is_owner()
async def blacklist_list(interaction: discord.Interaction):
    """List all blacklisted users"""
    if not data_manager.blacklist:
        await interaction.response.send_message(
            'The blacklist is empty.',
            ephemeral=True
        )
        return
    
    user_list = []
    for user_id in data_manager.blacklist:
        user = bot.get_user(user_id)
        if user:
            user_list.append(f'{user.mention} (ID: {user_id})')
        else:
            user_list.append(f'Unknown User (ID: {user_id})')
    
    embed = discord.Embed(
        title='Blacklisted Users',
        description='\n'.join(user_list),
        color=discord.Color.dark_red()
    )
    embed.set_footer(text=f'Total: {len(data_manager.blacklist)} users')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Violation Commands
@bot.tree.command(name="view_violations", description="View user violations")
@app_commands.describe(user="User to check violations")
@is_owner()
async def view_violations(interaction: discord.Interaction, user: discord.User):
    """View user violation history"""
    violation_count = data_manager.user_violations.get(user.id, 0)
    is_whitelisted = data_manager.is_whitelisted(user.id)
    is_blacklisted = data_manager.is_blacklisted(user.id)
    
    color = discord.Color.green() if is_whitelisted else discord.Color.red() if is_blacklisted else discord.Color.orange()
    
    embed = discord.Embed(
        title=f'Violations: {user.name}',
        color=color
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name='Violations', value=str(violation_count), inline=True)
    embed.add_field(name='Whitelisted', value='Yes' if is_whitelisted else 'No', inline=True)
    embed.add_field(name='Blacklisted', value='Yes' if is_blacklisted else 'No', inline=True)
    
    if violation_count > 0:
        next_timeout = calculate_timeout(violation_count + 1)
        embed.add_field(name='Next Timeout', value=f'{next_timeout} minutes', inline=False)
    
    warnings = data_manager.get_warnings(user.id)
    embed.add_field(name='Warnings', value=str(len(warnings)), inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear_violations", description="Clear user violations")
@app_commands.describe(user="User to clear violations")
@is_owner()
async def clear_violations(interaction: discord.Interaction, user: discord.User):
    """Clear user violations"""
    if user.id not in data_manager.user_violations:
        await interaction.response.send_message(
            f'{user.mention} has no violations.',
            ephemeral=True
        )
        return
    
    violation_count = data_manager.user_violations[user.id]
    del data_manager.user_violations[user.id]
    data_manager.save_data()
    
    await interaction.response.send_message(
        f'Cleared {violation_count} violations for {user.mention}',
        ephemeral=True
    )
    
    await log_action(
        interaction.guild,
        'Violations Cleared',
        f'User: {user.mention}\nViolations removed: {violation_count}\nCleared by: {interaction.user.mention}',
        discord.Color.blue()
    )

# Security Status Command
@bot.tree.command(name="security_status", description="View bot security status")
@is_owner()
async def security_status(interaction: discord.Interaction):
    """View bot security status"""
    total_violations = sum(data_manager.user_violations.values())
    users_with_violations = len(data_manager.user_violations)
    total_warnings = sum(len(warnings) for warnings in data_manager.user_warnings.values())
    
    embed = discord.Embed(
        title='Security Bot Status',
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name='Bot Status',
        value=f'Online (24/7)\nLatency: {round(bot.latency * 1000)}ms\nServers: {len(bot.guilds)}',
        inline=True
    )
    
    embed.add_field(
        name='Protection Systems',
        value=f'Anti-Nuke: {"Enabled" if data_manager.anti_nuke_enabled else "Disabled"}\n'
              f'Anti-Raid: {"Enabled" if data_manager.anti_raid_enabled else "Disabled"}\n'
              f'Auto-Mod: {"Enabled" if data_manager.automod_enabled else "Disabled"}',
        inline=True
    )
    
    embed.add_field(
        name='Statistics',
        value=f'Whitelist: {len(data_manager.whitelist)} users\n'
              f'Blacklist: {len(data_manager.blacklist)} users\n'
              f'Total Violations: {total_violations}\n'
              f'Total Warnings: {total_warnings}',
        inline=False
    )
    
    embed.add_field(
        name='Configuration',
        value=f'Spam Threshold: {Config.SPAM_THRESHOLD} msg/{Config.SPAM_TIMEFRAME}s\n'
              f'Profanity Timeout: {Config.PROFANITY_TIMEOUT} min\n'
              f'Mention Limit: {Config.MENTION_LIMIT}',
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

"""
Elite Discord Security Bot - Part 8: Utility & Help Commands
Add this after Part 7
"""

# Utility Commands
@bot.command(name='ping')
async def ping_cmd(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title='Pong!',
        description=f'Latency: {latency}ms',
        color=discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='serverinfo')
async def serverinfo_cmd(ctx):
    """View server information"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title=f'{guild.name}',
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name='Server ID', value=str(guild.id), inline=True)
    embed.add_field(name='Owner', value=guild.owner.mention, inline=True)
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    
    embed.add_field(name='Members', value=str(guild.member_count), inline=True)
    embed.add_field(name='Roles', value=str(len(guild.roles)), inline=True)
    embed.add_field(name='Channels', value=str(len(guild.channels)), inline=True)
    
    embed.add_field(name='Text Channels', value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name='Voice Channels', value=str(len(guild.voice_channels)), inline=True)
    embed.add_field(name='Categories', value=str(len(guild.categories)), inline=True)
    
    embed.add_field(name='Verification Level', value=str(guild.verification_level).replace('_', ' ').title(), inline=True)
    embed.add_field(name='Boost Level', value=str(guild.premium_tier), inline=True)
    embed.add_field(name='Boosts', value=str(guild.premium_subscription_count), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='userinfo')
async def userinfo_cmd(ctx, member: discord.Member = None):
    """View user information"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f'{member.name}',
        color=member.color,
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    embed.add_field(name='User ID', value=str(member.id), inline=True)
    embed.add_field(name='Nickname', value=member.nick or 'None', inline=True)
    embed.add_field(name='Bot', value='Yes' if member.bot else 'No', inline=True)
    
    embed.add_field(name='Status', value=str(member.status).title(), inline=True)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Account Created', value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    
    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
    embed.add_field(name=f'Roles ({len(roles)})', value=' '.join(roles) if roles else 'None', inline=False)
    
    # Security info
    is_whitelisted = data_manager.is_whitelisted(member.id)
    is_blacklisted = data_manager.is_blacklisted(member.id)
    violations = data_manager.user_violations.get(member.id, 0)
    warnings = len(data_manager.get_warnings(member.id))
    
    security_info = []
    if is_whitelisted:
        security_info.append('Whitelisted')
    if is_blacklisted:
        security_info.append('Blacklisted')
    if violations > 0:
        security_info.append(f'{violations} violations')
    if warnings > 0:
        security_info.append(f'{warnings} warnings')
    
    if security_info:
        embed.add_field(name='Security Status', value=', '.join(security_info), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar_cmd(ctx, member: discord.Member = None):
    """View user avatar"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"{member.display_name}'s Avatar",
        color=member.color
    )
    embed.set_image(url=member.display_avatar.url)
    embed.add_field(name='Avatar URL', value=f'[Click Here]({member.display_avatar.url})', inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='botinfo')
async def botinfo_cmd(ctx):
    """View bot information"""
    embed = discord.Embed(
        title=f'{bot.user.name}',
        description='Elite Security Bot - Production Grade Protection',
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    embed.add_field(name='Bot ID', value=str(bot.user.id), inline=True)
    embed.add_field(name='Servers', value=str(len(bot.guilds)), inline=True)
    embed.add_field(name='Users', value=str(len(bot.users)), inline=True)
    
    embed.add_field(name='Prefix', value=Config.PREFIX, inline=True)
    embed.add_field(name='Latency', value=f'{round(bot.latency * 1000)}ms', inline=True)
    embed.add_field(name='Owner', value=f'<@{Config.OWNER_ID}>', inline=True)
    
    embed.add_field(
        name='Features',
        value='Anti-Nuke Protection\nAnti-Raid System\nAuto-Moderation\nVerification System\nAdvanced Logging',
        inline=False
    )
    
    embed.add_field(name='Status', value='Online (24/7)', inline=True)
    
    await ctx.send(embed=embed)

# Help Command
@bot.command(name='help')
async def help_cmd(ctx):
    """Display all commands"""
    is_owner_user = ctx.author.id == Config.OWNER_ID
    is_admin = ctx.author.guild_permissions.administrator if ctx.guild else False
    is_mod = ctx.author.guild_permissions.kick_members or ctx.author.guild_permissions.ban_members if ctx.guild else False
    
    embed = discord.Embed(
        title='Elite Security Bot - Commands',
        description=f'Prefix: `{Config.PREFIX}` | Slash commands: `/`',
        color=discord.Color.blue()
    )
    
    if is_owner_user:
        embed.add_field(
            name='Verification System',
            value='`/setup_verification` `/send_verification` `/verify_user`',
            inline=False
        )
    
    if is_mod or is_admin or is_owner_user:
        embed.add_field(
            name='Moderation',
            value='`+kick` `+ban` `+unban` `+softban` `+timeout` `+untimeout`\n`+warn` `+warnings` `+clearwarnings` `+purge` `+purgeuser` `+slowmode`',
            inline=False
        )
    
    if is_admin or is_owner_user:
        embed.add_field(
            name='Server Security',
            value='`+lock` `+unlock` `+lockdown` `+unlockdown`\n`+antiraid` `+antinuke` `+automod`\n`+roleall` `+unroleall` `+setstaffrole`',
            inline=False
        )
    
    if is_owner_user:
        embed.add_field(
            name='Whitelist & Blacklist',
            value='`/whitelist_add` `/whitelist_remove` `/whitelist_list`\n`/blacklist_add` `/blacklist_remove` `/blacklist_list`',
            inline=False
        )
        
        embed.add_field(
            name='Violations & Status',
            value='`/view_violations` `/clear_violations` `/security_status`',
            inline=False
        )
    
    embed.add_field(
        name='Utility',
        value='`+ping` `+serverinfo` `+userinfo` `+avatar` `+botinfo`\n`+viewstaffrole` `+removestaffrole`',
        inline=False
    )
    
    embed.add_field(
        name='Protection Active',
        value=f'Anti-Nuke: {"✅" if data_manager.anti_nuke_enabled else "❌"}\n'
              f'Anti-Raid: {"✅" if data_manager.anti_raid_enabled else "❌"}\n'
              f'Auto-Mod: {"✅" if data_manager.automod_enabled else "❌"}',
        inline=False
    )
    
    embed.set_footer(text=f'Requested by {ctx.author}')
    
    await ctx.send(embed=embed)

@bot.tree.command(name="help_security", description="View all bot commands")
async def help_security(interaction: discord.Interaction):
    """Display help via slash command"""
    embed = discord.Embed(
        title='Elite Security Bot - Commands',
        description=f'Use `{Config.PREFIX}help` for full command list',
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name='Quick Links',
        value=f'**Prefix Commands:** `{Config.PREFIX}help`\n'
              f'**Status:** `/security_status`\n'
              f'**Verification:** `/setup_verification`',
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Error Handlers
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('You do not have permission to use this command.')
    
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Missing required argument: `{error.param.name}`')
    
    elif isinstance(error, commands.BadArgument):
        await ctx.send('Invalid argument provided.')
    
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('Member not found.')
    
    elif isinstance(error, commands.UserNotFound):
        await ctx.send('User not found.')
    
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send('Role not found.')
    
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send('Channel not found.')
    
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'This command is on cooldown. Try again in {error.retry_after:.1f}s')
    
    else:
        logging.error(f'Command error in {ctx.command}: {error}')
        await ctx.send('An error occurred while executing this command.')

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors"""
    if isinstance(error, app_commands.CheckFailure):
        return
    
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            'You do not have permission to use this command.',
            ephemeral=True
        )
    
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'This command is on cooldown. Try again in {error.retry_after:.1f}s',
            ephemeral=True
        )
    
    else:
        logging.error(f'Slash command error: {error}')
        try:
            await interaction.response.send_message(
                'An error occurred while executing this command.',
                ephemeral=True
            )
        except:
            pass

      """
Elite Discord Security Bot - Part 9: Web Server & Main Run
Add this after Part 8 - FINAL PART
"""

# Keep-Alive Web Server for 24/7 Hosting
async def start_keep_alive():
    """Start web server for health checks"""
    from aiohttp import web
    
    async def health(request):
        return web.Response(
            text='Bot Online!',
            status=200,
            content_type='text/plain'
        )
    
    async def status_page(request):
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <title>Elite Security Bot</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
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
        <h1>🛡️ Elite Security Bot</h1>
        <div class="status">✅ ONLINE</div>
        <div class="info">Servers: {len(bot.guilds)}</div>
        <div class="info">Prefix: {Config.PREFIX}</div>
        <div class="info">Latency: {round(bot.latency * 1000)}ms</div>
        <div>
            <span class="badge">Anti-Nuke {'✅' if data_manager.anti_nuke_enabled else '❌'}</span>
            <span class="badge">Anti-Raid {'✅' if data_manager.anti_raid_enabled else '❌'}</span>
            <span class="badge">Auto-Mod {'✅' if data_manager.automod_enabled else '❌'}</span>
        </div>
    </div>
</body>
</html>
        '''
        return web.Response(
            text=html,
            content_type='text/html'
        )
    
    async def stats(request):
        stats_data = {
            'online': True,
            'servers': len(bot.guilds),
            'users': len(bot.users),
            'prefix': Config.PREFIX,
            'latency': round(bot.latency * 1000),
            'whitelist': len(data_manager.whitelist),
            'blacklist': len(data_manager.blacklist),
            'anti_nuke': data_manager.anti_nuke_enabled,
            'anti_raid': data_manager.anti_raid_enabled,
            'automod': data_manager.automod_enabled
        }
        return web.json_response(stats_data)
    
    app = web.Application()
    app.router.add_get('/', status_page)
    app.router.add_get('/health', health)
    app.router.add_get('/ping', health)
    app.router.add_get('/stats', stats)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
    await site.start()
    
    logging.info(f'Web server running on port {Config.PORT}')

# Main Function
async def main():
    """Main bot startup function"""
    await start_keep_alive()
    
    try:
        await bot.start(Config.TOKEN)
    except KeyboardInterrupt:
        logging.info('Bot shutdown requested')
        await bot.close()
    except Exception as e:
        logging.error(f'Bot error: {e}')
        await bot.close()

# Run Bot
if __name__ == '__main__':
    print('=' * 70)
    print('ELITE DISCORD SECURITY BOT')
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
        logging.info('Bot stopped by user')
    except Exception as e:
        logging.error(f'Failed to start bot: {e}')
        print(f'\nFailed to start: {e}')
