from . import abc

from typing import Any, Protocol, Tuple, TypeVar, Union

T = TypeVar("T")
# https://stackoverflow.com/questions/67404067/
T_cov = TypeVar("T_cov", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

Key_Type = TypeVar("Key_Type")
Val_Type = TypeVar("Val_Type")


class Data_Encoder(Protocol[T_contra]):
    """A function that takes an object of a field's value type and returns an
    object that is json serializable.

    Example
    -----------
    .. code-block:: python3
        def encode_datetime(d: datetime.datetime) -> str:
            return d.isoformat()
    """

    def __call__(self, a: T_contra) -> Any:
        ...


class Data_Decoder(Protocol[T_cov]):
    """A function that takes a json serializable representation of a field's
    value type given by a `Data_Encoder` and returns an object of the field's
    value type.

    Example
    -----------
    .. code-block:: python3
        def decode_datetime(s: str) -> datetime.datetime:
            return datetime.datetime.fromisoformat(s)
    """

    def __call__(self, obj: Any) -> T_cov:
        ...


# For some reason `tuple[str, ...]` gives an error in mypy but
# `Tuple[str, ...]` does not
class Key_Encoder(Protocol[T_contra]):
    """A function that takes a `Keyed_Field`'s key type and returns either a
    string or a tuple of strings that represent dictionary keys for where a
    value should be gotten from or stored.

    Examples
    -----------
    .. code-block:: python3
        def guild_member_key_encoder(
            guild: discord.Guild,
            member: discord.Member,
        ) -> tuple[str, str]:
            return (str(guild.id), str(member.id))

    .. code-block:: python3
        guild_key_encoder: Key_Encoder[discord.Guild] = lambda guild: str(
            guild.id
        )
    """

    def __call__(self, key: T_contra) -> Union[Tuple[str, ...], str]:
        ...


class Keyed_Field_Fallback(Protocol[T_cov]):
    """A function that tries to return a value for `Keyed_Field.get` if it was
    unable to successfully either encode the passed `key`, the encoded key did
    not match `Keyed_Field.key_len`, or if the method find a value
    corresponding to that key. It takes the `Keyed_Field`'s parent datastore,
    the unencoded key that was passed to `Keyed_Field.get`, and the value of
    `copy` passed to `Keyed_Field.get`

    For examples, see `utils.datastores.helpers`
    """

    def __call__(self, datastore: "abc.Base_Datastore", key: Any, copy: bool) -> T_cov:
        ...


class Unkeyed_Field_Fallback(Protocol[T_cov]):
    """A function that tries to return a value for `Unkeyed_Field.get` if the
    `Unkeyed_Field` has no value set. It takes the `Unkeyed_Field`'s parent
    datastore, the the value of `copy` passed to `Unkeyed_Field.get`

    For examples, see `utils.datastores.helpers`
    """

    def __call__(self, datastore: "abc.Base_Datastore", copy: bool) -> T_cov:
        ...
