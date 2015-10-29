
from parser import parse, ModelParseError
from math import log
from random import random, choice
from copy import copy, deepcopy

buses = {} 
passengers = {}
routes = {}
roads = {}
stops = {} 
mods = {}
stop_rates = {}
potential_events = {} 
current_passenger_id = 0
fileoutput = []
time = 0.0
experiment = False
experimenting_on = {'road':{},'board':[],'disembarks':[],'departs':[],'new_passengers':[],'num_buses':{},'capacity':{}}
optimise_params = False
opt_par_values = []

missed_passengers = {'stops':{},'routes':{}, 'total':0} 
average_passengers = {'buses':{},'routes':{}, 'total':[]}
queueing_time = {'stops':{},'total':[]}
average_waiting_passengers = {'stops':{},'routes':{},'total':[]}

def get_delay(all_rates):
	# Takes input of all delays in the form of an array
	mean = 0
	for rate in all_rates:
		mean = mean + float(rate)
	#mean = len(all_rates)/mean
	mean = 1/mean
	return -mean * log(random())

def main(*args):
	file_name = str(args[0][0])
	if file_name == 'runalltests':
		args[0].append('-tofile')
		#runs through tests and makes sure they're breaking properly
		test_list = {'test/experimentbreak.txt': ModelParseError, 'test/optparsbreak.txt': ModelParseError, 'test/duperoadtest.txt': ModelParseError, 'test/nostopsbreak.txt': ModelParseError, 'test/dupestopbreak.txt': ModelParseError, 'test/dupemodbreak.txt': ModelParseError, 'test/nonfloatroadbreak.txt': ModelParseError, 'test/nonfloatmodbreak.txt': ModelParseError, 'test/missingmodbreak.txt': ModelParseError}
		index = 1
		for test in test_list:
			try:
				#accounting for mods and experiment occasionally carrying over from one sim
				#to the next
				global mods
				mods = {}
				global experiment
				experiment = False
				run_all(test,args)
			except test_list[test] as e:
				print 'Test',index,'passed, message:',e.value
			except Exception: 
				print 'Test',index,'failed'
			else:
				print 'Test',index,'failed'
			finally:
				index += 1
		#runs through an actual scenario and does basic output tests
		print ""
		args[0].append('-runtests')
		run_all('test/5routetest.txt',args)
	else:
		run_all(file_name,args)

def run_all(file_name,args):
	# runs an individual file (all experiment iterations)
	global optimise_params
	optimise_params = False
	sim_config = {}
	sim_config = parse_file(file_name)
	set_up(sim_config)
	end_time = mods['stop_time']
	if '-tofile' in args[0]:
		whereto = 'output.txt'
	else:
		whereto = 0
	showstats = '-showstats' in args[0]
	showevents = '-showevents' in args[0]
	runtests = '-runtests' in args[0]

	if experiment:
		if runtests:
			print "Cannot run tests and an experiment at the same time!"
		if whereto != 0:
			print "Running experiments..."
		exp_headers = {}
		showstats = True

		experiments_to_run = generate_combos(experimenting_on)
		for ex in experiments_to_run:
			# optimised from being loops of setting up entire file to 
			# more efficient changing of sim_config
			reset_sim()
			total = 0.0
			if optimise_params:
				opt_par_values.append(ex)
			for var in ex:
				components = var.split(" ")
				if components[0] == 'road':
					sim_config['roads'][components[1]] = [ex[var]]
				elif components[0] == 'num_buses':
					sim_config['routes'][components[2]]['buses'] = [ex[var]]
				elif components[0] == 'capacity':
					sim_config['routes'][components[2]]['capacity'] = [ex[var]]
				elif components[0] == 'board' or components[0] == 'disembarks' or components[0] == 'departs':
					sim_config['modifiers'][components[0]] = [ex[var]]
				elif components[0] == 'new' and components[1] == 'passengers':
					sim_config['modifiers']['new_passengers'] = [ex[var]]
				elif components[0] == 'enters':
					sim_config['stop_rates'][int(components[1])] = [ex[var]]
				total += ex[var]
				fileoutput.append(var + " " + str(ex[var]))
			set_up(sim_config)
			run_sim(end_time, whereto, showstats, showevents)
			if optimise_params:
				opt_par_values[-1]['total'] = missed_passengers['total'] * total
		if optimise_params:
			i = 0
			max_total = opt_par_values[i]['total']
			for ex in opt_par_values:
				if ex['total'] < max_total:
					i = opt_par_values.index(ex)
					max_total = ex['total']
			print "Optimal parameters: "
			for var in opt_par_values[i]:
				if var != 'total':
					print var + " " + str(opt_par_values[i][var])
	else:
		if optimise_params and 'ignore_warnings' not in mods:
			raise ModelParseError("'optimise parameters' found without an experiment to run it on!")
		if whereto != 0:
			print "Running sim..."
		run_sim(end_time,whereto,showstats, showevents)
		if runtests:
			print "Running tests..."
			test_scenario(fileoutput)

def generate_combos(exp_on):
	# Generates every possible combination of the values being experimented on
	combos = []
	#optimised from two loops running through exp_on (title + content)
	#to one loop and an array of dictionaries holding both

	for variable in exp_on:
		if len(exp_on[variable]) > 0:
			if variable == 'road':
				for val in exp_on[variable]:
					if len(combos) == 0:
						combos.append({str(variable) + " " + str(val): exp_on[variable][val][0]})
					else:
						for c in combos:
							c[str(variable) + " " + str(val)] = exp_on[variable][val][0]
					original_len = len(combos)
					for subval in exp_on[variable][val][1:]:
						for c in range(original_len):
							combos.append(deepcopy(combos[c]))
							combos[-1][str(variable) + " " + str(val)] = subval
			elif variable == 'enters':
				for val in exp_on[variable]:
					if len(combos) == 0:
						combos.append({'enters ' + str(val):exp_on[variable][val][0]})
					else:
						for c in combos:
							c['enters ' + str(val)] = exp_on[variable][val][0]
					original_len = len(combos)
					for subval in exp_on[variable][val][1:]:
						for c in range(original_len):
							combos.append(deepcopy(combos[c]))
							combos[-1]['enters ' + str(val)] = subval
			elif variable == 'num_buses' or variable == 'capacity':
				for val in exp_on[variable]:
					if len(combos) == 0:
						combos.append({str(variable) + " route " + str(val): exp_on[variable][val][0]})
					else:
						for c in combos:
							c[str(variable) + " route " + str(val)] = exp_on[variable][val][0]
					original_len = len(combos)
					for subval in exp_on[variable][val][1:]:
						for c in range(original_len):
							combos.append(deepcopy(combos[c]))
							combos[-1][str(variable) + " route " + str(val)] = subval
			elif variable == 'board' or variable == 'disembarks' or variable == 'departs':
				if len(combos) == 0:
					for val in exp_on[variable]:
						combos.append({str(variable): val})
				else:
					for c in combos:
						c[str(variable)] = exp_on[variable][0]
					original_len = len(combos)
					for val in exp_on[variable][1:]:
						for c in range(original_len):
							combos.append(deepcopy(combos[c]))
							combos[-1][str(variable)] = val
			elif variable == 'new_passengers':
				if len(combos) == 0:
					for val in exp_on[variable]:
						combos.append({'new passengers': val})
				else:
					for c in combos:
						c['new passengers'] = exp_on[variable][0]
					original_len = len(combos)
					for val in exp_on[variable][1:]:
						for c in range(original_len):
							combos.append(deepcopy(combos[c]))
							combos[-1]['new passengers'] = val
						
	return combos

def reset_sim():
	#resets passengers and stat dictionaries before new simulation starts
	global passengers
	passengers = {}
	for stop in stops:
		missed_passengers['stops'][stop] = 0
		queueing_time['stops'][stop] = []
		average_waiting_passengers['stops'][stop] = []
	for bus in buses:
		average_passengers['buses'][bus] = []
	for route in routes:
		missed_passengers['routes'][str(route)] = 0
		average_passengers['routes'][str(route)] = []
		average_waiting_passengers['routes'][str(route)] = []
	missed_passengers['total'] = 0
	average_waiting_passengers['total'] = []
	average_passengers['total'] = []
	queueing_time['total'] = []

def print_all_dicts():
	# Testing method (unused)
	print "passengers: " 
	print passengers
	print ""
	print "routes: " 
	print routes
	print ""
	print "roads: " 
	print roads
	print ""
	print "buses: "
	print buses
	print ""
	print "stops: "
	print stops
	print ""
	print "mods: "
	print mods
	print ""	
	print "potential_events: "
	print potential_events
	print ""

def parse_file(file_name):
	return parse(file_name)

def set_up(sim_config):
	# parsing sim_config and populating dictionaries with simulation data
	# setting up experiments if necessary
	potential_events['new_passengers'] = 1
	potential_events['departs'] = {}
	potential_events['bus_arrive'] = {}
	potential_events['board'] = {}
	potential_events['disembarks'] = {}
	global experimenting_on
	global experiment
	experimenting_on = {'road':{},'board':[],'disembarks':[],'departs':[],'new_passengers':[],'num_buses':{},'capacity':{},'enters':{}}
	global optimise_params

	warnings = sim_config['warnings']

	unused_roads = []
	for road in sim_config['roads']:
		using = sim_config['roads'][road]
		if len(using) > 1:
			experiment = True
			experimenting_on['road'][road] = using
		roads[road] = using[0]
		unused_roads.append(road)
	for stop in sim_config['stops']:
		stops[stop] = {'bus_queue':[], 'routes':[], 'passengers':[]}
		missed_passengers['stops'][stop] = 0
		queueing_time['stops'][stop] = []
		average_waiting_passengers['stops'][stop] = []
		if stop in sim_config['stop_rates']:
			using = sim_config['stop_rates'][stop]
			if len(using) > 1:
				experiment = True
				experimenting_on['enters'][stop] = using
			stop_rates[stop] = sim_config['stop_rates'][stop][0]
		else:
			stop_rates[stop] = 1.0
	for route in sim_config['routes'].keys():
		using_buses = sim_config['routes'][route]['buses']
		using_cap = sim_config['routes'][route]['capacity']
		if len(using_buses) > 1:
			experiment = True
			experimenting_on['num_buses'][route] = using_buses
		if len(using_cap) > 1:
			experiment = True
			experimenting_on['capacity'][route] = using_cap
		for bus in range(sim_config['routes'][route]['buses'][0]):
			bus_id = str(route) + "." + str(bus)
			start_at = sim_config['routes'][route]['stops'][int(bus) % len(sim_config['routes'][route]['stops'])]
			stops[start_at]['bus_queue'].append(bus_id)
			if stops[start_at]['bus_queue'].index(bus_id) == 0:
				q_start_time = "X"
			else:
				q_start_time = 0.0
			buses[bus_id] = {'capacity':sim_config['routes'][route]['capacity'][0], 'position':start_at, 'on_road':'X', 'stops_at':sim_config['routes'][route]['stops'],'passengers_on':[],'queueing_start_time':q_start_time}
			potential_events['disembarks'][bus_id] = {}
			average_passengers['buses'][bus_id] = []
		routes[int(route)] = sim_config['routes'][route]['stops']
		these_stops = routes[int(route)]
		missed_passengers['routes'][route] = 0
		average_passengers['routes'][route] = []
		average_waiting_passengers['routes'][route] = []
		for stop in these_stops:
			stop0 = stop
			stop1 = these_stops[(these_stops.index(stop)+1)%len(these_stops)]
			this_road = str(stop0) + "-" + str(stop1)
			if this_road in unused_roads:
				unused_roads.remove(this_road)
			if this_road not in roads:
				raise ModelParseError("Route " + route + " is missing road " + this_road)
			potential_events['board'][stop] = {}
			stops[stop]['routes'].append(route)
	for mod in sim_config['modifiers']:	
		using = sim_config['modifiers'][mod]
		try:
			if len(using) > 1:
				experiment = True
				experimenting_on[mod] = using
			mods[mod] = using[0]
		except TypeError: 
			#catches if using is an int instead of an array
			mods[mod] = using
		mods['current_passenger_id'] = 1
	if 'board' not in mods or 'disembarks' not in mods or 'departs' not in mods or 'new_passengers' not in mods or 'stop_time' not in mods:
		raise ModelParseError("Mod was missing from input file!")
	if len(unused_roads) > 0:
		warnings.append("Unused road(s): " + str(unused_roads))
	for mod in mods:
		if mods[mod] > mods['stop_time']: 
			warnings.append("Mod " + str(mods[mod]) + " was higher than the end_time mod.")
	if 'ignore_warnings' not in mods and len(warnings) > 0:
		print ""
		for w in warnings:
			print w 
		print ""
		raise ModelParseError("Warnings found!")
	optimise_params = 'optimise_parameters' in mods

def run_sim(end_time,whereto,showstats,showevents):
	# runs an individual simulation (1 iteration of an experiment)
	global fileoutput
	global time
	time = 0.0

	if not experiment:
		fileoutput.append("")
	while time <= end_time:	
		refresh_events()
		rates = [mods['new_passengers']] 
		for bus in potential_events['departs']:
			rates.append(mods['departs'])
		for stop in potential_events['board']:
			for passenger in potential_events['board'][stop]:
				rates.append(mods['board'])
		for bus in potential_events['disembarks']:
			for passenger in potential_events['disembarks'][bus]:
				rates.append(mods['disembarks'])
		for road in potential_events['bus_arrive']:
			for bus in potential_events['bus_arrive'][road]:
				rates.append(roads[road])
		total_delay = get_delay(rates)
		event = pick_event(rates)
		handle_output(event,time,whereto,showevents)

		if showstats:
			route_list = dict.fromkeys(routes.keys(),0.0)
			for stop in stops:
				val = total_delay * float(len(stops[stop]['passengers']))
				average_waiting_passengers['stops'][stop].append(val)
				average_waiting_passengers['total'].append(val)
				for route in stops[stop]['routes']:
					route_list[int(route)] += val
			for route in route_list:
				average_waiting_passengers['routes'][str(route)].append(route_list[route])

		time += total_delay
	if not experiment:
		fileoutput.append("")

	# processing and appending the session's stats
	if showstats:
		stats = []
		for stop in missed_passengers['stops']:
			stats.append("number of missed passengers stop " + str(stop) + " " + str(missed_passengers['stops'][stop]))
		for route in missed_passengers['routes']:
			stats.append("number of missed passengers route " + str(route) + " " + str(missed_passengers['routes'][route]))
		stats.append("number of missed passengers " + str(missed_passengers['total']))
		stats.append("")
		for bus in average_passengers['buses']:
			num_vals = len(average_passengers['buses'][bus]) if len(average_passengers['buses'][bus]) > 0 else 1
			avg = float(sum(average_passengers['buses'][bus]))/num_vals
			stats.append("average passengers bus " + str(bus) + " " + str(avg))
		for route in average_passengers['routes']:
			num_vals = len(average_passengers['routes'][route]) if len(average_passengers['routes'][route]) > 0 else 1
			avg = float(sum(average_passengers['routes'][route]))/num_vals
			stats.append("average passengers route " + str(route) + " " + str(avg))
		num_vals_tot = len(average_passengers['total']) if len(average_passengers['total']) > 0 else 1
		avg_tot = float(sum(average_passengers['total']))/num_vals_tot
		stats.append("average passengers " + str(avg_tot))
		stats.append("")
		for stop in queueing_time['stops']:
			num_vals = len(queueing_time['stops'][stop]) if len(queueing_time['stops'][stop]) > 0 else 1
			avg = float(sum(queueing_time['stops'][stop]))/num_vals
			stats.append("average queueing at stop " + str(stop) + " " + str(avg))
		num_vals_tot = len(queueing_time['total']) if len(queueing_time['total']) > 0 else 1
		avg_tot = float(sum(queueing_time['total']))/num_vals_tot
		stats.append("average queueing at all stops " + str(avg_tot))
		stats.append("")
		for stop in average_waiting_passengers['stops']:
			avg = float(sum(average_waiting_passengers['stops'][stop]))/end_time
			stats.append("average waiting passengers at stop " + str(stop) + " " + str(avg))
		for route in average_waiting_passengers['routes']:
			avg = float(sum(average_waiting_passengers['routes'][route]))/end_time
			stats.append("average waiting passengers on route " + str(route) + " " + str(avg))
		avg_tot = float(sum(average_waiting_passengers['total']))/end_time
		stats.append("average waiting passengers " + str(avg_tot))

		if whereto == 'output.txt':
			fileoutput.append("")
			fileoutput += stats
		else:
			for line in stats:
				print line
	fileoutput.append("")
	if experiment:
		fileoutput.append("")

	if whereto == 'output.txt':
		with open(whereto, 'w') as output:
			for line in fileoutput:
				output.write(line)
				output.write("\n")
	
def pick_event(ratelist):
	# returns a dictionary containing the 'event' item and any other
	# pertinent information
	all_events = sum(ratelist)
	current_pos = 0.0
	choice = random()
	for event in potential_events:
		if event == 'bus_arrive':
			for road in potential_events[event]:
				for bus in potential_events[event][road]:
					probability = roads[road]/all_events
					if current_pos <= choice and choice < (current_pos + probability): 
						chosen = {'event':event,'bus':bus,'dest':potential_events[event][road][bus]}
						arrives(road,bus)
						return chosen
					else:
						current_pos += probability
		elif event == 'board':
			for orig in potential_events[event]:
				for passenger in potential_events[event][orig]:
					probability = mods[event]/all_events
					if current_pos <= choice and choice < (current_pos + probability): 
						bus = stops[orig]['bus_queue'][0]
						dest = passengers[passenger]['destination']
						chosen = {'event':event,'bus':bus,'stop':orig,'destination':dest}
						boards(stops[orig]['bus_queue'][0],passenger)
						return chosen
					else:
						current_pos += probability
		elif event == 'disembarks':
			for bus in potential_events[event]:
				for passenger in potential_events[event][bus]:
					probability = mods[event]/all_events
					if current_pos <= choice and choice < (current_pos + probability):
						chosen = {'event':event,'bus':bus,'stop':buses[bus]['position']}
						disembarks(bus,passenger)
						return chosen
					else:
						current_pos += probability
		elif event == 'departs':
			for bus in potential_events[event]:
				probability = mods[event]/all_events
				if current_pos <= choice and choice < (current_pos + probability):
					missed = 0
					stop = potential_events[event][bus]
					if len(buses[bus]['passengers_on']) >= buses[bus]['capacity']:
						for pas in stops[stop]['passengers']:
							dest = passengers[pas]['destination']
							if dest in buses[bus]['stops_at']:
								missed += 1
					missed_passengers['stops'][stop] += missed
					missed_passengers['routes'][bus.split('.')[0]] += missed
					missed_passengers['total'] += missed
					chosen = {'event':event,'bus':bus,'stop':stop}
					bus_depart(bus,stop)
					return chosen
				else:
					current_pos += probability
		else: 
			# at the moment, this only covers new_passenger
			if event == 'new_passengers':
				probability = mods[event]/all_events
				if current_pos <= choice and choice < (current_pos + probability):
					config = new_passengers()
					chosen = {'event':event, 'origin':config['orig'], 'destination':config['dest']}
					return chosen
				else:
					current_pos += probability
					continue
	fileoutput.append( "This shouldn't have happened! No event was selected this iteration." )

def bus_depart(bus,stop):
	# single-bus depart method
	average_passengers['buses'][bus].append(len(buses[bus]['passengers_on']))
	average_passengers['routes'][bus.split(".")[0]].append(len(buses[bus]['passengers_on']))
	average_passengers['total'].append(len(buses[bus]['passengers_on']))
	stops[stop]['bus_queue'].remove(bus)
	stop_index = buses[bus]['stops_at'].index(stop)
	buses[bus]['position'] = buses[bus]['stops_at'][(stop_index + 1) % len(buses[bus]['stops_at'])]
	next_road = str(stop) + "-" + str(buses[bus]['position'])
	buses[bus]['on_road'] = next_road
	if buses[bus]['queueing_start_time'] != "X":
		t = float(buses[bus]['queueing_start_time'])
		queueing_time['stops'][stop].append(time - t)
		queueing_time['total'].append(time - t)
		buses[bus]['queueing_start_time'] = "X"
	if len(stops[stop]['bus_queue']) > 0 and buses[stops[stop]['bus_queue'][0]]['queueing_start_time'] != "X":
		b = stops[stop]['bus_queue'][0]
		t = float(buses[b]['queueing_start_time'])
		queueing_time['stops'][stop].append(time - t)
		queueing_time['total'].append(time - t)
		buses[b]['queueing_start_time'] = "X"
	del potential_events['departs'][bus]	

def arrives(road,bus):
	# single-bus arrive method
	buses[bus]['on_road'] = 'X'
	stops[buses[bus]['position']]['bus_queue'].append(bus)
	if stops[buses[bus]['position']]['bus_queue'][0] != bus:
		buses[bus]['queueing_start_time'] = time
	else:
		buses[bus]['queueing_start_time'] = "X"
		queueing_time['stops'][buses[bus]['position']].append(0)
		queueing_time['total'].append(0)		
	del potential_events['bus_arrive'][road][bus]

def new_passengers():
	# single-passenger enter-simulation method
	possible_stops = stops.keys()
	orig = choose_from(possible_stops)
	possible_routes = stops[int(orig)]['routes']
	possible_dests = []
	for r in possible_routes:
		possible_dests = possible_dests + routes[int(r)]
	possible_dests = set(possible_dests)
	if orig in possible_dests:
		possible_dests.remove(orig)
	dest = int(choice(list(possible_dests)))
	pass_id = mods['current_passenger_id']
	mods['current_passenger_id'] = mods['current_passenger_id'] + 1
	passengers[pass_id] = {'origin':orig,'destination':dest}
	if bus_available(dest,orig):
		potential_events['board'][orig] = {pass_id:dest}
	stops[orig]['passengers'].append(pass_id)
	return {'orig':orig,'dest':dest}

def choose_from(possible_stops):
	# Extra credit portion
	# Iterates through stop rates and chooses according to probability
	# assigned to each
	choice = random()
	ratesum = 0.0
	current_pos = 0.0
	for stop in possible_stops:
		ratesum += stop_rates[stop]
	while current_pos < 1:
		for stop in possible_stops:
			probability = stop_rates[stop]/ratesum
			if current_pos <= choice and choice < (current_pos + probability):
				return stop
			else:
				current_pos += probability
	fileoutput.append("No origin stop was chosen for a passenger! This shouldn't have happened.")
		

def disembarks(bus_on,pass_id):
	# single-passenger disembark method
	stop = buses[bus_on]['position']
	if buses[bus_on]['position'] == passengers[pass_id]['destination'] and buses[bus_on]['on_road'] == 'X':
		del passengers[pass_id]
		ind = buses[bus_on]['passengers_on'].index(pass_id)
		del buses[bus_on]['passengers_on'][ind]
		del potential_events['disembarks'][bus_on][pass_id]
	else:
		fileoutput.append( "Passenger tried to disembark from bus " + str(bus_on) + " at stop " + str(stop) + ", but either the bus was on road " + str(buses[bus_on]['on_road']) + " or it was not at the correct destination " + str(passengers[pass_id]['destination']) + ". This shouldn't have happened!" )

def boards(bus,pass_id):
	# single-passenger board method
	if buses[bus]['capacity'] > len(buses[bus]['passengers_on']):
		buses[bus]['passengers_on'].append(pass_id)
		stops[buses[bus]['position']]['passengers'].remove(pass_id)
		del potential_events['board'][buses[bus]['position']][pass_id]
	else:
		fileoutput.append( "Bus is full! Cannot add new passenger! This shouldn't have happened." )

def refresh_events():
	# Checks through potential events list and sees if any are 
	# no longer possible. Also checks to see if there are any
	# new potential events and adds them.

	# Deleting no-longer-possible events
	global potential_events
	new_events = deepcopy(potential_events)
	for event in potential_events:
		if event == 'departs': 
			for bus in potential_events[event]:
				if buses[bus]['on_road'] != 'X' or buses[bus]['position'] != potential_events[event][bus] or (buses[bus]['capacity'] > len(buses[bus]['passengers_on']) and want_to_board(bus)) or want_to_disembark(bus):
					del new_events[event][bus]
		elif event == 'bus_arrive':
			for road in potential_events[event]:
				for bus in potential_events[event][road]:
					if buses[bus]['on_road'] == 'X':
						del new_events[event][road][bus]
		elif event == 'board':
			for stop in potential_events[event]:
				if len(stops[stop]['bus_queue']) > 0:
					bus = stops[stop]['bus_queue'][0]
					for pas in potential_events[event][stop]:
						if passengers[pas]['destination'] not in buses[bus]['stops_at'] or buses[bus]['capacity'] <= len(buses[bus]['passengers_on']) or pas not in stops[stop]['passengers']:
							del new_events[event][stop][pas]
				else:
					del new_events[event][stop]
		elif event == 'disembarks':
			for bus in potential_events[event]:
				for pas in potential_events[event][bus]:
					if pas not in buses[bus]['passengers_on'] or buses[bus]['position'] != passengers[pas]['destination'] or buses[bus]['on_road'] != 'X':
						del new_events[event][bus][pas]
	
	# Adding newly-possible events
	all_buses = buses.keys()
	for stop in stops: 
		#updating 'board' event
		if len(stops[stop]['bus_queue']) > 0:
			bus_0 = stops[stop]['bus_queue'][0] 
			buses_not_departing = set()
			for pas in stops[stop]['passengers']:
				if passengers[pas]['destination'] in buses[bus_0]['stops_at'] and buses[bus_0]['capacity'] > len(buses[bus_0]['passengers_on']):
					new_events['board'][stop] = {pas:passengers[pas]['destination']}
					buses_not_departing.add(bus_0)
		#updating 'disembarks' event
		for bus in stops[stop]['bus_queue']:
			if bus in all_buses:
				all_buses.remove(bus)
			for pas in buses[bus]['passengers_on']:
				if passengers[pas]['destination'] == stop:
					new_events['disembarks'][bus][pas] = passengers[pas]['destination']
					buses_not_departing.add(bus)
			#updating 'departs' event
			depart = True
			if bus in buses_not_departing:
				continue
			else:
				for pas in stops[stop]['passengers']:
					dest = passengers[pas]['destination']
					if dest in buses[bus]['stops_at'] and buses[bus]['capacity'] > len(buses[bus]['passengers_on']):
						depart = False
			if depart:
				new_events['departs'][bus] = buses[bus]['position']
	for bus in all_buses: #updating 'bus_arrive' event
		road = buses[bus]['on_road']
		if road != 'X':
			new_events['bus_arrive'][road] = {bus:buses[bus]['position']}

	potential_events = new_events
				

def want_to_board(bus):
	#checks to see if there are any passengers who want to board a bus
	stop = buses[bus]['position']
	for pas in stops[stop]['passengers']:
		if passengers[pas]['destination'] in buses[bus]['stops_at']:
			return True
	return False

def want_to_disembark(bus):
	#checks to see if there are any passengers who want to disembark from a bus
	stop = buses[bus]['position']
	for pas in buses[bus]['passengers_on']:
		if passengers[pas]['destination'] == stop:
			return True
	return False

def bus_available(dest_stop, stop_id):
	# checks to see if a bus for the correct route is currently
	# at a stop, at the front of the queue, and not at full capacity
	if len(stops[stop_id]['bus_queue']) == 0:
		return False
	front_bus = stops[stop_id]['bus_queue'][0]
	front_bus_stops = buses[front_bus]['stops_at']
	return dest_stop in front_bus_stops
		
def handle_output(event,time,whereto,showevents):
	# parses output event and adds to fileoutput if necessary
	kind = event['event']
	if kind == 'new_passengers':
		x = "A new passenger enters at stop " + str(event['origin']) + " with destination " + str(event['destination']) + " at time " + str(time)
		if showevents or not experiment:
			fileoutput.append(x)
			if whereto != 'output.txt':
				print x
	elif kind == 'bus_arrive':
		x = "Bus " + str(event['bus']) + " arrives at stop " + str(event['dest']) + " at time " + str(time)
		if showevents or not experiment:
			fileoutput.append(x)
			if whereto != 'output.txt':
				print x
	elif kind == 'board':
		x = "Passenger boards bus " + str(event['bus']) + " at stop " + str(event['stop'])+ " with destination " + str(event['destination']) + " at time " + str(time)
		if showevents or not experiment:
			fileoutput.append(x)
			if whereto != 'output.txt':
				print x
	elif kind == 'disembarks':
		x = "Passenger disembarks bus " + str(event['bus']) + " at stop " + str(event['stop']) + " at time " + str(time)
		if showevents or not experiment:
			fileoutput.append(x)
			if whereto != 'output.txt':
				print x
	elif kind == 'departs':
		x = "Bus " + str(event['bus']) + " leaves stop " + str(event['stop']) + " at time " + str(time)
		if showevents or not experiment:
			fileoutput.append(x)
			if whereto != 'output.txt':
				print x

def test_scenario(content):
	#Takes the output of a scenario as an array and parses for accuracy
	bus_list= {'blank':{}}
	for bus in buses:
		bus_list[bus] = {}
		bus_list[bus]['current_pos'] = 0	
	line_index = 1
	failure_list = []
	
	for line in content[1:]:
		components = line.split(" ")
		if "missed passengers" in line or len(components) <= 1:
			#accounts for if the test hits the stats block or an empty line
			break
		bus = 'blank'
		if "leaves stop" in line:
			i = components.index('stop')
			j = components.index('Bus')
			bus = components[j+1]
			pos = int(components[i+1])
			if bus_list[bus]['current_pos'] != 0 and int(bus_list[bus]['current_pos']) != pos:
				failure_list.append("Bus " + bus + " left the wrong stop on line " + str(line_index))
			bus_list[bus]['current_pos'] = pos
		if "arrives at stop" in line:
			i = components.index('stop')
			j = components.index('Bus')
			bus = components[j+1]
			prev = bus_list[bus]['current_pos']
			bus_stops = buses[bus]['stops_at']
			intended_next = bus_stops[(bus_stops.index(prev)+1)%len(bus_stops)]
			if components[i+1] != str(intended_next):
				failure_list.append( "Bus " + bus + " arrived at wrong stop on line " + str(line_index))
			bus_list[bus]['current_pos'] = components[i+1]
		if "boards bus" in line:
			i = components.index('stop')
			j = components.index('bus')
			k = components.index('destination')
			bus = components[j+1]
			if bus_list[bus]['current_pos'] == 0:
				bus_list[bus]['current_pos'] = int(components[i+1])
			else:
				if int(bus_list[bus]['current_pos']) != int(components[i+1]):
					failure_list.append("Passenger boarded bus " + bus + " at incorrect stop " + components[i+1] + " on line " + str(line_index))
			if int(components[k+1]) not in buses[bus]['stops_at']:
				failure_list.append("Passenger boarded bus " + bus + " for incorrect destination " + components[k+1])
		if "shouldn't have happened" in line:
			failure_list.append("Other error occured in line " + str(line_index) + ": " + line)
		line_index += 1

	if len(failure_list)>0:
		for out in failure_list:
			print out
	else:
		print "No failures!"


if __name__ == "__main__":
	import sys
	main(sys.argv[1:])


