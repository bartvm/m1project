import networkx as nx
import csv
import matplotlib.pyplot as plt

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
		G.add_node(station[0], pos=(float(station[15]), float(station[14])), label=station[11])

	for connection in connections:
		G.add_edge(connection[0], connection[1])
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