import mimetypes
from typing import Tuple, Optional

from urllib3 import Timeout

#
#
# TODO: this is a copy paste from solidlab-attach. Use it as an import from that lib instead!
#
#
#


def upload_attachment_file(
    session,
    *,
    result_endpoint: str,
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

        return upload_attachment(
            session,
            result_endpoint=result_endpoint,
            attach_type=attach_type,
            sub_type=sub_type,
            description=description,
            content=content,
            content_type=content_type,
        )


def upload_attachment(
    session,
    *,
    result_endpoint: str,
    attach_type: str,
    sub_type: str,
    description: str,
    content_type: str,
    content: bytes,
) -> Tuple[int, str]:
    """

    :param session:
    :param result_endpoint:
    :param attach_type:
    :param sub_type:
    :param description:
    :param content_type: examples "text/csv" "text/plain" "image/svg+xml" "image/png"
    :param content:
    :return:
    """
    assert result_endpoint.startswith("http")
    assert not result_endpoint.endswith("/")
    assert not result_endpoint.endswith("result/")
    assert not result_endpoint.endswith("result")
    assert not result_endpoint.endswith("attachment")
    assert not result_endpoint.endswith("attachment/")

    post_attach_meta_resp = session.post(
        f"{result_endpoint}/attachment",
        params={},
        headers={
            "Content-Type": content_type,
            "X-Solidlab-Attachment-Type": attach_type,
            "X-Solidlab-Attachment-Subtype": sub_type,
            "X-Solidlab-Attachment-Description": description,
        },
        timeout=Timeout(connect=2.0, read=3.0),
        data=content,
    )
    post_attach_meta_resp.raise_for_status()
    attachment_url = post_attach_meta_resp.json()["@id"]
    attachment_id = post_attach_meta_resp.json()["id"]
    return attachment_id, attachment_url
