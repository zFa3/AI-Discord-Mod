import datetime
import time
from discord.ext import commands
import discord
from Gemini import Interface
import os
from random import randint

# current version
VERSION = "v1.0.2"
TIME_AT_STARTUP = time.strftime('%Y-%m-%d %H:%M:%S')

API_KEY: str | None = os.getenv('API_KEY')

INTENTS: discord.Intents = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

# Change to 'True' if you want to log all messages (includes deleted) to a .txt
SAVE_HISTORY = False
MODERATE_MESSAGES = False

# maximum allowed timeout
MAX_TIMEOUT = 2419200  # 28 days (Max discord allows)
MAX_TIMEOUT = 24192    # ~6 hours

# save history
FILENAME = "History.txt"

# Role names
ADMIN_ROLE_NAME = "Admin"
MOD_ROLE_NAME = "Playtester"

# gemini api
CHATBOT: Interface = Interface()

# use the '!' prefix for commands
bot: commands.Bot = commands.Bot(command_prefix='!', intents=INTENTS)

async def save_to_file(text):
    ''' save data to a file '''
    with open(FILENAME + ".csv", "a+") as file:
        file.write(text)

# events

@bot.event
async def on_ready() -> None:
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    if MODERATE_MESSAGES:
        pass
        # TODO ADD AI MODERATION
    content = f"Message from {message.author} at {time.strftime('%Y-%m-%d %H:%M:%S')}: {message.content}"

    if SAVE_HISTORY:
        save_to_file(content)
    # print(content)
    await bot.process_commands(message)

@bot.event
async def on_member_join(ctx: discord.Member) -> None:
    '''Add member role upon joining'''
    await ctx.guild.system_channel.send(f'Welcome {ctx.mention}!')
    await addrole(ctx, "Member")

@commands.has_permissions(moderate_members=True)
async def apply_timeout(
    ctx: commands.Context,
    member: discord.Member,
    seconds: int,
    *,
    reason: str | None = None
) -> None:
    '''applies timeout to a user'''
    seconds = max(1, seconds)
    duration: datetime.timedelta = datetime.timedelta(minutes=seconds / 60)
    try:
        await member.timeout(duration, reason=reason)
        await ctx.send(f'🔇 {member.mention} has been timed out for {seconds} second{"s" if seconds > 1 else ""}.')
    except Exception as e:
        await ctx.send(f'❌ Failed to timeout member: {e}', delete_after=5)

@commands.has_permissions(moderate_members=True)
async def remove_timeout(
    ctx: commands.Context,
    member: discord.Member,
    *,
    reason: str | None = None
) -> None:
    '''remove a timeout from a user'''
    try:
        await member.timeout(None, reason=reason)
        await ctx.send(f'🔊 {member.mention} has been removed from timeout.')
    except Exception as e:
        await ctx.send(f'❌ Failed to remove timeout: {e}', delete_after=5)

async def sendfile(ctx, TEMPORARY_FILENAME: str):
    # if file does not exist, will throw FileNotFoundError
    with open(TEMPORARY_FILENAME, 'rb') as f:
        file = discord.File(f, filename=TEMPORARY_FILENAME)
        await ctx.send(" ", file=file)
    with open(TEMPORARY_FILENAME, 'w') as f:
        f.write("")

async def addrole(ctx: discord.Member, role_name: str) -> None:
    await ctx.add_roles(discord.utils.get(ctx.guild.roles, name=role_name))

### Admin Commands

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def purge(ctx, amount: int):
    '''Bulk purge messages - Format: !purge {# of messages}'''
    if amount < 1:
        await ctx.send("Enter a number > 0")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Deleted {len(deleted)-1} messages", delete_after=5)

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def slowmode(ctx, seconds: int):
    '''applies slowmode to a channel\n'''
    seconds = max(0, seconds)  # limits to non negative integers
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"Set slowmode to {seconds} seconds.")

### Moderator Commands

@bot.command(aliases=['timeout', 'gotojail'])
@commands.has_role(MOD_ROLE_NAME)
async def mute(
    ctx: commands.Context,
    mention: str,
    seconds: int = 15, # defaults to 15 seconds
    *,
    reason: str | None = None
) -> None:
    '''Apply a timeout to a member - Format: !mute @mention {seconds}'''
    # limit the timeout
    seconds = max(0, min(seconds, MAX_TIMEOUT))
    try:
        user_id: int = int(mention[2:-1])
        member: discord.Member | None = ctx.guild.get_member(user_id)
        if member:
            await apply_timeout(ctx, member, seconds, reason=reason)
        else:
            await ctx.send("Member not found in this server.")
    except ValueError:
        await ctx.send("Invalid mention format.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}", delete_after=5)

@bot.command(aliases=['jailbreak', 'rtimeout'])
@commands.has_role(MOD_ROLE_NAME)
async def unmute(ctx: commands.Context, member: discord.Member) -> None:
    '''Remove a timeout from a member - Format: !unmute @mention'''
    try:
        await member.edit(timed_out_until=None)
        await ctx.send(f"✅ Timeout removed for {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to modify this user.", delete_after=5)
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to remove timeout: {e}", delete_after=5)

@bot.command(aliases=['makepoll', 'question'])
@commands.has_role(MOD_ROLE_NAME)
async def poll(ctx: commands.Context, question: str, *, options: str):
    '''Create a poll - Format: !poll "{question}" {ans, ans2, ans3...}'''
    number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    option_list = [opt.strip() for opt in options.split(",")]
    if not 2 <= len(option_list) <= 10:
        await ctx.send("❌ You must provide between 2 and 10 options, separated by commas.", delete_after=5)
        return
    description = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(option_list))
    embed = discord.Embed(title=question, description=description, color=discord.Color.blue())
    embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
    poll_msg = await ctx.send(embed=embed)
    for i in range(len(option_list)):
        await poll_msg.add_reaction(number_emojis[i])

@bot.command(aliases=['nick'])
@commands.has_role(MOD_ROLE_NAME)
async def setnick(ctx, member: discord.Member, *, nickname: str):
    '''Edit/change a member's nick'''
    await member.edit(nick=nickname)
    await ctx.send(f"Changed nickname for {member.mention} to `{nickname}`.")

@bot.command(aliases=['addrole', 'apply'])
@commands.has_role(MOD_ROLE_NAME)
async def role(ctx: commands.Context, member: discord.Member, *, role_name: str | None = None) -> None:
    '''applies a role to mention - Format: !role {@mention} {rolename}'''
    # Cannot be Admin
    if role_name == ADMIN_ROLE_NAME:
        await ctx.send("Cannot add Admin")
        return
    print(member, role_name)
    try:
        await addrole(member, role_name)
        await ctx.send(f"Success! Added role {role_name}")
    except:
        await ctx.send(f"Failed to add role")

### Member Commands

@bot.event
async def on_command_error(ctx, error):
    # in the event of a typo
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(error)
    else:
        raise error

@bot.command(aliases=['hey', 'chat'])
async def c(ctx: commands.Context, *, message: str) -> None:
    '''Gemini 2.5 flash-lite - Format: !c {msg} (1000 rpd) (NO MEMORY)'''
    CHATBOT = Interface(model="gemini-2.5-flash-lite-preview-06-17")
    response: str = await CHATBOT.generate(f"Keep your message brief but detailed:\n<START OF PROMPT>\n{message}\n<END OF PROMPT>")
    TEMPORARY_FILENAME = "Requested_response_is_longer_than_2000_tokens.txt"
    if len(response) > 2000:
        with open(TEMPORARY_FILENAME, 'w') as f:
            f.write(response)
        await sendfile(ctx, TEMPORARY_FILENAME)
    else:
        await ctx.send(response)

@bot.command(aliases=['whois', 'user'])
async def profile(ctx: commands.Context, member: discord.Member = None) -> None:
    '''Display information about a mentioned user. Format: !whois @mention'''
    if member is None:
        member = ctx.author
    info = (
        f"**User Info:**\n"
        f"- Mention: {member.mention}\n"
        f"- Username: `{member}`\n"
        f"- ID: `{member.id}`\n"
        f"- Nickname: `{member.nick}`\n"
        f"- Bot: `{member.bot}`\n"
        f"- Top Role: `{member.top_role}`\n"
        f"- Joined Server: `{member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"- Account Created: `{member.created_at.strftime('%Y-%m-%d %H:%M:%S')}`\n"
    )
    await ctx.send(info)

@bot.command(aliases=['rng', 'dice'])
async def roll(ctx: commands.Context, *, roll: str = "") -> None:
    '''rolls a dice - format: !roll {lower # (OPTIONAL)} {upper #(OPTIONAL)}'''
    try:
        match len(roll.split()):
            case 2:
                low, high = int(roll.split()[0]), int(roll.split()[1])
                await ctx.send(randint(low, high))
            case 1:
                await ctx.send(randint(0, int(roll)))
            case _:
                await ctx.send(randint(1, 6))
    except:
        await ctx.send("An error occured")

@bot.command(aliases=['coinflip', 'coin'])
async def flip(ctx: commands.Context) -> None:
    '''coinflip - format: !flip'''
    await ctx.send(":regional_indicator_h:" if randint(0, 1) else ":regional_indicator_t:")

@bot.command()
async def ping(ctx):
    '''ping latency'''
    await ctx.send(f"Pong! {round(bot.latency * 1000)} milliseconds")

@bot.command(aliases=['bot', 'model', 'release'])
async def version(ctx):
    '''returns the current bot version'''
    await ctx.send(f"Current Version: {VERSION}, last updated {TIME_AT_STARTUP}")

# run the bot
if __name__ == "__main__":
    bot.run(API_KEY)
