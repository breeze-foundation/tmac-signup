from motor.motor_asyncio import AsyncIOMotorClient
from umongo import Document, fields
from umongo.frameworks import MotorAsyncIOInstance

import discord
from discord.ext import commands
import secrets
import requests
from dotenv import load_dotenv
import os


load_dotenv()
_mongo_client = AsyncIOMotorClient(os.getenv('DB_PATH'))
_db =  _mongo_client.local
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

@client.command()
async def claim(ctx,username='',*args):
    # if "ticket" not in ctx.message.channel.name: 
    #     return
    
    if ctx.channel.id != CHANNEL_ID or ctx.guild.id != SERVER_ID:
        return
    
    # validate username
    if len(username) == 0:
        await ctx.send("Username cannot be empty")
        return
    
    if len(username) < 5:
        await ctx.send("Username should be 5 or more characters")
        return
    
    if username.isalnum() == False:
        await ctx.send("Username should only contain alpha-numeric characters")
        return

    # check if username is already taken or not
    if is_username_taken(username) == True:
        await ctx.send("Username exists. Please choose another username")
        return
    
    # Check against the db
    user = await User.find_one({"user_id": ctx.author.id})
    if user is not None:
        if user.user_status == 0:
            await ctx.send(f"Hello <@{ctx.author.id}>. You already claimed {username} which is pending for registeration")
        else:
            await ctx.send(f"Hello <@{ctx.author.id}>. You already claimed {username}. You can not claim more accounts")
        
        return
    # get activation token
    activation_token = secrets.token_hex(16)
    user = User(
        user_name = username,
        user_id = ctx.author.id,
        user_token = activation_token,
        user_status = 0
    )
    await user.commit()
    
    # DM user token
    discord_user = await client.fetch_user(ctx.author.id)
    await discord_user.send(f'Hello\nHere is your activation token {activation_token}')

@client.event
async def on_ready():
    print("I'm ready")

client.run(os.getenv('BOT_TOKEN'))
