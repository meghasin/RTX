#!/bin/env python3


def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import sys
import os
import traceback
import json
import ast

from response import Response

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../UI/OpenAPI/python-flask-server/")
from swagger_server.models.query_graph import QueryGraph
from swagger_server.models.knowledge_graph import KnowledgeGraph
from swagger_server.models.q_node import QNode
from swagger_server.models.q_edge import QEdge


class ARAXExpander:

    #### Constructor
    def __init__(self):
        self.response = None
        self.message = None
        self.parameters = {'edge_id': None, 'node_id': None, 'kp': None, 'enforce_directionality': None,
                           'use_synonyms': None, 'synonym_handling': None, 'continue_if_no_results': None}

    def describe_me(self):
        """
        Little helper function for internal use that describes the actions and what they can do
        :return:
        """
        # this is quite different than the `describe_me` in ARAX_overlay and ARAX_filter_kg due to expander being less
        # of a dispatcher (like overlay and filter_kg) and more of a single self contained class
        brief_description = """
`expand` effectively takes a query graph (QG) and reaches out to various knowledge providers (KP's) to find all bioentity subgraphs
that satisfy that QG and augments the knowledge graph (KG) with them. As currently implemented, `expand` can utilize the ARA Expander
team KG1 and KG2 Neo4j instances as well as BioThings Explorer to fulfill QG's, with functionality built in to reach out to other KP's as they are rolled out.
        """
        description_list = []
        params_dict = dict()
        params_dict['brief_description'] = brief_description
        params_dict['edge_id'] = {"a query graph edge ID or list of such IDs to expand (optional, default is to expand entire query graph)"}  # this is a workaround due to how self.parameters is utilized in this class
        params_dict['node_id'] = {"a query graph node ID to expand (optional, default is to expand entire query graph)"}
        params_dict['kp'] = {"the knowledge provider to use - current options are `ARAX/KG1`, `ARAX/KG2`, or `BTE` (optional, default is `ARAX/KG1`)"}
        params_dict['enforce_directionality'] = {"whether to obey (vs. ignore) edge directions in query graph - options are `true` or `false` (optional, default is `false`)"}
        params_dict['use_synonyms'] = {"whether to consider synonym curies for query nodes with a curie specified - options are `true` or `false` (optional, default is `true`)"}
        params_dict['synonym_handling'] = {"how to handle synonyms in the answer - options are `map_back` (default; map edges using a synonym back to the original curie) or `add_all` (add synonym nodes as they are - no mapping/merging)"}
        params_dict['continue_if_no_results'] = {"whether to continue execution if no paths are found matching the query graph - options are `true` or `false` (optional, default is `false`)"}
        description_list.append(params_dict)
        return description_list

    #### Top level decision maker for applying filters
    def apply(self, input_message, input_parameters, response=None):

        #### Define a default response
        if response is None:
            response = Response()
        self.response = response
        self.message = input_message
        message = self.message

        #### Basic checks on arguments
        if not isinstance(input_parameters, dict):
            response.error("Provided parameters is not a dict", error_code="ParametersNotDict")
            return response

        #### Define a complete set of allowed parameters and their defaults
        parameters = self.parameters
        parameters['kp'] = "ARAX/KG1"
        parameters['enforce_directionality'] = False
        parameters['use_synonyms'] = True
        parameters['synonym_handling'] = 'map_back'
        parameters['continue_if_no_results'] = False

        #### Loop through the input_parameters and override the defaults and make sure they are allowed
        for key,value in input_parameters.items():
            if key and key not in parameters:
                response.error(f"Supplied parameter {key} is not permitted", error_code="UnknownParameter")
            else:
                if type(value) is str and value.lower() == "true":
                    value = True
                elif type(value) is str and value.lower() == "false":
                    value = False
                parameters[key] = value

        # Default to expanding the entire query graph if the user didn't specify what to expand
        if not parameters['edge_id'] and not parameters['node_id']:
            parameters['edge_id'] = [edge.id for edge in self.message.query_graph.edges]
            parameters['node_id'] = self.__get_orphan_query_node_ids(self.message.query_graph)

        #### Return if any of the parameters generated an error (showing not just the first one)
        if response.status != 'OK':
            return response

        #### Store these final parameters for convenience
        response.data['parameters'] = parameters
        self.parameters = parameters

        #### Do the actual expansion!
        response.debug(f"Applying Expand to Message with parameters {parameters}")
        input_edge_ids = self.__convert_to_list(parameters['edge_id'])
        input_node_ids = self.__convert_to_list(parameters['node_id'])
        kp_to_use = self.parameters['kp']
        continue_if_no_results = self.parameters['continue_if_no_results']

        # Convert message knowledge graph to dictionary format, for faster processing
        dict_kg = self.__convert_standard_kg_to_dict_kg(self.message.knowledge_graph)

        # Expand any specified edges
        if input_edge_ids:
            query_sub_graph = self.__extract_query_subgraph(input_edge_ids, self.message.query_graph)
            if response.status != 'OK':
                return response
            self.response.debug(f"Query graph for this Expand() call is: {query_sub_graph.to_dict()}")

            # Expand the query graph edge by edge (much faster for neo4j queries, and allows easy integration with BTE)
            ordered_qedges_to_expand = self.__get_order_to_expand_edges_in(query_sub_graph)
            node_usages_by_edges_map = dict()

            for qedge in ordered_qedges_to_expand:
                answer_kg, edge_node_usage_map = self.__expand_edge(qedge, kp_to_use, dict_kg, continue_if_no_results)
                if response.status != 'OK':
                    return response
                node_usages_by_edges_map[qedge.id] = edge_node_usage_map

                self.__process_and_merge_answer(answer_kg, dict_kg)
                if response.status != 'OK':
                    return response

                self.__prune_dead_end_paths(dict_kg, query_sub_graph, node_usages_by_edges_map)
                if response.status != 'OK':
                    return response

            # Make sure no node/edge fulfills more than one qg id (until we come up with a way to handle this)
            self.__check_for_multiple_qg_ids(dict_kg)
            if self.response.status != 'OK':
                return response

        # Expand any specified nodes
        if input_node_ids:
            for qnode_id in input_node_ids:
                answer_kg = self.__expand_node(qnode_id, kp_to_use, continue_if_no_results)
                if response.status != 'OK':
                    return response

                self.__process_and_merge_answer(answer_kg, dict_kg)
                if response.status != 'OK':
                    return response

        # Convert message knowledge graph back to API standard format
        self.message.knowledge_graph = self.__convert_dict_kg_to_standard_kg(dict_kg)

        #### Return the response and done
        kg = self.message.knowledge_graph
        response.info(f"After Expand, Message.KnowledgeGraph has {len(kg.nodes)} nodes and {len(kg.edges)} edges")
        return response

    def __extract_query_subgraph(self, qedge_ids_to_expand, message_query_graph):
        # This function extracts a sub-query graph containing the provided qedge IDs from a larger query graph
        sub_query_graph = QueryGraph(nodes=[], edges=[])

        for qedge_id in qedge_ids_to_expand:
            # Make sure this query edge ID actually exists in the larger query graph
            if not any(qedge.id == qedge_id for qedge in message_query_graph.edges):
                self.response.error(f"An edge with ID '{qedge_id}' does not exist in Message.QueryGraph",
                                    error_code="UnknownValue")
            else:
                # Grab this qedge and its two qnodes
                qedge = next(qedge for qedge in message_query_graph.edges if qedge.id == qedge_id)
                qnodes = [self.__get_query_node(message_query_graph, qedge.source_id),
                          self.__get_query_node(message_query_graph, qedge.target_id)]

                # Add (a copy of) this qedge to our new query sub graph
                qedge_copy = self.__copy_qedge(qedge)
                if not any(qedge.id == qedge_copy.id for qedge in sub_query_graph.edges):
                    sub_query_graph.edges.append(qedge_copy)

                # Add (copies of) this qedge's two qnodes to our new query sub graph
                for qnode in qnodes:
                    qnode_copy = self.__copy_qnode(qnode)
                    if not any(qnode.id == qnode_copy.id for qnode in sub_query_graph.nodes):
                        sub_query_graph.nodes.append(qnode_copy)

        return sub_query_graph

    def __get_query_graph_for_edge(self, qedge, dict_kg):
        # This function creates a query graph for the specified qedge, updating its qnodes' curies as needed
        edge_query_graph = QueryGraph(nodes=[], edges=[])
        qnodes = [self.__get_query_node(self.message.query_graph, qedge.source_id),
                  self.__get_query_node(self.message.query_graph, qedge.target_id)]

        # Add (a copy of) this qedge to our edge query graph
        edge_query_graph.edges.append(self.__copy_qedge(qedge))

        # Update this qedge's qnodes as appropriate and add (copies of) them to the edge query graph
        qedge_has_already_been_expanded = qedge.id in dict_kg['edges']
        qnodes_using_curies_from_prior_step = set()
        for qnode in qnodes:
            qnode_copy = self.__copy_qnode(qnode)

            # Handle case where we need to feed curies from a prior Expand() step as the curie for this qnode
            qnode_already_fulfilled = qnode_copy.id in dict_kg['nodes']
            if qnode_already_fulfilled and not qnode_copy.curie and not qedge_has_already_been_expanded:
                qnode_copy.curie = list(dict_kg['nodes'][qnode_copy.id].keys())
                qnodes_using_curies_from_prior_step.add(qnode_copy.id)

            edge_query_graph.nodes.append(qnode_copy)

        return edge_query_graph, qnodes_using_curies_from_prior_step

    def __expand_edge(self, qedge, kp_to_use, dict_kg, continue_if_no_results):
        # This function answers a single-edge (one-hop) query using the specified knowledge provider
        self.response.info(f"Expanding edge {qedge.id} using {kp_to_use}")

        edge_query_graph, qnodes_using_curies_from_prior_step = self.__get_query_graph_for_edge(qedge, dict_kg)

        valid_kps = ["ARAX/KG1", "ARAX/KG2", "BTE"]
        if kp_to_use not in valid_kps:
            self.response.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are {', '.join(valid_kps)}",
                                error_code="UnknownValue")
            return None, None
        else:
            if kp_to_use == 'BTE':
                from Expand.bte_querier import BTEQuerier
                kp_querier = BTEQuerier(self.response)
            else:
                from Expand.kg_querier import KGQuerier
                kp_querier = KGQuerier(self.response, kp_to_use)

            answer_kg, edge_node_usage_map = kp_querier.answer_one_hop_query(edge_query_graph, qnodes_using_curies_from_prior_step)

            # Make sure all of the QG IDs in our query have been fulfilled (unless we're continuing if no results)
            if self.response.status == 'OK' and not continue_if_no_results:
                for qnode in edge_query_graph.nodes:
                    if qnode.id not in answer_kg['nodes'] or not len(answer_kg['nodes'][qnode.id]):
                        self.response.error(f"Returned answer KG does not contain any results for QNode {qnode.id}",
                                            error_code="UnfulfilledQGID")
                for qedge in edge_query_graph.edges:
                    if qedge.id not in answer_kg['edges'] or not len(answer_kg['edges'][qedge.id]):
                        self.response.error(f"Returned answer KG does not contain any results for QEdge {qedge.id}",
                                            error_code="UnfulfilledQGID")

            return answer_kg, edge_node_usage_map

    def __expand_node(self, qnode_id, kp_to_use, continue_if_no_results):
        # This function expands a single node using the specified knowledge provider
        self.response.debug(f"Expanding node {qnode_id} using {kp_to_use}")

        query_node = self.__get_query_node(self.message.query_graph, qnode_id)
        if self.response.status != 'OK':
            return None

        if kp_to_use == 'BTE':
            self.response.error(f"Cannot use BTE to answer single node queries", error_code="InvalidQuery")
            return None
        elif kp_to_use == 'ARAX/KG2' or kp_to_use == 'ARAX/KG1':
            from Expand.kg_querier import KGQuerier
            kg_querier = KGQuerier(self.response, kp_to_use)
            answer_kg = kg_querier.answer_single_node_query(query_node)

            # Make sure all qnodes have been fulfilled (unless we're continuing if no results)
            if self.response.status == 'OK' and not continue_if_no_results:
                if query_node.id not in answer_kg['nodes'] or not len(answer_kg['nodes'][query_node.id]):
                    self.response.error(f"Returned answer KG does not contain any results for QNode {query_node.id}",
                                        error_code="UnfulfilledQGID")
            return answer_kg
        else:
            self.response.error(f"Invalid knowledge provider: {kp_to_use}. Valid options are ARAX/KG1 or ARAX/KG2")
            return None

    def __process_and_merge_answer(self, answer_dict_kg, dict_kg):
        # This function merges an answer KG (from the current edge/node expansion) into the overarching KG
        self.response.debug("Merging answer into Message.KnowledgeGraph")

        for qnode_id, nodes in answer_dict_kg['nodes'].items():
            for node_key, node in nodes.items():
                is_valid = self.__validate_node(node_key, node)
                if is_valid:
                    self.__add_node_to_message_kg(node, qnode_id, dict_kg)
                else:
                    return
        for qedge_id, edges_dict in answer_dict_kg['edges'].items():
            for edge_key, edge in edges_dict.items():
                is_valid = self.__validate_edge(edge_key, edge)
                if is_valid:
                    self.__add_edge_to_message_kg(edge, qedge_id, dict_kg)
                else:
                    return

    def __prune_dead_end_paths(self, dict_kg, full_query_graph, node_usages_by_edges_map):
        # This function removes any 'dead-end' paths from the KG. (Because edges are expanded one-by-one, not all edges
        # found in the last expansion will connect to edges in the next one)
        self.response.debug(f"Pruning any paths that are now dead ends")

        # Create a map of which qnodes are connected to which other qnodes
        # Example qnode_connections_map: {'n00': {'n01'}, 'n01': {'n00', 'n02'}, 'n02': {'n01'}}
        qnode_connections_map = dict()
        for qnode in full_query_graph.nodes:
            qnode_connections_map[qnode.id] = set()
            for qedge in full_query_graph.edges:
                if qedge.source_id == qnode.id or qedge.target_id == qnode.id:
                    connected_qnode_id = qedge.target_id if qedge.target_id != qnode.id else qedge.source_id
                    qnode_connections_map[qnode.id].add(connected_qnode_id)

        # Create a map of which nodes each node is connected to (organized by the qnode_id they're fulfilling)
        # Example node_usages_by_edges_map: {'e00': {'KG1:111221': {'n00': 'CUI:122', 'n01': 'CUI:124'}}}
        # Example node_connections_map: {'CUI:1222': {'n00': {'DOID:122'}, 'n02': {'UniProtKB:22', 'UniProtKB:333'}}}
        node_connections_map = dict()
        for qedge_id, edges_to_nodes_dict in node_usages_by_edges_map.items():
            current_qedge = next(qedge for qedge in full_query_graph.edges if qedge.id == qedge_id)
            qnode_ids = [current_qedge.source_id, current_qedge.target_id]
            for edge_id, node_usages_dict in edges_to_nodes_dict.items():
                for current_qnode_id in qnode_ids:
                    connected_qnode_id = next(qnode_id for qnode_id in qnode_ids if qnode_id != current_qnode_id)
                    current_node_id = node_usages_dict[current_qnode_id]
                    connected_node_id = node_usages_dict[connected_qnode_id]
                    if current_qnode_id not in node_connections_map:
                        node_connections_map[current_qnode_id] = dict()
                    if current_node_id not in node_connections_map[current_qnode_id]:
                        node_connections_map[current_qnode_id][current_node_id] = dict()
                    if connected_qnode_id not in node_connections_map[current_qnode_id][current_node_id]:
                        node_connections_map[current_qnode_id][current_node_id][connected_qnode_id] = set()
                    node_connections_map[current_qnode_id][current_node_id][connected_qnode_id].add(connected_node_id)

        # Iteratively remove all disconnected nodes until there are none left
        qnode_ids_already_expanded = list(node_connections_map.keys())
        found_dead_end = True
        while found_dead_end:
            found_dead_end = False
            for qnode_id in qnode_ids_already_expanded:
                qnode_ids_should_be_connected_to = qnode_connections_map[qnode_id].intersection(qnode_ids_already_expanded)
                for node_id, node_mappings_dict in node_connections_map[qnode_id].items():
                    # Check if any mappings are even entered for all qnode_ids this node should be connected to
                    if set(node_mappings_dict.keys()) != qnode_ids_should_be_connected_to:
                        if node_id in dict_kg['nodes'][qnode_id]:
                            dict_kg['nodes'][qnode_id].pop(node_id)
                            found_dead_end = True
                    else:
                        # Verify that at least one of the entered connections still exists (for each connected qnode_id)
                        for connected_qnode_id, connected_node_ids in node_mappings_dict.items():
                            if not connected_node_ids.intersection(set(dict_kg['nodes'][connected_qnode_id].keys())):
                                if node_id in dict_kg['nodes'][qnode_id]:
                                    dict_kg['nodes'][qnode_id].pop(node_id)
                                    found_dead_end = True

        # Then remove all orphaned edges
        for qedge_id, edges_dict in node_usages_by_edges_map.items():
            for edge_key, node_mappings in edges_dict.items():
                for qnode_id, used_node_id in node_mappings.items():
                    if used_node_id not in dict_kg['nodes'][qnode_id]:
                        if edge_key in dict_kg['edges'][qedge_id]:
                            dict_kg['edges'][qedge_id].pop(edge_key)

    def __get_order_to_expand_edges_in(self, query_graph):
        # This function determines what order to expand the edges in a query graph in; it attempts to start with
        # qedges that have a qnode with a specific curie, and move out from there.
        edges_remaining = [edge for edge in query_graph.edges]
        ordered_edges = []
        while edges_remaining:
            if not ordered_edges:
                # Start with an edge that has a node with a curie specified
                edge_with_curie = self.__get_edge_with_curie_node(query_graph)
                first_edge = edge_with_curie if edge_with_curie else edges_remaining[0]
                ordered_edges = [first_edge]
                edges_remaining.pop(edges_remaining.index(first_edge))
            else:
                # Add connected edges in a rightward (target) direction if possible
                right_end_edge = ordered_edges[-1]
                edge_connected_to_right_end = self.__find_connected_edge(edges_remaining, right_end_edge)
                if edge_connected_to_right_end:
                    ordered_edges.append(edge_connected_to_right_end)
                    edges_remaining.pop(edges_remaining.index(edge_connected_to_right_end))
                else:
                    left_end_edge = ordered_edges[0]
                    edge_connected_to_left_end = self.__find_connected_edge(edges_remaining, left_end_edge)
                    if edge_connected_to_left_end:
                        ordered_edges.insert(0, edge_connected_to_left_end)
                        edges_remaining.pop(edges_remaining.index(edge_connected_to_left_end))
        return ordered_edges

    def __get_orphan_query_node_ids(self, query_graph):
        node_ids_used_by_edges = set()
        node_ids = set()
        for edge in query_graph.edges:
            node_ids_used_by_edges.add(edge.source_id)
            node_ids_used_by_edges.add(edge.target_id)
        for node in query_graph.nodes:
            node_ids.add(node.id)
        return list(node_ids.difference(node_ids_used_by_edges))

    def __get_edge_with_curie_node(self, query_graph):
        for edge in query_graph.edges:
            source_node = self.__get_query_node(query_graph, edge.source_id)
            target_node = self.__get_query_node(query_graph, edge.target_id)
            if source_node.curie or target_node.curie:
                return edge
        return None

    def __find_connected_edge(self, edge_list, edge):
        edge_node_ids = {edge.source_id, edge.target_id}
        for potential_connected_edge in edge_list:
            potential_connected_edge_node_ids = {potential_connected_edge.source_id, potential_connected_edge.target_id}
            if edge_node_ids.intersection(potential_connected_edge_node_ids):
                return potential_connected_edge
        return None

    def __get_query_node(self, query_graph, qnode_id):
        matching_nodes = [node for node in query_graph.nodes if node.id == qnode_id]
        if not matching_nodes:
            self.response.error(f"A node with ID '{qnode_id}' does not exist in Message.QueryGraph", error_code="UnknownValue")
            return None
        else:
            return matching_nodes[0]

    def __validate_node(self, node_key, node):
        is_valid = True
        if node_key != node.id:
            self.response.error(f"Node key is different from node id in Expand (key: {node_key}, id: {node.id})",
                                error_code="InvalidDataStructure")
            is_valid = False
        elif not node.qnode_id:
            self.response.error(f"Node {node_key} in answer is missing its corresponding qnode_id",
                                error_code="MissingProperty")
            is_valid = False
        return is_valid

    def __validate_edge(self, edge_key, edge):
        is_valid = True
        if edge_key != edge.id:
            self.response.error(f"Edge key is different from edge id in Expand (key: {edge_key}, id: {edge.id})",
                                error_code="InvalidDataStructure")
            is_valid = False
        elif not edge.qedge_id:
            self.response.error(f"Edge {edge_key} in answer is missing its corresponding qedge_id",
                                error_code="MissingProperty")
            is_valid = False
        return is_valid

    def __check_for_multiple_qg_ids(self, dict_kg):
        # Figure out if any nodes are being used to fulfill more than one QNode ID
        all_node_ids = set()
        nodes_with_multiple_qg_ids = set()
        nodes_dict = dict_kg.get('nodes')
        for qnode_id, nodes in nodes_dict.items():
            node_ids = set(nodes.keys())
            nodes_with_multiple_qg_ids = all_node_ids.intersection(node_ids)
            all_node_ids = all_node_ids.union(node_ids)
        if nodes_with_multiple_qg_ids:
            for node_id in nodes_with_multiple_qg_ids:
                used_qnode_ids = [qnode_id for qnode_id in nodes_dict.keys() if nodes_dict[qnode_id].get(node_id)]
                self.response.error(f"Node {node_id} has been returned as an answer for multiple query graph nodes"
                                    f" ({', '.join(used_qnode_ids)})", error_code="MultipleQGIDs")

        # Figure out if any edges are being used to fulfill more than one QEdge ID
        all_edge_ids = set()
        edges_with_multiple_qg_ids = set()
        edges_dict = dict_kg.get('edges')
        for qedge_id, edges in edges_dict.items():
            edge_ids = set(edges.keys())
            edges_with_multiple_qg_ids = all_edge_ids.intersection(edge_ids)
            all_edge_ids = all_edge_ids.union(edge_ids)
        if edges_with_multiple_qg_ids:
            for edge_id in edges_with_multiple_qg_ids:
                used_qedge_ids = [qedge_id for qedge_id in edges_dict.keys() if edges_dict[qedge_id].get(edge_id)]
                self.response.warning(f"Edge {edge_id} has been returned as an answer for multiple query graph edges"
                                    f" ({', '.join(used_qedge_ids)})")

    def __convert_to_list(self, string_or_list):
        if type(string_or_list) is str:
            return [string_or_list]
        elif type(string_or_list) is list:
            return string_or_list
        else:
            return []

    def __add_node_to_message_kg(self, node, qnode_id, dict_kg):
        if qnode_id not in dict_kg['nodes']:
            dict_kg['nodes'][qnode_id] = dict()
        dict_kg['nodes'][qnode_id][node.id] = node

    def __add_edge_to_message_kg(self, edge, qedge_id, dict_kg):
        if qedge_id not in dict_kg['edges']:
            dict_kg['edges'][qedge_id] = dict()
        dict_kg['edges'][qedge_id][edge.id] = edge

    def __convert_standard_kg_to_dict_kg(self, knowledge_graph):
        dict_kg = {'nodes': dict(), 'edges': dict()}
        if knowledge_graph.nodes is not None:
            for node in knowledge_graph.nodes:
                if node.qnode_id not in dict_kg['nodes']:
                    dict_kg['nodes'][node.qnode_id] = dict()
                dict_kg['nodes'][node.qnode_id][node.id] = node
        if knowledge_graph.edges is not None:
            for edge in knowledge_graph.edges:
                if edge.qedge_id not in dict_kg['edges']:
                    dict_kg['edges'][edge.qedge_id] = dict()
                dict_kg['edges'][edge.qedge_id][edge.id] = edge
        return dict_kg

    def __convert_dict_kg_to_standard_kg(self, dict_kg):
        standard_kg = KnowledgeGraph()
        standard_kg.nodes = []
        standard_kg.edges = []
        for qnode_id, nodes_dict in dict_kg.get('nodes').items():
            for node in nodes_dict.values():
                standard_kg.nodes.append(node)
        for qedge_id, edges_dict in dict_kg.get('edges').items():
            for edge in edges_dict.values():
                standard_kg.edges.append(edge)
        return standard_kg

    def __copy_qedge(self, old_qedge):
        new_qedge = QEdge()
        for edge_property in new_qedge.to_dict():
            value = getattr(old_qedge, edge_property)
            setattr(new_qedge, edge_property, value)
        return new_qedge

    def __copy_qnode(self, old_qnode):
        new_qnode = QNode()
        for node_property in new_qnode.to_dict():
            value = getattr(old_qnode, node_property)
            setattr(new_qnode, node_property, value)
        return new_qnode

##########################################################################################
def main():

    #### Note that most of this is just manually doing what ARAXQuery() would normally do for you

    #### Create a response object
    response = Response()

    #### Create an ActionsParser object
    from actions_parser import ActionsParser
    actions_parser = ActionsParser()
 
    #### Set a list of actions
    actions_list = [
        "create_message",
        "add_qnode(id=n00, curie=CHEMBL.COMPOUND:CHEMBL112)",  # acetaminophen
        "add_qnode(id=n01, type=protein, is_set=true)",
        "add_qedge(id=e00, source_id=n00, target_id=n01)",
        # "add_qnode(id=n00, curie=DOID:14330)",  # parkinson's
        # "add_qnode(id=n01, type=protein, is_set=True)",
        # "add_qnode(id=n02, type=chemical_substance)",
        # "add_qedge(id=e00, source_id=n01, target_id=n00)",
        # "add_qedge(id=e01, source_id=n01, target_id=n02, type=physically_interacts_with)",
        # "add_qnode(curie=DOID:8398, id=n00)",  # osteoarthritis
        # "add_qnode(type=phenotypic_feature, is_set=True, id=n01)",
        # "add_qnode(type=disease, is_set=true, id=n02)",
        # "add_qedge(source_id=n01, target_id=n00, id=e00)",
        # "add_qedge(source_id=n01, target_id=n02, id=e01)",
        "expand(edge_id=e00, kp=BTE)",
        # "expand(edge_id=e00, kp=ARAX/KG2)",
        # "expand(edge_id=e01, kp=ARAX/KG2)",
        # "expand(edge_id=[e00,e01], kp=ARAX/KG1)",
        "return(message=true, store=false)",
    ]

    #### Parse the raw action_list into commands and parameters
    result = actions_parser.parse(actions_list)
    response.merge(result)
    if result.status != 'OK':
        print(response.show(level=Response.DEBUG))
        return response
    actions = result.data['actions']

    #### Create a Messager and an Expander and execute the command list
    from ARAX_messenger import ARAXMessenger
    messenger = ARAXMessenger()
    expander = ARAXExpander()

    #### Loop over each action and dispatch to the correct place
    for action in actions:
        if action['command'] == 'create_message':
            result = messenger.create_message()
            message = result.data['message']
            response.data = result.data
        elif action['command'] == 'add_qnode':
            result = messenger.add_qnode(message,action['parameters'])
        elif action['command'] == 'add_qedge':
            result = messenger.add_qedge(message,action['parameters'])
        elif action['command'] == 'expand':
            result = expander.apply(message,action['parameters'])
        elif action['command'] == 'return':
            break
        else:
            response.error(f"Unrecognized command {action['command']}", error_code="UnrecognizedCommand")
            print(response.show(level=Response.DEBUG))
            return response

        #### Merge down this result and end if we're in an error state
        response.merge(result)
        if result.status != 'OK':
            print(response.show(level=Response.DEBUG))
            return response

    #### Show the final response
    # print(json.dumps(ast.literal_eval(repr(message.knowledge_graph)),sort_keys=True,indent=2))
    print(response.show(level=Response.DEBUG))


if __name__ == "__main__":
    main()
