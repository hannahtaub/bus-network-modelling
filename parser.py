
from re import split


def parse(filename):
	# returns a nested dictionary modelinput, with routes, 
	# roads, modifiers, and the list of all stops as sub-dictionaries 

	warnings = []
	model_input = {}
	all_routes = {}
	all_roads = {}
	all_modifiers = {}
	all_stops = set([])
	all_stop_rates = {}
	try:
		with open(filename, 'r') as model_file:
			# avoiding iterating over empty space forever 
			current_line = model_file.readline()
			next_line = "--"
			while(current_line != next_line or current_line != ""):
				line = split(" +",current_line)
				line_type = line[0]
				if(line_type == ("#")):
					current_line = next_line
					next_line = model_file.readline()
					continue
				elif(line_type == ("route")):
					# enters data in dictionary in form:
					# {"routes":{1:{"stops":[1,2,3], "buses":4, "capacity":50}}}
					route_return = route_parse(line)
					route = route_return[0]
					warnings += route_return[1]
					route_nodupes = set(route['stops'])
					if len(route['stops']) <= 1:
						raise ModelParseError(str(len(route_nodupes)) + " stop(s) given for route " + str(line[1]))
					elif len(route['stops']) != len(route_nodupes):
						raise ModelParseError("Duplicated stop on route " + str(line[1]))
				
					else:
						if line[1] in all_routes:
							warnings.append("Route " + line[1] + " was duplicated.")
						all_routes[line[1]] = route

				elif(line_type == ("road")):
					# enters data in dictionary in form:
					# {"roads":{"1-2":0.3}}
					if (line[1] + "-" + line[2]) in all_roads:
						warnings.append("Road " + line[1] + "-" + line[2] + " was duplicated.")
					road_return = road_parse(line)
					all_roads[line[1] + "-" + line[2]] = road_return[0]
					warnings += road_return[1]

				elif(line_type in ["board", "disembarks", "departs"]):
					# enters data in dictionary in form:
					# {"modifiers":{"board":1.0}}
					if line_type in all_modifiers:
						warnings.append("Mod " + str(line_type) + " was duplicated.")
					mod_return = mod_parse(line, 1)
					all_modifiers[line_type] = mod_return[0]
					warnings += mod_return[1]

				elif(line_type in ["new", "stop"]):
					# enters data in dictionary in form:
					# {"modifiers":{"new_passengers":8.0}}
					if line_type + "_" + line[1] in all_modifiers:
						warnings.append("Mod " + str(line_type + "_" + line[1]) + " was duplicated.")
					mod_return = mod_parse(line, 2)
					all_modifiers[line_type + "_" + line[1]] = mod_return[0]
					warnings += mod_return[1]

				elif(line_type in ["ignore", "optimise"]):
					# enters data in dictionary in form:
					#{"modifiers":{'ignore_warnings':1}}
					mod = line_type + "_" + line[1].rstrip()
					if mod in all_modifiers:
						warnings.append("Mod " + str(mod) + " was duplicated.")
					all_modifiers[mod] = 1
			
				elif(line_type == "enters"):
					# enters data in dictionary in form:
					#{"stop_rates":{1:0.9}}
					if int(line[1]) in all_stop_rates:
						warnings.append("Stop rate " + line[1] + " was duplicated.")
					stop_return = stop_parse(line)
					all_stop_rates[int(line[1])] = stop_return[0]
					warnings += stop_return[1]

				current_line = next_line
				next_line = model_file.readline()
	except IOError:
		raise ModelParseError("No such file exists!")
	for route in all_routes:
		all_stops |= set(all_routes[route]['stops'])
	model_input = {"routes":all_routes, "roads":all_roads, "modifiers":all_modifiers, "stops":list(all_stops), "warnings":warnings, "stop_rates":all_stop_rates}	
	return model_input

def route_parse(line_in):
	warnings = []
	stop_loc = line_in.index("buses")
	bus_stops = []
	for l in line_in[3:stop_loc]:
		try:
			stop = int(l)
		except ValueError:
			raise ModelParseError("Non-integer value given in route stop list.")
		else:
			bus_stops.append(stop)
	if 'experiment' in line_in:
		indices = [i for i, x in enumerate(line_in) if x == "experiment"]
		for i in indices:
			try:
				subject = line_in[i-1]
				if subject == 'capacity':
					cap = list(map(int,line_in[i+1:]))
					if len(cap) == 1:
						warnings.append("An 'experiment' was found, but only one variable was present.")
					if len(cap) == 0:
						raise ModelParseError("No values given after 'experiment' for buses in route line.")
					if line_in[stop_loc+1] != 'experiment':
						num_buses = [int(line_in[stop_loc+1])]
				elif subject == 'buses':
					j = line_in.index('capacity')
					num_buses = list(map(int,line_in[stop_loc+2:j]))
					if len(num_buses) == 1:
						warnings.append("An 'experiment' was found, but only one variable was present.")
					if len(num_buses) == 0:
						raise ModelParseError("No values given after 'experiment' for capacity in route line.")
					if line_in[j+1] != 'experiment':
						cap = [int(line_in[j+1])]
			except IndexError:
				raise ModelParseError("Unexpected 'experiment' encountered when parsing route line.")
			except ValueError:
				raise ModelParseError("Non-integer value given in route line.")
	else:
		try:
			cap = [int(line_in[stop_loc + 3])]
			num_buses = [int(line_in[stop_loc + 1])]
		except ValueError:
			raise ModelParseError("Non-integer value given in route line.")
	return [{'stops':bus_stops, 'buses':num_buses, 'capacity':cap},warnings]

def road_parse(line_in):
	warnings = []
	if 'experiment' in line_in:
		i = line_in.index('experiment')
		try:
			rate = map(float,line_in[i+1:])
			if len(rate) == 1:
				warnings.append("An 'experiment' was found, but only one variable was present.")
			if len(rate) == 0:
				raise ModelParseError("No values given after 'experiment' for road rate(s).")
		except ValueError:
			raise ModelParseError("ValueError: Non-float value given for road rate.")
		except IndexError:
			raise ModelParseError("No values given after 'experiment' for road rate(s).")
		else:
			return [list(rate),warnings]
	else:
		try:
			rate = float(line_in[3])
		except ValueError:
			raise ModelParseError("ValueError: Non-float value given for road rate.")
		else:
			return [[rate],warnings]

def stop_parse(line_in):
	warnings = []
	if 'experiment' in line_in:
		i = line_in.index('experiment')
		stop = line_in[1]
		try: 
			val = map(float, line_in[i+1:])
			if len(val) == 1:
				warnings.append("An 'experiment' was found in stop " + stop + ", but only one variable was present.")
			if len(val) == 0:
				raise ModelParseError("No values given after 'experiment' for stop " + stop)
		except ValueError:
			raise ModelParseError("ValueError: Non-float value given for stop " + stop)
		except IndexError:
			raise ModelParseError("No values given after 'experiment' for mod " + stop)
		else:
			return [val,warnings]
	else:
		try:
			val = float(line_in[2])
		except ValueError:
			raise ModelParseError("Non-float value given in stop line.")
		return [[val],warnings]

def mod_parse(line_in, index):
	warnings = []
	if 'experiment' in line_in:
		i = line_in.index('experiment')
		mod = ' '.join(line_in[0:i])
		try: 
			val = map(float, line_in[i+1:])
			if len(val) == 1:
				warnings.append("An 'experiment' was found in mod '" + mod + "', but only one variable was present.")
			if len(val) == 0:
				raise ModelParseError("No values given after 'experiment' for mod  '" + mod + "'")
		except ValueError:
			raise ModelParseError("ValueError: Non-float value given for mod '" + mod + "'")
		except IndexError:
			raise ModelParseError("No values given after 'experiment' for mod '" + mod + "'")
		else:
			return [val,warnings]
	else:
		try:
			val = float(line_in[index])
		except ValueError:
			raise ModelParseError("Non-float value given in modifier line.")
		return [[val],warnings]

class ModelParseError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)


