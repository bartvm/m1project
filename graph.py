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
			if line[0] in lines:
				stations.append(connection[0])
				stations.append(connection[1])
	return list(set(stations))

def load(exclude=[], stations_file='data/stations.csv', lines_file='data/lines.csv', connections_file='data/connections.csv'):

	# Open and load the CSV files

	f1 = open(stations_file)
	f2 = open(lines_file)
	f3 = open(connections_file)

	stations = csv.DictReader(f1)
	lines = csv.DictReader(f2)
	connections = csv.DictReader(f3)

	# Create the graph

	G = nx.Graph()

	for station in stations:
		G.add_node(int(station['id']), pos=(float(station['lon']), float(station['lat'])), label=station['name'])

	for connection in connections:
		if not int(connection['line_id']) in exclude:
			G.add_edge(int(connection['station1_id']), int(connection['station2_id']), weight=distance(G.node[int(connection['station1_id'])]['pos'], G.node[int(connection['station2_id'])]['pos']))
			for line in lines:
				if line['id'] == connection['line_id']:
					line_colour = line['color']
					line_name = line['name']
					f2.seek(0)
					break
			G[int(connection['station1_id'])][int(connection['station2_id'])].setdefault('lines', []).append([int(connection['line_id']), line_name, line_colour])

	degrees = G.degree()
	orphans = [n for n in degrees if degrees[n] == 0]
	G.remove_nodes_from(orphans)

	return G

def plot(G):
	edge_colours = ['#' + G[f][t]['lines'][0][2] for f,t in G.edges()]
	nx.draw(G, nx.get_node_attributes(G,'pos'), with_labels=False, font_size=10, labels=nx.get_node_attributes(G,'label'), node_color='#ffffff', edge_color=edge_colours, node_shape='.', node_size=100, width=3)
	plt.show()