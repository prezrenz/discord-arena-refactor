from typing import Any
import arena
import helpers

import discord
from discord.ext import commands
from os import getenv
import random

class ArenaHelp(commands.MinimalHelpCommand):
	async def send_bot_help(self, mapping):
		embed = discord.Embed(title="Arena Help")
		getting_started = 	"""
							To start a fight in the channel, use the `//challenge` command
							For those who want to join, use the `//join` command
							Once there is at least two combatants,
							Fighter No. 1 in the roster can use the `//start` command to start the fight

							Admins can use the `//end` command to end an ongoing match, and those who
							joined a match before starting can use the `//retire` command to back out
							
							The other commands are action commands, good luck
							"""
		
		embed.add_field(name="Getting Started", value=getting_started, inline=True)

		for cog, commands in mapping.items():
			command_signatures = [self.get_command_signature(c) for c in commands]
			if command_signatures:
				embed.add_field(name="Commands", value='\n'.join(command_signatures), inline=False)
		
		channel = self.get_destination()
		await channel.send(embed=embed)
	
	async def send_command_help(self, command):
		embed = discord.Embed(title=self.get_command_signature(command), color=discord.Color.dark_blue())

		if command.help:
			embed.description = command.help
		
		channel = self.get_destination()
		await channel.send(embed=embed)

if __name__ == '__main__':
	matches = []
    
	intents = discord.Intents.default()
	intents.message_content = True

	bot = commands.Bot(command_prefix='//', intents=intents)
	bot.help_command = ArenaHelp()

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

	def get_ranged_distance(origin, target):
		return abs(target[0]-origin[0]) + abs(target[1]-origin[1])

	def move_shove_target(match, offset, target):
		target.map_move(offset[0]*2, offset[1]*2, match.map)

	async def check_win(ctx, match):
		global matches

		match.remove_dead()

		if len(match.fighters) == 1:
			matches.remove(match)
			await ctx.send(f"{match.fighters[0].user.mention} has won!")

	async def damage_target(ctx, damage, target, match):
		target.hp -= damage
		match.check_actions_left()
		await check_win(ctx, match)

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

	async def send_error(ctx, error_code, *argv):
		
		match error_code:

			case 0: message = "only admins can end matches"
			case 1: message = "channel has match currently ongoing"
			case 2: message = "no match ongoing in this channel"
			case 3: message = "match already started"
			case 4: message = "please finish your match first"
			case 5: message = "need at least 1 more fighter to start"
			case 6: message = "Fighter #1 needs to be one to start match"
			case 7: message = "cannot join, match already full"
			case 8: message = "you are not part of this match"
			case 9: message = "match has not started on this channel"
			case 10: message = f"{ctx.author.mention}, it's not your turn!"
			case 11: message = "you tried to move more than 4 squares"
			case 12: message = "you tried to move into another fighter"
			case 13: message = "the arguements must be proper numbers"
			case 14: message = "please input a valid direction"
			case 15: message = "no target in that direction"
			case 16: message = "match has already started, fight to the death!"
			case 17: message = f"you must equip {argv[0]} to use {argv[1]} command"
			case 18: message = f"no target called {argv[0]} found"
			case 19: message = "target is out of range of 5 squares"
			case _: message = "unknown error occured, this should not be possible"
		
		await ctx.send("Error: " + message)

	@bot.command()
	async def challenge(ctx):
		"""
		Challenge the current channel and start looking for other combatants.
		Only 1 match per channel is allowed.
		"""
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
		"""
		Start the match in the current channel.
		Fighter No. 1 in the roster must start the fight.
		"""
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
		"""
		Join a match in the current channel if there are any.
		"""
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
		"""
		Back out from the match you joined in the current channel.
		"""
		global matches

		channel_match = get_match_in_channel(ctx.channel, ctx.guild)

		if channel_match is None:
			await send_error(ctx, 2)
			return
		if not channel_match.started:
			channel_match.remove_fighter(ctx.author)
		else:
			await send_error(ctx, 16)
			return
		if not channel_match.fighters:
			matches.remove(channel_match)
			await ctx.send(f"Admin {ctx.author} has ended the Battle at the {ctx.channel}!")
			return
		else:
			channel_match.invoker = channel_match.fighters[0].user

		await ctx.send(f"{ctx.author} has retired from the match", embed=channel_match.display_roster())

	@bot.command()
	async def end(ctx):
		"""
		***FOR ADMINS ONLY***

		End or cancel the match on the current channel, if there are any.
		"""
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
		"""
		Used to move around the map via the x and y axis.
		You can only move 4 squares, x and y must not total greater than 4.
		Negative x is left, positive x is right.
		Negative y is up, positive y is down.

		***PARAMATERS***:
		`x` - positive or negative number of squares to move in the x axis
		`y` - positive or negative number of squares to move in the y axis

		***EXAMPLE***:
		`//move 0 0` to skip an action

		`//move 1 0` to move 1 square to the right
		`//move -1 0` to move 1 square to the left

		`//move 1 2` to move 1 square left and 2 squares down
		"""
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
		if (abs(x)+abs(y)) > 4:
			await send_error(ctx, 11)
			return
		
		invoker = channel_match.get_current_turn()
		move = invoker.map_move(int(x), int(y), channel_match.map)
		move_location = invoker.x + str(invoker.y)
		
		if move == 0:
			await ctx.send(f"{ctx.author.mention} has moved to {move_location}")
		elif move == invoker:
			await ctx.send(f"{ctx.author.mention} has not moved and skipped an action")
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
		"""
		Attack in a certain direction, and damage an enemy
		if there are any in the direction. Attack range depend on weapon.

		***ARGUEMENTS***:
		`atk_dir` - must be the directions `up`, `down`, `left`, or `right`
		"""
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
		else:
			await ctx.send(f"{attacker.user.mention} has dealt {attacker.equip['damage']} with a {attacker.equip['name']} to {target.user.mention}")
			await damage_target(ctx, attacker.equip['damage'], target, channel_match)
			await ctx.send(embed=channel_match.update_map())

	@bot.command()
	async def throw(ctx, target_mention):
		"""
		***SPECIAL COMMAND: REQUIRES DAGGER***
		Throw a dagger at the mentioned user, if user is in match.
		Will succeed if the target is within 5 squares from your square.

		***ARGUEMENTS***:
		`target_mention` - must be an `@mention` of a target in match
		"""
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
		
		attacker = channel_match.get_current_turn()
		if attacker.equip['name'] != "dagger":
			await send_error(ctx, 17, "dagger", "throw")
			return
		
		target = channel_match.find_user_in_match(target_mention)
		if target is None:
			await send_error(ctx, 18, target_mention)
			return
		
		distance = get_ranged_distance(attacker.get_position(), target.get_position())
		if distance > 5:
			await send_error(ctx, 19)
		else:
			await ctx.send(f"{attacker.user.mention} threw a dagger at {target_mention}, dealing {attacker.equip['damage']}")
			await damage_target(ctx, attacker.equip['damage'], target, channel_match)
			await ctx.send(embed=channel_match.update_map())

	@bot.command()
	async def shove(ctx, atk_dir):
		"""
		***SPECIAL COMMAND: REQUIRES AXE***
		Shove the target in the specified direction and push
		them 2 squares in that direction and deal 1 damage.

		***ARGUEMENTS***:
		`atk_dir` - must be the directions `up`, `down`, `left`, or `right`
		"""
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
		
		attacker = channel_match.get_current_turn()
		if attacker.equip['name'] != "axe":
			await send_error(ctx, 17, "axe", "shove")
			return

		offset = get_attack_offset(atk_dir)
		if offset is None:
			await send_error(ctx, 14)
			return

		target = get_attack_target(attacker.equip['range'], attacker.get_position(), offset, channel_match.map)
		if target is None:
			await send_error(ctx, 15)
		else:
			await ctx.send(f"{attacker.user.mention} has shoved {target.user.mention} by 2 square with a {attacker.equip['name']} and dealt 1 damage")
			move_shove_target(channel_match, offset, target)
			await damage_target(ctx, 1, target, channel_match)
			await ctx.send(embed=channel_match.update_map())

	@bot.command()
	async def disarm(ctx, atk_dir):
		"""
		***SPECIAL COMMAND: REQUIRES RAPIER***
		Removes the weapon of target in the specified direction
		and force them to use their fists.

		***ARGUEMENTS***:
		`atk_dir` - must be the directions `up`, `down`, `left`, or `right`
		"""
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
		
		attacker = channel_match.get_current_turn()
		if attacker.equip['name'] != "rapier":
			await send_error(ctx, 17, "rapier", "disarm")
			return

		offset = get_attack_offset(atk_dir)
		if offset is None:
			await send_error(ctx, 14)
			return

		target = get_attack_target(attacker.equip['range'], attacker.get_position(), offset, channel_match.map)
		if target is None:
			await send_error(ctx, 15)
		else:
			await ctx.send(f"{attacker.user.mention} has disarmed {target.user.mention}")
			target.equip = arena.weapons_data[0]
			await ctx.send(embed=channel_match.update_map())

	@move.error
	@attack.error
	@throw.error
	@shove.error
	@disarm.error
	async def discord_errors(ctx, error):
		if isinstance(error, commands.MissingRequiredArgument):
			await ctx.send("Error: missing arguements for command used")

	bot.run(getenv("TOKEN"))