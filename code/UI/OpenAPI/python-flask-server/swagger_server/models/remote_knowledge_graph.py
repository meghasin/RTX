# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class RemoteKnowledgeGraph(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, url: str=None, credentials: object=None):  # noqa: E501
        """RemoteKnowledgeGraph - a model defined in Swagger

        :param url: The url of this RemoteKnowledgeGraph.  # noqa: E501
        :type url: str
        :param credentials: The credentials of this RemoteKnowledgeGraph.  # noqa: E501
        :type credentials: object
        """
        self.swagger_types = {
            'url': str,
            'credentials': object
        }

        self.attribute_map = {
            'url': 'url',
            'credentials': 'credentials'
        }

        self._url = url
        self._credentials = credentials

    @classmethod
    def from_dict(cls, dikt) -> 'RemoteKnowledgeGraph':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The RemoteKnowledgeGraph of this RemoteKnowledgeGraph.  # noqa: E501
        :rtype: RemoteKnowledgeGraph
        """
        return util.deserialize_model(dikt, cls)

    @property
    def url(self) -> str:
        """Gets the url of this RemoteKnowledgeGraph.

        URL that provides programmatic access to the remote knowledge graph  # noqa: E501

        :return: The url of this RemoteKnowledgeGraph.
        :rtype: str
        """
        return self._url

    @url.setter
    def url(self, url: str):
        """Sets the url of this RemoteKnowledgeGraph.

        URL that provides programmatic access to the remote knowledge graph  # noqa: E501

        :param url: The url of this RemoteKnowledgeGraph.
        :type url: str
        """

        self._url = url

    @property
    def credentials(self) -> object:
        """Gets the credentials of this RemoteKnowledgeGraph.

        Credentials needed for programmatic access to the remote knowledge graph  # noqa: E501

        :return: The credentials of this RemoteKnowledgeGraph.
        :rtype: object
        """
        return self._credentials

    @credentials.setter
    def credentials(self, credentials: object):
        """Sets the credentials of this RemoteKnowledgeGraph.

        Credentials needed for programmatic access to the remote knowledge graph  # noqa: E501

        :param credentials: The credentials of this RemoteKnowledgeGraph.
        :type credentials: object
        """

        self._credentials = credentials
