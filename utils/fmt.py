import string
from typing import Any, Mapping, Optional, Sequence, Union


def bound_str(s: str, maxlen: int, add_ellipsis: bool = True) -> str:
    """Shortens a string to a maximum length if it is too long.

    Parameters
    -----------
    s: str
    The string to shorten.

    maxlen: int
    The maximum length for the string being shortened.

    add_ellipsis: bool
    Whether or not '...' should be added to the end of the string if it is
    shortened. The ellipses are included when calculating the max length.
    """
    if len(s) <= maxlen:
        return s
    elif add_ellipsis:
        if maxlen <= 3:
            return "." * maxlen
        else:
            return f"{s[:maxlen-3]}..."
    else:
        return s[:maxlen]


def format_maxlen(
    format_string: str,
    /,
    *args,
    max_total_len: Optional[int] = 2000,
    max_field_len: Optional[int] = None,
    add_ellipsis: bool = True,
    **kwargs,
) -> str:
    """Formats a string while while keeping below a maximum length.

    Examples
    -----------
    .. code-block:: python3
        format_maxlen(
            "AB {} CD {}",
            "123",
            456,
            max_total_len=None,
        ) == "AB 123 CD 456"

    .. code-block:: python3
        format_maxlen(
            "AB {num} CD",
            num=123,
            max_total_len=None,
        ) == "AB 123 CD"

    .. code-block:: python3
        format_maxlen(
            "AB {} CD",
            123456789,
            max_total_len=12,
        ) == "AB 123... CD"

    .. code-block:: python3
        format_maxlen(
            "AB {} CD",
            123456789,
            max_total_len=None,
            max_field_len=6,
        ) == "AB 123... CD"

    Parameters
    -----------
    format_string: str,
    The string to format. Uses standard Python string format specifiers.
    https://docs.python.org/3/library/string.html#format-string-syntax

    *args
    args to insert into replacement fields. There can not be any args unused
    by `format_string`.

    max_total_len: Optional[int]
    The maximum length for the return string. Replacement fields will be
    shortened roughly evenly until the length of the final string will be
    within the max length. `format_string` will not be shortened to reduce the
    return string's length.

    max_field_len: Optional[int]
    The maximum length for every replacement field. This is applied before
    shortening fields to ensure that the return string's length is also within
    `max_total_len`.

    add_ellipsis: bool
    Whether or not fields that are shortened to fit either `max_total_len` or
    `max_field_len` should have '...' at the end.

    *kwargs
    kwargs to insert into replacement fields. There can not be any kwargs
    unused by `format_string`.
    """
    return Maxlen_Formatter(
        max_total_len=max_total_len,
        max_field_len=max_field_len,
        add_ellipsis=add_ellipsis,
        allow_unused_args=False,
    ).format(format_string, *args, **kwargs)


class Maxlen_Formatter(string.Formatter):
    def __init__(
        self,
        *,
        max_total_len: Optional[int] = 2000,
        max_field_len: Optional[int] = None,
        add_ellipsis: bool = True,
        allow_unused_args: bool = False,
    ):
        """Parameters
        -----------
        max_total_len: Optional[int]
        The maximum length for the return string. Replacement fields will be
        shortened roughly evenly until the length of the final string will be
        within the max length. `format_string` will not be shortened to reduce
        the return string's length.

        max_field_len: Optional[int]
        The maximum length for every replacement field. This is applied before
        shortening fields to ensure that the return string's length is also
        within `max_total_len`.

        add_ellipsis: bool
        Whether or not fields that are shortened to fit either `max_total_len`
        or `max_field_len` should have '...' at the end.

        allow_unused_args: bool
        If there are any unused args or kwargs passed to `format` and
        `allow_unused_args` is `False`, an error will be thrown.
        """
        self.max_total_len = max_total_len
        self.max_field_len = max_field_len
        self.add_ellipsis = add_ellipsis
        self.allow_unused_args = allow_unused_args

    def vformat(
        self, format_string: str, args: Sequence[Any], kwargs: Mapping[str, Any]
    ) -> str:
        used_args: set[str] = set()
        result, _ = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(list(used_args), args, kwargs)
        return result

    def _vformat(
        self,
        format_string: str,
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
        used_args: set[str],
        recursion_depth: int,
        auto_arg_index: int = 0,
    ):
        # Slightly modified version of string.Formatter._vformat method
        if recursion_depth < 0:
            raise ValueError("Max string recursion exceeded")

        literals = []
        formatted_fields = []
        ends_with_field = False
        for literal_text, field_name, format_spec, conversion in self.parse(
            format_string
        ):
            # output the literal text
            literals.append(literal_text)
            # store whether or not the parser returned a field
            ends_with_field = field_name is not None

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # handle arg indexing when empty field_names are given.
                if field_name == "":
                    if auto_arg_index is False:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    # disable auto arg incrementing, if it gets
                    # used later on, then an exception will be raised
                    auto_arg_index = False

                # given the field_name, find the object it references
                #  and the argument it came from
                obj, arg_used = self.get_field(field_name, args, kwargs)
                used_args.add(arg_used)

                if conversion is not None:
                    # do any conversion on the resulting object
                    obj = self.convert_field(obj, conversion)

                if format_spec is not None:
                    # expand the format spec, if needed
                    format_spec, auto_arg_index = self._vformat(
                        format_spec,
                        args,
                        kwargs,
                        used_args,
                        recursion_depth - 1,
                        auto_arg_index=auto_arg_index,
                    )
                if format_spec is not None:
                    # format the object and append to the result
                    formatted_field = self.format_field(obj, format_spec)

                formatted_fields.append(
                    bound_str(
                        formatted_field,
                        self.max_field_len,
                        self.add_ellipsis,
                    )
                    if self.max_field_len is not None
                    else formatted_field
                )

        if literals or formatted_fields:
            if self.max_total_len is not None:
                # Bound fields
                max_total_field_len = self.max_total_len - sum(
                    (len(s) for s in literals)
                )
                formatted_fields = self._bound_fields(
                    formatted_fields, max_total_field_len
                )

            # Combine literals and fields
            ret = "".join(
                (literal + field for literal, field in zip(literals, formatted_fields))
            )
            # If the last iteration through parse had a literal, add it to the
            # end of ret.
            if not ends_with_field:
                ret += literals[-1]
            return ret, auto_arg_index
        else:
            return "", auto_arg_index

    def _bound_fields(self, fields: list[str], max_field_len: int) -> list[str]:
        if self.max_total_len is None:
            return fields

        field_lens = [len(s) for s in fields]
        total_field_len = sum(field_lens)

        # Bound fields if necessary
        if max_field_len < total_field_len:
            field_lens.sort()
            running_field_len_sum = 0
            for field_len, remaining_fields in zip(
                field_lens, range(len(fields), 0, -1)
            ):
                # Check to see whether or not the return string would remain
                # within the max length if all the remaining fields were the
                # same length as the current field. If not, then find how much
                # all of the remaining strings would have to be shortened by
                # to remain within the max length and shorten them to that
                # length.
                if (
                    running_field_len_sum + (field_len * remaining_fields)
                    >= max_field_len
                ):
                    # In order to ensure that the replacement fields at the
                    # end of the format string get shortened the most,
                    # bound_len rounds up for the max length for each field.
                    # long_fields then keeps track of how many fields can have
                    # this rounded-up length before the fields must be
                    # shortened one extra character.
                    # Ex. for the fields ["ABCD", "abcd" "1234"], when
                    # shortening to a max total field length of 8, bound_len
                    # would be 3 and long_fields would be 2, meaning the first
                    # 2 fields "ABCD" and "abcd" would be bound to 3
                    # characters, and "1234" would be bound to 2 characters.
                    bound_len = (
                        (max_field_len - running_field_len_sum) // remaining_fields
                    ) + 1
                    long_fields = (
                        max_field_len
                        - running_field_len_sum
                        - (remaining_fields * (bound_len - 1))
                    )
                    break
                else:
                    running_field_len_sum += field_len

            for index, field in enumerate(fields):
                if len(field) > bound_len:
                    fields[index] = bound_str(
                        field, bound_len - (long_fields <= 0), self.add_ellipsis
                    )
                    long_fields -= 1

        return fields

    def check_unused_args(
        self,
        used_args: Sequence[Union[int, str]],
        args: Sequence[Any],
        kwargs: Mapping[str, Any],
    ) -> None:
        if not self.allow_unused_args:
            for i in range(len(args)):
                if i not in used_args:
                    raise ValueError(f"arg {i} ({args[i]}) was never used")
            for key in kwargs.keys():
                if key not in used_args:
                    raise ValueError(f"kwarg {key} ({kwargs[key]}) was never used")
