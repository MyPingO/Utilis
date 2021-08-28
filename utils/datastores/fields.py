import json
import copy as cp
from abc import ABC, abstractmethod
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Optional, Union

from . import abc, types


def require_field_init(f: Callable) -> Callable:
    """A wrapper for field methods that can only be called with initialized
    fields. If such methods are called without the field being initialized, an
    error is raised.
    """

    @wraps(f)
    def wrapper(field: abc.Base_Field, *args, **kwargs):
        if not field._initialized:
            raise RuntimeError(
                f"{f.__name__} can only be used as an attribute of an datafield instance."
            )
        return f(field, *args, **kwargs)

    return wrapper


class Base_Datafield(abc.Base_Field[types.Val_Type], ABC):
    """An abstract base for `Keyed_Field`'s and `Unkeyed_Field`'s shared
    logic.
    """

    _internal_version: int
    _type: str

    _data: Any

    _dirty: bool = False
    _transaction: bool = False

    def __init__(
        self,
        *,
        version: int,
        data_encoder: types.Data_Encoder[types.Val_Type],
        data_decoder: types.Data_Decoder[types.Val_Type],
    ):
        self._version = version
        self._data_encoder = data_encoder
        self._data_decoder = data_decoder

    @property
    @require_field_init
    def name(self) -> str:
        return self._name

    @property
    @require_field_init
    def full_name(self) -> str:
        return f"{self._parent.full_name}.{self.name}"

    @property
    @require_field_init
    def path(self) -> Path:
        return self._parent.path / f"{self._name}.json"

    @property
    def version(self) -> int:
        return self._version

    @property
    def data_encoder(self) -> types.Data_Encoder[types.Val_Type]:
        return self._data_encoder

    @property
    def data_decoder(self) -> types.Data_Decoder[types.Val_Type]:
        return self._data_decoder

    @abstractmethod
    def _get_default_data(self) -> Any:
        """The default data for the field. Fields with their data set to the
        default will not be saved to a file."""

    @require_field_init
    def _load_default(self) -> None:
        self._data = self._get_default_data()

    @require_field_init
    def _load_data_from_json_dict(self, json_dict: dict[str, Any]) -> None:
        self._data = (
            json_dict["data"] if "data" in json_dict else self._get_default_data()
        )

    @require_field_init
    def _check_data(self, json_dict: dict[str, Any]) -> None:
        """Checks to make sure that the data being loaded from a json dict is
        valid. Raises an error if it is not.
        """
        # Raises a keyerror if any keys are missing in the dict

        # Check field's internal version
        if json_dict["internal_version"] < self._internal_version:
            # TODO: Update out of date fields
            raise ValueError(f"Invalid version {json_dict['internal_version']}.")
        elif json_dict["internal_version"] > self._internal_version:
            raise ValueError(
                f"Can not load field with internal version {json_dict['internal_version']}. "
                f"The newest expected internal field version is {self._internal_version}"
            )

        # Check field's version
        if json_dict["version"] < self._version:
            # TODO: Update out of date fields
            raise ValueError(f"Invalid version {json_dict['version']}.")
        elif json_dict["version"] > self._version:
            raise ValueError(
                f"Can not load field with version {json_dict['version']}. "
                f"The newest expected field version is {self._version}"
            )

        # Check field's type
        if json_dict["type"] != self._type:
            raise ValueError(
                f"Saved field data has type '{json_dict['type']}'; expected '{self._type}'."
            )

    @require_field_init
    def _load(self):
        """Tries to load field data from a saved json file, or loads the
        default data if that's not possible. If the saved json file is
        invalid, an error is thrown.
        """
        if self.path.exists():
            with self.path.open("r") as f:
                json_dict = json.load(f)
                self._check_data(json_dict)
                self._load_data_from_json_dict(json_dict)
        else:
            self._load_default()

    @require_field_init
    def _get_save_data(self) -> dict[str, Any]:
        """Returns a dictionary with everything that should be saved to the
        field's json file.
        """
        return {
            "version": self._version,
            "internal_version": self._internal_version,
            "data": self._data,
            "type": self._type,
        }

    @require_field_init
    def _save(self, mark_dirty: bool = True):
        """Saves the field to a json file if `self._dirty` or `mark_dirty` are
        `True`.
        """
        # TODO: Add support for making multiple edits without saving
        self._dirty |= mark_dirty
        if self._dirty and not self._transaction:
            if self._data != self._get_default_data():
                # If there is any data, save it
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("w") as f:
                    json.dump(self._get_save_data(), f)
            else:
                # If there is no data, remove the field's file instead of
                # saving one without anything meaningful in it.
                self.path.unlink(missing_ok=True)
            self._dirty = False


class Nested_Field(abc.Base_Datastore, abc.Base_Field, ABC):
    """A field that can store other fields. This can be used to group fields
    storing related data together.

    To use `Nested_Field`s, declare a subclass of `Nested_Field` with other
    fields as attributes.

    Fields that are attributes of `Nested_Field` will be saved together in a
    directory named after the field's name inside of the `Nested_Field`'s
    path.

    For examples on how to use `Nested_Fields`, see helper_fields.py
    """

    _name: str
    _path: Path

    def _create_field(self, parent: abc.Base_Datastore, name: str) -> "Nested_Field":
        ret: Nested_Field = super()._create_field(parent, name)  # type: ignore
        ret._path = parent._path / name
        ret._fields = {}

        # Load nested fields
        for attr_name, attr in type(ret).__dict__.items():
            for attr_name, attr in ret.__dict__.items():
                if isinstance(attr, abc.Base_Field):
                    new_field = attr._create_field(ret, attr_name)
                    ret._fields[attr_name] = new_field
                    setattr(ret, attr_name, new_field)

        return ret

    @property
    @require_field_init
    def name(self) -> str:
        return self._name

    @property
    @require_field_init
    def full_name(self) -> str:
        return f"{self._parent.full_name}.{self.name}"

    @property
    @require_field_init
    def path(self):
        return self._path


class Keyed_Field(
    Generic[types.Key_Type, types.Val_Type],
    Base_Datafield[types.Val_Type],
):
    """A field that stores values based on a key. These stored values are
    saved to disk when set and then restored when the bot restarts.

    `Keyed_Fields` must be used as attributes of an instance of a subclass of
    `Datastore` or in a `Nested_Field`.

    Attributes
    ------------
    key_encoder: types.Key_Encoder[types.Key_Type]
    A function that takes an object of type `types.Key_Type` and returns
    either a string or a tuple of strings that represent dictionary keys for
    where a value should be gotten from or stored. The object passed to
    `key_encoder` is the 'unencoded key', and the string(s) returned by
    `key_encoder` are the 'encoded key'. If the number of keys returned by
    `key_encoder` is not equal `key_depth`, an error will be raised.

    key_depth: int
    The number of keys that `key_encoder` should return. If `key_encoder`
    returns the wrong number of keys, an error is raised.

    version: int
    The field's version. Updates to the field's layout, name, or key encoding
    should be accompanied with a change to the version.
    TODO: Add ways to update out of date versions of the field.

    data_encoder: types.Data_Encoder[types.Val_Type]
    A function that takes an object of a type `types.Val_Type` and returns an
    object that is json serializable.

    data_decoder: types.Data_Decoder[types.Val_Type]
    A function that takes a json serializable representation of a value given
    by a `Data_Encoder` and returns an object of type `types.Val_Type`.

    fallback: Optional[types.Keyed_Field_Fallback[types.Val_Type]]
    A function that tries to return a value for `get` if it was unable to
    successfully either encode the passed `key`, the encoded key did not match
    `key_len`, or if the method find a value corresponding to that key. It
    takes the field's parent datastore, the unencoded key that was passed to
    `get`, and the value of `copy` passed to `Keyed_Field.get`
    """
    _data: dict[str, Any]
    _internal_version = 1
    _type = "keyed_field"

    def __init__(
        self,
        *,
        key_encoder: types.Key_Encoder[types.Key_Type],
        key_depth: int = 1,
        version: int,
        data_encoder: types.Data_Encoder[types.Val_Type] = lambda d: d,
        data_decoder: types.Data_Decoder[types.Val_Type] = lambda d: d,
        fallback: Optional[types.Keyed_Field_Fallback[types.Val_Type]] = None,
    ):
        self._fallback = fallback
        self._key_encoder = key_encoder
        self._key_depth = key_depth
        super().__init__(
            version=version,
            data_encoder=data_encoder,
            data_decoder=data_decoder,
        )

    @require_field_init
    def get(
        self, key: types.Key_Type, /, *, copy: bool = False, use_fallback: bool = True
    ) -> types.Val_Type:
        """Returns the value associated with `key` stored in the field. If no
        value is associated with `key` is stored the field or an error occurs
        encoding `key`, the field has a `fallback` function, and
        `use_fallback` is `True`, the return value of `self.fallback` is
        returned instead.

        Parameters
        ----------
        copy: bool
        Whether or not the method should return a deepcopy of the value. If
        the return value is a mutable object that may be at some point edited,
        copy should be `True` to avoid changes being made to the value without
        them being saved.

        use_fallback:
        Whether or not the field's fallback function should be used if the
        field does not have a value associated with `key`, or if `key` can not
        be encoded. If an error is raised by the fallback function it will
        propagate through `get`. If `use_fallback` is `False` or there is no
        fallback function, an error will be raised.
        """
        try:
            keys = self.key_encoder(key)
            if isinstance(keys, str):
                keys = (keys,)
            if len(keys) != self.key_depth:
                pass
            get_from = self._data
            for k in keys[:-1]:
                get_from = get_from[k]
            ret = self.data_decoder(get_from[keys[-1]])
            if copy:
                return cp.deepcopy(ret)
            else:
                return ret
        except Exception as e:
            if self.fallback is not None and use_fallback:
                return self.fallback(self._parent, key, copy=copy)
            else:
                raise e

    @require_field_init
    def set(self, key: types.Key_Type, val: types.Val_Type, /) -> None:
        """Sets a value for a given key. This will overwrite any previous
        value the key had. The new value will be automatically saved to disk.
        """
        keys = self.key_encoder(key)
        if isinstance(keys, str):
            keys = (keys,)
        save_to = self._data
        for k in keys[:-1]:
            if k not in save_to:
                save_to[k] = {}
            save_to = save_to[k]
        save_to[keys[-1]] = self.data_encoder(val)
        self._save()

    @require_field_init
    def _delete(self, d: dict[str, Any], keys: tuple[str, ...]) -> None:
        # Recursive empty dict deleter. Raises keyerror if keys are not in d
        if len(keys) > 1:
            self._delete(d[keys[0]], keys[1:])
        if not d[keys[0]]:
            del d[keys[0]]

    @require_field_init
    def delete(self, key: types.Key_Type, /) -> bool:
        """Deletes the associated value with a key. Returns whether or not
        `key` had a value associated with it.
        """
        try:
            keys = self.key_encoder(key)
            if isinstance(keys, str):
                keys = (keys,)
            self._delete(self._data, keys)
            self._save()
            return True
        except Exception:
            return False

    @require_field_init
    def delete_all(self) -> bool:
        """Deletes ALL values stored in the field. This is automatically
        saved, and CAN NOT be undone.
        Returns whether or not any data was stored in the field.
        """
        if self._data == self._get_default_data():
            return False
        self._data = self._get_default_data()
        self._save()
        return True

    @property
    def key_encoder(self) -> types.Key_Encoder[types.Key_Type]:
        return self._key_encoder

    @property
    def key_depth(self) -> int:
        return self._key_depth

    @property
    def fallback(self) -> Optional[types.Keyed_Field_Fallback[types.Val_Type]]:
        return self._fallback

    @require_field_init
    def _get_default_data(self) -> dict:
        return {}

    @require_field_init
    def _get_save_data(self) -> dict[str, Any]:
        return super()._get_save_data() | {
            "key_depth": self.key_depth,
        }

    @require_field_init
    def _check_data(self, json_dict: dict[str, Any]) -> None:
        super()._check_data(json_dict)

        # Check key depth
        if json_dict["key_depth"] != self.key_depth:
            raise ValueError(
                f"Saved field data has key depth '{json_dict['key_depth']}'; expected '{self.key_depth}'."
            )

    def _create_field(
        self, parent: abc.Base_Datastore, name: str
    ) -> "Keyed_Field[types.Key_Type, types.Val_Type]":
        ret: Keyed_Field[types.Key_Type, types.Val_Type] = super()._create_field(
            parent, name
        )  # type: ignore
        ret._load()
        return ret


class _No_Val_Type:
    """A sentinel value type for `Unkeyed_Field`s without stored values."""


_NO_VAL = _No_Val_Type()


class Unkeyed_Field(
    Generic[types.Val_Type],
    Base_Datafield[types.Val_Type],
):
    """A field that stores a value. This stored value is saved to disk when
    set and then restored when the bot restarts.

    `Keyed_Fields` must be used as attributes of an instance of a subclass of
    `Datastore` or in a `Nested_Field`.

    Attributes
    ------------
    version: int
    The field's version. Updates to the field's layout, name, or key encoding
    should be accompanied with a change to the version.
    TODO: Add ways to update out of date versions of the field.

    data_encoder: types.Data_Encoder[types.Val_Type]
    A function that takes an object of a type `types.Val_Type` and returns an
    object that is json serializable.

    data_decoder: types.Data_Decoder[types.Val_Type]
    A function that takes a json serializable representation of a value given
    by a `Data_Encoder` and returns an object of type `types.Val_Type`.

    fallback: Optional[types.Unkeyed_Field_Fallback[types.Val_Type]]
    A function that tries to return a value for `get` the field does not have
    any data stored. It takes the field's parent datastore, and the value of
    `copy` passed to `Unkeyed_Field.get`
    """

    _data: Union[types.Val_Type, _No_Val_Type]
    _internal_version = 1
    _type = "unkeyed_field"

    def __init__(
        self,
        *,
        version: int,
        data_encoder: types.Data_Encoder[types.Val_Type] = lambda d: d,
        data_decoder: types.Data_Decoder[types.Val_Type] = lambda d: d,
        fallback: Optional[types.Unkeyed_Field_Fallback[types.Val_Type]] = None,
    ):
        self.fallback = fallback
        super().__init__(
            version=version,
            data_encoder=data_encoder,
            data_decoder=data_decoder,
        )

    @require_field_init
    def get(self, *, copy: bool = False, use_fallback: bool = True) -> types.Val_Type:
        """Returns the value stored in the field. If no value is stored,
        the field has a `fallback` function and `use_fallback` is `True`, the
        return value of `self.fallback` is returned instead.

        Parameters
        ----------
        copy: bool
        Whether or not the method should return a deepcopy of the value. If
        the return value is a mutable object that may be at some point edited,
        copy should be `True` to avoid changes being made to the value without
        them being saved.

        use_fallback:
        Whether or not the field's fallback function should be used if the
        field does not have a stored value. If an error is raised by the
        fallback function it will propagate through `get`. If `use_fallback`
        is `False` or there is no fallback function, an error will be raised.
        """
        if self._data is not _NO_VAL:
            if copy:
                return cp.deepcopy(self.data_decoder(self._data))
            else:
                return self.data_decoder(self._data)
        elif self.fallback and use_fallback:
            return self.fallback(self._parent, copy)
        else:
            raise ValueError("No value stored.")

    @require_field_init
    def set(self, val: types.Val_Type) -> None:
        """Sets a value for the field. This will overwrite any previous value
        the field had. The new value will be automatically saved to disk.
        """
        self._data = self.data_encoder(val)
        self._save()

    @require_field_init
    def delete(self) -> bool:
        """Deletes the value stored in the field. This is automatically saved,
        and CAN NOT be undone.
        Returns whether or not any data was stored in the field.
        """
        if self._data == self._get_default_data():
            return False
        self._data = self._data = self._get_default_data()
        self._save()
        return True

    @require_field_init
    def _get_default_data(self) -> _No_Val_Type:
        return _NO_VAL

    def _create_field(
        self, parent: abc.Base_Datastore, name: str
    ) -> "Unkeyed_Field[types.Val_Type]":
        ret: Unkeyed_Field[types.Val_Type] = super()._create_field(parent, name)  # type: ignore
        ret._load()
        return ret
