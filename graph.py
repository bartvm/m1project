import networkx as nx
import csv
import matplotlib.pyplot as plt
import math
from random import choice

def distance(G, origin, destination, pos='pos'):
	lon1, lat1 = G.node[origin][pos]
	lon2, lat2 = G.node[destination][pos]
	radius = 6371.009 # km

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
			G.add_edge(int(connection['station1_id']), int(connection['station2_id']), distance=distance(G, int(connection['station1_id']), int(connection['station2_id'])))
			for line in lines:
				if line['id'] == connection['line_id']:
					line_colour = line['color']
					line_name = line['name']
					f2.seek(0)
					break
			G[int(connection['station1_id'])][int(connection['station2_id'])].setdefault('lines', []).append([int(connection['line_id']), line_name, line_colour])

	# In case some lines were excluded, remove orphan nodes

	degrees = G.degree()
	orphans = [n for n in degrees if degrees[n] == 0]
	G.remove_nodes_from(orphans)

	return G

def plot(G):
	edge_colours = ['#' + G[f][t]['lines'][0][2] for f,t in G.edges()]
	nx.draw(G, nx.get_node_attributes(G,'pos'), with_labels=False, font_size=10, labels=nx.get_node_attributes(G,'label'), node_color='#ffffff', edge_color=edge_colours, node_shape='.', node_size=100, width=3)
	plt.show()

def random_removal_largest_cluster(G, runs=1, plot=False):
	data = [0 for i in range(len(G.nodes()) + 1)]
	for i in range(runs):
		H = G.copy()
		while len(H.nodes()) > 0:
			max_cluster = max(len(cluster) for cluster in nx.connected_components(H))
			data[len(G.nodes()) - len(H.nodes())] += float(max_cluster) / len(G.nodes())
			H.remove_node(choice(H.nodes()))
	data = [value / runs for value in data]
	if plot:
		return [[float(i) / len(G.nodes()) for i in range(len(G.nodes()) + 1)], data]
	else:
		return data

def random_removal_efficiency(G, runs=1, plot=False):
	data = [0 for i in range(len(G.nodes()) + 1)]
	for i in range(runs):
		H = G.copy()
		while len(H.nodes()) > 1:
			summation = 0
			for station in H.nodes():
				destinations = nx.single_source_shortest_path_length(H, station)
				summation += sum([1. / destinations[j] for j in destinations if not j == station])
			data[len(G.nodes()) - len(H.nodes())] += \
				1. / (len(H.nodes()) * (len(H.nodes()) - 1)) * summation
			H.remove_node(choice(H.nodes()))
	data = [value / runs for value in data]
	if plot:
		return [[float(i) / len(G.nodes()) for i in range(len(G.nodes()) + 1)], data]
	else:
		return data
