from motor.motor_asyncio import AsyncIOMotorClient
from umongo import Document, fields
from umongo.frameworks import MotorAsyncIOInstance

from datetime import datetime
import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound
import secrets
import requests
from dotenv import load_dotenv
import os
import re

load_dotenv()
_mongo_client = AsyncIOMotorClient(os.getenv('DB_PATH'))
_db =  _mongo_client.newDB
instance = MotorAsyncIOInstance(_db)
client = commands.Bot(command_prefix=os.getenv('CMD_PREFIX'), intents = discord.Intents().all())


CHANNEL_ID = int(os.getenv('BOT_CHANNEL_ID'))
SERVER_ID = int(os.getenv('BOT_SERVER_ID'))

API_CHECK_ACCOUNT = os.getenv('API_CHECK_ACCOUNT')
if not API_CHECK_ACCOUNT.endswith('/'):
    API_CHECK_ACCOUNT += '/'

# DB Schema
@instance.register
class User(Document):
    user_id = fields.IntField(required=True)
    user_name = fields.StrField(required=True)
    user_token = fields.StrField(required=True)
    user_status = fields.IntField(required=True)
    user_time = fields.IntField(required=True)

    class Meta:
        collection_name = 'accounts'

def is_username_taken(username:str):
    r = requests.get(f'{API_CHECK_ACCOUNT}{username}')
    response = r.json()
    err = response.get('error', None)
    if err is None: 
        return True
    else:
        return False

@client.command(help='Claiming a new account')
async def claim(ctx,username=''):
    # if "ticket" not in ctx.message.channel.name: 
    #     return
    
    if ctx.channel.id != CHANNEL_ID or ctx.guild.id != SERVER_ID:
        return
    
    # validate username
    if len(username) == 0:
        await ctx.send(f"Hello <@{ctx.author.id}>. Username cannot be empty")
        return
    
    if len(username) < 5:
        await ctx.send(f"Hello <@{ctx.author.id}>. Username should be 5 or more characters")
        return
    
    match = re.match("^[A-Za-z0-9-]*$", username)
    if match is None:
        await ctx.send(f"Hello <@{ctx.author.id}>. Username should only contain alpha-numeric characters and/or dashes")
        return

    # check if username is already taken or not
    if is_username_taken(username) == True:
        await ctx.send(f"Hello <@{ctx.author.id}>. Username exists. Please choose another username")
        return
    
    
    
    # Check against the db
    user = await User.find_one({"user_id": ctx.author.id})
    if user is not None:
        if user.user_status == 0:
            await ctx.send(f"Hello <@{ctx.author.id}>. You have already claimed `{user.user_name}` which is pending for registeration")
        else:
            await ctx.send(f"Hello <@{ctx.author.id}>. You have already claimed `{user.user_name}`. You can not claim more accounts")
        
        return
    
    
    # Check if anyone has this username reserveed
    user = await User.find_one({"user_name": username})
    if user is not None:
        await ctx.send(f"Hello <@{ctx.author.id}>. '{username}' is already claimed by another user. Please choose another one")
        return
    
    # get activation token
    activation_token = secrets.token_hex(16)
    user = User(
        user_name = username,
        user_id = ctx.author.id,
        user_token = activation_token,
        user_status = 0,
        user_time = int(datetime.now().timestamp())
    )
    await user.commit()
    
    # DM user token
    discord_user = await client.fetch_user(ctx.author.id)
    await ctx.send(f"Hello <@{ctx.author.id}>. token has been sent via DM")
    await discord_user.send(f'Hello <@{ctx.author.id}>. \nHere is your activation token {activation_token}')

@client.event
async def on_ready():
    print("I'm ready")

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        await ctx.send(f"Hello <@{ctx.author.id}>. Wrong command. Please use `!help` to get list of supported commands")
        return
    raise error


client.run(os.getenv('BOT_TOKEN'))
