import arena
import helpers

import discord
from discord.ext import commands
from os import getenv
import random

if __name__ == '__main__':
	matches = []
    
	intents = discord.Intents.default()
	intents.message_content = True

	bot = commands.Bot(command_prefix='//', intents=intents)

	def get_attack_offset(atk_dir: str):
		atk_dir = atk_dir.lower()
		match atk_dir:
			case "up": return [0, -1]
			case "down": return [0, 1]
			case "left": return [-1, 0]
			case "right": return [1, 0]
			case _: return None

	def get_attack_target(weapon_range, position, offset, match_map):
		for i in range(1, weapon_range+1, 1):
			rx = helpers.clamp(position[0]+(offset[0]*i), 1, 10)
			ry = helpers.clamp(position[1]+(offset[1]*i), 1, 10)
			map_target = match_map[rx-1][ry-1]

			if isinstance(map_target, arena.Fighter):
				return map_target
		
		#return None

	async def check_win(ctx, match):
		global matches

		match.remove_dead()

		if len(match.fighters) == 1:
			matches.remove(match)
			await ctx.send("{match.get_current_turn().user.mention} has won!")

	def damage_target(ctx, damage, target, match):
		target.hp -= damage
		match.check_actions_left()
		check_win(ctx, match)

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

			case 0: message = "only admins can end matches"
			case 1: message = "channel has match currently ongoing"
			case 2: message = "no match ongoing in this channel"
			case 3: message = "match already started"
			case 4: message = "please finish your match first"
			case 5: message = "need at least 1 more fighter to start"
			case 6: message = "challenger needs to be one to start match"
			case 7: message = "cannot join, match already full"
			case 8: message = "you are not part of this match"
			case 9: message = "match has not started on this channel"
			case 10: message = f"{ctx.author.mention}, it's not your turn!"
			case 11: message = "you tried to move more than 4 squares"
			case 12: message = "you tried to move into another fighter"
			case 13: message = "the arguements must be proper numbers"
			case 14: message = "please input a valid direction"
			case 15: message = "no target in that direction"
			case _: message = "unknown error occured, this should not be possible"
		
		await ctx.send("Error: " + message)

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
		if not ctx.author.guild_permissions.administrator:
			await send_error(ctx, 0)
			return

		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return
		if not channel_match.started:
			await send_error(ctx, 9)
			return
		
		#channel_match.end_match()
		matches.remove(channel_match)
		await ctx.send(f"Admin {ctx.author} has ended the Battle at the {ctx.channel}!")

	@bot.command()
	async def move(ctx, x, y):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)
		
		try:
			x = int(x)
			y = int(y)
		except ValueError:
			await send_error(ctx, 13)
			return
		if channel_match is None:
			await send_error(ctx, 2)
			return
		if not channel_match.started:
			await send_error(ctx, 9)
			return
		if channel_match.get_current_turn().user != ctx.author:
			await send_error(ctx, 10)
			return
		if (int(x)+int(y)) > 4:
			await send_error(ctx, 11)
			return
		
		move = channel_match.get_current_turn().map_move(int(x), int(y), channel_match.map)
		move_location = channel_match.get_current_turn().x + str(channel_match.get_current_turn().y)
		
		if move == 0:
			await ctx.send(f"{ctx.author.mention} has moved to {move_location}")
		elif isinstance(move, arena.Fighter):
			await send_error(ctx, 12)
			return
		elif isinstance(move, arena.Weapon):
			await ctx.send(f"{ctx.author.mention} has equipped a {channel_match.get_current_turn().equip['name']} and moved to {move_location}")
		elif isinstance(move, arena.Trap):
			await ctx.send(f"{ctx.author.mention} has stepped into a {move.name} trap and moved to {move_location}")

		channel_match.check_actions_left()
		await ctx.send(embed=channel_match.update_map())

	@bot.command()
	async def attack(ctx, atk_dir):
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)
		
		if channel_match is None:
			await send_error(ctx, 2)
			return
		if not channel_match.started:
			await send_error(ctx, 9)
			return
		if channel_match.get_current_turn().user != ctx.author:
			await send_error(ctx, 10)
			return
		
		offset = get_attack_offset(atk_dir)
		if offset is None:
			await send_error(ctx, 14)
			return
		
		attacker = channel_match.get_current_turn()
		target = get_attack_target(attacker.equip['range'], attacker.get_position(), offset, channel_match.map)
		if target is None:
			await send_error(ctx, 15)
			return
		else:
			await ctx.send(f"{attacker.user.mention} has dealt {attacker.equip['damage']} with a {attacker.equip['name']} to {target.user.mention}")
			damage_target(ctx, attacker.equip['damage'], target, channel_match)
			await ctx.send(embed=channel_match.update_map())

	@move.error
	@attack.error
	async def discord_errors(ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send("Error: missing arguements for command used")

	bot.run(getenv("TOKEN"))