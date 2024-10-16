import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import yt_dlp
import asyncio
from requests import get


load_dotenv()
MY_GUILD = discord.Object(os.environ['GUILD'])

yt_dlp_variables = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_variables = {
    'options': '-vn'
}


ytdl = yt_dlp.YoutubeDL(yt_dlp_variables)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_variables), data=data)
    
    
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.current_voice_channel = None

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

intents = discord.Intents.default()
client = MyClient(intents=intents)


# Search for youtube video using keyword
def search_yt(arg):
    try:
        get(arg)
    except:
        video = ytdl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
    else:
        video = ytdl.extract_info(arg, download=False)
    print (video)
    return video


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.tree.command()
async def hello(interaction: discord.Interaction):
    """ Says hello """ 
    await interaction.response.send_message(f"Hi, {interaction.user.mention}")

@client.tree.command()
@app_commands.describe(
    to_echo="Something to echo"
)
async def echo(interaction: discord.Interaction, to_echo: str):
    """ Echoes a message """ 
    await interaction.response.send_message(f"{to_echo}")

""" @client.tree.command()
async def join(interaction: discord.Interaction):
    
    if(interaction.user.voice):
        await interaction.response.send_message(f"Joining....")
        client.current_voice_channel = await interaction.user.voice.channel.connect()
    else:
        await interaction.response.send_message("You must be in a voice channel to use this command") """

@client.tree.command()
@app_commands.describe(
    url="URL to play"
)
async def play(interaction: discord.Interaction, url: str):

    if(interaction.user.voice):
        if(client.current_voice_channel):
            await interaction.response.send_message(f"Attempting to play {url}")   
        else:
            await interaction.response.send_message(f"Joining and attempting to play {url}")
            client.current_voice_channel = await interaction.user.voice.channel.connect()
    else:
        await interaction.response.send_message("You must be in a voice channel to use this command")
    player = await YTDLSource.from_url(url, stream=True)
    guild = interaction.guild
    guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

@client.tree.command()
async def pause(interaction: discord.Interaction):
    """ Pauses the current audio """
    if(client.current_voice_channel):
        if(client.current_voice_channel.is_paused()):
            await interaction.response.send_message(f"Audio is already paused")
            return
        client.current_voice_channel.pause()
        await interaction.response.send_message(f"Audio paused")
    else:
        await interaction.response.send_message("Not currently in a voice channel")
        
@client.tree.command()
async def resume(interaction: discord.Interaction):
    """ Resumes the current audio """
    if(client.current_voice_channel):
        if(client.current_voice_channel.is_paused()):
            await interaction.response.send_message(f"Resuming audio")
            client.current_voice_channel.resume()
        else:
            await interaction.response.send_message(f"Audio is not currently paused")
    else:
        await interaction.response.send_message("Not currently in a voice channel")

@client.tree.command()
async def stop(interaction: discord.Interaction):
    """ Leaves the current voice channel"""
    if(client.current_voice_channel):
        await client.current_voice_channel.disconnect()
        await interaction.response.send_message("Bye bye")
        client.current_voice_channel = None
    else:
        await interaction.response.send_message("Not currently in a voice channel")

@client.tree.command()
async def search(interaction: discord.Interaction, arg:str):
    if(interaction.user.voice):
        if(client.current_voice_channel):
            await interaction.response.send_message(f"Searching for {arg}")   
        else:
            await interaction.response.send_message(f"Joining and searching for {arg}")
            client.current_voice_channel = await interaction.user.voice.channel.connect()
    else:
        await interaction.response.send_message("You must be in a voice channel to use this command")
    video = search_yt(arg)
    player = await YTDLSource.from_url(video['url'], stream=True)
    guild = interaction.guild
    guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)


client.run(os.environ['BOT_TOKEN'])