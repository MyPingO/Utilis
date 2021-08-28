from . import types

from abc import ABC, abstractmethod
from copy import copy
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar, Union


class Base_Datastore(ABC):
    """A base class for datastores that can contain fields. Must be made
    attributes of subclasses of Base_Datastores, and then used with instances
    of those subclasses.
    """

    _name: str
    _path: Path
    _fields: dict[str, "Base_Field"]

    @property
    def fields(self) -> dict[str, "Base_Field"]:
        """A dictionary of all the fields contained in the datastore."""
        return self._fields.copy()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        """The name of the datastore."""
        return self._name

    @property
    @abstractmethod
    def full_name(self) -> str:
        """The name of the datastore including the names of any parents at the
        start, separated by periods."""


class Base_Field(Generic[types.Val_Type], ABC):
    """The base class for a field that can store data. Must be used as an
    attribute of a datastore.
    """

    # True if the field is an attribute of a class instance and False if the
    # field is an attribute of a class type.
    _initialized: bool = False

    _name: str
    _parent: Base_Datastore

    def _create_field(self, parent: Base_Datastore, name: str) -> "Base_Field":
        """Fields are their own factories. `_create_field` returns an
        'initialized' copy of the field, that is aware of its `Base_Datastore`
        parent, as well as the name the field attribute was given in its
        parent.
        """
        ret = copy(self)
        ret._initialized = True
        ret._parent = parent
        ret._name = name
        return ret

    @property
    def name(self) -> str:
        """The name of the field."""
        return self._name

    @property
    @abstractmethod
    def full_name(self) -> str:
        """The name of the field including the names of any parents at the
        start, separated by periods."""

    @property
    @abstractmethod
    def path(self) -> Path:
        """Returns the path at which the field's data is saved. May be a
        directory or a file depending on the field's type."""
