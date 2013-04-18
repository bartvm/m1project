import networkx as nx
import csv
import matplotlib.pyplot as plt
import math

def distance(origin, destination):
	lon1, lat1 = origin
	lon2, lat2 = destination
	radius = 6371009 # m

	lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

	dlat = lat2 - lat1
	dlon = lon2 - lon1
	a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	d = radius * c

	return d

def stations_on_lines(G, lines):
	stations = []
	for connection in G.edges():
		for line in G[connection[0]][connection[1]]['lines']:
			if int(line[0]) in lines:
				stations.append(connection[0])
				stations.append(connection[1])
	return list(set(stations))

def load(stations_file="data/stations.csv", lines_file="data/lines.csv", connections_file="data/connections.csv"):

	f1 = open(stations_file)
	f2 = open(lines_file)
	f3 = open(connections_file)

	stations = csv.reader(f1)
	lines = csv.reader(f2)
	connections = csv.reader(f3)

	stations.next()
	lines.next()
	connections.next()

	G = nx.Graph()
	G.station_positions = {}
	G.station_names = {}
	G.connection_line_ids = {}
	G.connection_line_names = {}
	G.connection_line_colours = {}

	paths = {}

	for station in stations:
		G.add_node(int(station[0]), pos=(float(station[15]), float(station[14])), label=station[11])

	for connection in connections:
		connection = map(int, connection)
		G.add_edge(connection[0], connection[1], weight=distance(G.node[connection[0]]['pos'], G.node[connection[1]]['pos']))
		for line in lines:
			if line[0] == connection[2]:
				line_colour = line[2]
				line_name = line[4]
				f2.seek(0)
				break
		G[connection[0]][connection[1]].setdefault('lines', []).append([connection[2], line_name, line_colour])
	return G

def plot(G):
	edge_colours = ["#" + G[f][t]["lines"][0][2] for f,t in G.edges()]
	nx.draw(G, nx.get_node_attributes(G,'pos'), with_labels=False, font_size=10, labels=nx.get_node_attributes(G,'label'), node_color='#ffffff', edge_color=edge_colours, node_shape='.', node_size=100, width=3)
	plt.show()