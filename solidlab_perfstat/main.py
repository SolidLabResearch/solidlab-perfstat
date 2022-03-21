import logging
import signal
import sys
from time import sleep

from solidlab_perfstat.result import Result

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.ERROR)


def main() -> int:
    show_help = True
    result_post_endpoint = None
    if len(sys.argv) == 2:
        result_post_endpoint = sys.argv[1].strip()
        show_help = not result_post_endpoint.startswith("http")
    elif len(sys.argv) == 1:
        result_post_endpoint = None
        show_help = False
    if show_help:
        print("Usage: interval-system-monitor [<result_post_endpoint>]")
        print(
            "          report_post_endpoint: the URL of the solidlab-perftest-server result endpoint (optional)"
        )
        return 1

    result = Result()

    # noinspection PyUnusedLocal
    def signal_handler(sig, frame):
        print("SIGINT received. Will finishing work.")
        result.finish()

    signal.signal(signal.SIGINT, signal_handler)

    result.start()  # forget first values, we can only get relevant values after 1 second.
    while result.running:
        sleep(1.0)
        result.add()

    if not result_post_endpoint:
        result.make_all()
    else:
        result.post_all(result_post_endpoint)

    return 0


if __name__ == "__main__":
    sys.exit(main())
