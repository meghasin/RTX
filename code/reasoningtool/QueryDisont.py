""" This module is the definition of class QueryDisont. It is written to connect
 with disease-ontology to query disease ontology and mesh id of given disont_id.
"""

__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

import requests
import CachedMethods


class QueryDisont:

    API_BASE_URL = 'http://www.disease-ontology.org/api'

    @staticmethod
    def send_query_get(handler, url_suffix):
        url_str = QueryDisont.API_BASE_URL + "/" + handler + "/" + url_suffix
#        print(url_str)
        res = requests.get(url_str, headers={'accept': 'application/json'})
        assert res.status_code == 200
        return res

    @staticmethod
    @CachedMethods.register
    def query_disont_to_child_disonts(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``set`` with keys as DOIDs
        """
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
#        print(res_json)
        disease_children_list = res_json.get("children", None)
        if disease_children_list is not None:
            return set([int(disease_child_list[1].split(':')[1]) for disease_child_list in disease_children_list])
        else:
            return set()

    @staticmethod
    @CachedMethods.register
    def query_disont_to_label(disont_id):
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
        return res_json.get('name', '')

    @staticmethod
    @CachedMethods.register
    def query_disont_to_child_disonts_desc(disont_id):
        """for a disease ontology ID (including prefix "DOID:", with zero padding), return child DOIDs

        :param disont_id: string, like ``'DOID:14069'``
        :returns: ``dict`` with keys as DOIDs and values as human-readable disease names
        """

        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
#        print(res_json)
        disease_children_list = res_json.get("children", None)
        if disease_children_list is not None:
            return dict([[disease_child_list[1], disease_child_list[0]] for disease_child_list in disease_children_list])
        else:
            return dict()

    @staticmethod
    @CachedMethods.register
    def query_disont_to_mesh_id(disont_id):
        """convert a disease ontology ID (including prefix "DOID:", with zero padding) to MeSH ID

        :param disont_id: string, like ``'DOID:14069'``
        """
        res_json = QueryDisont.send_query_get('metadata', disont_id).json()
        xref_strs = res_json.get("xrefs", None)
        if xref_strs is not None:
            mesh_ids = set([xref_str.split('MESH:')[1] for xref_str in xref_strs if 'MESH:' in xref_str])
        else:
            mesh_ids = set()
        return mesh_ids

if __name__ == '__main__':
    print(QueryDisont.query_disont_to_mesh_id("DOID:9352"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:1837"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:10182"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:11712"))
    print(QueryDisont.query_disont_to_child_disonts_desc("DOID:9352"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:14069"))
    print(QueryDisont.query_disont_to_child_disonts_desc("DOID:12365"))
    print(QueryDisont.query_disont_to_mesh_id("DOID:0050741"))
    print(QueryDisont.query_disont_to_label("DOID:0050741"))
