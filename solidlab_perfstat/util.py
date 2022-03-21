from datetime import datetime
from subprocess import PIPE, STDOUT, Popen
from typing import List, Tuple

from dateutil.parser import parse as dateutil_parse


def dump_rfc3339(dt: datetime) -> str:
    assert dt.tzinfo is not None  # enforce timezone aware (non-naive) datetime
    dt = dt.replace(microsecond=0)  # not interested in sub second precision
    res = dt.isoformat()
    if res.endswith("+00:00"):
        # +00:00 is nicer to write as Z (Zulu timezone)
        # But both are valid.
        res = res[:-6] + "Z"
    return res


def parse_rfc3339(date_str: str) -> datetime:
    # dateutil_parse parses ISO 8601, which contains almost all of RFC3339. This is good enough.
    res = dateutil_parse(date_str)
    assert res.tzinfo is not None  # assert timezone aware (non-naive) datetime
    return res


def call_external_command(*params: str, **kwargs) -> Tuple[int, str]:
    res = ""
    com: List[str] = list(params)
    kwargs["stdout"] = PIPE
    kwargs["stderr"] = STDOUT
    kwargs["universal_newlines"] = True
    with Popen(com, **kwargs) as proc:
        for line in proc.stdout:
            res += line
        res_code = proc.wait()
        # if res_code != 0:
        #     raise Exception('Command returned error ({}): {} (command={} )'.format(res_code, res.strip(), com))
        return res_code, res.strip()
