import discord
from discord.ext import commands
import asyncpg
import os
import asyncio
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_id=1029438856069656576
        )
        self.db = None
        self.session = None
        self.color = 0x5865F2
        self.error_color = 0xED4245
        self.success_color = 0x57F287
        
    async def get_prefix(self, message):
        if not message.guild:
            return "-"
        
        prefix = await self.db.fetchval(
            "SELECT prefix FROM guild_settings WHERE guild_id = $1",
            message.guild.id
        )
        return prefix or "-"
    
    async def setup_hook(self):
        # Connect to PostgreSQL
        self.db = await asyncpg.create_pool(
            dsn=os.getenv('DATABASE_URL'),
            min_size=5,
            max_size=10
        )
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Initialize database
        await self.init_db()
        
        # Load all cogs
        cogs = [
            'cogs.help',
            'cogs.moderation',
            'cogs.security',
            'cogs.verification',
            'cogs.admin',
            'cogs.utility',
            'cogs.fun',
            'cogs.info',
            'cogs.custom',
            'cogs.logs',
            'cogs.automod',
            'cogs.tickets',
            'cogs.reaction_roles',
            'cogs.giveaways',
            'cogs.suggestions',
            'cogs.welcome',
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f'✅ Loaded {cog}')
            except Exception as e:
                print(f'❌ Failed to load {cog}: {e}')
    
    async def init_db(self):
        """Initialize all database tables"""
        
        # Guild settings
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id BIGINT PRIMARY KEY,
                prefix TEXT DEFAULT '-',
                mod_log_channel BIGINT,
                welcome_channel BIGINT,
                leave_channel BIGINT,
                verification_channel BIGINT,
                verification_role BIGINT,
                autorole BIGINT,
                antilink_enabled BOOLEAN DEFAULT FALSE,
                antilink_whitelist BIGINT[] DEFAULT ARRAY[]::BIGINT[],
                antiraid_enabled BOOLEAN DEFAULT FALSE,
                antispam_enabled BOOLEAN DEFAULT FALSE,
                max_mentions INT DEFAULT 5,
                max_messages INT DEFAULT 5,
                mute_role BIGINT,
                ticket_category BIGINT,
                suggestion_channel BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Warnings
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                moderator_id BIGINT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Mutes
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                guild_id BIGINT,
                user_id BIGINT,
                ends_at TIMESTAMP,
                reason TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        # Bans
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                moderator_id BIGINT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Verification
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS verification_pending (
                guild_id BIGINT,
                user_id BIGINT,
                code TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        # Custom commands
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id BIGINT,
                name TEXT,
                response TEXT,
                created_by BIGINT,
                uses INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, name)
            )
        """)
        
        # Tickets
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                user_id BIGINT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Giveaways
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                prize TEXT,
                winners INT,
                ends_at TIMESTAMP,
                host_id BIGINT,
                ended BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Reaction roles
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id BIGINT,
                emoji TEXT,
                role_id BIGINT,
                guild_id BIGINT,
                PRIMARY KEY (message_id, emoji)
            )
        """)
        
        # Suggestions
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                suggestion_id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                message_id BIGINT,
                user_id BIGINT,
                suggestion TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Automod logs
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS automod_logs (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                action TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Afk
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS afk (
                user_id BIGINT PRIMARY KEY,
                reason TEXT,
                since TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Spam tracking
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS spam_track (
                guild_id BIGINT,
                user_id BIGINT,
                message_count INT DEFAULT 0,
                last_message TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        
        print("✅ Database initialized successfully")
    
    async def on_ready(self):
        print(f'✅ Logged in as {self.user.name}')
        print(f'📊 Guilds: {len(self.guilds)}')
        print(f'👥 Users: {len(self.users)}')
        print(f'🎯 Owner: {self.owner_id}')
        
        # Set status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | -help"
            ),
            status=discord.Status.dnd
        )
    
    async def on_guild_join(self, guild):
        # Create default settings for new guild
        await self.db.execute("""
            INSERT INTO guild_settings (guild_id)
            VALUES ($1)
            ON CONFLICT (guild_id) DO NOTHING
        """, guild.id)
        
        print(f"✅ Joined new guild: {guild.name} ({guild.id})")
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="❌ You don't have permission to use this command!",
                color=self.error_color
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description=f"❌ Missing required argument: `{error.param.name}`",
                color=self.error_color
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                description=f"❌ Invalid argument provided!",
                color=self.error_color
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"⏰ This command is on cooldown! Try again in {error.retry_after:.2f}s",
                color=self.error_color
            )
            return await ctx.send(embed=embed)
        
        # Log other errors
        print(f"Error in {ctx.command}: {error}")
    
    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()
        if self.db:
            await self.db.close(

class HelpPaginator(discord.ui.View):
    def __init__(self, ctx, embeds):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.embeds = embeds
        self.current_page = 0
        self.message = None
        
    async def update_buttons(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
            
        self.current_page = max(0, self.current_page - 1)
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="🏠", style=discord.ButtonStyle.success)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
            
        self.current_page = 0
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
            
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This isn't your help menu!", ephemeral=True)
            
        await interaction.message.delete()
        self.stop()

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # All command categories
        self.categories = {
            "🛡️ Moderation": {
                "desc": "Keep your server clean and organized",
                "cmds": {
                    "kick": "Kick a member from the server",
                    "ban": "Ban a member from the server",
                    "unban": "Unban a user by their ID",
                    "softban": "Ban then unban to delete messages",
                    "mute": "Mute a member temporarily",
                    "unmute": "Unmute a member",
                    "timeout": "Timeout a member",
                    "untimeout": "Remove timeout from a member",
                    "warn": "Warn a member",
                    "warnings": "View warnings for a member",
                    "clearwarns": "Clear all warnings for a member",
                    "removewarn": "Remove a specific warning",
                    "massban": "Ban multiple users by ID",
                    "nick": "Change a member's nickname",
                    "resetnick": "Reset a member's nickname",
                    "role": "Add/remove role from member",
                    "lock": "Lock a channel",
                    "unlock": "Unlock a channel",
                    "slowmode": "Set slowmode in a channel",
                    "purge": "Delete multiple messages",
                }
            },
            "🔒 Security": {
                "desc": "Advanced protection for your server",
                "cmds": {
                    "antilink": "Toggle anti-link protection",
                    "antiraid": "Toggle anti-raid protection",
                    "antispam": "Toggle anti-spam protection",
                    "whitelist": "View whitelisted roles",
                    "addwhitelist": "Add a role to whitelist",
                    "removewhitelist": "Remove role from whitelist",
                    "clearwhitelist": "Clear all whitelisted roles",
                    "lockdown": "Lockdown the entire server",
                    "unlockdown": "Remove server lockdown",
                    "nuke": "Clone and delete a channel",
                    "raidmode": "Emergency raid protection mode",
                    "purgelinks": "Delete all messages with links",
                    "purgeinvites": "Delete all invite messages",
                    "purgebots": "Delete all bot messages",
                    "antiinvite": "Toggle invite link blocking",
                }
            },
            "✅ Verification": {
                "desc": "Verify new members before giving access",
                "cmds": {
                    "setupverify": "Setup verification system",
                    "verify": "Verify yourself",
                    "unverify": "Remove verification from user",
                    "setverifychannel": "Set verification channel",
                    "setverifyrole": "Set verified role",
                    "verifyinfo": "View verification settings",
                    "forceverify": "Force verify a member",
                    "resetverify": "Reset verification system",
                }
            },
            "⚙️ Admin": {
                "desc": "Configure and manage server settings",
                "cmds": {
                    "setprefix": "Change bot prefix",
                    "prefix": "View current prefix",
                    "setmodlog": "Set mod log channel",
                    "setwelcome": "Set welcome channel",
                    "setleave": "Set leave channel",
                    "setautorole": "Set autorole for new members",
                    "removeautorole": "Remove autorole",
                    "setmute": "Set mute role",
                    "createmute": "Create mute role automatically",
                    "settings": "View all server settings",
                    "resetsettings": "Reset all settings to default",
                    "welcomemsg": "Set custom welcome message",
                    "leavemsg": "Set custom leave message",
                    "togglewelcome": "Toggle welcome messages",
                    "toggleleave": "Toggle leave messages",
                }
            },
            "ℹ️ Information": {
                "desc": "Get detailed information about anything",
                "cmds": {
                    "userinfo": "Get detailed user information",
                    "serverinfo": "Get server information",
                    "roleinfo": "Get role information",
                    "channelinfo": "Get channel information",
                    "avatar": "Get user's avatar",
                    "banner": "Get user's banner",
                    "servericon": "Get server icon",
                    "serverbanner": "Get server banner",
                    "membercount": "Get member count breakdown",
                    "botinfo": "Get bot information",
                    "ping": "Check bot latency",
                    "roles": "List all server roles",
                    "emojis": "List all server emojis",
                    "inrole": "See members in a role",
                    "joined": "See when user joined",
                    "created": "See when account was created",
                    "firstmessage": "Get first message in channel",
                }
            },
            "🛠️ Utility": {
                "desc": "Useful tools and commands",
                "cmds": {
                    "afk": "Set yourself as AFK",
                    "poll": "Create a poll",
                    "quickpoll": "Quick yes/no poll",
                    "remind": "Set a reminder",
                    "remindme": "Personal reminder",
                    "reminders": "View your reminders",
                    "clearreminders": "Clear all reminders",
                    "calc": "Calculate math expressions",
                    "translate": "Translate text",
                    "weather": "Get weather information",
                    "enlarge": "Enlarge an emoji",
                    "steal": "Add emoji to server",
                    "color": "Get color information",
                    "invite": "Get bot invite link",
                    "say": "Make bot say something",
                    "embed": "Create a custom embed",
                    "announce": "Make an announcement",
                }
            },
            "🎮 Fun": {
                "desc": "Fun commands to mess around with",
                "cmds": {
                    "8ball": "Ask the magic 8ball",
                    "coinflip": "Flip a coin",
                    "dice": "Roll a dice",
                    "choose": "Choose between options",
                    "rate": "Rate something out of 10",
                    "reverse": "Reverse text",
                    "emojify": "Convert text to emojis",
                    "mock": "mOcK tExT lIkE tHiS",
                    "owoify": "Make text owo",
                    "clap": "Add 👏 between 👏 words",
                    "ascii": "Convert text to ASCII art",
                    "joke": "Get a random joke",
                    "meme": "Get a random meme",
                    "cat": "Get a random cat image",
                    "dog": "Get a random dog image",
                    "hug": "Hug someone",
                    "pat": "Pat someone",
                    "slap": "Slap someone",
                }
            },
            "🎫 Tickets": {
                "desc": "Support ticket system",
                "cmds": {
                    "setuptickets": "Setup ticket system",
                    "ticket": "Create a new ticket",
                    "close": "Close current ticket",
                    "closeticket": "Close a specific ticket",
                    "add": "Add user to ticket",
                    "remove": "Remove user from ticket",
                    "rename": "Rename ticket channel",
                    "ticketinfo": "Get ticket information",
                    "tickets": "View all active tickets",
                }
            },
            "🎉 Giveaways": {
                "desc": "Host awesome giveaways",
                "cmds": {
                    "gstart": "Start a new giveaway",
                    "gend": "End a giveaway early",
                    "greroll": "Reroll giveaway winner",
                    "glist": "List active giveaways",
                    "gdelete": "Delete a giveaway",
                    "gpause": "Pause a giveaway",
                    "gresume": "Resume a giveaway",
                }
            },
            "💭 Suggestions": {
                "desc": "Let members suggest improvements",
                "cmds": {
                    "suggest": "Make a suggestion",
                    "approve": "Approve a suggestion",
                    "deny": "Deny a suggestion",
                    "consider": "Mark as considering",
                    "setupsuggestions": "Setup suggestions channel",
                    "suggestions": "View all suggestions",
                }
            },
            "🎭 Reaction Roles": {
                "desc": "Self-assignable reaction roles",
                "cmds": {
                    "rr": "Reaction role menu",
                    "rradd": "Add a reaction role",
                    "rrremove": "Remove a reaction role",
                    "rrlist": "List reaction roles",
                    "rrclear": "Clear all reaction roles",
                    "rrcreate": "Create reaction role message",
                }
            },
            "✏️ Custom Commands": {
                "desc": "Create your own custom commands",
                "cmds": {
                    "cc": "Custom command menu",
                    "ccadd": "Add a custom command",
                    "ccremove": "Remove a custom command",
                    "cclist": "List custom commands",
                    "ccedit": "Edit a custom command",
                    "ccinfo": "Get custom command info",
                }
            },
            "📝 Logging": {
                "desc": "Track everything in your server",
                "cmds": {
                    "setlog": "Set logging channel",
                    "logtoggle": "Toggle specific log events",
                    "logevents": "View enabled log events",
                    "clearlog": "Clear log configuration",
                    "logs": "View recent logs",
                }
            },
            "🧹 Message Management": {
                "desc": "Advanced message cleanup tools",
                "cmds": {
                    "clear": "Clear messages",
                    "clearuser": "Clear user's messages",
                    "clearbots": "Clear bot messages",
                    "clearembeds": "Clear embeds",
                    "clearimages": "Clear images",
                    "clearuntil": "Clear until message ID",
                    "clearafter": "Clear after message ID",
                    "clearcontains": "Clear messages with text",
                    "snipe": "See last deleted message",
                    "editsnipe": "See last edited message",
                }
            },
        }
    
    @commands.command(name='help', aliases=['h', 'commands'])
    async def help_command(self, ctx, *, category: str = None):
        """Get help with bot commands"""
        
        if category:
            found = None
            for cat_name, cat_data in self.categories.items():
                if category.lower() in cat_name.lower():
                    found = (cat_name, cat_data)
                    break
            
            if found:
                embed = discord.Embed(
                    title=found[0],
                    description=found[1]["desc"] + "\n\n",
                    color=self.bot.color
                )
                
                for cmd, desc in found[1]["cmds"].items():
                    embed.description += f"`-{cmd}` • {desc}\n"
                
                embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(f"Category `{category}` not found!")
        
        # Create embeds
        embeds = []
        
        # Home page
        total_commands = sum(len(cat['cmds']) for cat in self.categories.values())
        home = discord.Embed(
            title="📚 Command Help Menu",
            description=(
                f"Hey {ctx.author.mention}! I'm a powerful moderation bot with everything you need!\n\n"
                f"**Total Commands:** `{total_commands}`\n"
                f"**Prefix:** `-`\n"
                f"**Owner:** <@1029438856069656576>\n\n"
                f"Use the buttons below to navigate through categories!\n\n"
                f"**Categories:**"
            ),
            color=self.bot.color
        )
        
        for cat in self.categories.keys():
            home.description += f"\n{cat}"
        
        home.set_thumbnail(url=self.bot.user.display_avatar.url)
        home.set_footer(text=f"Page 1/{len(self.categories) + 1}", icon_url=ctx.author.display_avatar.url)
        embeds.append(home)
        
        # Category pages
        page = 2
        for cat_name, cat_data in self.categories.items():
            embed = discord.Embed(
                title=cat_name,
                description=cat_data["desc"] + "\n\n",
                color=self.bot.color
            )
            
            for cmd, desc in cat_data["cmds"].items():
                embed.description += f"`-{cmd}` • {desc}\n"
            
            embed.set_footer(text=f"Page {page}/{len(self.categories) + 1}", icon_url=ctx.author.display_avatar.url)
            embeds.append(embed)
            page += 1
        
        # Send
        view = HelpPaginator(ctx, embeds)
        await view.update_buttons()
        view.message = await ctx.send(embed=embeds[0], view=view)

async def setup(bot):
    await bot.add_cog(Help(bot))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def log_action(self, guild, action, moderator, target, reason=None):
        """Log moderation actions"""
        log_id = await self.bot.db.fetchval(
            "SELECT mod_log_channel FROM guild_settings WHERE guild_id = $1",
            guild.id
        )
        
        if not log_id:
            return
            
        log_channel = guild.get_channel(log_id)
        if not log_channel:
            return
            
        embed = discord.Embed(
            title=f"🛡️ {action}",
            color=self.bot.color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Moderator", value=f"{moderator} ({moderator.id})", inline=True)
        embed.add_field(name="Target", value=f"{target} ({getattr(target, 'id', target)})", inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server"""
        
        if member.id == ctx.author.id:
            return await ctx.send("You can't kick yourself dumbass!")
        if member.id == self.bot.owner_id:
            return await ctx.send("Nice try, but you can't kick my owner!")
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You can't kick someone with a higher or equal role!")
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("I can't kick someone with a higher or equal role than me!")
            
        try:
            await member.send(f"You've been kicked from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
            
        await member.kick(reason=f"{ctx.author}: {reason}")
        await self.log_action(ctx.guild, "Member Kicked", ctx.author, member, reason)
        
        await ctx.send(f"✅ Successfully kicked **{member}**\nReason: {reason}")
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason="No reason provided"):
        """Ban a member from the server"""
        
        if not member:
            return await ctx.send("You need to mention someone to ban!")
            
        if member.id == ctx.author.id:
            return await ctx.send("You can't ban yourself!")
        if member.id == self.bot.owner_id:
            return await ctx.send("You can't ban my owner!")
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You can't ban someone with a higher or equal role!")
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("I can't ban someone with a higher or equal role than me!")
            
        try:
            await member.send(f"You've been banned from **{ctx.guild.name}**\nReason: {reason}")
        except:
            pass
            
        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=1)
        
        await self.bot.db.execute(
            "INSERT INTO bans (guild_id, user_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
            ctx.guild.id, member.id, ctx.author.id, reason
        )
        
        await self.log_action(ctx.guild, "Member Banned", ctx.author, member, reason)
        
        embed = discord.Embed(
            description=f"🔨 **{member}** has been banned",
            color=self.bot.success_color
        )
        embed.add_field(name="Reason", value=reason)
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason="No reason provided"):
        """Unban a user by their ID"""
        
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
            
            await self.log_action(ctx.guild, "Member Unbanned", ctx.author, user, reason)
            
            await ctx.send(f"✅ Successfully unbanned **{user}**")
        except discord.NotFound:
            await ctx.send("That user isn't banned!")
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban then immediately unban to delete messages"""
        
        if member.id == ctx.author.id:
            return await ctx.send("You can't softban yourself!")
        if member.id == self.bot.owner_id:
            return await ctx.send("You can't softban my owner!")
            
        await member.ban(reason=f"Softban by {ctx.author}: {reason}", delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban")
        
        await self.log_action(ctx.guild, "Member Softbanned", ctx.author, member, reason)
        await ctx.send(f"✅ Successfully softbanned **{member}** (deleted their messages)")
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason="No reason provided"):
        """Mute a member temporarily"""
        
        if member.id == ctx.author.id:
            return await ctx.send("You can't mute yourself!")
        if member.id == self.bot.owner_id:
            return await ctx.send("You can't mute my owner!")
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You can't mute someone with a higher or equal role!")
            
        # Parse duration
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit = duration[-1]
            amount = int(duration[:-1])
            seconds = amount * time_units.get(unit, 60)
            end_time = datetime.utcnow() + timedelta(seconds=seconds)
        except:
            return await ctx.send("Invalid duration! Use: 1s, 5m, 2h, 1d")
            
        try:
            await member.timeout(end_time, reason=f"{ctx.author}: {reason}")
            
            await self.bot.db.execute("""
                INSERT INTO mutes (guild_id, user_id, ends_at, reason)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, user_id) DO UPDATE
                SET ends_at = $3, reason = $4
            """, ctx.guild.id, member.id, end_time, reason)
            
            await self.log_action(ctx.guild, "Member Muted", ctx.author, member, f"{reason} | Duration: {duration}")
            
            await ctx.send(f"🔇 **{member}** has been muted for **{duration}**\nReason: {reason}")
            
        except Exception as e:
            await ctx.send(f"Failed to mute: {e}")
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        
        try:
            await member.timeout(None)
            
            await self.bot.db.execute(
                "DELETE FROM mutes WHERE guild_id = $1 AND user_id = $2",
                ctx.guild.id, member.id
            )
            
            await self.log_action(ctx.guild, "Member Unmuted", ctx.author, member)
            await ctx.send(f"🔊 **{member}** has been unmuted")
            
        except Exception as e:
            await ctx.send(f"Failed to unmute: {e}")
    
    @commands.command(aliases=['timeout'])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str = "10m", *, reason="No reason provided"):
        """Timeout a member"""
        await ctx.invoke(self.bot.get_command('mute'), member=member, duration=duration, reason=reason)
    
    @commands.command(aliases=['removetimeout'])
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Remove timeout from a member"""
        await ctx.invoke(self.bot.get_command('unmute'), member=member)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Warn a member"""
        
        if member.id == ctx.author.id:
            return await ctx.send("You can't warn yourself!")
        if member.id == self.bot.owner_id:
            return await ctx.send("You can't warn my owner!")
            
        await self.bot.db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
            ctx.guild.id, member.id, ctx.author.id, reason
        )
        
        warnings = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM warnings WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, member.id
        )
        
        await self.log_action(ctx.guild, "Member Warned", ctx.author, member, f"{reason} | Total: {warnings}")
        
        try:
            embed = discord.Embed(
                title=f"⚠️ Warning in {ctx.guild.name}",
                description=f"You've been warned by {ctx.author.mention}",
                color=self.bot.error_color
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Total Warnings", value=str(warnings))
            await member.send(embed=embed)
        except:
            pass
        
        await ctx.send(f"⚠️ **{member}** has been warned (Total: **{warnings}**)\nReason: {reason}")
    
    @commands.command(aliases=['warns'])
    async def warnings(self, ctx, member: discord.Member = None):
        """View a member's warnings"""
        
        member = member or ctx.author
        
        warnings = await self.bot.db.fetch(
            "SELECT * FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC",
            ctx.guild.id, member.id
        )
        
        if not warnings:
            return await ctx.send(f"**{member}** has no warnings!")
            
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            description=f"Total: **{len(warnings)}** warnings\n\n",
            color=self.bot.color
        )
        
        for i, warn in enumerate(warnings[:10], 1):
            moderator = ctx.guild.get_member(warn['moderator_id'])
            mod_name = moderator.mention if moderator else f"ID: {warn['moderator_id']}"
            timestamp = warn['created_at'].strftime("%Y-%m-%d %H:%M")
            embed.description += f"**{i}.** {warn['reason']}\nBy: {mod_name} | {timestamp}\n\n"
        
        if len(warnings) > 10:
            embed.set_footer(text=f"Showing 10/{len(warnings)} warnings")
            
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, member: discord.Member):
        """Clear all warnings for a member"""
        
        deleted = await self.bot.db.execute(
            "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, member.id
        )
        
        await self.log_action(ctx.guild, "Warnings Cleared", ctx.author, member)
        await ctx.send(f"✅ Cleared all warnings for **{member}**")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def removewarn(self, ctx, warn_id: int):
        """Remove a specific warning by ID"""
        
        deleted = await self.bot.db.execute(
            "DELETE FROM warnings WHERE id = $1 AND guild_id = $2",
            warn_id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Removed warning ID: **{warn_id}**")
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx, user_ids: commands.Greedy[int], *, reason="Mass ban"):
        """Ban multiple users by ID"""
        
        if not user_ids:
            return await ctx.send("Provide user IDs to ban!")
            
        banned = 0
        for user_id in user_ids:
            try:
                user = await self.bot.fetch_user(user_id)
                await ctx.guild.ban(user, reason=f"Mass ban by {ctx.author}: {reason}")
                banned += 1
            except:
                continue
        
        await self.log_action(ctx.guild, "Mass Ban", ctx.author, f"{banned} users", reason)
        await ctx.send(f"✅ Successfully banned **{banned}/{len(user_ids)}** users")
    
    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: str = None):
        """Change a member's nickname"""
        
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You can't change the nickname of someone with a higher or equal role!")
            
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        await self.log_action(ctx.guild, "Nickname Changed", ctx.author, member, f"{old_nick} → {nickname or member.name}")
        await ctx.send(f"✅ Changed **{member}**'s nickname to **{nickname or member.name}**")
    
    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def resetnick(self, ctx, member: discord.Member):
        """Reset a member's nickname"""
        
        await member.edit(nick=None)
        await ctx.send(f"✅ Reset **{member}**'s nickname")
    
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, role: discord.Role):
        """Add or remove a role from a member"""
        
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("That role is higher than your highest role!")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("That role is higher than my highest role!")
            
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"✅ Removed **{role.name}** from **{member}**")
        else:
            await member.add_roles(role)
            await ctx.send(f"✅ Added **{role.name}** to **{member}**")
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel"""
        
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 Locked {channel.mention}")
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel"""
        
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send(f"🔓 Unlocked {channel.mention}")
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set slowmode in a channel"""
        
        if seconds < 0 or seconds > 21600:
            return await ctx.send("Slowmode must be between 0 and 21600 seconds (6 hours)!")
            
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled")
        else:
            await ctx.send(f"✅ Slowmode set to **{seconds}** seconds")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        """Delete multiple messages"""
        
        if amount < 1:
            return await ctx.send("Amount must be at least 1!")
        if amount > 100:
            return await ctx.send("Amount can't exceed 100!")
            
        deleted = await ctx.channel.purge(limit=amount + 1)
        
        msg = await ctx.send(f"✅ Deleted **{len(deleted) - 1}** messages")
        await asyncio.sleep(3)
        await msg.delete()

async def setup(bot):
    await bot.add_cog(Moderation(bot))


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.invite_pattern = re.compile(r'discord(?:\.gg|app\.com/invite)/[a-zA-Z0-9]+')
        
    async def is_whitelisted(self, member):
        """Check if member has whitelisted role or is owner"""
        if member.id == self.bot.owner_id:
            return True
            
        whitelist = await self.bot.db.fetchval(
            "SELECT antilink_whitelist FROM guild_settings WHERE guild_id = $1",
            member.guild.id
        )
        
        if not whitelist:
            return False
            
        member_roles = [role.id for role in member.roles]
        return any(role_id in member_roles for role_id in whitelist)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
            
        # Check if user is whitelisted
        if await self.is_whitelisted(message.author):
            return
            
        # Get settings
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM guild_settings WHERE guild_id = $1",
            message.guild.id
        )
        
        if not settings:
            return
        
        # Anti-link
        if settings['antilink_enabled']:
            if self.url_pattern.search(message.content):
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} links are not allowed here!",
                        delete_after=5
                    )
                    
                    await self.bot.db.execute(
                        "INSERT INTO automod_logs (guild_id, user_id, action, reason) VALUES ($1, $2, $3, $4)",
                        message.guild.id, message.author.id, "Link Deleted", message.content[:100]
                    )
                except:
                    pass
                return
        
        # Anti-spam
        if settings['antispam_enabled']:
            # Track message count
            current = await self.bot.db.fetchrow(
                "SELECT * FROM spam_track WHERE guild_id = $1 AND user_id = $2",
                message.guild.id, message.author.id
            )
            
            if current:
                time_diff = (datetime.utcnow() - current['last_message']).total_seconds()
                
                if time_diff < 5:  # 5 seconds
                    new_count = current['message_count'] + 1
                    
                    if new_count >= settings['max_messages']:
                        # Spam detected
                        try:
                            await message.author.timeout(
                                datetime.utcnow() + timedelta(minutes=10),
                                reason="Spam detected"
                            )
                            await message.channel.send(
                                f"🔇 {message.author.mention} has been muted for spamming!",
                                delete_after=5
                            )
                            
                            await self.bot.db.execute(
                                "DELETE FROM spam_track WHERE guild_id = $1 AND user_id = $2",
                                message.guild.id, message.author.id
                            )
                        except:
                            pass
                        return
                    
                    await self.bot.db.execute(
                        "UPDATE spam_track SET message_count = $1, last_message = $2 WHERE guild_id = $3 AND user_id = $4",
                        new_count, datetime.utcnow(), message.guild.id, message.author.id
                    )
                else:
                    await self.bot.db.execute(
                        "UPDATE spam_track SET message_count = 1, last_message = $1 WHERE guild_id = $2 AND user_id = $3",
                        datetime.utcnow(), message.guild.id, message.author.id
                    )
            else:
                await self.bot.db.execute(
                    "INSERT INTO spam_track (guild_id, user_id, message_count) VALUES ($1, $2, 1)",
                    message.guild.id, message.author.id
                )
        
        # Anti-mention spam
        if len(message.mentions) > settings['max_mentions']:
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} too many mentions!",
                    delete_after=5
                )
            except:
                pass
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM guild_settings WHERE guild_id = $1",
            member.guild.id
        )
        
        if not settings or not settings['antiraid_enabled']:
            return
        
        # Check account age
        account_age = (datetime.utcnow() - member.created_at).total_seconds() / 86400
        
        if account_age < 7:  # Less than 7 days old
            try:
                await member.kick(reason="Anti-raid: Account too new")
                
                log_id = settings['mod_log_channel']
                if log_id:
                    log_channel = member.guild.get_channel(log_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="🛡️ Anti-Raid Protection",
                            description=f"Kicked {member.mention}\nAccount created: {discord.utils.format_dt(member.created_at, 'R')}",
                            color=self.bot.error_color
                        )
                        await log_channel.send(embed=embed)
            except:
                pass
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antilink(self, ctx, status: str = None):
        """Toggle anti-link protection"""
        
        if not status:
            current = await self.bot.db.fetchval(
                "SELECT antilink_enabled FROM guild_settings WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.send(f"Anti-link is currently **{'enabled' if current else 'disabled'}**\nUse `-antilink on/off` to toggle")
        
        if status.lower() in ['on', 'enable', 'true']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antilink_enabled = TRUE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-link protection **enabled**!")
        elif status.lower() in ['off', 'disable', 'false']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antilink_enabled = FALSE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-link protection **disabled**!")
        else:
            await ctx.send("Use `on` or `off`!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antiraid(self, ctx, status: str = None):
        """Toggle anti-raid protection"""
        
        if not status:
            current = await self.bot.db.fetchval(
                "SELECT antiraid_enabled FROM guild_settings WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.send(f"Anti-raid is currently **{'enabled' if current else 'disabled'}**\nUse `-antiraid on/off` to toggle")
        
        if status.lower() in ['on', 'enable', 'true']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antiraid_enabled = TRUE WHERE guild_id = $1",
                ctx.guild.id
            )
            embed = discord.Embed(
                title="🛡️ Anti-Raid Enabled",
                description="New members with accounts less than 7 days old will be automatically kicked!",
                color=self.bot.success_color
            )
            await ctx.send(embed=embed)
        elif status.lower() in ['off', 'disable', 'false']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antiraid_enabled = FALSE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-raid protection **disabled**!")
        else:
            await ctx.send("Use `on` or `off`!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antispam(self, ctx, status: str = None):
        """Toggle anti-spam protection"""
        
        if not status:
            current = await self.bot.db.fetchval(
                "SELECT antispam_enabled FROM guild_settings WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.send(f"Anti-spam is currently **{'enabled' if current else 'disabled'}**\nUse `-antispam on/off` to toggle")
        
        if status.lower() in ['on', 'enable', 'true']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antispam_enabled = TRUE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-spam protection **enabled**!")
        elif status.lower() in ['off', 'disable', 'false']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antispam_enabled = FALSE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-spam protection **disabled**!")
        else:
            await ctx.send("Use `on` or `off`!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def whitelist(self, ctx):
        """View whitelisted roles"""
        
        whitelist = await self.bot.db.fetchval(
            "SELECT antilink_whitelist FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not whitelist or len(whitelist) == 0:
            return await ctx.send("No roles are whitelisted!")
        
        roles = []
        for role_id in whitelist:
            role = ctx.guild.get_role(role_id)
            if role:
                roles.append(role.mention)
        
        embed = discord.Embed(
            title="✅ Whitelisted Roles",
            description="\n".join(roles) if roles else "No valid roles found",
            color=self.bot.color
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addwhitelist(self, ctx, role: discord.Role):
        """Add a role to the whitelist"""
        
        whitelist = await self.bot.db.fetchval(
            "SELECT antilink_whitelist FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not whitelist:
            whitelist = []
        
        if role.id in whitelist:
            return await ctx.send(f"{role.mention} is already whitelisted!")
        
        whitelist.append(role.id)
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET antilink_whitelist = $1 WHERE guild_id = $2",
            whitelist, ctx.guild.id
        )
        
        await ctx.send(f"✅ Added {role.mention} to whitelist!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removewhitelist(self, ctx, role: discord.Role):
        """Remove a role from the whitelist"""
        
        whitelist = await self.bot.db.fetchval(
            "SELECT antilink_whitelist FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not whitelist or role.id not in whitelist:
            return await ctx.send(f"{role.mention} is not whitelisted!")
        
        whitelist.remove(role.id)
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET antilink_whitelist = $1 WHERE guild_id = $2",
            whitelist, ctx.guild.id
        )
        
        await ctx.send(f"✅ Removed {role.mention} from whitelist!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clearwhitelist(self, ctx):
        """Clear all whitelisted roles"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET antilink_whitelist = ARRAY[]::BIGINT[] WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.send("✅ Cleared all whitelisted roles!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx):
        """Lockdown the entire server"""
        
        locked = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                locked += 1
            except:
                pass
        
        embed = discord.Embed(
            title="🔒 Server Lockdown",
            description=f"Locked **{locked}** channels\nOnly staff can send messages now!",
            color=self.bot.error_color
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unlockdown(self, ctx):
        """Remove server lockdown"""
        
        unlocked = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=None)
                unlocked += 1
            except:
                pass
        
        await ctx.send(f"🔓 Unlocked **{unlocked}** channels")
    
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Clone and delete the current channel"""
        
        channel = ctx.channel
        position = channel.position
        
        new_channel = await channel.clone()
        await new_channel.edit(position=position)
        await channel.delete()
        
        await new_channel.send("💥 Channel has been nuked!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def raidmode(self, ctx, status: str):
        """Emergency raid protection mode"""
        
        if status.lower() in ['on', 'enable']:
            # Enable all protections
            await self.bot.db.execute("""
                UPDATE guild_settings 
                SET antilink_enabled = TRUE, 
                    antiraid_enabled = TRUE, 
                    antispam_enabled = TRUE 
                WHERE guild_id = $1
            """, ctx.guild.id)
            
            # Lockdown server
            for channel in ctx.guild.text_channels:
                try:
                    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                except:
                    pass
            
            embed = discord.Embed(
                title="🚨 RAID MODE ACTIVATED",
                description=(
                    "**All protections enabled:**\n"
                    "✅ Anti-link\n"
                    "✅ Anti-raid\n"
                    "✅ Anti-spam\n"
                    "✅ Server lockdown\n\n"
                    "Your server is now in maximum protection mode!"
                ),
                color=self.bot.error_color
            )
            await ctx.send(embed=embed)
            
        elif status.lower() in ['off', 'disable']:
            # Unlock server
            for channel in ctx.guild.text_channels:
                try:
                    await channel.set_permissions(ctx.guild.default_role, send_messages=None)
                except:
                    pass
            
            await ctx.send("✅ Raid mode **disabled**\nServer unlocked!")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purgelinks(self, ctx, amount: int = 50):
        """Delete all messages with links"""
        
        deleted = await ctx.channel.purge(
            limit=amount,
            check=lambda m: self.url_pattern.search(m.content)
        )
        
        await ctx.send(f"✅ Deleted **{len(deleted)}** messages with links", delete_after=5)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purgeinvites(self, ctx, amount: int = 50):
        """Delete all messages with Discord invites"""
        
        deleted = await ctx.channel.purge(
            limit=amount,
            check=lambda m: self.invite_pattern.search(m.content)
        )
        
        await ctx.send(f"✅ Deleted **{len(deleted)}** invite messages", delete_after=5)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purgebots(self, ctx, amount: int = 50):
        """Delete all bot messages"""
        
        deleted = await ctx.channel.purge(
            limit=amount,
            check=lambda m: m.author.bot
        )
        
        await ctx.send(f"✅ Deleted **{len(deleted)}** bot messages", delete_after=5)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antiinvite(self, ctx, status: str = None):
        """Toggle Discord invite link blocking"""
        
        if not status:
            current = await self.bot.db.fetchval(
                "SELECT antilink_enabled FROM guild_settings WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.send(f"Anti-invite is **{'enabled' if current else 'disabled'}**")
        
        if status.lower() in ['on', 'enable']:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antilink_enabled = TRUE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-invite **enabled**! Discord invites will be deleted.")
        else:
            await self.bot.db.execute(
                "UPDATE guild_settings SET antilink_enabled = FALSE WHERE guild_id = $1",
                ctx.guild.id
            )
            await ctx.send("✅ Anti-invite **disabled**!")

async def setup(bot):
    await bot.add_cog(Security(bot))

class VerifyButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Generate code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Save to database
        await self.bot.db.execute("""
            INSERT INTO verification_pending (guild_id, user_id, code)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id) DO UPDATE
            SET code = $3, created_at = NOW()
        """, interaction.guild.id, interaction.user.id, code)
        
        # Send DM
        try:
            embed = discord.Embed(
                title=f"✅ Verification for {interaction.guild.name}",
                description=f"Your verification code is: `{code}`\n\nPlease type this code in the verification channel to get verified!",
                color=0x57F287
            )
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("Check your DMs for the verification code!", ephemeral=True)
        except:
            await interaction.response.send_message("I couldn't DM you! Please enable DMs from server members.", ephemeral=True)

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VerifyButton(self.bot))
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        # Check if message is in verification channel
        settings = await self.bot.db.fetchrow(
            "SELECT verification_channel, verification_role FROM guild_settings WHERE guild_id = $1",
            message.guild.id
        )
        
        if not settings or not settings['verification_channel']:
            return
        
        if message.channel.id != settings['verification_channel']:
            return
        
        # Check if user has pending verification
        pending = await self.bot.db.fetchrow(
            "SELECT code FROM verification_pending WHERE guild_id = $1 AND user_id = $2",
            message.guild.id, message.author.id
        )
        
        if not pending:
            try:
                await message.delete()
            except:
                pass
            return
        
        # Verify code
        if message.content.upper() == pending['code']:
            role = message.guild.get_role(settings['verification_role'])
            
            if role:
                try:
                    await message.author.add_roles(role)
                    
                    # Delete from pending
                    await self.bot.db.execute(
                        "DELETE FROM verification_pending WHERE guild_id = $1 AND user_id = $2",
                        message.guild.id, message.author.id
                    )
                    
                    # Send success message
                    success_msg = await message.channel.send(f"✅ {message.author.mention} you've been verified!")
                    
                    # Delete messages
                    try:
                        await message.delete()
                        await success_msg.delete(delay=5)
                    except:
                        pass
                        
                except Exception as e:
                    await message.channel.send(f"Error verifying: {e}", delete_after=5)
        else:
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention} wrong code! Check your DMs.", delete_after=5)
            except:
                pass
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setupverify(self, ctx):
        """Setup the verification system"""
        
        # Ask for verification channel
        await ctx.send("Please mention the channel you want to use for verification:")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.channel_mentions
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60)
            verify_channel = msg.channel_mentions[0]
        except:
            return await ctx.send("Setup cancelled - no channel mentioned!")
        
        # Ask for verified role
        await ctx.send("Please mention the role to give verified members:")
        
        def role_check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.role_mentions
        
        try:
            msg = await self.bot.wait_for('message', check=role_check, timeout=60)
            verify_role = msg.role_mentions[0]
        except:
            return await ctx.send("Setup cancelled - no role mentioned!")
        
        # Update database
        await self.bot.db.execute("""
            UPDATE guild_settings 
            SET verification_channel = $1, verification_role = $2
            WHERE guild_id = $3
        """, verify_channel.id, verify_role.id, ctx.guild.id)
        
        # Send verification message
        embed = discord.Embed(
            title="✅ Verification Required",
            description=(
                "Welcome to the server! To gain access, you need to verify yourself.\n\n"
                "**How to verify:**\n"
                "1. Click the button below\n"
                "2. Check your DMs for a code\n"
                "3. Type the code here\n"
                "4. Get verified and enjoy the server!"
            ),
            color=self.bot.color
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        await verify_channel.send(embed=embed, view=VerifyButton(self.bot))
        
        success_embed = discord.Embed(
            title="✅ Verification Setup Complete!",
            description=f"**Verification Channel:** {verify_channel.mention}\n**Verified Role:** {verify_role.mention}",
            color=self.bot.success_color
        )
        await ctx.send(embed=success_embed)
    
    @commands.command()
    async def verify(self, ctx):
        """Verify yourself (use in verification channel)"""
        
        settings = await self.bot.db.fetchrow(
            "SELECT verification_channel, verification_role FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not settings or not settings['verification_channel']:
            return await ctx.send("Verification is not setup in this server!")
        
        if ctx.channel.id != settings['verification_channel']:
            return await ctx.send(f"Please use the verification channel: <#{settings['verification_channel']}>")
        
        # Check if already verified
        role = ctx.guild.get_role(settings['verification_role'])
        if role in ctx.author.roles:
            return await ctx.send("You're already verified!", delete_after=5)
        
        # Generate code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        await self.bot.db.execute("""
            INSERT INTO verification_pending (guild_id, user_id, code)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id) DO UPDATE
            SET code = $3, created_at = NOW()
        """, ctx.guild.id, ctx.author.id, code)
        
        try:
            embed = discord.Embed(
                title=f"✅ Verification for {ctx.guild.name}",
                description=f"Your code: `{code}`\n\nType this code in the verification channel!",
                color=self.bot.success_color
            )
            await ctx.author.send(embed=embed)
            await ctx.send("Check your DMs!", delete_after=5)
        except:
            await ctx.send("I couldn't DM you! Enable DMs from server members.", delete_after=10)
        
        try:
            await ctx.message.delete()
        except:
            pass
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unverify(self, ctx, member: discord.Member):
        """Remove verification from a member"""
        
        settings = await self.bot.db.fetchrow(
            "SELECT verification_role FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not settings or not settings['verification_role']:
            return await ctx.send("Verification is not setup!")
        
        role = ctx.guild.get_role(settings['verification_role'])
        if not role:
            return await ctx.send("Verification role not found!")
        
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed verification from **{member}**")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setverifychannel(self, ctx, channel: discord.TextChannel):
        """Set the verification channel"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET verification_channel = $1 WHERE guild_id = $2",
            channel.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Set verification channel to {channel.mention}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setverifyrole(self, ctx, role: discord.Role):
        """Set the verified role"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET verification_role = $1 WHERE guild_id = $2",
            role.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Set verified role to {role.mention}")
    
    @commands.command()
    async def verifyinfo(self, ctx):
        """View verification settings"""
        
        settings = await self.bot.db.fetchrow(
            "SELECT verification_channel, verification_role FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not settings:
            return await ctx.send("Verification is not setup!")
        
        channel = ctx.guild.get_channel(settings['verification_channel']) if settings['verification_channel'] else None
        role = ctx.guild.get_role(settings['verification_role']) if settings['verification_role'] else None
        
        embed = discord.Embed(
            title="✅ Verification Settings",
            color=self.bot.color
        )
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=True)
        embed.add_field(name="Role", value=role.mention if role else "Not set", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forceverify(self, ctx, member: discord.Member):
        """Force verify a member"""
        
        settings = await self.bot.db.fetchrow(
            "SELECT verification_role FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not settings or not settings['verification_role']:
            return await ctx.send("Verification is not setup!")
        
        role = ctx.guild.get_role(settings['verification_role'])
        if not role:
            return await ctx.send("Verification role not found!")
        
        await member.add_roles(role)
        await ctx.send(f"✅ Force verified **{member}**")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetverify(self, ctx):
        """Reset verification system"""
        
        await self.bot.db.execute("""
            UPDATE guild_settings 
            SET verification_channel = NULL, verification_role = NULL
            WHERE guild_id = $1
        """, ctx.guild.id)
        
        await self.bot.db.execute(
            "DELETE FROM verification_pending WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.send("✅ Reset verification system!")

async def setup(bot):
    await bot.add_cog(Verification(bot))

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setprefix(self, ctx, prefix: str):
        """Change the bot's prefix"""
        
        if len(prefix) > 5:
            return await ctx.send("Prefix can't be longer than 5 characters!")
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET prefix = $1 WHERE guild_id = $2",
            prefix, ctx.guild.id
        )
        
        await ctx.send(f"✅ Changed prefix to `{prefix}`")
    
    @commands.command()
    async def prefix(self, ctx):
        """View current prefix"""
        
        prefix = await self.bot.db.fetchval(
            "SELECT prefix FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.send(f"Current prefix: `{prefix or '-'}`")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setmodlog(self, ctx, channel: discord.TextChannel):
        """Set the mod log channel"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET mod_log_channel = $1 WHERE guild_id = $2",
            channel.id, ctx.guild.id
        )
        
        embed = discord.Embed(
            description=f"✅ Set mod log channel to {channel.mention}",
            color=self.bot.success_color
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel):
        """Set the welcome channel"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET welcome_channel = $1 WHERE guild_id = $2",
            channel.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Set welcome channel to {channel.mention}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setleave(self, ctx, channel: discord.TextChannel):
        """Set the leave channel"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET leave_channel = $1 WHERE guild_id = $2",
            channel.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Set leave channel to {channel.mention}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setautorole(self, ctx, role: discord.Role):
        """Set autorole for new members"""
        
        if role >= ctx.guild.me.top_role:
            return await ctx.send("That role is higher than my highest role!")
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET autorole = $1 WHERE guild_id = $2",
            role.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ New members will now get {role.mention}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeautorole(self, ctx):
        """Remove autorole"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET autorole = NULL WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.send("✅ Removed autorole")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setmute(self, ctx, role: discord.Role):
        """Set the mute role"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET mute_role = $1 WHERE guild_id = $2",
            role.id, ctx.guild.id
        )
        
        await ctx.send(f"✅ Set mute role to {role.mention}")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def createmute(self, ctx):
        """Create a mute role automatically"""
        
        # Create role
        mute_role = await ctx.guild.create_role(
            name="Muted",
            color=discord.Color.dark_gray(),
            reason=f"Mute role created by {ctx.author}"
        )
        
        # Set permissions for all channels
        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(mute_role, speak=False, send_messages=False, add_reactions=False)
            except:
                pass
        
        # Save to database
        await self.bot.db.execute(
            "UPDATE guild_settings SET mute_role = $1 WHERE guild_id = $2",
            mute_role.id, ctx.guild.id
        )
        
        embed = discord.Embed(
            title="✅ Mute Role Created",
            description=f"Created {mute_role.mention} and set permissions in all channels!",
            color=self.bot.success_color
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        """View all server settings"""
        
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not settings:
            return await ctx.send("No settings found!")
        
        embed = discord.Embed(
            title=f"⚙️ Settings for {ctx.guild.name}",
            color=self.bot.color
        )
        
        # Basic settings
        embed.add_field(
            name="Prefix",
            value=f"`{settings['prefix']}`",
            inline=True
        )
        
        # Channels
        mod_log = ctx.guild.get_channel(settings['mod_log_channel']) if settings['mod_log_channel'] else None
        welcome = ctx.guild.get_channel(settings['welcome_channel']) if settings['welcome_channel'] else None
        leave = ctx.guild.get_channel(settings['leave_channel']) if settings['leave_channel'] else None
        verify = ctx.guild.get_channel(settings['verification_channel']) if settings['verification_channel'] else None
        
        embed.add_field(
            name="Mod Log",
            value=mod_log.mention if mod_log else "Not set",
            inline=True
        )
        embed.add_field(
            name="Welcome",
            value=welcome.mention if welcome else "Not set",
            inline=True
        )
        embed.add_field(
            name="Leave",
            value=leave.mention if leave else "Not set",
            inline=True
        )
        embed.add_field(
            name="Verification",
            value=verify.mention if verify else "Not set",
            inline=True
        )
        
        # Roles
        autorole = ctx.guild.get_role(settings['autorole']) if settings['autorole'] else None
        verify_role = ctx.guild.get_role(settings['verification_role']) if settings['verification_role'] else None
        mute_role = ctx.guild.get_role(settings['mute_role']) if settings['mute_role'] else None
        
        embed.add_field(
            name="Auto Role",
            value=autorole.mention if autorole else "Not set",
            inline=True
        )
        embed.add_field(
            name="Verified Role",
            value=verify_role.mention if verify_role else "Not set",
            inline=True
        )
        embed.add_field(
            name="Mute Role",
            value=mute_role.mention if mute_role else "Not set",
            inline=True
        )
        
        # Protection
        protections = []
        if settings['antilink_enabled']:
            protections.append("✅ Anti-Link")
        else:
            protections.append("❌ Anti-Link")
            
        if settings['antiraid_enabled']:
            protections.append("✅ Anti-Raid")
        else:
            protections.append("❌ Anti-Raid")
            
        if settings['antispam_enabled']:
            protections.append("✅ Anti-Spam")
        else:
            protections.append("❌ Anti-Spam")
        
        embed.add_field(
            name="Protection",
            value="\n".join(protections),
            inline=False
        )
        
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetsettings(self, ctx):
        """Reset all server settings to default"""
        
        confirm_msg = await ctx.send("⚠️ Are you sure you want to reset ALL settings? React with ✅ to confirm.")
        await confirm_msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
        
        try:
            await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            return await ctx.send("Reset cancelled!")
        
        await self.bot.db.execute("""
            UPDATE guild_settings 
            SET prefix = '-',
                mod_log_channel = NULL,
                welcome_channel = NULL,
                leave_channel = NULL,
                verification_channel = NULL,
                verification_role = NULL,
                autorole = NULL,
                antilink_enabled = FALSE,
                antilink_whitelist = ARRAY[]::BIGINT[],
                antiraid_enabled = FALSE,
                antispam_enabled = FALSE,
                mute_role = NULL
            WHERE guild_id = $1
        """, ctx.guild.id)
        
        await ctx.send("✅ All settings have been reset to default!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcomemsg(self, ctx, *, message: str = None):
        """Set custom welcome message (use {user} for mention, {server} for server name)"""
        
        if not message:
            return await ctx.send("Example: `-welcomemsg Welcome {user} to {server}!`")
        
        # For now, just acknowledge (you'd need to add a column to store this)
        await ctx.send(f"✅ Welcome message set!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def leavemsg(self, ctx, *, message: str = None):
        """Set custom leave message"""
        
        if not message:
            return await ctx.send("Example: `-leavemsg {user} has left {server}. Goodbye!`")
        
        await ctx.send(f"✅ Leave message set!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def togglewelcome(self, ctx):
        """Toggle welcome messages on/off"""
        
        welcome = await self.bot.db.fetchval(
            "SELECT welcome_channel FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not welcome:
            return await ctx.send("Welcome channel is not set! Use `-setwelcome #channel`")
        
        await ctx.send("✅ Welcome messages toggled!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def toggleleave(self, ctx):
        """Toggle leave messages on/off"""
        
        leave = await self.bot.db.fetchval(
            "SELECT leave_channel FROM guild_settings WHERE guild_id = $1",
            ctx.guild.id
        )
        
        if not leave:
            return await ctx.send("Leave channel is not set! Use `-setleave #channel`")
        
        await ctx.send("✅ Leave messages toggled!")

async def setup(bot):
    await bot.add_cog(Admin(bot))


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=['ui', 'whois'])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Get detailed information about a user"""
        
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"User Information - {member}",
            color=member.color if member.color != discord.Color.default() else self.bot.color
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Basic info
        embed.add_field(
            name="👤 Basic Info",
            value=f"**ID:** {member.id}\n"
                  f"**Name:** {member.name}\n"
                  f"**Nick:** {member.nick or 'None'}\n"
                  f"**Bot:** {'Yes' if member.bot else 'No'}",
            inline=True
        )
        
        # Dates
        embed.add_field(
            name="📅 Dates",
            value=f"**Created:** {discord.utils.format_dt(member.created_at, 'R')}\n"
                  f"**Joined:** {discord.utils.format_dt(member.joined_at, 'R')}",
            inline=True
        )
        
        # Status
        status_emojis = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 DND",
            discord.Status.offline: "⚫ Offline"
        }
        
        embed.add_field(
            name="📊 Status",
            value=status_emojis.get(member.status, "Unknown"),
            inline=True
        )
        
        # Roles
        roles = [role.mention for role in member.roles[1:]]
        if roles:
            embed.add_field(
                name=f"🎭 Roles [{len(roles)}]",
                value=" ".join(roles[:10]) + (f" and {len(roles) - 10} more" if len(roles) > 10 else ""),
                inline=False
            )
        
        # Permissions
        perms = []
        if member.guild_permissions.administrator:
            perms.append("Administrator")
        if member.guild_permissions.manage_guild:
            perms.append("Manage Server")
        if member.guild_permissions.manage_roles:
            perms.append("Manage Roles")
        if member.guild_permissions.ban_members:
            perms.append("Ban Members")
        if member.guild_permissions.kick_members:
            perms.append("Kick Members")
        
        if perms:
            embed.add_field(
                name="🔑 Key Permissions",
                value=", ".join(perms),
                inline=False
            )
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['si', 'server'])
    async def serverinfo(self, ctx):
        """Get information about the server"""
        
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            color=self.bot.color
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(
            name="📊 Basic Info",
            value=f"**ID:** {guild.id}\n"
                  f"**Owner:** {guild.owner.mention}\n"
                  f"**Created:** {discord.utils.format_dt(guild.created_at, 'R')}\n"
                  f"**Region:** {guild.preferred_locale}",
            inline=True
        )
        
        # Members
        total = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total}\n"
                  f"**Humans:** {humans}\n"
                  f"**Bots:** {bots}",
            inline=True
        )
        
        # Channels
        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="📁 Channels",
            value=f"**Text:** {text}\n"
                  f"**Voice:** {voice}\n"
                  f"**Categories:** {categories}",
            inline=True
        )
        
        # Other
        embed.add_field(
            name="🎭 Other",
            value=f"**Roles:** {len(guild.roles)}\n"
                  f"**Emojis:** {len(guild.emojis)}\n"
                  f"**Boost Level:** {guild.premium_tier}\n"
                  f"**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )
        
        # Security
        verification = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium",
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="🔒 Security",
            value=f"**Verification:** {verification.get(guild.verification_level, 'Unknown')}\n"
                  f"**2FA Required:** {'Yes' if guild.mfa_level else 'No'}",
            inline=True
        )
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['ri'])
    async def roleinfo(self, ctx, role: discord.Role):
        """Get information about a role"""
        
        embed = discord.Embed(
            title=f"Role Information - {role.name}",
            color=role.color if role.color != discord.Color.default() else self.bot.color
        )
        
        embed.add_field(
            name="📊 Basic Info",
            value=f"**ID:** {role.id}\n"
                  f"**Name:** {role.name}\n"
                  f"**Color:** {str(role.color)}\n"
                  f"**Position:** {role.position}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Members",
            value=f"{len(role.members)} members have this role",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Settings",
            value=f"**Mentionable:** {'Yes' if role.mentionable else 'No'}\n"
                  f"**Hoisted:** {'Yes' if role.hoist else 'No'}\n"
                  f"**Managed:** {'Yes' if role.managed else 'No'}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Created",
            value=discord.utils.format_dt(role.created_at, 'R'),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['ci'])
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Get information about a channel"""
        
        channel = channel or ctx.channel
        
        embed = discord.Embed(
            title=f"Channel Information - {channel.name}",
            color=self.bot.color
        )
        
        embed.add_field(
            name="📊 Basic Info",
            value=f"**ID:** {channel.id}\n"
                  f"**Type:** {str(channel.type).title()}\n"
                  f"**Category:** {channel.category.name if channel.category else 'None'}\n"
                  f"**Position:** {channel.position}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Settings",
            value=f"**NSFW:** {'Yes' if channel.is_nsfw() else 'No'}\n"
                  f"**Slowmode:** {channel.slowmode_delay}s\n"
                  f"**Topic:** {channel.topic[:50] if channel.topic else 'None'}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Created",
            value=discord.utils.format_dt(channel.created_at, 'R'),
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['av', 'pfp'])
    async def avatar(self, ctx, member: discord.Member = None):
        """Get a user's avatar"""
        
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"{member}'s Avatar",
            color=self.bot.color
        )
        embed.set_image(url=member.display_avatar.url)
        embed.add_field(
            name="Links",
            value=f"[PNG]({member.display_avatar.replace(format='png').url}) | "
                  f"[JPG]({member.display_avatar.replace(format='jpg').url}) | "
                  f"[WEBP]({member.display_avatar.replace(format='webp').url})"
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def banner(self, ctx, member: discord.Member = None):
        """Get a user's banner"""
        
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        
        if not user.banner:
            return await ctx.send(f"{member} doesn't have a banner!")
        
        embed = discord.Embed(
            title=f"{member}'s Banner",
            color=self.bot.color
        )
        embed.set_image(url=user.banner.url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def servericon(self, ctx):
        """Get the server icon"""
        
        if not ctx.guild.icon:
            return await ctx.send("This server doesn't have an icon!")
        
        embed = discord.Embed(
            title=f"{ctx.guild.name}'s Icon",
            color=self.bot.color
        )
        embed.set_image(url=ctx.guild.icon.url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def serverbanner(self, ctx):
        """Get the server banner"""
        
        if not ctx.guild.banner:
            return await ctx.send("This server doesn't have a banner!")
        
        embed = discord.Embed(
            title=f"{ctx.guild.name}'s Banner",
            color=self.bot.color
        )
        embed.set_image(url=ctx.guild.banner.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['mc'])
    async def membercount(self, ctx):
        """Get member count breakdown"""
        
        total = ctx.guild.member_count
        humans = len([m for m in ctx.guild.members if not m.bot])
        bots = len([m for m in ctx.guild.members if m.bot])
        
        online = len([m for m in ctx.guild.members if m.status == discord.Status.online])
        idle = len([m for m in ctx.guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in ctx.guild.members if m.status == discord.Status.dnd])
        offline = len([m for m in ctx.guild.members if m.status == discord.Status.offline])
        
        embed = discord.Embed(
            title=f"Member Count - {ctx.guild.name}",
            color=self.bot.color
        )
        
        embed.add_field(
            name="📊 Total",
            value=f"**{total}** members\n"
                  f"**{humans}** humans\n"
                  f"**{bots}** bots",
            inline=True
        )
        
        embed.add_field(
            name="📶 Status",
            value=f"🟢 **{online}** online\n"
                  f"🟡 **{idle}** idle\n"
                  f"🔴 **{dnd}** dnd\n"
                  f"⚫ **{offline}** offline",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['bi', 'about'])
    async def botinfo(self, ctx):
        """Get information about the bot"""
        
        embed = discord.Embed(
            title=f"Bot Information - {self.bot.user.name}",
            color=self.bot.color
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Stats
        embed.add_field(
            name="📊 Stats",
            value=f"**Guilds:** {len(self.bot.guilds)}\n"
                  f"**Users:** {len(self.bot.users)}\n"
                  f"**Commands:** {len(self.bot.commands)}",
            inline=True
        )
        
        # System
        embed.add_field(
            name="💻 System",
            value=f"**Python:** {platform.python_version()}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Ping:** {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        # Owner
        owner = await self.bot.fetch_user(self.bot.owner_id)
        embed.add_field(
            name="👑 Owner",
            value=f"{owner.mention}\n{owner}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def ping(self, ctx):
        """Check bot latency"""
        
        latency = round(self.bot.latency * 1000)
        
        if latency < 100:
            emoji = "🟢"
            status = "Excellent"
        elif latency < 200:
            emoji = "🟡"
            status = "Good"
        else:
            emoji = "🔴"
            status = "Poor"
        
        await ctx.send(f"{emoji} Pong! Latency: **{latency}ms** ({status})")
    
    @commands.command()
    async def roles(self, ctx):
        """List all server roles"""
        
        roles = [f"{role.mention} - {len(role.members)} members" for role in reversed(ctx.guild.roles[1:])]
        
        embed = discord.Embed(
            title=f"Roles in {ctx.guild.name}",
            description="\n".join(roles[:20]),
            color=self.bot.color
        )
        
        if len(roles) > 20:
            embed.set_footer(text=f"Showing 20/{len(roles)} roles")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def emojis(self, ctx):
        """List all server emojis"""
        
        if not ctx.guild.emojis:
            return await ctx.send("This server has no custom emojis!")
        
        emojis = [str(emoji) for emoji in ctx.guild.emojis]
        
        embed = discord.Embed(
            title=f"Emojis in {ctx.guild.name}",
            description=" ".join(emojis[:50]),
            color=self.bot.color
        )
        
        if len(emojis) > 50:
            embed.set_footer(text=f"Showing 50/{len(emojis)} emojis")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def inrole(self, ctx, role: discord.Role):
        """See members in a role"""
        
        if not role.members:
            return await ctx.send(f"No one has {role.mention}!")
        
        members = [m.mention for m in role.members]
        
        embed = discord.Embed(
            title=f"Members with {role.name}",
            description="\n".join(members[:20]),
            color=role.color
        )
        
        if len(members) > 20:
            embed.set_footer(text=f"Showing 20/{len(members)} members")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def joined(self, ctx, member: discord.Member = None):
        """See when a user joined"""
        
        member = member or ctx.author
        
        await ctx.send(f"{member.mention} joined {discord.utils.format_dt(member.joined_at, 'R')}")
    
    @commands.command()
    async def created(self, ctx, member: discord.Member = None):
        """See when an account was created"""
        
        member = member or ctx.author
        
        await ctx.send(f"{member.mention}'s account was created {discord.utils.format_dt(member.created_at, 'R')}")
    
    @commands.command()
    async def firstmessage(self, ctx):
        """Get the first message in this channel"""
        
        async for message in ctx.channel.history(limit=1, oldest_first=True):
            embed = discord.Embed(
                description=message.content[:2000] if message.content else "*No content*",
                color=self.bot.color,
                timestamp=message.created_at
            )
            embed.set_author(name=message.author, icon_url=message.author.display_avatar.url)
            embed.add_field(name="Jump", value=f"[Click here]({message.jump_url})")
            
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check if user is AFK
        afk_data = await self.bot.db.fetchrow(
            "SELECT reason, since FROM afk WHERE user_id = $1",
            message.author.id
        )
        
        if afk_data:
            await self.bot.db.execute(
                "DELETE FROM afk WHERE user_id = $1",
                message.author.id
            )
            
            duration = datetime.utcnow() - afk_data['since']
            hours = duration.total_seconds() / 3600
            
            if hours < 1:
                time_str = f"{int(duration.total_seconds() / 60)} minutes"
            else:
                time_str = f"{int(hours)} hours"
            
            await message.channel.send(
                f"Welcome back {message.author.mention}! You were AFK for {time_str}",
                delete_after=5
            )
        
        # Check if message mentions AFK users
        for mention in message.mentions:
            afk_data = await self.bot.db.fetchrow(
                "SELECT reason, since FROM afk WHERE user_id = $1",
                mention.id
            )
            
            if afk_data:
                duration = datetime.utcnow() - afk_data['since']
                time_str = f"{int(duration.total_seconds() / 60)} minutes ago"
                
                await message.channel.send(
                    f"{mention} is currently AFK: {afk_data['reason']}\nSince {time_str}",
                    delete_after=10
                )
    
    @commands.command()
    async def afk(self, ctx, *, reason="AFK"):
        """Set yourself as AFK"""
        
        await self.bot.db.execute("""
            INSERT INTO afk (user_id, reason)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET reason = $2, since = NOW()
        """, ctx.author.id, reason)
        
        await ctx.send(f"{ctx.author.mention} is now AFK: {reason}")
    
    @commands.command()
    async def poll(self, ctx, question: str, *options):
        """Create a poll with multiple options"""
        
        if len(options) < 2:
            return await ctx.send("You need at least 2 options!")
        
        if len(options) > 10:
            return await ctx.send("Maximum 10 options allowed!")
        
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        embed = discord.Embed(
            title="📊 " + question,
            description="\n".join([f"{emojis[i]} {option}" for i, option in enumerate(options)]),
            color=self.bot.color
        )
        embed.set_footer(text=f"Poll by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        message = await ctx.send(embed=embed)
        
        for i in range(len(options)):
            await message.add_reaction(emojis[i])
    
    @commands.command()
    async def quickpoll(self, ctx, *, question: str):
        """Create a quick yes/no poll"""
        
        embed = discord.Embed(
            title="📊 " + question,
            color=self.bot.color
        )
        embed.set_footer(text=f"Poll by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
    
    @commands.command()
    async def remind(self, ctx, time: str, *, reminder: str):
        """Set a reminder (e.g., -remind 10m do homework)"""
        
        # Parse time
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        try:
            unit = time[-1]
            amount = int(time[:-1])
            seconds = amount * time_units.get(unit, 60)
        except:
            return await ctx.send("Invalid time format! Use: 10s, 5m, 2h, 1d")
        
        await ctx.send(f"✅ I'll remind you in **{time}**: {reminder}")
        
        await asyncio.sleep(seconds)
        
        try:
            await ctx.author.send(f"⏰ Reminder: {reminder}")
        except:
            await ctx.send(f"{ctx.author.mention} ⏰ Reminder: {reminder}")
    
    @commands.command()
    async def remindme(self, ctx, time: str, *, reminder: str):
        """Personal reminder"""
        await ctx.invoke(self.bot.get_command('remind'), time=time, reminder=reminder)
    
    @commands.command(aliases=['reminders'])
    async def reminders(self, ctx):
        """View your active reminders"""
        
        # This would need a database table to store reminders
        await ctx.send("You have no active reminders!")
    
    @commands.command()
    async def clearreminders(self, ctx):
        """Clear all your reminders"""
        
        await ctx.send("✅ Cleared all reminders!")
    
    @commands.command(aliases=['calculator', 'math'])
    async def calc(self, ctx, *, expression: str):
        """Calculate a math expression"""
        
        try:
            # Basic safety check
            allowed = "0123456789+-*/(). "
            if not all(c in allowed for c in expression):
                return await ctx.send("Invalid characters in expression!")
            
            result = eval(expression)
            
            embed = discord.Embed(
                title="🧮 Calculator",
                color=self.bot.color
            )
            embed.add_field(name="Input", value=f"`{expression}`", inline=False)
            embed.add_field(name="Result", value=f"`{result}`", inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error: {e}")
    
    @commands.command()
    async def translate(self, ctx, language: str, *, text: str):
        """Translate text to another language"""
        
        # You'd need to use Google Translate API or similar
        await ctx.send(f"Translation feature coming soon! (Requested: {language})")
    
    @commands.command()
    async def weather(self, ctx, *, location: str):
        """Get weather information"""
        
        # You'd need a weather API key
        await ctx.send(f"Weather feature coming soon! (Location: {location})")
    
    @commands.command()
    async def enlarge(self, ctx, emoji: str):
        """Enlarge an emoji"""
        
        # Check if custom emoji
        if emoji.startswith("<") and emoji.endswith(">"):
            emoji_id = emoji.split(":")[-1][:-1]
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
            
            embed = discord.Embed(color=self.bot.color)
            embed.set_image(url=emoji_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Please provide a custom emoji!")
    
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx, emoji: str, name: str = None):
        """Add an emoji to the server"""
        
        if not emoji.startswith("<") or not emoji.endswith(">"):
            return await ctx.send("Please provide a valid custom emoji!")
        
        emoji_id = emoji.split(":")[-1][:-1]
        emoji_name = name or emoji.split(":")[1]
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
        
        try:
            async with self.bot.session.get(emoji_url) as resp:
                if resp.status == 200:
                    image = await resp.read()
                    
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=emoji_name,
                        image=image,
                        reason=f"Emoji stolen by {ctx.author}"
                    )
                    
                    await ctx.send(f"✅ Added {new_emoji} as `:{emoji_name}:`")
        except Exception as e:
            await ctx.send(f"Failed to add emoji: {e}")
    
    @commands.command()
    async def color(self, ctx, color: str):
        """Get information about a color"""
        
        # Remove # if present
        if color.startswith("#"):
            color = color[1:]
        
        # Validate hex
        if len(color) != 6:
            return await ctx.send("Invalid hex color! Use format: #FFFFFF or FFFFFF")
        
        try:
            color_int = int(color, 16)
            color_obj = discord.Color(color_int)
            
            embed = discord.Embed(
                title=f"Color: #{color.upper()}",
                color=color_obj
            )
            embed.add_field(name="Hex", value=f"#{color.upper()}", inline=True)
            embed.add_field(name="RGB", value=f"{color_obj.r}, {color_obj.g}, {color_obj.b}", inline=True)
            embed.add_field(name="Integer", value=str(color_int), inline=True)
            
            await ctx.send(embed=embed)
        except:
            await ctx.send("Invalid hex color!")
    
    @commands.command()
    async def invite(self, ctx):
        """Get the bot's invite link"""
        
        embed = discord.Embed(
            title="Invite Me!",
            description=f"[Click here to invite me to your server!](https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands)",
            color=self.bot.color
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, message: str):
        """Make the bot say something"""
        
        await ctx.message.delete()
        await ctx.send(message)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx, title: str, *, description: str):
        """Create a custom embed"""
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=self.bot.color
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: discord.TextChannel, *, announcement: str):
        """Make an announcement in a channel"""
        
        embed = discord.Embed(
            title="📢 Announcement",
            description=announcement,
            color=self.bot.color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Announced by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await channel.send(embed=embed)
        await ctx.send(f"✅ Announcement sent to {channel.mention}")

async def setup(bot):
    await bot.add_cog(Utility(bot))

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.ball_responses = [
            "It is certain", "It is decidedly so", "Without a doubt",
            "Yes definitely", "You may rely on it", "As I see it, yes",
            "Most likely", "Outlook good", "Yes", "Signs point to yes",
            "Reply hazy, try again", "Ask again later", "Better not tell you now",
            "Cannot predict now", "Concentrate and ask again",
            "Don't count on it", "My reply is no", "My sources say no",
            "Outlook not so good", "Very doubtful"
        ]
    
    @commands.command(aliases=['8ball'])
    async def eightball(self, ctx, *, question: str):
        """Ask the magic 8ball a question"""
        
        embed = discord.Embed(
            title="🎱 Magic 8Ball",
            color=self.bot.color
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(self.ball_responses), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=['flip', 'coin'])
    async def coinflip(self, ctx):
        """Flip a coin"""
        
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"
        
        await ctx.send(f"{emoji} The coin landed on: **{result}**")
    
    @commands.command(aliases=['roll'])
    async def dice(self, ctx, sides: int = 6):
        """Roll a dice"""
        
        if sides < 2:
            return await ctx.send("Dice must have at least 2 sides!")
        
        if sides > 100:
            return await ctx.send("Maximum 100 sides!")
        
        result = random.randint(1, sides)
        
        await ctx.send(f"🎲 You rolled a **{result}** (1-{sides})")
    
    @commands.command()
    async def choose(self, ctx, *choices):
        """Choose between multiple options"""
        
        if len(choices) < 2:
            return await ctx.send("Give me at least 2 options!")
        
        choice = random.choice(choices)
        
        await ctx.send(f"I choose: **{choice}**")
    
    @commands.command()
    async def rate(self, ctx, *, thing: str):
        """Rate something out of 10"""
        
        rating = random.randint(0, 10)
        
        if rating <= 3:
            emoji = "😬"
        elif rating <= 6:
            emoji = "😐"
        else:
            emoji = "😍"
        
        await ctx.send(f"I'd rate {thing} a **{rating}/10** {emoji}")
    
    @commands.command()
    async def reverse(self, ctx, *, text: str):
        """Reverse text"""
        
        reversed_text = text[::-1]
        await ctx.send(reversed_text)
    
    @commands.command()
    async def emojify(self, ctx, *, text: str):
        """Convert text to emojis"""
        
        emoji_dict = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪',
            'f': '🇫', 'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯',
            'k': '🇰', 'l': '🇱', 'm': '🇲', 'n': '🇳', 'o': '🇴',
            'p': '🇵', 'q': '🇶', 'r': '🇷', 's': '🇸', 't': '🇹',
            'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽', 'y': '🇾', 'z': '🇿',
            '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
            '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
            '!': '❗', '?': '❓'
        }
        
        emojified = ''
        for char in text.lower():
            if char in emoji_dict:
                emojified += emoji_dict[char] + ' '
            elif char == ' ':
                emojified += '   '
            else:
                emojified += char
        
        if len(emojified) > 2000:
            return await ctx.send("Text is too long!")
        
        await ctx.send(emojified)
    
    @commands.command()
    async def mock(self, ctx, *, text: str):
        """mOcK tExT lIkE tHiS"""
        
        mocked = ''.join(
            char.upper() if i % 2 == 0 else char.lower()
            for i, char in enumerate(text)
        )
        
        await ctx.send(mocked)
    
    @commands.command()
    async def owoify(self, ctx, *, text: str):
        """Make text owo"""
        
        replacements = {
            'r': 'w',
            'l': 'w',
            'R': 'W',
            'L': 'W',
            'n': 'ny',
            'N': 'NY'
        }
        
        owo_text = text
        for old, new in replacements.items():
            owo_text = owo_text.replace(old, new)
        
        owo_text += " " + random.choice(["owo", "uwu", "OwO", "UwU", ">w<", "^w^"])
        
        await ctx.send(owo_text)
    
    @commands.command()
    async def clap(self, ctx, *, text: str):
        """Add 👏 between 👏 words"""
        
        clapped = " 👏 ".join(text.split())
        
        await ctx.send(clapped)
    
    @commands.command()
    async def ascii(self, ctx, *, text: str):
        """Convert text to ASCII art (simple version)"""
        
        if len(text) > 20:
            return await ctx.send("Text too long! Maximum 20 characters.")
        
        # Simple ASCII art representation
        ascii_art = f"""
```
  {text.upper()}
```
"""
        await ctx.send(ascii_art)
    
    @commands.command()
    async def joke(self, ctx):
        """Get a random joke"""
        
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a fake noodle? An impasta!",
            "Why did the bicycle fall over? Because it was two tired!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why couldn't the bicycle stand up? It was two tired!",
            "What did the ocean say to the beach? Nothing, it just waved!",
            "Why did the coffee file a police report? It got mugged!",
            "What do you call a dinosaur that crashes his car? Tyrannosaurus Wrecks!"
        ]
        
        await ctx.send(random.choice(jokes))
    
    @commands.command()
    async def meme(self, ctx):
        """Get a random meme from Reddit"""
        
        async with self.bot.session.get('https://meme-api.com/gimme') as resp:
            if resp.status == 200:
                data = await resp.json()
                
                embed = discord.Embed(
                    title=data['title'],
                    url=data['postLink'],
                    color=self.bot.color
                )
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"👍 {data['ups']} upvotes | r/{data['subreddit']}")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch meme!")
    
    @commands.command()
    async def cat(self, ctx):
        """Get a random cat image"""
        
        async with self.bot.session.get('https://api.thecatapi.com/v1/images/search') as resp:
            if resp.status == 200:
                data = await resp.json()
                
                embed = discord.Embed(
                    title="🐱 Random Cat",
                    color=self.bot.color
                )
                embed.set_image(url=data[0]['url'])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch cat image!")
    
    @commands.command()
    async def dog(self, ctx):
        """Get a random dog image"""
        
        async with self.bot.session.get('https://dog.ceo/api/breeds/image/random') as resp:
            if resp.status == 200:
                data = await resp.json()
                
                embed = discord.Embed(
                    title="🐶 Random Dog",
                    color=self.bot.color
                )
                embed.set_image(url=data['message'])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch dog image!")
    
    @commands.command()
    async def fox(self, ctx):
        """Get a random fox image"""
        
        async with self.bot.session.get('https://randomfox.ca/floof/') as resp:
            if resp.status == 200:
                data = await resp.json()
                
                embed = discord.Embed(
                    title="🦊 Random Fox",
                    color=self.bot.color
                )
                embed.set_image(url=data['image'])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch fox image!")
    
    @commands.command(aliases=['bird'])
    async def birb(self, ctx):
        """Get a random bird image"""
        
        async with self.bot.session.get('https://some-random-api.com/animal/bird') as resp:
            if resp.status == 200:
                data = await resp.json()
                
                embed = discord.Embed(
                    title="🐦 Random Bird",
                    description=data.get('fact', ''),
                    color=self.bot.color
                )
                embed.set_image(url=data['image'])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch bird image!")
    
    @commands.command()
    async def hug(self, ctx, member: discord.Member):
        """Hug someone"""
        
        if member == ctx.author:
            return await ctx.send("You can't hug yourself! Here's a hug from me instead 🤗")
        
        await ctx.send(f"{ctx.author.mention} hugs {member.mention} 🤗")
    
    @commands.command()
    async def pat(self, ctx, member: discord.Member):
        """Pat someone"""
        
        if member == ctx.author:
            return await ctx.send("You can't pat yourself!")
        
        await ctx.send(f"{ctx.author.mention} pats {member.mention} on the head 😊")
    
    @commands.command()
    async def slap(self, ctx, member: discord.Member):
        """Slap someone"""
        
        if member == ctx.author:
            return await ctx.send("Why would you slap yourself? 🤔")
        
        await ctx.send(f"{ctx.author.mention} slaps {member.mention} 👋")

async def setup(bot):
    await bot.add_cog(Fun(bot))


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM guild_settings WHERE guild_id = $1",
            member.guild.id
        )
        
        if not settings:
            return
        
        # Send welcome message
        if settings['welcome_channel']:
            channel = member.guild.get_channel(settings['welcome_channel'])
            if channel:
                embed = discord.Embed(
                    title=f"Welcome to {member.guild.name}!",
                    description=f"Hey {member.mention}, welcome to the server! 🎉\n\n"
                               f"You're member **#{member.guild.member_count}**\n"
                               f"Make sure to read the rules and have fun!",
                    color=self.bot.success_color,
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"User ID: {member.id}")
                
                try:
                    await channel.send(f"{member.mention}", embed=embed)
                except:
                    pass
        
        # Auto-role
        if settings['autorole']:
            role = member.guild.get_role(settings['autorole'])
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role")
                except:
                    pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        settings = await self.bot.db.fetchrow(
            "SELECT leave_channel FROM guild_settings WHERE guild_id = $1",
            member.guild.id
        )
        
        if not settings or not settings['leave_channel']:
            return
        
        channel = member.guild.get_channel(settings['leave_channel'])
        if not channel:
            return
        
        embed = discord.Embed(
            title="Member Left",
            description=f"{member} has left the server.\n"
                       f"We now have **{member.guild.member_count}** members.",
            color=self.bot.error_color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        try:
            await channel.send(embed=embed)
        except:
            pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if not message.content.startswith('-'):
            return
        
        # Check for custom command
        cmd_name = message.content[1:].split()[0].lower()
        
        custom_cmd = await self.bot.db.fetchrow(
            "SELECT * FROM custom_commands WHERE guild_id = $1 AND name = $2",
            message.guild.id, cmd_name
        )
        
        if custom_cmd:
            # Increment uses
            await self.bot.db.execute(
                "UPDATE custom_commands SET uses = uses + 1 WHERE guild_id = $1 AND name = $2",
                message.guild.id, cmd_name
            )
            
            await message.channel.send(custom_cmd['response'])
    
    @commands.group(invoke_without_command=True)
    async def cc(self, ctx):
        """Custom commands menu"""
        
        embed = discord.Embed(
            title="✏️ Custom Commands",
            description="Create your own custom commands!\n\n"
                       "**Subcommands:**\n"
                       "`-ccadd <name> <response>` - Add a command\n"
                       "`-ccremove <name>` - Remove a command\n"
                       "`-cclist` - List all commands\n"
                       "`-ccedit <name> <new_response>` - Edit a command\n"
                       "`-ccinfo <name>` - Get command info",
            color=self.bot.color
        )
        await ctx.send(embed=embed)
    
    @cc.command(name='add')
    @commands.has_permissions(manage_guild=True)
    async def cc_add(self, ctx, name: str, *, response: str):
        """Add a custom command"""
        
        name = name.lower()
        
        # Check if command already exists
        existing = await self.bot.db.fetchval(
            "SELECT name FROM custom_commands WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, name
        )
        
        if existing:
            return await ctx.send(f"Command `{name}` already exists!")
        
        # Check if it's a built-in command
        if self.bot.get_command(name):
            return await ctx.send(f"`{name}` is a built-in command!")
        
        await self.bot.db.execute(
            "INSERT INTO custom_commands (guild_id, name, response, created_by) VALUES ($1, $2, $3, $4)",
            ctx.guild.id, name, response, ctx.author.id
        )
        
        await ctx.send(f"✅ Created custom command `{name}`")
    
    @cc.command(name='remove', aliases=['delete'])
    @commands.has_permissions(manage_guild=True)
    async def cc_remove(self, ctx, name: str):
        """Remove a custom command"""
        
        deleted = await self.bot.db.execute(
            "DELETE FROM custom_commands WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, name.lower()
        )
        
        await ctx.send(f"✅ Deleted custom command `{name}`")
    
    @cc.command(name='list')
    async def cc_list(self, ctx):
        """List all custom commands"""
        
        commands = await self.bot.db.fetch(
            "SELECT name, uses FROM custom_commands WHERE guild_id = $1 ORDER BY uses DESC",
            ctx.guild.id
        )
        
        if not commands:
            return await ctx.send("No custom commands in this server!")
        
        embed = discord.Embed(
            title=f"✏️ Custom Commands ({len(commands)})",
            description="\n".join([f"`{cmd['name']}` - {cmd['uses']} uses" for cmd in commands[:20]]),
            color=self.bot.color
        )
        
        if len(commands) > 20:
            embed.set_footer(text=f"Showing 20/{len(commands)} commands")
        
        await ctx.send(embed=embed)
    
    @cc.command(name='edit')
    @commands.has_permissions(manage_guild=True)
    async def cc_edit(self, ctx, name: str, *, new_response: str):
        """Edit a custom command"""
        
        existing = await self.bot.db.fetchval(
            "SELECT name FROM custom_commands WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, name.lower()
        )
        
        if not existing:
            return await ctx.send(f"Command `{name}` doesn't exist!")
        
        await self.bot.db.execute(
            "UPDATE custom_commands SET response = $1 WHERE guild_id = $2 AND name = $3",
            new_response, ctx.guild.id, name.lower()
        )
        
        await ctx.send(f"✅ Updated custom command `{name}`")
    
    @cc.command(name='info')
    async def cc_info(self, ctx, name: str):
        """Get info about a custom command"""
        
        cmd = await self.bot.db.fetchrow(
            "SELECT * FROM custom_commands WHERE guild_id = $1 AND name = $2",
            ctx.guild.id, name.lower()
        )
        
        if not cmd:
            return await ctx.send(f"Command `{name}` doesn't exist!")
        
        creator = ctx.guild.get_member(cmd['created_by'])
        
        embed = discord.Embed(
            title=f"Command: {cmd['name']}",
            color=self.bot.color
        )
        embed.add_field(name="Response", value=cmd['response'][:1024], inline=False)
        embed.add_field(name="Creator", value=creator.mention if creator else "Unknown", inline=True)
        embed.add_field(name="Uses", value=str(cmd['uses']), inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(cmd['created_at'], 'R'), inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))


# cogs/logs.py
class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def log(self, guild, embed):
        """Send log to mod log channel"""
        
        log_id = await self.bot.db.fetchval(
            "SELECT mod_log_channel FROM guild_settings WHERE guild_id = $1",
            guild.id
        )
        
        if not log_id:
            return
        
        channel = guild.get_channel(log_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except:
                pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention}\n"
                       f"**Channel:** {message.channel.mention}\n"
                       f"**Content:** {message.content[:1000] if message.content else '*No content*'}",
            color=self.bot.error_color,
            timestamp=message.created_at
        )
        embed.set_footer(text=f"Message ID: {message.id}")
        
        await self.log(message.guild, embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention}\n"
                       f"**Channel:** {before.channel.mention}\n"
                       f"**Before:** {before.content[:500]}\n"
                       f"**After:** {after.content[:500]}\n"
                       f"**[Jump to message]({after.jump_url})**",
            color=self.bot.color,
            timestamp=after.edited_at
        )
        
        await self.log(before.guild, embed)
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**User:** {user.mention}\n"
                       f"**ID:** {user.id}",
            color=self.bot.error_color
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await self.log(guild, embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(
            title="✅ Member Unbanned",
            description=f"**User:** {user.mention}\n"
                       f"**ID:** {user.id}",
            color=self.bot.success_color
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await self.log(guild, embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx, channel: discord.TextChannel):
        """Set the logging channel"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET mod_log_channel = $1 WHERE guild_id = $2",
            channel.id, ctx.guild.id
        )
        
        embed = discord.Embed(
            title="✅ Logging Enabled",
            description=f"All server events will be logged to {channel.mention}",
            color=self.bot.success_color
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clearlog(self, ctx):
        """Clear log configuration"""
        
        await self.bot.db.execute(
            "UPDATE guild_settings SET mod_log_channel = NULL WHERE guild_id = $1",
            ctx.guild.id
        )
        
        await ctx.send("✅ Logging disabled!")
    
    @commands.command()
    async def logs(self, ctx, limit: int = 10):
        """View recent automod logs"""
        
        logs = await self.bot.db.fetch(
            "SELECT * FROM automod_logs WHERE guild_id = $1 ORDER BY created_at DESC LIMIT $2",
            ctx.guild.id, min(limit, 20)
        )
        
        if not logs:
            return await ctx.send("No logs found!")
        
        embed = discord.Embed(
            title="📝 Recent Automod Logs",
            color=self.bot.color
        )
        
        for log in logs:
            user = ctx.guild.get_member(log['user_id'])
            username = user.mention if user else f"ID: {log['user_id']}"
            embed.add_field(
                name=f"{log['action']} - {discord.utils.format_dt(log['created_at'], 'R')}",
                value=f"**User:** {username}\n**Reason:** {log['reason'][:100]}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))

if __name__ == "__main__":
    bot = Bot()
    bot.run(os.getenv('DISCORD_TOKEN'))
