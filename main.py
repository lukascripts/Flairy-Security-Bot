import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
from typing import Optional, Set, Dict, List
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

class Config:
    """Bot configuration settings"""
    
    # Owner ID - ONLY this user can execute whitelist commands
    OWNER_ID = 1029438856069656576
    
    # Bot token from environment variable (REQUIRED for Render)
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    # Command prefix
    PREFIX = '+'
    
    # Render port configuration
    PORT = int(os.getenv('PORT', 8080))
    
    # Anti-Spam Configuration
    SPAM_THRESHOLD = 5  # Messages within timeframe
    SPAM_TIMEFRAME = 5  # Seconds
    SPAM_TIMEOUT_BASE = 5  # Base timeout in minutes
    
    # Spam timeout calculation (scales with violations)
    SPAM_TIMEOUT_MULTIPLIER = {
        1: 5,    # First offense: 5 minutes
        2: 15,   # Second offense: 15 minutes
        3: 30,   # Third offense: 30 minutes
        4: 60,   # Fourth offense: 1 hour
        5: 120   # Fifth+ offense: 2 hours
    }
    
    # Automod Configuration
    PROFANITY_TIMEOUT = 20  # Minutes for profanity violations
    
    # Banned words list (expandable)
    BANNED_WORDS = [
        'fuck', 'shit', 'bitch', 'ass', 'damn',
        'nigger', 'nigga', 'n1gger', 'n1gga',
    ]
    
    # Regex patterns for advanced filtering
    BANNED_PATTERNS = [
        r'n[i1!]gg[ae]r',
        r'f[u*]ck',
    ]
    
    # Dangerous permissions
    DANGEROUS_PERMISSIONS = [
        discord.Permissions.administrator,
        discord.Permissions.kick_members,
        discord.Permissions.ban_members,
        discord.Permissions.manage_channels,
        discord.Permissions.manage_guild,
        discord.Permissions.manage_roles,
        discord.Permissions.manage_webhooks,
    ]

# ============================================
# DATA STORAGE
# ============================================

class DataManager:
    """Manages persistent data storage"""
    
    def __init__(self):
        self.data_file = 'security_data.json'
        self.whitelist: Set[int] = set()
        self.user_violations: Dict[int, int] = defaultdict(int)
        self.message_history: Dict[int, List[float]] = defaultdict(list)
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.whitelist = set(data.get('whitelist', []))
                    self.user_violations = defaultdict(
                        int, 
                        {int(k): v for k, v in data.get('violations', {}).items()}
                    )
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def save_data(self):
        """Save data to JSON file"""
        try:
            data = {
                'whitelist': list(self.whitelist),
                'violations': {str(k): v for k, v in self.user_violations.items()}
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def add_to_whitelist(self, user_id: int):
        """Add user to whitelist"""
        self.whitelist.add(user_id)
        self.save_data()
    
    def remove_from_whitelist(self, user_id: int):
        """Remove user from whitelist"""
        self.whitelist.discard(user_id)
        self.save_data()
    
    def is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return user_id in self.whitelist

# ============================================
# BOT SETUP
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(
    command_prefix=Config.PREFIX,
    intents=intents,
    help_command=None
)

data_manager = DataManager()

# ============================================
# UTILITY FUNCTIONS
# ============================================

def is_owner():
    """Decorator to check if user is the bot owner"""
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id != Config.OWNER_ID:
            await interaction.response.send_message(
                "❌ Only the bot owner can use this command!",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

async def log_action(guild: discord.Guild, title: str, description: str, color: discord.Color):
    """Log security actions to a log channel"""
    log_channel = discord.utils.get(guild.text_channels, name='security-logs')
    if not log_channel:
        try:
            log_channel = await guild.create_text_channel(
                'security-logs',
                reason='Security bot log channel'
            )
        except:
            return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    try:
        await log_channel.send(embed=embed)
    except:
        pass

def calculate_spam_timeout(violation_count: int) -> int:
    """Calculate timeout duration based on violation count"""
    if violation_count >= 5:
        return Config.SPAM_TIMEOUT_MULTIPLIER[5]
    return Config.SPAM_TIMEOUT_MULTIPLIER.get(violation_count, 5)

def contains_profanity(content: str) -> tuple[bool, str]:
    """Check if message contains profanity"""
    content_lower = content.lower()
    
    for word in Config.BANNED_WORDS:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, content_lower):
            return True, word
    
    for pattern in Config.BANNED_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            match = re.search(pattern, content_lower, re.IGNORECASE)
            return True, match.group(0)
    
    return False, ''

def has_excessive_caps(content: str, threshold: float = 0.7) -> bool:
    """Check if message has excessive capital letters"""
    if len(content) < 10:
        return False
    
    letters = [c for c in content if c.isalpha()]
    if not letters:
        return False
    
    caps_count = sum(1 for c in letters if c.isupper())
    caps_ratio = caps_count / len(letters)
    
    return caps_ratio >= threshold

# ============================================
# BOT EVENTS
# ============================================

@bot.event
async def on_ready():
    """Called when bot is ready"""
    print('=' * 60)
    print(f'✅ {bot.user} is now ONLINE!')
    print(f'📊 Connected to {len(bot.guilds)} server(s)')
    print(f'🌐 Running on Render - 24/7 Uptime')
    print(f'⚙️  Prefix: {Config.PREFIX}')
    print('=' * 60)
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"your server | {Config.PREFIX}help"
        ),
        status=discord.Status.online
    )
    
    print('🛡️  All security systems ACTIVE!')
    print('=' * 60)

@bot.event
async def on_guild_role_create(role: discord.Role):
    """Monitor role creation for suspicious activity"""
    guild = role.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.target.id == role.id:
            creator = entry.user
            
            if creator.bot and not data_manager.is_whitelisted(creator.id):
                try:
                    await role.delete(reason='Unauthorized bot role creation')
                    await log_action(
                        guild,
                        '🛡️ ANTI-NUKE: Role Deleted',
                        f'Deleted role created by unauthorized bot: {creator.mention}\n'
                        f'Role name: {role.name}',
                        discord.Color.red()
                    )
                except:
                    pass
            break

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Monitor for bot additions and role changes"""
    
    if after.bot and before.joined_at != after.joined_at:
        return
    
    added_roles = set(after.roles) - set(before.roles)
    
    if added_roles:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                moderator = entry.user
                
                if data_manager.is_whitelisted(moderator.id) or moderator.id == Config.OWNER_ID:
                    break
                
                dangerous_perms_granted = False
                for role in added_roles:
                    for perm in Config.DANGEROUS_PERMISSIONS:
                        if getattr(role.permissions, perm[0], False):
                            dangerous_perms_granted = True
                            break
                
                if dangerous_perms_granted:
                    try:
                        roles_to_remove = [r for r in moderator.roles if r != after.guild.default_role]
                        await moderator.remove_roles(*roles_to_remove, reason='Unauthorized dangerous permission grant')
                        
                        await log_action(
                            after.guild,
                            '🛡️ ANTI-NUKE: Roles Stripped',
                            f'Stripped roles from {moderator.mention} for granting dangerous permissions without authorization',
                            discord.Color.orange()
                        )
                    except:
                        pass
                break

@bot.event
async def on_member_join(member: discord.Member):
    """Monitor bot additions and mass joins"""
    
    # Bot addition protection
    if member.bot:
        guild = member.guild
        await asyncio.sleep(1)
        
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                inviter = entry.user
                
                if inviter.id == Config.OWNER_ID or data_manager.is_whitelisted(inviter.id):
                    await log_action(
                        guild,
                        '✅ Bot Addition Authorized',
                        f'{inviter.mention} added bot: {member.mention}\n'
                        f'Status: **AUTHORIZED** (Whitelisted user)',
                        discord.Color.green()
                    )
                    return
                
                try:
                    await member.kick(reason=f'Unauthorized bot addition by {inviter}')
                    
                    inviter_member = guild.get_member(inviter.id)
                    if inviter_member:
                        roles_to_remove = [
                            role for role in inviter_member.roles 
                            if role != guild.default_role and role.position < guild.me.top_role.position
                        ]
                        
                        if roles_to_remove:
                            await inviter_member.remove_roles(
                                *roles_to_remove,
                                reason='Unauthorized bot addition - Security measure'
                            )
                    
                    await log_action(
                        guild,
                        '🚨 ANTI-NUKE: Unauthorized Bot Blocked',
                        f'**Bot Kicked:** {member.mention} (`{member.id}`)\n'
                        f'**Added By:** {inviter.mention} (`{inviter.id}`)\n'
                        f'**Action Taken:** Bot kicked and user roles stripped\n'
                        f'**Reason:** Unauthorized bot addition without permission',
                        discord.Color.red()
                    )
                    
                    try:
                        await inviter.send(
                            f'⚠️ **Security Alert**\n\n'
                            f'Your attempt to add a bot to **{guild.name}** was blocked.\n'
                            f'Your roles have been removed for security reasons.\n\n'
                            f'Only authorized users can add bots. Contact the server owner if you believe this was an error.'
                        )
                    except:
                        pass
                    
                except discord.Forbidden:
                    await log_action(
                        guild,
                        '❌ ANTI-NUKE: Action Failed',
                        f'Detected unauthorized bot addition by {inviter.mention}\n'
                        f'Bot: {member.mention}\n'
                        f'**ERROR:** Insufficient permissions to take action',
                        discord.Color.dark_red()
                    )
                except Exception as e:
                    await log_action(
                        guild,
                        '❌ ANTI-NUKE: Error',
                        f'Error while handling unauthorized bot addition:\n```{str(e)}```',
                        discord.Color.dark_red()
                    )
                
                break
    
    # Raid detection
    guild = member.guild
    current_time = datetime.utcnow().timestamp()
    
    if not hasattr(bot, 'recent_joins'):
        bot.recent_joins = defaultdict(list)
    
    bot.recent_joins[guild.id].append(current_time)
    
    bot.recent_joins[guild.id] = [
        ts for ts in bot.recent_joins[guild.id]
        if current_time - ts <= 10
    ]
    
    if len(bot.recent_joins[guild.id]) >= 10:
        try:
            await guild.edit(
                verification_level=discord.VerificationLevel.high,
                reason='Raid detected - increasing security'
            )
            
            await log_action(
                guild,
                '🚨 ANTI-RAID: Raid Detected',
                f'**Mass join detected:** {len(bot.recent_joins[guild.id])} users in 10 seconds\n'
                f'**Action:** Verification level increased to HIGH\n'
                f'**Note:** You may want to manually review recent joins',
                discord.Color.red()
            )
            
            bot.recent_joins[guild.id].clear()
            
        except:
            pass

@bot.event
async def on_guild_channel_delete(channel):
    """Monitor channel deletions for nuke attempts"""
    guild = channel.guild
    
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        if entry.target.id == channel.id:
            deleter = entry.user
            
            if data_manager.is_whitelisted(deleter.id) or deleter.id == Config.OWNER_ID:
                break
            
            deletion_count = 0
            async for del_entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.channel_delete):
                if del_entry.user.id == deleter.id:
                    if (datetime.utcnow() - del_entry.created_at).total_seconds() < 30:
                        deletion_count += 1
            
            if deletion_count >= 3:
                try:
                    member = guild.get_member(deleter.id)
                    if member:
                        roles_to_remove = [r for r in member.roles if r != guild.default_role]
                        await member.remove_roles(*roles_to_remove, reason='Potential nuke attempt detected')
                        
                        await member.timeout(timedelta(days=7), reason='Mass channel deletion detected')
                        
                        await log_action(
                            guild,
                            '🚨 ANTI-NUKE: Mass Deletion Detected',
                            f'User: {deleter.mention}\n'
                            f'Channels deleted: {deletion_count}\n'
                            f'Action: Roles stripped and timed out for 7 days',
                            discord.Color.red()
                        )
                except:
                    pass
            break

@bot.event
async def on_message(message: discord.Message):
    """Monitor messages for spam and profanity"""
    
    if message.author.bot or not message.guild:
        return
    
    if data_manager.is_whitelisted(message.author.id):
        await bot.process_commands(message)
        return
    
    user_id = message.author.id
    current_time = datetime.utcnow().timestamp()
    
    # Anti-spam check
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
        
        timeout_minutes = calculate_spam_timeout(violation_count)
        
        try:
            try:
                await message.channel.purge(
                    limit=20,
                    check=lambda m: m.author.id == user_id,
                    reason='Spam detected'
                )
            except:
                pass
            
            await message.author.timeout(
                timedelta(minutes=timeout_minutes),
                reason=f'Spam detected - {message_count} messages in {Config.SPAM_TIMEFRAME}s'
            )
            
            warning_msg = await message.channel.send(
                f'⚠️ {message.author.mention} has been timed out for **{timeout_minutes} minutes** for spamming.\n'
                f'**Violation #{violation_count}** | Messages: {message_count} in {Config.SPAM_TIMEFRAME}s'
            )
            
            await asyncio.sleep(10)
            try:
                await warning_msg.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                '🚫 ANTI-SPAM: User Timed Out',
                f'**User:** {message.author.mention} (`{message.author.id}`)\n'
                f'**Messages:** {message_count} in {Config.SPAM_TIMEFRAME} seconds\n'
                f'**Violation Count:** {violation_count}\n'
                f'**Timeout Duration:** {timeout_minutes} minutes\n'
                f'**Channel:** {message.channel.mention}',
                discord.Color.orange()
            )
            
        except discord.Forbidden:
            await log_action(
                message.guild,
                '❌ ANTI-SPAM: Action Failed',
                f'Cannot timeout {message.author.mention} - insufficient permissions',
                discord.Color.dark_red()
            )
        except Exception as e:
            print(f'Error in anti-spam: {e}')
        
        data_manager.message_history[user_id].clear()
        return
    
    # Profanity filter
    is_profane, matched_word = contains_profanity(message.content)
    
    if is_profane:
        try:
            await message.delete()
            
            await message.author.timeout(
                timedelta(minutes=Config.PROFANITY_TIMEOUT),
                reason=f'Profanity detected: {matched_word}'
            )
            
            warning = await message.channel.send(
                f'⚠️ {message.author.mention} has been timed out for **{Config.PROFANITY_TIMEOUT} minutes** '
                f'for using inappropriate language.'
            )
            
            await asyncio.sleep(8)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                '🔇 AUTOMOD: Profanity Detected',
                f'**User:** {message.author.mention} (`{message.author.id}`)\n'
                f'**Channel:** {message.channel.mention}\n'
                f'**Matched Word:** `{matched_word}`\n'
                f'**Timeout:** {Config.PROFANITY_TIMEOUT} minutes\n'
                f'**Message:** {message.content[:100]}...' if len(message.content) > 100 else f'**Message:** {message.content}',
                discord.Color.purple()
            )
            
        except discord.Forbidden:
            await log_action(
                message.guild,
                '❌ AUTOMOD: Action Failed',
                f'Cannot moderate {message.author.mention} - insufficient permissions',
                discord.Color.dark_red()
            )
        except Exception as e:
            print(f'Automod error: {e}')
        return
    
    # Excessive caps filter
    if has_excessive_caps(message.content):
        try:
            await message.delete()
            
            warning = await message.channel.send(
                f'⚠️ {message.author.mention}, please don\'t use excessive caps. Your message was removed.'
            )
            
            await asyncio.sleep(5)
            try:
                await warning.delete()
            except:
                pass
            
        except:
            pass
        return
    
    # Mention spam filter
    mention_count = len(message.mentions) + len(message.role_mentions)
    
    if mention_count >= 5:
        try:
            await message.delete()
            
            await message.author.timeout(
                timedelta(minutes=10),
                reason=f'Mention spam: {mention_count} mentions'
            )
            
            warning = await message.channel.send(
                f'⚠️ {message.author.mention} has been timed out for **10 minutes** for mention spam.'
            )
            
            await asyncio.sleep(8)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(
                message.guild,
                '🔇 AUTOMOD: Mention Spam',
                f'**User:** {message.author.mention}\n'
                f'**Mentions:** {mention_count}\n'
                f'**Action:** 10 minute timeout',
                discord.Color.purple()
            )
            
        except:
            pass
        return
    
    await bot.process_commands(message)

# ============================================
# WHITELIST COMMANDS
# ============================================

@bot.tree.command(
    name="whitelist_add",
    description="Add a user to the whitelist (Owner only)"
)
@is_owner()
async def whitelist_add(
    interaction: discord.Interaction,
    user: discord.User
):
    """Add a user to the whitelist"""
    
    if data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(
            f'ℹ️ {user.mention} is already whitelisted!',
            ephemeral=True
        )
        return
    
    data_manager.add_to_whitelist(user.id)
    
    if user.id in data_manager.user_violations:
        del data_manager.user_violations[user.id]
        data_manager.save_data()
    
    embed = discord.Embed(
        title='✅ User Whitelisted',
        description=f'{user.mention} has been added to the whitelist.',
        color=discord.Color.green()
    )
    embed.add_field(
        name='Permissions',
        value='• Immune to spam detection\n'
              '• Immune to automod filters\n'
              '• Can add bots\n'
              '• Can grant roles with dangerous permissions',
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        '✅ Whitelist Updated',
        f'{interaction.user.mention} added {user.mention} to whitelist',
        discord.Color.green()
    )

@bot.tree.command(
    name="whitelist_remove",
    description="Remove a user from the whitelist (Owner only)"
)
@is_owner()
async def whitelist_remove(
    interaction: discord.Interaction,
    user: discord.User
):
    """Remove a user from the whitelist"""
    
    if not data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(
            f'ℹ️ {user.mention} is not whitelisted!',
            ephemeral=True
        )
        return
    
    data_manager.remove_from_whitelist(user.id)
    
    embed = discord.Embed(
        title='🔴 User Removed from Whitelist',
        description=f'{user.mention} has been removed from the whitelist.',
        color=discord.Color.red()
    )
    embed.add_field(
        name='Note',
        value='This user is now subject to all security and automod rules.',
        inline=False
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        '🔴 Whitelist Updated',
        f'{interaction.user.mention} removed {user.mention} from whitelist',
        discord.Color.orange()
    )

@bot.tree.command(
    name="whitelist_list",
    description="View all whitelisted users (Owner only)"
)
@is_owner()
async def whitelist_list(interaction: discord.Interaction):
    """List all whitelisted users"""
    
    if not data_manager.whitelist:
        await interaction.response.send_message(
            '📝 The whitelist is currently empty.',
            ephemeral=True
        )
        return
    
    user_list = []
    for user_id in data_manager.whitelist:
        user = bot.get_user(user_id)
        if user:
            user_list.append(f'• {user.mention} (`{user.id}`)')
        else:
            user_list.append(f'• Unknown User (`{user_id}`)')
    
    embed = discord.Embed(
        title='📋 Whitelisted Users',
        description='\n'.join(user_list),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f'Total: {len(data_manager.whitelist)} user(s)')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(
    name="clear_violations",
    description="Clear violation history for a user (Owner only)"
)
@is_owner()
async def clear_violations(
    interaction: discord.Interaction,
    user: discord.User
):
    """Clear a user's violation history"""
    
    if user.id not in data_manager.user_violations:
        await interaction.response.send_message(
            f'ℹ️ {user.mention} has no violation history.',
            ephemeral=True
        )
        return
    
    violation_count = data_manager.user_violations[user.id]
    del data_manager.user_violations[user.id]
    data_manager.save_data()
    
    embed = discord.Embed(
        title='🗑️ Violations Cleared',
        description=f'Cleared **{violation_count}** violation(s) for {user.mention}',
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)
    
    await log_action(
        interaction.guild,
        '🗑️ Violations Cleared',
        f'{interaction.user.mention} cleared violation history for {user.mention}\n'
        f'Previous violations: {violation_count}',
        discord.Color.blue()
    )

@bot.tree.command(
    name="view_violations",
    description="View violation history for a user (Owner only)"
)
@is_owner()
async def view_violations(
    interaction: discord.Interaction,
    user: discord.User
):
    """View a user's violation history"""
    
    violation_count = data_manager.user_violations.get(user.id, 0)
    is_whitelisted = data_manager.is_whitelisted(user.id)
    
    embed = discord.Embed(
        title=f'📊 Violation History: {user.name}',
        color=discord.Color.blue() if is_whitelisted else discord.Color.orange()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(
        name='Total Violations',
        value=str(violation_count),
        inline=True
    )
    embed.add_field(
        name='Whitelisted',
        value='✅ Yes' if is_whitelisted else '❌ No',
        inline=True
    )
    
    if violation_count > 0:
        next_timeout = calculate_spam_timeout(violation_count + 1)
        embed.add_field(
            name='Next Timeout Duration',
            value=f'{next_timeout} minutes',
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

"""
Discord Security Bot - Part 7: Management & Execution
UPDATED: Render deployment with 24/7 uptime and + prefix
"""

# ============================================
# MANAGEMENT COMMANDS
# ============================================

@bot.tree.command(
    name="security_status",
    description="View security bot status and statistics (Owner only)"
)
@is_owner()
async def security_status(interaction: discord.Interaction):
    """Display security bot statistics"""
    
    guild = interaction.guild
    
    # Count total violations
    total_violations = sum(data_manager.user_violations.values())
    users_with_violations = len(data_manager.user_violations)
    
    embed = discord.Embed(
        title='🛡️ Security Bot Status',
        description='Current security system statistics',
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    # Bot info
    embed.add_field(
        name='Bot Status',
        value=f'✅ Online (24/7 on Render)\n'
              f'Latency: {round(bot.latency * 1000)}ms\n'
              f'Prefix: `{Config.PREFIX}`\n'
              f'Servers: {len(bot.guilds)}',
        inline=True
    )
    
    # Protection stats
    embed.add_field(
        name='Protection Systems',
        value='🛡️ Anti-Nuke: Active\n'
              '🚫 Anti-Spam: Active\n'
              '🔇 Automod: Active\n'
              '🚨 Anti-Raid: Active',
        inline=True
    )
    
    # Whitelist info
    embed.add_field(
        name='Whitelist',
        value=f'{len(data_manager.whitelist)} user(s)',
        inline=True
    )
    
    # Violation stats
    embed.add_field(
        name='Violation Statistics',
        value=f'Total Violations: {total_violations}\n'
              f'Users with Violations: {users_with_violations}',
        inline=False
    )
    
    # Configuration
    embed.add_field(
        name='⚙️ Configuration',
        value=f'Spam Threshold: {Config.SPAM_THRESHOLD} msg/{Config.SPAM_TIMEFRAME}s\n'
              f'Profanity Timeout: {Config.PROFANITY_TIMEOUT}m\n'
              f'Banned Words: {len(Config.BANNED_WORDS)}',
        inline=False
    )
    
    embed.set_footer(text=f'Requested by {interaction.user}')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(
    name="config_update",
    description="Update bot configuration (Owner only)"
)
@is_owner()
async def config_update(
    interaction: discord.Interaction,
    spam_threshold: Optional[int] = None,
    spam_timeframe: Optional[int] = None,
    profanity_timeout: Optional[int] = None
):
    """Update bot configuration settings"""
    
    changes = []
    
    if spam_threshold is not None:
        Config.SPAM_THRESHOLD = spam_threshold
        changes.append(f'Spam Threshold: {spam_threshold} messages')
    
    if spam_timeframe is not None:
        Config.SPAM_TIMEFRAME = spam_timeframe
        changes.append(f'Spam Timeframe: {spam_timeframe} seconds')
    
    if profanity_timeout is not None:
        Config.PROFANITY_TIMEOUT = profanity_timeout
        changes.append(f'Profanity Timeout: {profanity_timeout} minutes')
    
    if not changes:
        await interaction.response.send_message(
            '❌ No configuration changes specified!',
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title='⚙️ Configuration Updated',
        description='The following settings have been updated:',
        color=discord.Color.green()
    )
    embed.add_field(
        name='Changes',
        value='\n'.join(f'• {change}' for change in changes),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="add_banned_word",
    description="Add a word to the profanity filter (Owner only)"
)
@is_owner()
async def add_banned_word(
    interaction: discord.Interaction,
    word: str
):
    """Add a word to the banned words list"""
    
    word_lower = word.lower()
    
    if word_lower in Config.BANNED_WORDS:
        await interaction.response.send_message(
            f'❌ The word is already in the filter!',
            ephemeral=True
        )
        return
    
    Config.BANNED_WORDS.append(word_lower)
    
    await interaction.response.send_message(
        f'✅ Added word to profanity filter.\n'
        f'Total banned words: {len(Config.BANNED_WORDS)}',
        ephemeral=True
    )

@bot.tree.command(
    name="help_security",
    description="View security bot commands and information"
)
async def help_security(interaction: discord.Interaction):
    """Display help information"""
    
    is_owner_user = interaction.user.id == Config.OWNER_ID
    
    embed = discord.Embed(
        title='🛡️ Security Bot - Help',
        description=f'Comprehensive server protection system\nPrefix: `{Config.PREFIX}`',
        color=discord.Color.blue()
    )
    
    # Protection features
    embed.add_field(
        name='🛡️ Anti-Nuke Protection',
        value='• Blocks unauthorized bot additions\n'
              '• Monitors suspicious role changes\n'
              '• Detects mass channel deletions\n'
              '• Auto-strips roles from violators',
        inline=False
    )
    
    embed.add_field(
        name='🚫 Anti-Spam System',
        value=f'• Detects message spam ({Config.SPAM_THRESHOLD} msg/{Config.SPAM_TIMEFRAME}s)\n'
              '• Progressive timeout system\n'
              '• Auto-purges spam messages\n'
              '• Tracks violation history',
        inline=False
    )
    
    embed.add_field(
        name='🔇 Automod Features',
        value=f'• Profanity filter ({Config.PROFANITY_TIMEOUT}m timeout)\n'
              '• Excessive caps filter\n'
              '• Mention spam protection (5+ mentions)\n'
              '• Automatic message deletion',
        inline=False
    )
    
    embed.add_field(
        name='🚨 Anti-Raid Detection',
        value='• Monitors mass user joins\n'
              '• Auto-increases server security\n'
              '• Real-time raid alerts',
        inline=False
    )
    
    if is_owner_user:
        embed.add_field(
            name='⚙️ Owner Commands',
            value='`/whitelist_add` - Whitelist a user\n'
                  '`/whitelist_remove` - Remove from whitelist\n'
                  '`/whitelist_list` - View all whitelisted users\n'
                  '`/clear_violations` - Clear user violations\n'
                  '`/view_violations` - View user violations\n'
                  '`/security_status` - View bot status\n'
                  '`/config_update` - Update settings\n'
                  '`/add_banned_word` - Add filtered word',
            inline=False
        )
    
    embed.set_footer(text='Running 24/7 on Render | Whitelisted users bypass all restrictions')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# ERROR HANDLERS
# ============================================

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You don\'t have permission to use this command!')
    else:
        print(f'Error: {error}')

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    """Handle slash command errors"""
    if isinstance(error, app_commands.CheckFailure):
        # Already handled by the check
        return
    else:
        await interaction.response.send_message(
            f'❌ An error occurred: {str(error)}',
            ephemeral=True
        )
        print(f'Command error: {error}')

# ============================================
# RENDER 24/7 UPTIME - WEB SERVER
# ============================================

async def start_keep_alive():
    """Start the keep-alive web server for Render"""
    from aiohttp import web
    
    async def health(request):
        return web.Response(text='🛡️ Security Bot Online!', status=200)
    
    async def status_page(request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Discord Security Bot</title>
            <meta http-equiv="refresh" content="60">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                .container {{
                    text-align: center;
                    background: rgba(0, 0, 0, 0.4);
                    padding: 50px;
                    border-radius: 25px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                    backdrop-filter: blur(10px);
                }}
                h1 {{ font-size: 3.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                .status {{ 
                    background: #10b981;
                    padding: 15px 30px;
                    border-radius: 15px;
                    display: inline-block;
                    margin: 30px 0;
                    font-size: 1.3em;
                    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
                }}
                p {{ font-size: 1.3em; margin: 10px 0; }}
                .info {{ 
                    background: rgba(255, 255, 255, 0.1);
                    padding: 20px;
                    border-radius: 15px;
                    margin-top: 30px;
                }}
                .pulse {{
                    animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.7; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Security Bot</h1>
                <div class="status pulse">✅ ONLINE - 24/7</div>
                <p>Bot is running and protecting your server!</p>
                <p>Prefix: <strong>{Config.PREFIX}</strong></p>
                <div class="info">
                    <p><strong>Servers:</strong> {len(bot.guilds)}</p>
                    <p><strong>Latency:</strong> {round(bot.latency * 1000)}ms</p>
                    <p><strong>Platform:</strong> Render</p>
                </div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    app = web.Application()
    app.router.add_get('/', status_page)
    app.router.add_get('/health', health)
    app.router.add_get('/ping', health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
    await site.start()
    
    print(f'🌐 Keep-alive server running on port {Config.PORT}')

# ============================================
# RUN THE BOT
# ============================================

async def main():
    """Main function to run bot and web server"""
    # Start keep-alive server
    await start_keep_alive()
    
    # Start the bot
    try:
        await bot.start(Config.TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        print(f'❌ Bot error: {e}')
        await bot.close()

if __name__ == '__main__':
    print('=' * 60)
    print('🚀 DISCORD SECURITY BOT - RENDER DEPLOYMENT')
    print('=' * 60)
    print(f'Owner ID: {Config.OWNER_ID}')
    print(f'Prefix: {Config.PREFIX}')
    print(f'Port: {Config.PORT}')
    print('Starting bot with 24/7 uptime...')
    print('=' * 60)
    
    if not Config.TOKEN:
        print('❌ ERROR: DISCORD_BOT_TOKEN environment variable not set!')
        print('Set it in Render dashboard: Environment > Add Environment Variable')
        exit(1)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f'❌ Failed to start: {e}')

