import helpers
import battlemap

import random
import discord.embeds

weapons_data = [
	{"name": "fist", "damage": 1, "range": 1},
	{"name": "dagger", "damage": 2, "range": 1},
	{"name": "rapier", "damage": 3, "range": 1},
	{"name": "axe", "damage": 3, "range": 1},
	{"name": "spear", "damage": 2, "range": 2},
]

class Object:
	def __init__(self, x, y, map):
		self.x = chr(x + 96)
		self.y = y
		map[x-1][y-1] = self
	
	def get_position(self):
		return [ord(self.x) - 96, self.y]
		
	def put_in_map(self):
		pass # must override

class Fighter(Object):
	def __init__(self, x, y, map, user, shortcode):
		Object.__init__(self, x, y, map)
		self.user = user
		
		self.move = 4
		self.actions = 2
		self.hp = 12
	
		self.equip = weapons_data[0]

		self.shortcode = shortcode

	def confirm_move(self, x, y, map):
		prev_x, prev_y = self.get_position()
	
		map[prev_x-1][prev_y-1] = 0
		self.x = helpers.num_to_alpha(helpers.clamp(prev_x+x, 1, 10))
		self.y = helpers.clamp(prev_y+y, 1, 10)
		map[helpers.alpha_to_num(self.x)-1][self.y-1] = self

	def map_move(self, x, y, map):
		prev_x, prev_y = self.get_position()
		cx = helpers.clamp(prev_x+x, 1, 10)
		cy = helpers.clamp(prev_y+y, 1, 10)

		destination_object = map[cx-1][cy-1]
		if destination_object == 0:
			self.confirm_move(x, y, map)
			
			return "Empty"
		else:
			obj_type = type(destination_object).__name__
			match obj_type:
				case "Fighter":
					pass
					
				case "Weapon":
					self.equip = destination_object.data
					self.confirm_move(x, y, map)
					
				case "Trap":
					self.hp -= destination_object.damage
					self.confirm_move(x, y, map)
				
			return destination_object
	
	def reset_actions(self):
		self.move = 4
		self.actions = 2
	
	def put_in_map(self):
		return f"/{self.x}{self.y}~{self.shortcode}"

class Weapon(Object):
	def __init__(self, x, y, data, map):
		Object.__init__(self, x, y, map)
		self.data = data
	
	def put_in_map(self):
		return f"/{self.x}{self.y}-{self.data['name']}"

class Trap(Object):
	def __init__(self, x, y, name, damage, map):
		Object.__init__(self, x, y, map)
		self.name = name
		self.damage = damage
	
	def put_in_map(self):
		return f"/{self.x}{self.y}-{self.name}"

class MatchState:
	def __init__(self, ctx):
		self.guild = ctx.guild
		self.channel = ctx.channel
		self.invoker = ctx.author

		self.started = False
		self.fighters = []
		self.weapons = []
		self.traps = []
		self.map = [[0 for i in range(10)] for j in range(10)]

		self.current_turn = 0
		self.current_round = 0

		self.add_fighter(ctx.author)
	
	def is_empty(self, x, y):
		return self.map[x-1][y-1] == 0

	def generate_weapons(self):
		generate = 4

		while generate > 0:
			x = random.randint(1, 10)
			y = random.randint(1, 10)
			data = weapons_data[random.randint(1, len(weapons_data)-1)]

			if self.is_empty(x, y):
				self.weapons.append(Weapon(x, y, data, self.map))
				generate -= 1

	def generate_traps(self):
		generate = 4

		while generate > 0:
			x = random.randint(1, 10)
			y = random.randint(1, 10)
			
			if self.is_empty(x, y):
				self.traps.append(Trap(x, y, "spikes", 2, self.map))
				generate -= 1

	def start_match(self):
		random.shuffle(self.fighters)
		self.generate_weapons()
		self.generate_traps()

		self.current_turn += 1
		self.current_round += 1
		self.started = True
	
	def find_user_in_match(self, user_mention):
		for i in self.fighters:
			if i.user.mention == user_mention:
				return i

	def add_fighter(self, user):
		x = random.randint(1, 10)
		y = random.randint(1, 10)

		while not self.is_empty(x, y):
			x = random.randint(1, 10)
			y = random.randint(1, 10)

		# does not work without profile picture
		# check output of user.avatar.url if no profile
		shortcode = battlemap.get_shortcode(user.avatar.url)
		new = Fighter(x, y, self.map, user, shortcode)

		self.fighters.append(new)
	
	def remove_fighter(self, user):
		obj = self.find_user_in_match(user.mention)
		x, y = obj.get_position()
		self.map[x-1][y-1] = 0
		self.fighters.remove(obj)
	
	def get_current_turn(self):
		return self.fighters[self.current_turn]
	
	def end_turn(self):
		if (self.current_turn + 1) >= len(self.fighters):
			self.current_round += 1
			self.current_turn = 0

			for i in self.fighters:
				i.reset_actions()
		else:
			self.current_turn += 1

	def check_actions_left(self):
		if self.get_current_turn().actions > 1:
			self.get_current_turn().actions -= 1

		else:
			self.end_turn()
	
	def remove_dead(self):
		for i in self.fighters:
			if i.hp <= 0:
				self.remove_fighter(i.user)

	def update_map(self):
		message = 	f"""Current Turn: {self.get_current_turn().user.mention}
						Current Round: {self.current_round}
						Current Actions Left: {self.get_current_turn().actions}
						Current Health: {self.get_current_turn().hp}/12
						Equipped: {self.get_current_turn().equip['name']}"""

		embed = discord.Embed(title="Battlemap", description=message)
		url = battlemap.get_url() + "10x10"
		for i in self.map:
			for j in i:
				if j != 0:
					url = url + j.put_in_map()
	
		embed.set_image(url=url)
		return embed
	
	def display_roster(self):
		message = f"FIGHTERS({len(self.fighters)}/4):\n"

		for i in self.fighters:
			message += f"{self.fighters.index(i)+1}. {i.user.mention}\n"
		
		return discord.Embed(title=f"Battle at {self.channel}!", description=message)