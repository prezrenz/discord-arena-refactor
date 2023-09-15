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
			case 5: message = "need at least 1 more fighter to start"
			case 6: message = "challenger needs to be one to start match"
			case 7: message = "cannot join, match already full"
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
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return
		if channel_match.started:
			await send_error(ctx, 3)
			return
		if len(channel_match.fighters) <= 1:
			await send_error(ctx, 5)
			return
		if channel_match.invoker != ctx.author:
			await send_error(ctx, 6)
			return
		
		channel_match.start_match()
		await ctx.send("Battle has started!", embed=channel_match.update_map())

	@bot.command()
	async def join(ctx):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return
		if channel_match.started:
			await send_error(ctx, 3)
			return
		if find_user_in_matches(ctx.author.mention):
			await send_error(ctx, 4)
			return
		if len(channel_match.fighters) >= 4:
			await send_error(ctx, 7)
			return
		
		channel_match.add_fighter(ctx.author)
		await ctx.send(f"{ctx.author.mention} has joined the Battle at the {ctx.channel}!", embed=channel_match.display_roster())

	@bot.command()
	async def retire(ctx):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return

	@bot.command()
	async def end(ctx):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return

	bot.run(getenv("TOKEN"))