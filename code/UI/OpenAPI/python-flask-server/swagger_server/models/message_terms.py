# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class MessageTerms(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, disease: str=None, protein: str=None, anatomical_entity: str=None, chemical_substance: str=None, metabolite: str=None):  # noqa: E501
        """MessageTerms - a model defined in Swagger

        :param disease: The disease of this MessageTerms.  # noqa: E501
        :type disease: str
        :param protein: The protein of this MessageTerms.  # noqa: E501
        :type protein: str
        :param anatomical_entity: The anatomical_entity of this MessageTerms.  # noqa: E501
        :type anatomical_entity: str
        :param chemical_substance: The chemical_substance of this MessageTerms.  # noqa: E501
        :type chemical_substance: str
        :param metabolite: The metabolite of this MessageTerms.  # noqa: E501
        :type metabolite: str
        """
        self.swagger_types = {
            'disease': str,
            'protein': str,
            'anatomical_entity': str,
            'chemical_substance': str,
            'metabolite': str
        }

        self.attribute_map = {
            'disease': 'disease',
            'protein': 'protein',
            'anatomical_entity': 'anatomical_entity',
            'chemical_substance': 'chemical_substance',
            'metabolite': 'metabolite'
        }

        self._disease = disease
        self._protein = protein
        self._anatomical_entity = anatomical_entity
        self._chemical_substance = chemical_substance
        self._metabolite = metabolite

    @classmethod
    def from_dict(cls, dikt) -> 'MessageTerms':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Message_terms of this MessageTerms.  # noqa: E501
        :rtype: MessageTerms
        """
        return util.deserialize_model(dikt, cls)

    @property
    def disease(self) -> str:
        """Gets the disease of this MessageTerms.


        :return: The disease of this MessageTerms.
        :rtype: str
        """
        return self._disease

    @disease.setter
    def disease(self, disease: str):
        """Sets the disease of this MessageTerms.


        :param disease: The disease of this MessageTerms.
        :type disease: str
        """

        self._disease = disease

    @property
    def protein(self) -> str:
        """Gets the protein of this MessageTerms.


        :return: The protein of this MessageTerms.
        :rtype: str
        """
        return self._protein

    @protein.setter
    def protein(self, protein: str):
        """Sets the protein of this MessageTerms.


        :param protein: The protein of this MessageTerms.
        :type protein: str
        """

        self._protein = protein

    @property
    def anatomical_entity(self) -> str:
        """Gets the anatomical_entity of this MessageTerms.


        :return: The anatomical_entity of this MessageTerms.
        :rtype: str
        """
        return self._anatomical_entity

    @anatomical_entity.setter
    def anatomical_entity(self, anatomical_entity: str):
        """Sets the anatomical_entity of this MessageTerms.


        :param anatomical_entity: The anatomical_entity of this MessageTerms.
        :type anatomical_entity: str
        """

        self._anatomical_entity = anatomical_entity

    @property
    def chemical_substance(self) -> str:
        """Gets the chemical_substance of this MessageTerms.


        :return: The chemical_substance of this MessageTerms.
        :rtype: str
        """
        return self._chemical_substance

    @chemical_substance.setter
    def chemical_substance(self, chemical_substance: str):
        """Sets the chemical_substance of this MessageTerms.


        :param chemical_substance: The chemical_substance of this MessageTerms.
        :type chemical_substance: str
        """

        self._chemical_substance = chemical_substance

    @property
    def metabolite(self) -> str:
        """Gets the metabolite of this MessageTerms.


        :return: The metabolite of this MessageTerms.
        :rtype: str
        """
        return self._metabolite

    @metabolite.setter
    def metabolite(self, metabolite: str):
        """Sets the metabolite of this MessageTerms.


        :param metabolite: The metabolite of this MessageTerms.
        :type metabolite: str
        """

        self._metabolite = metabolite
