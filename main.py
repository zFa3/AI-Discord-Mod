import datetime, time
from discord.ext import commands
import discord
from Gemini import Interface
import os
from random import randint

API_KEY: str | None = os.getenv('API_KEY')

INTENTS: discord.Intents = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

# max in seconds
MAX_TIMEOUT = 2419200

# save history
FILENAME = "History.txt"

MOD_ROLE_NAME = "Playtester"

# gemini api
CHATBOT: Interface = Interface()

# use the '!' prefix for commands
bot: commands.Bot = commands.Bot(command_prefix='!', intents=INTENTS)

async def save_to_file(text):
    ''' save data to a file '''
    
    with open(FILENAME + ".csv", "a+") as file:
        
        file.write(text)

@bot.event
async def on_ready() -> None:
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author == bot.user:
        return

    content = f"Message from {message.author} at {time.strftime('%Y-%m-%d %H:%M:%S')}: {message.content}"

    # save_to_file(content)
    print(content)

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
        await ctx.send(f'❌ Failed to timeout member: {e}')

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

        await ctx.send(f'❌ Failed to remove timeout: {e}')


async def addrole(ctx: discord.Member, role_name: str) -> None:
    role: discord.Role | None = discord.utils.get(ctx.guild.roles, name=role_name)
    await ctx.guild.system_channel.send(f"Role '{role_name}' has been applied")
    await ctx.add_roles(role)

### moderator commands

@bot.command(aliases=['timeout', 'gotojail'])
@commands.has_role(MOD_ROLE_NAME)
async def mute(
    ctx: commands.Context,
    mention: str,
    seconds: int = 15,
    *,
    reason: str | None = None
) -> None:
    '''Apply a timeout to a member - Format: !mute @mention {seconds}'''

    required_role: str = MOD_ROLE_NAME

    if not any(role.name == required_role for role in ctx.author.roles):
        await ctx.send("❌ You don't have permission to use this command.")
        return

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
        await ctx.send(f"❌ Error: {e}")

@bot.command(aliases=['jailbreak', 'rtimeout'])
@commands.has_role(MOD_ROLE_NAME)
async def unmute(ctx: commands.Context, member: discord.Member) -> None:
    '''Remove a timeout from a member - Format: !unmute @mention'''
    try:
        await member.edit(timed_out_until=None)
        await ctx.send(f"✅ Timeout removed for {member.mention}.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to modify this user.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to remove timeout: {e}")


@bot.command(aliases=['makepoll', 'question'])
@commands.has_role(MOD_ROLE_NAME)
async def poll(ctx: commands.Context, question: str, *, options: str):
    '''Create a poll - Format: !poll "{question}" {ans, ans2, ans3...}'''
    number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    option_list = [opt.strip() for opt in options.split(",")]

    if not 2 <= len(option_list) <= 10:
        await ctx.send("❌ You must provide between 2 and 10 options, separated by commas.")
        return

    description = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(option_list))
    embed = discord.Embed(title=question, description=description, color=discord.Color.blue())
    embed.set_footer(text=f"Poll created by {ctx.author.display_name}")

    poll_msg = await ctx.send(embed=embed)
    for i in range(len(option_list)):
        await poll_msg.add_reaction(number_emojis[i])

# regular commands

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(error)
    else:
        raise error

@bot.command(aliases=['hey', 'chat'])
async def c(ctx: commands.Context, *, message: str) -> None:
    '''Gemini 2.5 flash-lite - Format: !c {msg} (1000 rpd) (NO MEMORY)'''
    CHATBOT = Interface(model = "gemini-2.5-flash-lite-preview-06-17")
    
    response: str = await CHATBOT.generate(f"Keep your message brief but detailed:\n<START OF PROMPT>\n{message}\n<END OF PROMPT>")
    
    # print(response, len(response))

    TEMPORARY_FILENAME = "Requested_response_is_longer_than_2000_tokens.txt"

    if len(response) > 2000:

        with open(TEMPORARY_FILENAME, 'w') as f:
        
            f.write(response)
        
        await sendfile(ctx, TEMPORARY_FILENAME)

    else:
        await ctx.send(
            response
        )

async def sendfile(ctx, TEMPORARY_FILENAME: str):
    # Ensure the file exists at this path
    with open(TEMPORARY_FILENAME, 'rb') as f:
        
        file = discord.File(f, filename=TEMPORARY_FILENAME)

        await ctx.send(" ", file=file)

    with open(TEMPORARY_FILENAME, 'w') as f:
        f.write("")

@bot.command(aliases=['whois', 'user', 'me'])
async def profile(ctx: commands.Context, member: discord.Member = None) -> None:
    '''Display information about a mentioned user. Format: !whois @mention'''
    if member == None: member = ctx.author
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

@bot.command(aliases=['moderator'])
async def playtester(ctx: commands.Context) -> None:
    '''Adds playtester role to the author'''
    await addrole(ctx.author, MOD_ROLE_NAME)

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

# run the bot
if __name__ == "__main__":
    bot.run(API_KEY)
