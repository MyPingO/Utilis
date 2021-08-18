import math
from typing import Optional


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


# TODO: Optimize algorithm
# TODO: Add kwargs support
def format_maxlen(
    fstring: str,
    *args,
    max_total_len: Optional[int] = 2000,
    max_arg_len: Optional[int] = None,
    add_ellipsis: bool = True,
) -> str:
    """Formats a string replacing instances of `"{}"` with args while keeping
    below a maximum length.

    Examples
    -----------
    .. code-block:: python3
        format_maxlen(
            "AB {} CD {}",
            "123",
            456,
            max_total_len=None
        ) == "AB 123 CD 456"

    .. code-block:: python3
        format_maxlen(
            "AB {} CD",
            123456789
            max_total_len=12
        ) == "AB 123... CD"

    .. code-block:: python3
        format_maxlen(
            "AB {} CD",
            123456789
            max_total_len=None,
            max_arg_len=6
        ) == "AB 123... CD"

    Parameters
    -----------
    fstring: str,
    The string to format. "{}" should be used as placeholders for args.

    *args
    The args to replace the placeholder "{}"s in `fstring` with. The number of
    args must be equal to the number of placeholders.

    max_total_len: Optional[int]
    The maximum length for the return string. args will be shortened roughly
    evenly until the length of the final string will be within the max length.
    `fstring` will not be shortened to reduce the final string's length.

    max_arg_len: Optional[int]
    The maximum length for every arg. This is applied before shortening args
    to ensure that the return string's length is also within `max_total_len`.

    add_ellipsis: bool
    Whether or not args that are shortened to fit either `max_total_len` or
    `max_arg_len` should have '...' at the end.
    """
    # If there's nothing to format, return the string.
    if "{}" not in fstring and len(args) == 0:
        return fstring

    split_fstring = fstring.split("{}")
    if len(split_fstring) != len(args) + 1:
        raise ValueError("Number of arguments does not match number of placeholders.")

    # Convert args to a list of strings
    if max_arg_len is not None:
        # Limit the length of each arg to max_arg_len if it was given.
        arg_list = [bound_str(str(arg), max_arg_len, add_ellipsis) for arg in args]
    elif max_total_len is not None:
        # Limit the length of each arg to max_total_len if it was given,
        # because each arg can be at most that long.
        arg_list = [bound_str(str(arg), max_total_len, add_ellipsis) for arg in args]
    else:
        arg_list = [str(arg) for arg in args]

    # If a max length was given for the string, shorten args to fit it.
    if max_total_len is not None:
        # Get a list of the length of every arg
        arg_lens = [len(arg) for arg in arg_list]

        # Get the total lengths of the fstring and args.
        total_fstring_len = sum(len(s) for s in split_fstring)
        total_args_len = sum(arg_lens)

        # The maximum total length of all args in order to keep the return
        # string's length within max_total_len.
        total_args_maxlen = max_total_len - total_fstring_len

        # If the fstring is too long to fit any args in, return the fstring.
        if total_args_len <= 0:
            return "".join(split_fstring)

        # Keep shortening the longest args until all args are within the total
        # length for all args.
        while total_args_len > total_args_maxlen:
            # Get the longest and second longest arg lengths.
            sorted_unique_lens = sorted(set(arg_lens))
            maxlen = sorted_unique_lens[-1]
            if len(sorted_unique_lens) > 1:
                second_maxlen = sorted_unique_lens[-2]
            else:
                second_maxlen = 0

            # Get the indecies of args to shorten. The list is reversed so
            # that the last args get shortened the most.
            max_len_indecies = [i for i, v in enumerate(arg_lens) if v == maxlen]
            max_len_indecies.reverse()

            # How much space can be saved by shortening the longest strings.
            # This can either be enough space to bring the total length of
            # args below the max length, or shortening the longest strings to
            # the length of the second largest strings, so that the second
            # largest strings will also be shortened in the next step in the
            # loop.
            total_delta = min(
                total_args_len - total_args_maxlen,
                len(max_len_indecies) * (maxlen - second_maxlen),
            )

            # Shorten the longest args.
            for index_num, index in enumerate(max_len_indecies):
                # The amount to shorten the arg. This should be as short as
                # possible.
                # The amount that each string gets shortened by gets smaller
                # as the loop continues, as total_delta will decrease and
                shorten_amount = math.ceil(
                    total_delta / (len(max_len_indecies) - index_num)
                )
                # What to shorten the arg to. Should not be shorter than the
                # second largest args.
                shorten_to = max(
                    maxlen - shorten_amount,
                    second_maxlen,
                )
                # Shorten the arg
                arg_list[index] = bound_str(arg_list[index], shorten_to, add_ellipsis)
                # Update the arg's length in the list of arg lengths
                arg_lens[index] = len(arg_list[index])
                # Decrease how much the rest of the longest args need to be
                # shortened by in order to reach the target total length.
                delta = maxlen - arg_lens[index]
                total_delta -= delta

            # Update the total arg lengths.
            total_args_len = sum(arg_lens)

    # Insert args into the fstring and return
    ret = "".join(
        fstring_part + arg_part
        for fstring_part, arg_part in zip(split_fstring, arg_list)
    )
    return ret + split_fstring[-1]
