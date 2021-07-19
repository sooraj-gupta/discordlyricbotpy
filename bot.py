import os
import discord
import requests
import json
from dotenv import load_dotenv
from eventemitter import EventEmitter
from youtubesearchpython.__future__ import VideosSearch
prefix = "&"

musixmatch = "https://api.musixmatch.com/ws/1.1/"

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

client = discord.Client()

emitter = EventEmitter()


requestTypes = {
    "getlyricsbysong": "matcher.lyrics.get",
    "search": "track.search",
    "getlyricsbyid": "track.lyrics.get"
}

defaultApiParams = {
    "format":"json",   
     "page_size": "20", 
     "s_track_rating": "desc", 
     "s_artist_rating": "desc", 
     "apikey": "83ff4ead3ace8c3aa2deb86f310ea93f" 
}

state = "default"
tracks = []
trackQuery = ""

def httpRequest( params, requestType ):
    r = requests.get(musixmatch + requestType, params = params)
    result = json.loads( r.content )
    return result

def getTracksByQuery( message, query, params, category ):
    global state 
    params.update( defaultApiParams )
    result = httpRequest( params, requestTypes["search"] )
    track_list = result["message"]["body"]["track_list"]
    tracks = []
    for track in track_list:
        tracks.append( {
            "title": track["track"]["track_name"],
            "artist": track["track"]["artist_name"],
            "album": track["track"]["album_name"],
            "url": track["track"]["track_share_url"],
            "id": track["track"]["track_id"]
        } )
    state = "number"
    embed = discord.Embed( title = "Search results for: " + query, color = 0x00ff00 )
    for index, track in enumerate( track_list ):
        embed.add_field( name = ( str(index + 1) + ". " + track["track"]["track_name"] ), value = track["track"]["artist_name"] )
    emitter.remove_all_listeners()
    async def handleTrackSelection( args ):
        num = args["num"] - 1
        if( args["num"] <= len(tracks) ):
            await message.reply( "Getting lyrics for **" + tracks[num]["title"] + "** by " + tracks[num]["artist"] +"..." )
            trackQuery = tracks[num]["title"] + " by " + tracks[num]["artist"]
            res = await VideosSearch( trackQuery, limit = 1 ).next()
            url = res['result'][0]['link']
            requestParams = { 
                "track_id": tracks[num]["id"]
            }
            requestParams.update( defaultApiParams )
            lyricsResult = httpRequest( requestParams, requestTypes["getlyricsbyid"] )
            lyrics = lyricsResult["message"]["body"]["lyrics"]["lyrics_body"]
            lyrics = lyrics[0: lyrics.index( "******* T" ) ]
            print( lyrics )
            await message.channel.send( embed = discord.Embed( description = lyrics + "\n \n [More Lyrics...](" + tracks[num]["url"] + ") \n [Video]("+ url +")" ) )  

            
        else:
            await message.channel.send( "The number you chose was out of bounds" )
    emitter.on("track_selection", handleTrackSelection)
    return embed
    

class Commands:
    # Help message. Go through each function name in the Commands class and add the name to msg then set add msg to the description of the embed message
    async def help( self, message ):
        '''Prints this message'''
        msg = "**__Commands__**\n"
        for name in dir(self):
            if not name.startswith("__"):
                msg += "`" + name + "`" + " - " + getattr(self, name).__doc__ + "\n"

        await message.channel.send( embed = discord.Embed( title = "Bot Help", description = msg ) )

    #make a request to musixmatch for artist by the message parameter
    async def artist( self, message ):
        '''Returns the top 20 songs of an artist'''
        artist = message.content.replace( prefix + "artist", "" )
        await message.channel.send( embed = getTracksByQuery( message, artist, { "q_artist": artist }, "artist" ) )
    
    # Search for tracks with certain lyrics
    async def lyrics( self, message ):
        '''Returns the top 20 songs with some lyrics'''
        lyrics = message.content.replace( prefix + "lyrics", "" )
        await message.channel.send( embed = getTracksByQuery( message, lyrics, { "q_lyrics": lyrics }, "lyrics" ) )

    # Search for tracks with track name
    async def track( self, message ):
        '''Returns the top 20 songs with the track name'''
        track = message.content.replace( prefix + "track", "" )
        await message.channel.send( embed = getTracksByQuery( message, track, { "q_track": track }, "track" ) )
    
    # Search for tracks with any query
    async def q( self, message ):
        '''Returns the top 20 songs with any query'''
        query = message.content.replace( prefix + "q", "" )
        await message.channel.send( embed = getTracksByQuery( message, query, { "q": query }, "q" ) )

    # Do yt search for a query and display the video name
    async def yt( self, message ):
        '''Returns the top youtube result a query'''        
        query = message.content.replace( prefix + "yt", "" )
        res = await VideosSearch( query, limit = 1 ).next()
        url = res['result'][0]['link']




commands = Commands()

@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")


@client.event
async def on_message(message):
    if( not message.content.startswith(prefix) or message.author.id == client.user.id ):
        return
    
    global state

    key = message.content[len(prefix):].split(" ")[0]
    if( state == "default" ):
        if( key in dir(commands) ):
            await getattr(commands, key)( message )
    elif( state == "number" ):
        print( "in number state" )
        if( key.isdigit() ):
            print( "number" )
            emitter.emit( "track_selection", {"num": int(key) } )
        else:
            if( key in dir(commands) ):
                await getattr(commands, key)( message )        
        state = "default"

client.run(token)