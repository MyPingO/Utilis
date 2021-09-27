import datetime
import re

_re_arg_splitter = re.compile(
    #       Match text in quotes as a single group
    #       V                          Match any number of double backslashes so that \" is a valid quote escape but \\" isn't.
    #       V                          V          Match \" within quotes
    #       V                          V          V        Match content within quotes
    #       V                          V          V        V          Match closing quote
    #       V                          V          V        V          V               Match unquoted content
    #       V                          V          V        V          V               V           End match with the end of the
    #       V                          V          V        V          V               V           string, a comma with any amount
    #       V                          V          V        V          V               V           of whitespace, or whitespace.
    #       V                          V          V        V          V               V           V
    r'\s*(?:(?:\"(?P<quoted_text>(?:(?:(?:\\\\)*)|(?:\\\")|(?:[^"]))*)\")|(?:(?P<text>[^\s,，]+)))(?P<tail>$|(?:\s*[,，]\s*)|(?:\s+))'
)
_re_remove_escaped_quote = re.compile(r'((?:[^\\]|^)(?:\\\\)*)\\"')


def split_args(args: str, treat_comma_as_space: bool = False) -> list[str]:
    """Splits a string of arguments into a list of arguments. Arguments are
    separated by spaces, unless `treat_comma_as_space` is `True` and `args`
    contains a comma not enclosed in quotes, in which case arguments are
    separated by commas. Arguments can also be grouped using quotes to include
    spaces or commas without being separated. Quotes escaped using a backslash
    can be included in quoted text. Double backslashes are also replaced with
    single backslashes.

    Examples
    -----------
    .. code-block:: python3
        split_args('A B C D') == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A B, C D', False) == ['A B', 'C D']

    .. code-block:: python3
        split_args('A B, C D', True) == ['A', 'B', 'C', 'D']

    .. code-block:: python3
        split_args('A "B C" D', False) == ['A', 'B C', 'D']

    .. code-block:: python3
        # Single escaped backslash
        split_args('A "B\\"C" D', False) == ['A', 'B"C', 'D']
    """
    comma_separated = False

    # Get matches
    matches = []
    for m in _re_arg_splitter.finditer(args):
        matches.append(m)
        comma_separated = comma_separated or (
            not treat_comma_as_space
            and m.group("tail") != ""
            and not m.group("tail").isspace()  # Checks for comma
        )

    # Matches can contain their arg in the groups "text" or "quoted_text"
    if not comma_separated:
        ret = [
            m.group("text") if m.group("text") is not None else m.group("quoted_text")
            for m in matches
        ]
    else:
        # If args are comma separated, group all matches in between commas
        # into a single string.
        ret = []

        # A list of matches that appear together before a comma
        combine: list[re.Match] = []
        for match in matches:
            if match.group("tail") and not match.group("tail").isspace():
                # If match ends with a comma, combine it with previous matches
                # without commas into one single arg.

                if match.group("text"):
                    ret.append(
                        "".join(m.group(0) for m in combine) + match.group("text")
                    )
                elif not combine:
                    # If the match contains text in quotes and there are no
                    # previous matches to combine it with, add only the text
                    # inside of the quotes to the list of arguments.
                    ret.append(match.group("quoted_text"))
                else:
                    ret.append(
                        "".join(m.group(0) for m in combine)
                        + match.group("quoted_text")
                    )
                combine = []
            else:
                combine.append(match)
        if combine:
            if len(combine) == 1 and combine[0].group("quoted_text") is not None:
                # If there is only one match that contains text in quotes add
                # only the text inside of the quotes to the list of arguments.
                last_arg = combine[0].group("quoted_text")
            else:
                # Otherwise, combine all remaining matches into one argument
                last_arg = "".join(m.group(0) for m in combine[:-1])
                # Exclude the tail of the last match
                last_match = combine[-1]
                last_arg += (
                    last_match.group("text")
                    if last_match.group("text") is not None
                    else last_match.group("quoted_text")
                )
            ret.append(last_arg)

    # Replace \" with " and \\ with \
    ret = [_re_remove_escaped_quote.sub(r'\1"', s).replace("\\\\", "\\") for s in ret]

    return ret


re_time = re.compile(
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>[ap]m)?", re.IGNORECASE
)


def str_to_time(s: str) -> datetime.time:
    """Return s as a timezone naive time, or raise an exception on failure.
    Only handles hours and minutes. Does not handle seconds.
    """
    m = re_time.fullmatch(s.strip())
    if m is None:
        raise ValueError(f'Could not parse"{s}" as time.')

    minute = int(m.group("minute")) if m.group("minute") else 0

    hour = int(m.group("hour"))
    if m.group("period") is not None:
        is_am = m.group("period").casefold() == "am"
        if is_am:
            # Handle AM times
            if hour == 12:
                # Change 12am to midnight
                hour = 0
            elif hour > 12:
                raise ValueError(f"Can not have an AM time after 12.")
        else:
            # Handle PM times
            if hour < 12:
                hour += 12

    return datetime.time(hour, minute)


_re_month_name_date = re.compile(
    r"(?P<month>[a-z]{3,9})\s+(?P<day>\d{1,2})(?:(?:(?:\s*,\s*)|(?:\s*))(?P<year>(?:\d{4})|(?:\d{2}))$)?",
    re.IGNORECASE,
)


def _auto_set_date_year(d: datetime.date) -> datetime.date:
    """For dates without years, changes the year from the default of 1900 to
    the current year or next year, depending on whether the month and day have
    passed the current year or not.
    """
    today = datetime.date.today()
    d = d.replace(year=today.year)
    if d < today:
        d = d.replace(year=d.year + 1)
    return d


def str_to_date(s: str, require_year: bool = False) -> datetime.date:
    """Return s as a date, or raise an exception on failure. Function assumes
    month/day/year format and is case and whitespace insensitive.

    Examples of valid formats for September 30th, 2021:
      9/30/21
      9/30/2021
      09/30/21
      09/30/2021
      September 30 21
      September 30, 21
      September 30 2021
      September 30, 2021
      Sep 31 21
      Sep 31, 21
      Sep 31 2021
      Sep 31, 2021

    If `require_year` is `False`, then the year can be omitted. If the current
    date is before the month and day given, then the year will be set to the
    current year. Otherwise, the year will be set to the next year.
    """
    s = s.strip()
    # Try to parse date as month/day/year
    for format_code in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(s, format_code).date()
        except Exception:
            pass
    if not require_year:
        # Try to parse date as month/day
        try:
            return _auto_set_date_year(datetime.datetime.strptime(s, "%m/%d").date())
        except Exception:
            pass
    # Try to parse date as written month then day and possibly year
    m = _re_month_name_date.fullmatch(s)
    if m:
        if m.group("year"):
            parse_date = f"{m.group('year')} {m.group('month')} {m.group('day')}"
            # Try to parse date
            year_fmt = "%y" if len(m.group("year")) == 2 else "%Y"
            for month_fmt in ("%b", "%B"):
                format_code = f"{year_fmt} {month_fmt} %d"
                try:
                    return datetime.datetime.strptime(parse_date, format_code).date()
                except Exception:
                    pass
        elif not require_year:
            parse_date = f"{m.group('month')} {m.group('day')}"
            today = datetime.date.today()

            for month_fmt in ("%b", "%B"):
                try:
                    format_code = f"{month_fmt} %d"
                    return _auto_set_date_year(
                        datetime.datetime.strptime(s, format_code).date()
                    )
                except Exception:
                    pass
    raise ValueError(f'Could not parse "{s}" as date.')


re_duration = re.compile(r"(?:(?P<weeks>\d+)\s*w(?:eeks?)?)?\s*(?:(?P<days>\d+)\s*d(?:ays?)?)?\s*(?:(?P<hours>\d+)\s*h(?:ours?)?)?\s*(?:(?P<minutes>\d+)\s*m(?:inutes?)?)?$", re.IGNORECASE)


def str_to_timedelta(s: str) -> datetime.timedelta:
    m = re_duration.fullmatch(s.strip())
    if m is None:
        raise ValueError(f'Could not parse "{s}" as datetime.')

    match = m.groupdict(default=0)
    for k, v in match.items():
        match[k] = int(v)
    return datetime.timedelta(**match)
