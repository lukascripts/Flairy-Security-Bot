"""
=============================================================================
DISCORD ADVANCED SECURITY BOT - PART 1 OF 5
=============================================================================
Copy this into main.py FIRST
Features: Verification Panel, Anti-Nuke, Less Strict Automod, Advanced Commands
Prefix: +
Owner ID: 1029438856069656576
=============================================================================
"""

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
from typing import Optional, Set, Dict, List
import re
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

class Config:
    OWNER_ID = 1029438856069656576
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    PREFIX = '+'
    PORT = int(os.getenv('PORT', 8080))

# staff role id 
    STAFF_ROLE_ID = 1432081794647199895
    
    # LESS STRICT AUTOMOD (Relaxed settings)
    SPAM_THRESHOLD = 10  # 10 messages instead of 5
    SPAM_TIMEFRAME = 5   # In 5 seconds
    SPAM_TIMEOUT_MULTIPLIER = {1: 5, 2: 10, 3: 15, 4: 30, 5: 60}
    
    PROFANITY_TIMEOUT = 5  # Only 5 minutes instead of 20
    
    # Only extreme words banned
    BANNED_WORDS = ['nigger', 'nigga', 'n1gger', 'n1gga', 'faggot']
    BANNED_PATTERNS = [r'n[i1!]gg[ae]r', r'f[a4]gg[o0]t']
    
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
# DATA MANAGER
# ============================================

class DataManager:
    def __init__(self):
        self.data_file = 'security_data.json'
        self.whitelist: Set[int] = set()
        self.user_violations: Dict[int, int] = defaultdict(int)
        self.message_history: Dict[int, List[float]] = defaultdict(list)
        
        # Verification system
        self.verified_role_id: Optional[int] = None
        self.unverified_role_id: Optional[int] = None
        self.verification_channel_id: Optional[int] = None

# staff role 
        self.staff_role_id: Optional[int] = None
        
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.whitelist = set(data.get('whitelist', []))
                    self.user_violations = defaultdict(int, {int(k): v for k, v in data.get('violations', {}).items()})
                    self.verified_role_id = data.get('verified_role_id')
                    self.unverified_role_id = data.get('unverified_role_id')
                    self.verification_channel_id = data.get('verification_channel_id')
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def save_data(self):
        try:
            data = {
                'whitelist': list(self.whitelist),
                'violations': {str(k): v for k, v in self.user_violations.items()},
                'verified_role_id': self.verified_role_id,
                'unverified_role_id': self.unverified_role_id,
                'verification_channel_id': self.verification_channel_id,
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def add_to_whitelist(self, user_id: int):
        self.whitelist.add(user_id)
        self.save_data()
    
    def remove_from_whitelist(self, user_id: int):
        self.whitelist.discard(user_id)
        self.save_data()
    
    def is_whitelisted(self, user_id: int) -> bool:
        return user_id in self.whitelist

# ============================================
# BOT SETUP
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents, help_command=None)
data_manager = DataManager()

# ============================================
# UTILITY FUNCTIONS
# ============================================

def is_owner():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.id != Config.OWNER_ID:
            await interaction.response.send_message("❌ Only the bot owner can use this!", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

def is_owner_or_admin():
    async def predicate(ctx):
        return ctx.author.id == Config.OWNER_ID or ctx.author.guild_permissions.administrator
    return commands.check(predicate)

async def log_action(guild: discord.Guild, title: str, description: str, color: discord.Color):
    log_channel = discord.utils.get(guild.text_channels, name='security-logs')
    if not log_channel:
        try:
            log_channel = await guild.create_text_channel('security-logs', reason='Security logs')
        except:
            return
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
    try:
        await log_channel.send(embed=embed)
    except:
        pass

def calculate_spam_timeout(violation_count: int) -> int:
    return Config.SPAM_TIMEOUT_MULTIPLIER.get(violation_count, 60) if violation_count <= 5 else 60

def contains_profanity(content: str) -> tuple[bool, str]:
    content_lower = content.lower()
    for word in Config.BANNED_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', content_lower):
            return True, word
    for pattern in Config.BANNED_PATTERNS:
        if match := re.search(pattern, content_lower, re.IGNORECASE):
            return True, match.group(0)
    return False, ''

# ============================================
# VERIFICATION BUTTON VIEW
# ============================================

class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="✅ Verify Me", style=discord.ButtonStyle.green, custom_id="verify_button", emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        member = interaction.user
        
        verified_role = guild.get_role(data_manager.verified_role_id) if data_manager.verified_role_id else None
        unverified_role = guild.get_role(data_manager.unverified_role_id) if data_manager.unverified_role_id else None
        
        if not verified_role:
            await interaction.response.send_message("❌ Verification not set up! Contact an admin.", ephemeral=True)
            return
        
        if verified_role in member.roles:
            await interaction.response.send_message("✅ You're already verified!", ephemeral=True)
            return
        
        try:
            await member.add_roles(verified_role, reason="User verified")
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason="User verified")
            
            await interaction.response.send_message(
                f"✅ **Welcome to {guild.name}!**\n\nYou've been verified and now have full access to the server!",
                ephemeral=True
            )
            
            await log_action(guild, '✅ User Verified', f'{member.mention} verified successfully', discord.Color.green())
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

"""
=============================================================================
PART 2 OF 5 - Bot Events & Anti-Nuke Protection
=============================================================================
Copy this AFTER Part 1
"""

# ============================================
# BOT EVENTS
# ============================================

@bot.event
async def on_ready():
    print('=' * 70)
    print(f'✅ {bot.user} is ONLINE!')
    print(f'📊 Servers: {len(bot.guilds)}')
    print(f'👥 Users: {len(bot.users)}')
    print(f'🌐 Render 24/7 | Prefix: {Config.PREFIX}')
    print('=' * 70)
    
    bot.add_view(VerificationView())
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'❌ Command sync failed: {e}')
    
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{Config.PREFIX}help | Protecting servers"),
        status=discord.Status.online
    )
    
    print('🛡️  ALL SYSTEMS ACTIVE!')
    print('=' * 70)

@bot.event
async def on_member_join(member: discord.Member):
    # Auto-assign unverified role
    if data_manager.unverified_role_id:
        unverified_role = member.guild.get_role(data_manager.unverified_role_id)
        if unverified_role:
            try:
                await member.add_roles(unverified_role, reason="Auto-assign unverified")
            except:
                pass
    
    # Bot addition protection
    if member.bot:
        guild = member.guild
        await asyncio.sleep(1)
        
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                inviter = entry.user
                
                if inviter.id == Config.OWNER_ID or data_manager.is_whitelisted(inviter.id):
                    await log_action(guild, '✅ Bot Addition Authorized',
                        f'{inviter.mention} added {member.mention}\n**Status:** AUTHORIZED',
                        discord.Color.green())
                    return
                
                try:
                    await member.kick(reason=f'Unauthorized bot by {inviter}')
                    
                    inviter_member = guild.get_member(inviter.id)
                    if inviter_member:
                        roles_to_remove = [r for r in inviter_member.roles 
                            if r != guild.default_role and r.position < guild.me.top_role.position]
                        if roles_to_remove:
                            await inviter_member.remove_roles(*roles_to_remove, reason='Unauthorized bot')
                    
                    await log_action(guild, '🚨 ANTI-NUKE: Bot Blocked',
                        f'**Bot:** {member.mention}\n**Added By:** {inviter.mention}\n**Action:** Kicked, roles stripped',
                        discord.Color.red())
                except:
                    pass
                break
    
    # Raid detection
    guild = member.guild
    current_time = datetime.utcnow().timestamp()
    
    if not hasattr(bot, 'recent_joins'):
        bot.recent_joins = defaultdict(list)
    
    bot.recent_joins[guild.id].append(current_time)
    bot.recent_joins[guild.id] = [ts for ts in bot.recent_joins[guild.id] if current_time - ts <= 10]
    
    if len(bot.recent_joins[guild.id]) >= 10:
        try:
            await guild.edit(verification_level=discord.VerificationLevel.high, reason='Raid detected')
            await log_action(guild, '🚨 ANTI-RAID: Raid Detected',
                f'**Mass joins:** {len(bot.recent_joins[guild.id])} in 10s\n**Action:** Verification raised to HIGH',
                discord.Color.red())
            bot.recent_joins[guild.id].clear()
        except:
            pass

@bot.event
async def on_guild_role_create(role: discord.Role):
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        if entry.target.id == role.id:
            creator = entry.user
            if creator.bot and not data_manager.is_whitelisted(creator.id):
                try:
                    await role.delete(reason='Unauthorized bot role')
                    await log_action(guild, '🛡️ ANTI-NUKE: Role Deleted',
                        f'Deleted role by unauthorized bot: {creator.mention}\nRole: {role.name}',
                        discord.Color.red())
                except:
                    pass
            break

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    added_roles = set(after.roles) - set(before.roles)
    if added_roles:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                moderator = entry.user
                if data_manager.is_whitelisted(moderator.id) or moderator.id == Config.OWNER_ID:
                    break
                
                dangerous_granted = False
                for role in added_roles:
                    for perm in Config.DANGEROUS_PERMISSIONS:
                        if getattr(role.permissions, perm[0], False):
                            dangerous_granted = True
                            break
                
                if dangerous_granted:
                    try:
                        roles_to_remove = [r for r in moderator.roles if r != after.guild.default_role]
                        await moderator.remove_roles(*roles_to_remove, reason='Unauthorized dangerous permission')
                        await log_action(after.guild, '🛡️ ANTI-NUKE: Roles Stripped',
                            f'{moderator.mention} granted dangerous permissions without authorization',
                            discord.Color.orange())
                    except:
                        pass
                break

@bot.event
async def on_guild_channel_delete(channel):
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
                        await member.remove_roles(*roles_to_remove, reason='Mass deletion')
                        await member.timeout(timedelta(days=7), reason='Nuke attempt')
                        await log_action(guild, '🚨 ANTI-NUKE: Mass Deletion',
                            f'**User:** {deleter.mention}\n**Channels:** {deletion_count}\n**Action:** 7d timeout, roles stripped',
                            discord.Color.dark_red())
                except:
                    pass
            break

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    
    if data_manager.is_whitelisted(message.author.id):
        await bot.process_commands(message)
        return
    
    user_id = message.author.id
    current_time = datetime.utcnow().timestamp()
    
    # LESS STRICT SPAM (10 messages in 5s)
    data_manager.message_history[user_id].append(current_time)
    data_manager.message_history[user_id] = [ts for ts in data_manager.message_history[user_id] if current_time - ts <= Config.SPAM_TIMEFRAME]
    
    message_count = len(data_manager.message_history[user_id])
    
    if message_count >= Config.SPAM_THRESHOLD:
        data_manager.user_violations[user_id] += 1
        violation_count = data_manager.user_violations[user_id]
        data_manager.save_data()
        
        timeout_minutes = calculate_spam_timeout(violation_count)
        
        try:
            await message.channel.purge(limit=15, check=lambda m: m.author.id == user_id)
            await message.author.timeout(timedelta(minutes=timeout_minutes), reason=f'Spam: {message_count} msgs')
            
            warning = await message.channel.send(
                f'⚠️ {message.author.mention} timed out for **{timeout_minutes}min** - Spamming ({message_count} messages)'
            )
            await asyncio.sleep(8)
            try:
                await warning.delete()
            except:
                pass
            
            await log_action(message.guild, '🚫 Anti-Spam',
                f'**User:** {message.author.mention}\n**Messages:** {message_count}\n**Timeout:** {timeout_minutes}min',
                discord.Color.orange())
        except:
            pass
        
        data_manager.message_history[user_id].clear()
        return
    
    # LESS STRICT PROFANITY (only extreme words, 5min timeout)
    is_profane, matched = contains_profanity(message.content)
    if is_profane:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=Config.PROFANITY_TIMEOUT), reason=f'Profanity: {matched}')
            
            warning = await message.channel.send(
                f'⚠️ {message.author.mention} - Please watch your language. (5min timeout)'
            )
            await asyncio.sleep(6)
            try:
                await warning.delete()
            except:
                pass
        except:
            pass
        return
    
    # Mention spam (8+ mentions)
    mention_count = len(message.mentions) + len(message.role_mentions)
    if mention_count >= 8:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=5), reason=f'{mention_count} mentions')
            warning = await message.channel.send(f'⚠️ {message.author.mention} - Too many mentions (5min timeout)')
            await asyncio.sleep(6)
            try:
                await warning.delete()
            except:
                pass
        except:
            pass
        return
    
    await bot.process_commands(message)


    """
=============================================================================
PART 3 OF 5 - Verification System & Moderation Commands
=============================================================================
Copy this AFTER Part 2
"""

# ============================================
# VERIFICATION COMMANDS (Slash)
# ============================================

@bot.tree.command(name="setup_verification", description="Setup verification system (Owner only)")
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
        title='✅ Verification System Configured',
        description='Verification panel is ready!',
        color=discord.Color.green()
    )
    embed.add_field(name='✅ Verified Role', value=verified_role.mention, inline=True)
    embed.add_field(name='❌ Unverified Role', value=unverified_role.mention, inline=True)
    embed.add_field(name='📢 Channel', value=channel.mention, inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    await log_action(interaction.guild, '⚙️ Verification Configured',
        f'Verified: {verified_role.mention}\nUnverified: {unverified_role.mention}\nChannel: {channel.mention}',
        discord.Color.blue())

@bot.tree.command(name="send_verification", description="Send verification panel (Owner only)")
@is_owner()
async def send_verification(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    """Send the verification panel"""
    target_channel = channel or interaction.channel
    
    if not data_manager.verified_role_id:
        await interaction.response.send_message("❌ Setup verification first with `/setup_verification`!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title='🔐 Verification Required',
        description=(
            '**Welcome to the server!**\n\n'
            'To gain access to all channels, please click the button below to verify yourself.\n\n'
            '✅ Click **"Verify Me"** to get started!'
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text='This verification helps keep our server safe!')
    
    view = VerificationView()
    await target_channel.send(embed=embed, view=view)
    
    await interaction.response.send_message(f'✅ Verification panel sent to {target_channel.mention}', ephemeral=True)

@bot.tree.command(name="verify_user", description="Manually verify a user (Owner/Admin)")
async def verify_user(interaction: discord.Interaction, member: discord.Member):
    """Manually verify a user"""
    if interaction.user.id != Config.OWNER_ID and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need admin permissions!", ephemeral=True)
        return
    
    if not data_manager.verified_role_id:
        await interaction.response.send_message("❌ Setup verification first!", ephemeral=True)
        return
    
    verified_role = interaction.guild.get_role(data_manager.verified_role_id)
    unverified_role = interaction.guild.get_role(data_manager.unverified_role_id) if data_manager.unverified_role_id else None
    
    try:
        await member.add_roles(verified_role, reason=f'Manually verified by {interaction.user}')
        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)
        
        await interaction.response.send_message(f'✅ {member.mention} has been verified!', ephemeral=True)
        await log_action(interaction.guild, '✅ Manual Verification',
            f'{interaction.user.mention} manually verified {member.mention}',
            discord.Color.green())
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

# ============================================
# MODERATION COMMANDS (Prefix)
# ============================================

@bot.command(name='kick')
@is_owner_or_admin()
async def kick_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member"""
    try:
        await member.kick(reason=f'{reason} | By {ctx.author}')
        embed = discord.Embed(
            title='👢 Member Kicked',
            description=f'**Member:** {member.mention}\n**Reason:** {reason}\n**By:** {ctx.author.mention}',
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, '👢 Member Kicked', f'{member.mention} kicked by {ctx.author.mention}\nReason: {reason}', discord.Color.orange())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='ban')
@is_owner_or_admin()
async def ban_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member"""
    try:
        await member.ban(reason=f'{reason} | By {ctx.author}')
        embed = discord.Embed(
            title='🔨 Member Banned',
            description=f'**Member:** {member.mention}\n**Reason:** {reason}\n**By:** {ctx.author.mention}',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, '🔨 Member Banned', f'{member.mention} banned by {ctx.author.mention}\nReason: {reason}', discord.Color.red())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='unban')
@is_owner_or_admin()
async def unban_cmd(ctx, user_id: int, *, reason: str = "No reason provided"):
    """Unban a user by ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f'{reason} | By {ctx.author}')
        await ctx.send(f'✅ Unbanned **{user}** (ID: {user_id})')
        await log_action(ctx.guild, '✅ Member Unbanned', f'User ID: {user_id} unbanned by {ctx.author.mention}\nReason: {reason}', discord.Color.green())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='timeout')
@is_owner_or_admin()
async def timeout_cmd(ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
    """Timeout a member (duration in minutes)"""
    try:
        await member.timeout(timedelta(minutes=duration), reason=f'{reason} | By {ctx.author}')
        embed = discord.Embed(
            title='⏰ Member Timed Out',
            description=f'**Member:** {member.mention}\n**Duration:** {duration} minutes\n**Reason:** {reason}',
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, '⏰ Timeout', f'{member.mention} timed out for {duration}min\nReason: {reason}', discord.Color.orange())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='untimeout')
@is_owner_or_admin()
async def untimeout_cmd(ctx, member: discord.Member):
    """Remove timeout from a member"""
    try:
        await member.timeout(None, reason=f'Untimeout by {ctx.author}')
        await ctx.send(f'✅ {member.mention} timeout removed')
        await log_action(ctx.guild, '✅ Timeout Removed', f'{member.mention} untimeout by {ctx.author.mention}', discord.Color.green())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='warn')
@is_owner_or_admin()
async def warn_cmd(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Warn a member"""
    try:
        await member.send(f'⚠️ **Warning from {ctx.guild.name}**\n\n**Reason:** {reason}\n**Warned by:** {ctx.author}')
        await ctx.send(f'✅ {member.mention} has been warned')
        await log_action(ctx.guild, '⚠️ Warning Issued', f'{member.mention} warned by {ctx.author.mention}\nReason: {reason}', discord.Color.gold())
    except:
        await ctx.send(f'⚠️ Warning logged but couldn\'t DM {member.mention}')

@bot.command(name='purge')
@is_owner_or_admin()
async def purge_cmd(ctx, amount: int):
    """Delete messages (max 100)"""
    if amount > 100:
        await ctx.send('❌ Maximum 100 messages at once!')
        return
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f'✅ Deleted {len(deleted) - 1} messages')
        await asyncio.sleep(3)
        await msg.delete()
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='slowmode')
@is_owner_or_admin()
async def slowmode_cmd(ctx, seconds: int):
    """Set slowmode (0 to disable)"""
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send('✅ Slowmode disabled')
        else:
            await ctx.send(f'✅ Slowmode set to {seconds} seconds')
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

# ============================================
# FIND THE +lock COMMAND IN PART 3 AND REPLACE IT WITH THIS:
# ============================================

@bot.command(name='lock')
@is_owner_or_admin()
async def lock_cmd(ctx, channel: discord.TextChannel = None):
    """Lock a channel (staff can still talk)"""
    channel = channel or ctx.channel
    try:
        # Lock for @everyone
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        
        # Allow staff to talk if staff role is set
        if Config.STAFF_ROLE_ID:
            staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID)
            if staff_role:
                await channel.set_permissions(staff_role, send_messages=True)
        
        await ctx.send(f'🔒 {channel.mention} locked (staff can still talk)')
        await log_action(ctx.guild, '🔒 Channel Locked', f'{channel.mention} locked by {ctx.author.mention}\nStaff can still send messages', discord.Color.red())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='unlock')
@is_owner_or_admin()
async def unlock_cmd(ctx, channel: discord.TextChannel = None):
    """Unlock a channel"""
    channel = channel or ctx.channel
    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f'🔓 {channel.mention} unlocked')
        await log_action(ctx.guild, '🔓 Channel Unlocked', f'{channel.mention} unlocked by {ctx.author.mention}', discord.Color.green())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

# ============================================
# WHITELIST COMMANDS (Slash)
# ============================================

@bot.tree.command(name="whitelist_add", description="Add user to whitelist (Owner only)")
@is_owner()
async def whitelist_add(interaction: discord.Interaction, user: discord.User):
    """Add a user to whitelist"""
    if data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(f'ℹ️ {user.mention} is already whitelisted!', ephemeral=True)
        return
    
    data_manager.add_to_whitelist(user.id)
    if user.id in data_manager.user_violations:
        del data_manager.user_violations[user.id]
        data_manager.save_data()
    
    embed = discord.Embed(
        title='✅ User Whitelisted',
        description=f'{user.mention} added to whitelist',
        color=discord.Color.green()
    )
    embed.add_field(name='Permissions', value='• Bypass spam\n• Bypass automod\n• Add bots\n• Grant roles', inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, '✅ Whitelist', f'{user.mention} whitelisted by {interaction.user.mention}', discord.Color.green())

@bot.tree.command(name="whitelist_remove", description="Remove user from whitelist (Owner only)")
@is_owner()
async def whitelist_remove(interaction: discord.Interaction, user: discord.User):
    """Remove user from whitelist"""
    if not data_manager.is_whitelisted(user.id):
        await interaction.response.send_message(f'ℹ️ {user.mention} is not whitelisted!', ephemeral=True)
        return
    
    data_manager.remove_from_whitelist(user.id)
    
    embed = discord.Embed(
        title='🔴 User Removed from Whitelist',
        description=f'{user.mention} removed from whitelist',
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    await log_action(interaction.guild, '🔴 Whitelist', f'{user.mention} removed by {interaction.user.mention}', discord.Color.orange())

@bot.tree.command(name="whitelist_list", description="View whitelisted users (Owner only)")
@is_owner()
async def whitelist_list(interaction: discord.Interaction):
    """List all whitelisted users"""
    if not data_manager.whitelist:
        await interaction.response.send_message('📝 Whitelist is empty', ephemeral=True)
        return
    
    user_list = []
    for user_id in data_manager.whitelist:
        user = bot.get_user(user_id)
        user_list.append(f'• {user.mention if user else f"Unknown (`{user_id}`)"}')
    
    embed = discord.Embed(title='📋 Whitelisted Users', description='\n'.join(user_list), color=discord.Color.blue())
    embed.set_footer(text=f'Total: {len(data_manager.whitelist)} users')
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="view_violations", description="View user violations (Owner only)")
@is_owner()
async def view_violations(interaction: discord.Interaction, user: discord.User):
    """View user violation history"""
    violation_count = data_manager.user_violations.get(user.id, 0)
    is_whitelisted = data_manager.is_whitelisted(user.id)
    
    embed = discord.Embed(title=f'📊 Violations: {user.name}', color=discord.Color.blue() if is_whitelisted else discord.Color.orange())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name='Violations', value=str(violation_count), inline=True)
    embed.add_field(name='Whitelisted', value='✅ Yes' if is_whitelisted else '❌ No', inline=True)
    
    if violation_count > 0:
        next_timeout = calculate_spam_timeout(violation_count + 1)
        embed.add_field(name='Next Timeout', value=f'{next_timeout}min', inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear_violations", description="Clear user violations (Owner only)")
@is_owner()
async def clear_violations(interaction: discord.Interaction, user: discord.User):
    """Clear user violations"""
    if user.id not in data_manager.user_violations:
        await interaction.response.send_message(f'ℹ️ {user.mention} has no violations', ephemeral=True)
        return
    
    violation_count = data_manager.user_violations[user.id]
    del data_manager.user_violations[user.id]
    data_manager.save_data()
    
    await interaction.response.send_message(f'✅ Cleared **{violation_count}** violations for {user.mention}', ephemeral=True)
    await log_action(interaction.guild, '🗑️ Violations Cleared', f'{user.mention} violations cleared by {interaction.user.mention}', discord.Color.blue())

# ============================================
# FIND THE +lockdown COMMAND IN PART 4 AND REPLACE IT WITH THIS:
# ============================================

@bot.command(name='lockdown')
@is_owner_or_admin()
async def lockdown_cmd(ctx):
    """Lockdown entire server (staff can still talk)"""
    try:
        locked_count = 0
        staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID) if Config.STAFF_ROLE_ID else None
        
        for channel in ctx.guild.text_channels:
            try:
                # Lock for @everyone
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                
                # Allow staff to talk
                if staff_role:
                    await channel.set_permissions(staff_role, send_messages=True)
                
                locked_count += 1
            except:
                pass
        
        embed = discord.Embed(
            title='🔒 SERVER LOCKDOWN',
            description=f'🔒 Locked {locked_count} channels\n⚠️ Server is now in lockdown mode\n{"✅ Staff can still send messages" if staff_role else ""}',
            color=discord.Color.dark_red()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, '🔒 SERVER LOCKDOWN', f'Lockdown initiated by {ctx.author.mention}\n{locked_count} channels locked\nStaff role: {staff_role.mention if staff_role else "Not set"}', discord.Color.dark_red())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')

@bot.command(name='unlockdown')
@is_owner_or_admin()
async def unlockdown_cmd(ctx):
    """Remove server lockdown"""
    try:
        unlocked_count = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                unlocked_count += 1
            except:
                pass
        
        embed = discord.Embed(
            title='🔓 LOCKDOWN ENDED',
            description=f'✅ Unlocked {unlocked_count} channels\n✅ Server returned to normal',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await log_action(ctx.guild, '🔓 Lockdown Ended', f'Lockdown ended by {ctx.author.mention}\n{unlocked_count} channels unlocked', discord.Color.green())
    except Exception as e:
        await ctx.send(f'❌ Error: {e}')


@bot.command(name='antiraid')
@is_owner_or_admin()
async def antiraid_cmd(ctx, mode: str):
    """Enable/disable anti-raid (on/off)"""
    if mode.lower() == 'on':
        try:
            await ctx.guild.edit(
                verification_level=discord.VerificationLevel.high
            )
            await ctx.send('🛡️ **Anti-Raid Mode: ON**\n✅ Verification set to HIGH')
            await log_action(ctx.guild, '🛡️ Anti-Raid ON', f'Enabled by {ctx.author.mention}', discord.Color.green())
        except Exception as e:
            await ctx.send(f'❌ Error: {e}')
    elif mode.lower() == 'off':
        try:
            await ctx.guild.edit(
                verification_level=discord.VerificationLevel.low
            )
            await ctx.send('✅ **Anti-Raid Mode: OFF**\n✅ Verification restored')
            await log_action(ctx.guild, '🔓 Anti-Raid OFF', f'Disabled by {ctx.author.mention}', discord.Color.blue())
        except Exception as e:
            await ctx.send(f'❌ Error: {e}')
    else:
        await ctx.send('❌ Use `+antiraid on` or `+antiraid off`')

@bot.command(name='roleall')
@is_owner_or_admin()
async def roleall_cmd(ctx, role: discord.Role):
    """Give role to all members"""
    added = 0
    msg = await ctx.send(f'⏳ Adding role to all members...')
    
    for member in ctx.guild.members:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason=f'Role all by {ctx.author}')
                added += 1
            except:
                pass
    
    await msg.edit(content=f'✅ Added {role.mention} to {added} members')

@bot.command(name='unroleall')
@is_owner_or_admin()
async def unroleall_cmd(ctx, role: discord.Role):
    """Remove role from all members"""
    removed = 0
    msg = await ctx.send(f'⏳ Removing role from all members...')
    
    for member in role.members:
        try:
            await member.remove_roles(role, reason=f'Unrole all by {ctx.author}')
            removed += 1
        except:
            pass
    
    await msg.edit(content=f'✅ Removed {role.mention} from {removed} members')

        
# ============================================
# ADD THIS NEW COMMAND AT THE END OF PART 4 (After +unroleall):
# ============================================

@bot.command(name='setstaffrole')
@is_owner_or_admin()
async def setstaffrole_cmd(ctx, role: discord.Role):
    """Set the staff role that can talk in locked channels"""
    Config.STAFF_ROLE_ID = role.id
    data_manager.save_data()
    
    embed = discord.Embed(
        title='✅ Staff Role Set',
        description=f'Staff role set to {role.mention}',
        color=discord.Color.green()
    )
    embed.add_field(
        name='Permissions',
        value='• Can send messages in locked channels\n'
              '• Can send messages during lockdown\n'
              '• Bypasses channel locks',
        inline=False
    )
    
    await ctx.send(embed=embed)
    await log_action(ctx.guild, '⚙️ Staff Role Configured', 
        f'Staff role set to {role.mention} by {ctx.author.mention}\nCan talk in locked channels',
        discord.Color.blue())

@bot.command(name='viewstaffrole')
async def viewstaffrole_cmd(ctx):
    """View the current staff role"""
    if not Config.STAFF_ROLE_ID:
        await ctx.send('❌ No staff role set! Use `+setstaffrole @role` to set one.')
        return
    
    staff_role = ctx.guild.get_role(Config.STAFF_ROLE_ID)
    if staff_role:
        embed = discord.Embed(
            title='👥 Staff Role',
            description=f'Current staff role: {staff_role.mention}',
            color=discord.Color.blue()
        )
        embed.add_field(name='Role ID', value=Config.STAFF_ROLE_ID, inline=True)
        embed.add_field(name='Members', value=len(staff_role.members), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send('❌ Staff role not found! It may have been deleted.')

@bot.command(name='removestaffrole')
@is_owner_or_admin()
async def removestaffrole_cmd(ctx):
    """Remove the staff role setting"""
    if not Config.STAFF_ROLE_ID:
        await ctx.send('❌ No staff role is set!')
        return
    
    Config.STAFF_ROLE_ID = None
    data_manager.save_data()
    
    await ctx.send('✅ Staff role removed. Locked channels will now be locked for everyone.')
    await log_action(ctx.guild, '🔴 Staff Role Removed',
        f'Staff role removed by {ctx.author.mention}',
        discord.Color.orange())

# ============================================
# HELP COMMANDS
# ============================================

@bot.command(name='help')
async def help_cmd(ctx):
    """Display all commands"""
    is_owner_user = ctx.author.id == Config.OWNER_ID
    is_admin = ctx.author.guild_permissions.administrator if ctx.guild else False
    
    embed = discord.Embed(
        title='🛡️ Security Bot Commands',
        description=f'Prefix: `{Config.PREFIX}` | Less strict automod enabled',
        color=discord.Color.blue()
    )
    
    if is_owner_user:
        embed.add_field(
            name='🔐 Verification (Slash)',
            value='`/setup_verification` - Setup system\n`/send_verification` - Send panel\n`/verify_user` - Manually verify',
            inline=False
        )
    
    if is_admin or is_owner_user:
        embed.add_field(
            name='⚙️ Moderation',
            value='`+kick` `+ban` `+unban` `+timeout` `+untimeout`\n`+warn` `+purge` `+slowmode` `+lock` `+unlock`',
            inline=False
        )
        
        embed.add_field(
            name='🛡️ Advanced Security',
            value='`+lockdown` `+unlockdown` `+antiraid`\n`+roleall` `+unroleall`',
            inline=False
        )
    
    if is_owner_user:
        embed.add_field(
            name='📋 Whitelist (Slash)',
            value='`/whitelist_add` `/whitelist_remove` `/whitelist_list`\n`/view_violations` `/clear_violations`',
            inline=False
        )
    
    embed.add_field(
        name='🔧 Utility',
        value='`+ping` `+serverinfo` `+userinfo` `+avatar`\n`+botinfo` `+status`',
        inline=False
    )
    
    embed.add_field(
        name='ℹ️ Auto Protection',
        value='✅ Anti-Nuke | ✅ Anti-Raid | ✅ Anti-Spam\n✅ Auto Verification | ✅ Staff can talk in locked channels',
        inline=False
    )
    
    embed.set_footer(text=f'Requested by {ctx.author}')
    await ctx.send(embed=embed)

@bot.tree.command(name="help_security", description="View all bot commands")
async def help_security(interaction: discord.Interaction):
    await interaction.response.send_message('📖 Use `+help` to see all commands!', ephemeral=True)

# ============================================
# UTILITY COMMANDS
# ============================================

@bot.command(name='ping')
async def ping_cmd(ctx):
    await ctx.send(f'🏓 Pong! `{round(bot.latency * 1000)}ms`')

@bot.command(name='serverinfo')
async def serverinfo_cmd(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f'📊 {guild.name}', color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name='Members', value=guild.member_count, inline=True)
    embed.add_field(name='Roles', value=len(guild.roles), inline=True)
    embed.add_field(name='Channels', value=len(guild.channels), inline=True)
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    await ctx.send(embed=embed)

@bot.command(name='userinfo')
async def userinfo_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f'👤 {member.name}', color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name='ID', value=member.id, inline=True)
    embed.add_field(name='Nickname', value=member.nick or 'None', inline=True)
    embed.add_field(name='Status', value=str(member.status), inline=True)
    embed.add_field(name='Joined', value=member.joined_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Created', value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Roles', value=f'{len(member.roles) - 1}', inline=True)
    await ctx.send(embed=embed)

@bot.command(name='avatar')
async def avatar_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f'🖼️ {member.display_name}\'s Avatar', color=member.color)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='botinfo')
async def botinfo_cmd(ctx):
    embed = discord.Embed(title=f'🤖 {bot.user.name}', description='Advanced Security Bot', color=discord.Color.blue())
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.add_field(name='Servers', value=len(bot.guilds), inline=True)
    embed.add_field(name='Users', value=len(bot.users), inline=True)
    embed.add_field(name='Prefix', value=Config.PREFIX, inline=True)
    embed.add_field(name='Latency', value=f'{round(bot.latency * 1000)}ms', inline=True)
    embed.add_field(name='Owner', value=f'<@{Config.OWNER_ID}>', inline=True)
    embed.add_field(name='24/7', value='✅ Render', inline=True)
    await ctx.send(embed=embed)

@bot.tree.command(name="security_status", description="View bot status (Owner only)")
@is_owner()
async def security_status(interaction: discord.Interaction):
    total_violations = sum(data_manager.user_violations.values())
    users_with_violations = len(data_manager.user_violations)
    
    embed = discord.Embed(title='🛡️ Security Bot Status', color=discord.Color.blue(), timestamp=datetime.utcnow())
    embed.add_field(name='Bot Status', value=f'✅ Online (24/7)\nLatency: {round(bot.latency * 1000)}ms\nServers: {len(bot.guilds)}', inline=True)
    embed.add_field(name='Protection', value='🛡️ Anti-Nuke\n🚫 Anti-Spam\n🔇 Automod\n🚨 Anti-Raid', inline=True)
    embed.add_field(name='Whitelist', value=f'{len(data_manager.whitelist)} users', inline=True)
    embed.add_field(name='Violations', value=f'Total: {total_violations}\nUsers: {users_with_violations}', inline=False)
    embed.add_field(name='Config', value=f'Spam: {Config.SPAM_THRESHOLD}msg/{Config.SPAM_TIMEFRAME}s\nProfanity: {Config.PROFANITY_TIMEOUT}min', inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# ERROR HANDLERS
# ============================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ You don\'t have permission!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Missing argument: `{error.param.name}`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Invalid argument!')
    else:
        print(f'Error: {error}')

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    await interaction.response.send_message(f'❌ Error: {str(error)}', ephemeral=True)
    print(f'Slash error: {error}')

# ============================================
# RENDER 24/7 KEEP-ALIVE WEB SERVER
# ============================================

async def start_keep_alive():
    from aiohttp import web
    
    async def health(request):
        return web.Response(text='Bot Online!', status=200)
    
    async def status_page(request):
        html = '<html><body style="background:#667eea;color:white;text-align:center;padding:50px;"><h1>Security Bot ONLINE</h1><p>Servers: ' + str(len(bot.guilds)) + '</p><p>Prefix: ' + Config.PREFIX + '</p></body></html>'
        return web.Response(text=html, content_type='text/html')
    
    app = web.Application()
    app.router.add_get('/', status_page)
    app.router.add_get('/health', health)
    app.router.add_get('/ping', health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Config.PORT)
    await site.start()
    print(f'Web server running on port {Config.PORT}')

async def main():
    await start_keep_alive()
    try:
        await bot.start(Config.TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        print(f'Bot error: {e}')
        await bot.close()

if __name__ == '__main__':
    print('=' * 70)
    print('DISCORD SECURITY BOT STARTING')
    print('=' * 70)
    print(f'Owner: {Config.OWNER_ID}')
    print(f'Prefix: {Config.PREFIX}')
    print(f'Port: {Config.PORT}')
    print('=' * 70)
    
    if not Config.TOKEN:
        print('ERROR: DISCORD_BOT_TOKEN not set!')
        print('Set it in Render Environment Variables')
        exit(1)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f'Failed to start: {e}')
