from .abc import Base_Datastore, Base_Field

from abc import ABC
from pathlib import Path


class Datastore(Base_Datastore, ABC):
    """A class that can contain fields that contain values. In order to use
    fields with datastores, an instance of the datastore must be made.

    For an example of how to use Datastores, see bot_config.py
    """

    _default_base_path = Path("data")

    def __init__(self, name: str, *, base_path=Path("data")):
        """
        Sets the datastore's name and the directory in which its data will be
        saved. The datastore's save directory is set `base_path/name`. All
        fields will save their data in a file under the datafield.

        Changing the base path or the name will prevent the datastore from
        loading any data saved under the previous path. Similarly, renaming
        fields will cause them to use a new save path based on their new name.

        Parameters
        ----------
        name: str
        The name of the datastore.

        base_path: Path
        The base of the path to which the datastore should be saved.
        """
        # TODO: Allow changing datastore path while keeping data
        self._name = name
        self._path = base_path / name
        self._fields = {}
        for attr_name, attr in type(self).__dict__.items():
            if isinstance(attr, Base_Field):
                new_field = attr._create_field(self, attr_name)
                self._fields[attr_name] = new_field
                setattr(self, attr_name, new_field)

    @property
    def name(self) -> str:
        return self._name

    @property
    def full_name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        return self._path
