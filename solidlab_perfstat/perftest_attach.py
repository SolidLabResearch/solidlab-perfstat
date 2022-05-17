import mimetypes
from typing import Tuple, Optional

from urllib3 import Timeout

#
#
# TODO: this is a copy paste from solidlab-attach. Use it as an import from that lib instead!
#
#
#


def upload_artifact_file(
    session,
    *,
    perftest_endpoint: str,
    attach_type: str,
    sub_type: str,
    description: str,
    filename: str,
    content_type: Optional[str] = None,
) -> Tuple[int, str]:
    if not content_type:
        guesses = mimetypes.guess_type(filename)
        if not guesses:
            raise ValueError(f"mime type could not be guessed from filename.")
        content_type = guesses[0]
        # logger.debug(f"Guessed mime-type from filename: {mime_type!r}")

    with open(filename, "rb") as f:
        content = f.read()

        return upload_artifact(
            session,
            perftest_endpoint=perftest_endpoint,
            attach_type=attach_type,
            sub_type=sub_type,
            description=description,
            content=content,
            content_type=content_type,
        )


def upload_artifact(
    session,
    *,
    perftest_endpoint: str,
    attach_type: str,
    sub_type: str,
    description: str,
    content_type: str,
    content: bytes,
) -> Tuple[int, str]:
    """

    :param session:
    :param perftest_endpoint:
    :param attach_type:
    :param sub_type:
    :param description:
    :param content_type: examples "text/csv" "text/plain" "image/svg+xml" "image/png"
    :param content:
    :return:
    """
    assert perftest_endpoint.startswith("http")
    assert "/perftest/" in perftest_endpoint
    assert not perftest_endpoint.endswith("/")
    assert not perftest_endpoint.endswith("perftest/")
    assert not perftest_endpoint.endswith("perftest")
    assert not perftest_endpoint.endswith("artifact")
    assert not perftest_endpoint.endswith("artifact/")

    post_attach_meta_resp = session.post(
        f"{perftest_endpoint}/artifact",
        params={},
        headers={
            "Content-Type": content_type,
            "X-Solidlab-Artifact-Type": attach_type,
            "X-Solidlab-Artifact-Subtype": sub_type,
            "X-Solidlab-Artifact-Description": description,
        },
        timeout=Timeout(connect=2.0, read=3.0),
        data=content,
    )
    post_attach_meta_resp.raise_for_status()
    artifact_url = post_attach_meta_resp.json()["@id"]
    artifact_id = post_attach_meta_resp.json()["id"]
    return artifact_id, artifact_url
