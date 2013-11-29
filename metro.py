#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""This module creates classes to perform network analysis on metro networks.

Classes include the network itself, lines, services on these lines, stations
and properties for all these.
"""
from collections import Counter, defaultdict
from itertools import groupby, permutations, product
import csv
import networkx as nx
import heapq
import numpy
import pdb


def find(f, seq):
    """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item):
            return item


class MetroError(Exception):
    """Base class for exceptions"""
    pass


class Network(object):
    """Network class with global network properties and the structure. It
    contains stations, lines, services and nodes.
    """
    def __init__(self, name):
        self.name = name

        self.station = set()
        self.line = set()
        self.service = set()
        self.node = set()

    def __repr__(self):
        return "<Network %s>" % self.name

    def __iter__(self):
        return iter(self.station)

    def __contains__(self, item):
        if isinstance(item, Station):
            return item in self.station
        elif isinstance(item, tuple):
            return item[0].isneighbor(item[1])
        else:
            raise MetroError("Service can only contain stations or edges")

    def __len__(self):
        return len(self.station)

    def read_csv(self, stations='stations.csv', lines='lines.csv',
                 services='services.csv'):
        if self.station:
            raise MetroError("Cannot import twice")
        with open(stations) as f:
            [Station(int(station['id']), station['name'],
                     (float(station['lat']), float(station['lon'])), self)
             for station in csv.DictReader(f)]
        with open(lines) as f:
            [Line(int(line['id']), line['name'],
                  line['color'], self) for line in csv.DictReader(f)]
        with open(services) as f:
            for connection in csv.DictReader(f):
                origin = find(lambda station: station.id ==
                              int(connection['origin']), self.station)
                destination = find(lambda station: station.id ==
                                   int(connection['destination']),
                                   self.station)
                line = find(lambda line: line.id == int(connection['line']),
                            self.line)
                service = find(lambda service:
                               service.id == int(connection['service']) and
                               service.line.id == int(connection['line']),
                               self.service)
                if not service:
                    service = Service(int(connection['service']), line)
                service.add_connection(origin, destination,
                                       int(connection['timetabled']))
        line_to_release = set()
        for line in self.line:
            if not line.service:
                line_to_release.add(line)
        while line_to_release:
            line_to_release.pop().release()

    def graph(self, weighting='time', transfers=True):
        if transfers:
            assert weighting == 'time', "Transfers require temporal network"
        if transfers:
            G = nx.DiGraph(transfers=transfers, weighting=weighting)
            G.add_nodes_from(self.node)
            for station in self.station:
                for e in permutations(station.node, 2):
                    if not any((isinstance(node, Access) for node in e)):
                        G.add_edge(*e, weight=4.9)
                    elif (isinstance(e[0], Entrance) or
                          isinstance(e[1], Exit)) and \
                            not all((isinstance(node, Access) for node in e)):
                        G.add_edge(*e, weight=0)
            for service in self.service:
                for i in range(len(service.station) - 1):
                    weight = service.time[i]
                    u = find(lambda node: node.station ==
                             service.station[i], service.node)
                    v = find(lambda node: node.station ==
                             service.station[i + 1], service.node)
                    G.add_edge(u, v, weight=weight)
                    G.add_edge(v, u, weight=weight)
        else:
            G = nx.Graph(transfers=transfers, weighting=weighting)
            G.add_nodes_from(self.station)
            for service in self.service:
                for i in range(len(service.station) - 1):
                    if weighting:
                        if weighting == 'time':
                            weight = \
                                service.time[i]
                        elif weighting == 'distance':
                            weight = service.station[i].distance(
                                service.station[i + 1]
                            )
                        else:
                            raise MetroError("Invalid weighting")
                        G.add_edge(service.station[i], service.station[i + 1],
                                   weight=weight)
                    else:
                        G.add_edge(service.station[i], service.station[i + 1])
        self.G = G
        return G

    def shortest_path(self, G, source, target, K,
                      weighting='time', transfers=True):
        def station_path(path):
            return [k for k, l in groupby([node.station for node in path])]
        if transfers:
            source = find(lambda node: isinstance(node, Entrance), source.node)
            target = find(lambda node: isinstance(node, Exit), target.node)
        length, path = nx.bidirectional_dijkstra(G, source, target,
                                                 weight='weight')
        A = [(length, path, station_path(path))]
        filtered = []
        B = []

        k = 1
        while True:
            if transfers:
                if not A[k - 1][2] in (_[2] for _ in filtered):
                    c = Counter((node.station for node in A[k - 1][1]))
                    if not c.most_common(1)[0][1] > 2:
                        heapq.heappush(filtered, A[k - 1])
                        if len(filtered) == K:
                            break
            else:
                heapq.heappush(filtered, A[k - 1])
                if len(filtered) == K:
                    break
            for i in range(len(A[k - 1][1]) - 1):
                removed_edges = []
                spur_node = A[k - 1][1][i]
                root_path = A[k - 1][1][:(i + 1)]
                root_path_length = \
                    sum([G[root_path[j]][root_path[j + 1]]['weight']
                        for j in range(len(root_path) - 1)])
                j = 0
                for p in [_[1] for _ in A]:
                    if root_path == p[:(i + 1)]:
                        if transfers:
                            if p[i].station.id == p[i + 1].station.id:
                                continue
                            for e in p[i].parallel_edges(p[i + 1]):
                                if G.has_edge(*e):
                                    j += 1
                                    removed_edges.append(
                                        (e[0], e[1], G[e[0]][e[1]])
                                    )
                                    G.remove_edge(*e)
                        else:
                            if G.has_edge(p[i], p[i + 1]):
                                removed_edges.append(
                                    (p[i], p[i + 1], G[p[i]][p[i + 1]])
                                )
                                G.remove_edge(p[i], p[i + 1])
                if j != 0:
                    try:
                        spur_path = nx.bidirectional_dijkstra(G, spur_node,
                                                              target,
                                                              weight='weight')
                        total_path = root_path + spur_path[1][1:]
                        total_path = \
                            (root_path_length + spur_path[0], total_path,
                             station_path(total_path))
                        if total_path[0] == A[0][0]:
                            pdb.set_trace()
                        heapq.heappush(B, total_path)
                    except nx.NetworkXNoPath:
                        pass
                    for u, v, attr_dict in removed_edges:
                        G.add_edge(u, v, attr_dict)
            if not B:
                break
            A.append(heapq.heappop(B))
            k += 1
        if len(filtered) < K:
            return filtered + [(float('inf'), [], [])] * (K - len(filtered))
        return filtered


class Station(object):
    """Defines a station with a name, position, passenger flow, transfer times
    between lines, etc.
    """
    def __init__(self, id, name, pos, network):
        self.id = id
        self.network = network
        self.line = set()
        self.service = set()
        self.node = set()

        self.name = name
        self.pos = pos
        self.entry = defaultdict(int)

        self.network.station.add(self)
        Entrance(self)
        Exit(self)

    def __repr__(self):
        return "<Station %s>" % self.name

    def __cmp___(self, other):
        return cmp(self.name, other.name)

    def release(self):
        self.network.station.remove(self)
        for node in self.node:
            node.release()

    def distance(self, target):
        lat_source, lon_source = self.pos
        lat_target, lon_target = target.pos
        radius = 6371.009  # km

        lat_source, lon_source, lat_target, lon_target = \
            numpy.radians([lat_source, lon_source, lat_target, lon_target])

        dlat = lat_target - lat_source
        dlon = lon_target - lon_source
        a = numpy.sin(dlat / 2.0) ** 2 + numpy.cos(lat_source) * \
            numpy.cos(lat_target) * numpy.sin(dlon / 2.0) ** 2
        c = 2 * numpy.arctan2(numpy.sqrt(a), numpy.sqrt(1 - a))

        return radius * c

    def add_entry(self, target, entry):
        self.entry[target] = entry

    def total_entry(self):
        return numpy.sum(self.entry.values())

    def total_exit(self):
        return numpy.sum([station.entry[self] for station in self.network])

    def isneighbor(self, station):
        pass

    # def get_nodes(self, incoming='all', service=False):
    #     get_nodes = set()
    #     for node in self.node:
    #         if node.incoming == incoming or incoming == 'all':
    #             if service == True and node.service != None:
    #                 get_nodes.add(node)
    #             elif service == False:
    #                 get_nodes.add(node)
    #             elif node.service == service:
    #                 get_nodes.add(node)
    #     return get_nodes


class Line(object):
    """Defines a line, consisting of a number of services. Lines are identified
    by a name and a color.

    Colors have to be HTML strings e.g. #12a3f3.
    """
    def __init__(self, id, name, color, network):
        self.id = id
        self.network = network
        self.station = set()
        self.service = set()
        self.node = set()

        self.name = name
        self.color = color

        self.network.line.add(self)

    def release(self):
        for service in self.service:
            service.release()
        for station in self.station:
            station.release()
        self.network.line.remove(self)

    def __repr__(self):
        return "<Line %s>" % self.name

    def __iter__(self):
        return iter(self.service)


class Service(object):
    """A service is a sequence of stations, and the tracks that can be taken to
    travel between them. Note that some services can use multiple tracks
    between stations. The sequence of stations should be connected.

    Services are created by adding stations and tracks sequentially in
    separate lists, this way we can be sure that services can be iterated
    over, looked up in lists, etc. easily.
    """
    def __init__(self, id, line):
        self.id = id
        self.network = line.network
        self.station = []
        self.line = line
        self.node = set()

        self.network.service.add(self)
        self.line.service.add(self)

        self.time = []

    def release(self):
        self.network.service.remove(self)
        self.line.service.remove(self)
        if not self.line.service:
            self.line.release()
        for station in self.station:
            station.service.remove(self)
            if not station.service:
                station.release()

    def __repr__(self):
        if not self.station:
            return "<Service %s without stations>" % self.line
        else:
            return ("<Service %s between %s and %s>" %
                   (self.line, self.station[0], self.station[-1]))

    def __iter__(self):
        return iter(self.station)

    def __contains__(self, item):
        if isinstance(item, Station):
            return item in self.station
        elif isinstance(item, tuple):
            return item[0].isneighbor(item[1])
        else:
            raise MetroError("Service can only contain stations or edges")

    def __len__(self):
        return len(self.station)

    def add_connection(self, source, target, time):
        if not self.station:
            self.station.append(source)
            self.line.station.add(source)
            Platform(source, self)
        elif source != self.station[-1]:
            raise MetroError("The track from %s to %s " % (source, target) +
                             "could not be added to %s" % self)
        self.station.append(target)
        self.time.append(time)
        Platform(target, self)
        self.line.station.add(target)

    def next(self, station):
        try:
            return self.station[self.station.index(station) + 1]
        except IndexError:
            return None

    def previous(self, station):
        try:
            return self.station[self.station.index(station) - 1]
        except IndexError:
            return None


class Node(object):
    def __init__(self, station):
        self.network = station.network
        self.station = station

        self.network.node.add(self)
        self.station.node.add(self)

    def release(self):
        self.network.node.remove(self)
        self.station.node.remove(self)

    def __repr__(self):
        return "<%s at %s>" % (self.__class__.__name__, self.station)

    def parallel_edges(self, other):
        assert self.station.id != other.station.id
        return list(product(self.station.node, other.station.node))


class Access(Node):
    pass


class Exit(Access):
    pass


class Entrance(Access):
    pass


class Platform(Node):
    """This defines a node in the graph by the station and station, and also
    whether it's an incoming/outgoing track or an entry/exit point"""
    def __init__(self, station, service):
        super(Platform, self).__init__(station)
        self.line = service.line
        self.service = service

        self.line.node.add(self)
        self.service.node.add(self)

    def __repr__(self):
        return "<%s at %s for %s>" % \
            (self.__class__.__name__, self.station, self.service)

    def release(self):
        super(Platform, self).release()
        self.line.node.remove(self)
        self.service.node.remove(self)
