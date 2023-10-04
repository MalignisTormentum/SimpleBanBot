import requests
import datetime
import time
import json
import discord
import discord.ext
import rblxopencloud

intents = discord.Intents.all()
intents.message_content = True

discord_client = discord.Client(intents = intents)
tree = discord.app_commands.CommandTree(discord_client)

guild_id = 0
log_channel_id = 0
bot_role_id = 0

@discord_client.event
async def on_ready():
    await tree.sync()

time_dict = {"h" : 3600, "s" : 1, "m" : 60, "d" : 86400}
days_dict = {'h' : 'Hours', 's' : 'Seconds', 'm' : 'Minutes', 'd' : 'Days'}

log_channel = None

roblox_key = ''
game_universe_id = 0
experience = rblxopencloud.Experience(game_universe_id, roblox_key)

def get_human_readable_unban_date(seconds):
    return datetime.datetime.utcfromtimestamp(seconds).strftime('%m-%d-%Y %H:%M UTC')

def get_player_data(player):
    p = None

    try:
        p = int(player)
        p = requests.post('https://users.roblox.com/v1/users', headers = {'Content-Type' : 'application/json', 'accept' : 'application/json'}, json = {"userIds": [p], "excludeBannedUsers": True})
    except:
        p = str(player)
        p = requests.post('https://users.roblox.com/v1/usernames/users', headers={'Content-Type' : 'application/json', 'accept' : 'application/json'}, json = {"usernames": [p], "excludeBannedUsers": True})

    if 'data' in p.json() and len(p.json()['data']) > 0:
        dat = p.json()['data'][0]
        dat['player_image'] = requests.get('https://thumbnails.roblox.com/v1/users/avatar?userIds=%s&size=250x250&format=Png&isCircular=false' % dat['id']).json()['data'][0]['imageUrl']
        dat['profile'] = 'https://www.roblox.com/users/%s/profile' % dat['id']
        return dat
    else:
        return None
        
def get_embed(player_data):
    embed = discord.Embed(title = player_data['action'], color = player_data['color'])

    embed.add_field(name = 'Moderator', value = '<@%s>' % player_data['moderator'], inline = False)
    embed.add_field(name = 'Username', value = player_data['name'], inline = True)
    embed.add_field(name = 'ID', value = player_data['id'], inline = True)

    if 'seconds' in player_data:
        embed.add_field(name = 'Duration', value = player_data['duration'], inline = False)
        embed.add_field(name = 'Unbanned On', value = get_human_readable_unban_date(player_data['seconds'] + time.time()), inline = True)

    embed.add_field(name = 'Profile Link', value = player_data['profile'], inline = False)

    if 'reason' in player_data:
        embed.add_field(name = 'Reason', value = player_data['reason'], inline = False)

    return embed

@tree.command(name = 'game_temp_ban', description = 'Temporarily bans a user from AW')
async def slash_command(interaction : discord.Interaction, player : str, duration : str, reason : str):
    duration = duration.replace(' ', '')
    duration = duration.lower()

    if interaction.user.get_role(bot_role_id) == None:
        await interaction.response.send_message('You do not have the role needed to use this command.', delete_after = 5.0, ephemeral = True)
        return
    
    if len(list(filter(str.isalpha, duration))) != 1:
        await interaction.response.send_message('Invalid duration.', delete_after = 5.0, ephemeral = True)
        return
    
    if len(list(filter(str.isnumeric, duration))) == 0:
        await interaction.response.send_message('Invalid duration.', delete_after = 5.0, ephemeral = True)
        return
    
    letter = duration[len(duration) - 1]
    number = duration[:len(duration) - 1]

    if not letter in time_dict:
        await interaction.response.send_message('Invalid duration.', delete_after = 5.0, ephemeral = True)
        return
    
    try:
        number = float(number)
    except:
        await interaction.response.send_message('Invalid duration.', delete_after = 5.0, ephemeral = True)
        return
    
    log_channel = interaction.guild.get_channel(log_channel_id)
    player_data = get_player_data(player)

    if not player_data:
        await interaction.response.send_message('That player does not exist.', delete_after = 5.0, ephemeral = True)
        return
    
    player_data['seconds'] = number * time_dict[letter]
    player_data['duration'] = str(number) + ' ' + days_dict[letter]
    player_data['reason'] = reason
    player_data['moderator'] = interaction.user.id
    player_data['action'] = 'Player Temporarily Banned!'
    player_data['color'] = discord.Color.red()

    msg_data = {
        'Reason' : player_data['reason'],
        'UserId' : player_data['id'],
        'Duration' : str(number) + ' ' + days_dict[letter].lower()
    }

    ds_data = {
        'Reason' : player_data['reason'],
        'Length' : time.time() + player_data['seconds']
    } 

    experience.publish_message('discord', json.dumps(msg_data))
    experience.get_data_store('Ban_Data').set('Player_' + str(player_data['id']), ds_data)

    await log_channel.send(embed = get_embed(player_data))
    await interaction.response.send_message('%s was temporarily banned.' % player_data['name'], delete_after = 5.0, ephemeral = True)

@tree.command(name = 'game_perm_ban', description = 'Permanently bans a user from AW')
async def slash_command(interaction : discord.Interaction, player : str, reason : str):
    if interaction.user.get_role(bot_role_id) == None:
        await interaction.response.send_message('You do not have the role needed to use this command.', ephemeral = True, delete_after = 5.0)
        return
    
    log_channel = interaction.guild.get_channel(log_channel_id)
    player_data = get_player_data(player)

    if not player_data:
        await interaction.response.send_message('That player does not exist.', ephemeral = True, delete_after = 5.0)
        return
    
    player_data['reason'] = reason
    player_data['moderator'] = interaction.user.id
    player_data['action'] = 'Player Permanently Banned!'
    player_data['color'] = discord.Color.red()

    msg_data = {
        'Reason' : player_data['reason'],
        'UserId' : player_data['id'],
        'Duration' : 'inf'
    }

    ds_data = {
        'Reason' : player_data['reason'],
        'Length' : 'inf'
    } 
    
    experience.publish_message('discord', json.dumps(msg_data))
    experience.get_data_store('Ban_Data').set('Player_' + str(player_data['id']), ds_data)

    await log_channel.send(embed = get_embed(player_data))
    await interaction.response.send_message('%s was permanently banned.' % player_data['name'], ephemeral = True, delete_after = 5.0)

@tree.command(name = 'game_unban', description = 'Unbans a user from AW')
async def slash_command(interaction : discord.Interaction, player : str):
    if interaction.user.get_role(bot_role_id) == None:
        await interaction.response.send_message('You do not have the role needed to use this command.', ephemeral = True, delete_after = 5.0)
        return
    
    log_channel = interaction.guild.get_channel(log_channel_id)
    player_data = get_player_data(player)

    if not player_data:
        await interaction.response.send_message('That player does not exist.', ephemeral = True, delete_after = 5.0)
        return
    
    player_data['moderator'] = interaction.user.id
    player_data['action'] = 'Player Unbanned!'
    player_data['color'] = discord.Color.green()

    experience.get_data_store('Ban_Data').remove('Player_' + str(player_data['id']))

    await log_channel.send(embed = get_embed(player_data))
    await interaction.response.send_message('%s was unbanned.' % player_data['name'], ephemeral = True, delete_after = 5.0)

discord_client.run('')