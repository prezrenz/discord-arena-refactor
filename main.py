import arena

import discord
from discord.ext import commands
from os import getenv
import random

if __name__ == '__main__':
	matches = []
    
	intents = discord.Intents.default()
	intents.message_content = True

	bot = commands.Bot(command_prefix='//', intents=intents)

	def find_user_in_matches(user_mention):
		global matches
		
		if len(matches) == 0:
			return None
		
		for i in matches:
			if i.find_user_in_match(user_mention):
				return i
		
		return None

	def get_match_in_channel(channel, guild):
		global matches

		if len(matches) == 0:
			return None

		for i in matches:
			if i.channel == channel and i.guild == guild:
				return i
		
		return None

	async def send_error(ctx, error_code):
		
		match error_code:

			case 1: message = "channel has match currently ongoing"
			case 2: message = "no match ongoing in this channel"
			case 3: message = "match already started"
			case 4: message = "please finish your match first"
			case _: message = "unknown error occured, this should not be possible"
		
		await ctx.send(message)

	@bot.command()
	async def challenge(ctx):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match:
			await send_error(ctx, 1)
			return
		
		if find_user_in_matches(ctx.author.mention):
			await send_error(ctx, 4)
			return
		
		new = arena.MatchState(ctx)
		matches.append(new)
		await ctx.send(f"{ctx.author.mention} has challenged this channel!", embed=new.display_roster())

	@bot.command()
	async def start(ctx):
		await send_error(ctx, 0)

	@bot.command()
	async def join(ctx):
		await send_error(ctx, 0)

	@bot.command()
	async def retire(ctx):
		await send_error(ctx, 0)

	@bot.command()
	async def end(ctx):
		await send_error(ctx, 0)

	bot.run(getenv("TOKEN"))