from requests import Timeout


def post_attachment(
    session,
    result_post_endpoint: str,
    result_id: int,
    attach_type: str,
    subtype: str,
    description: str,
    content: bytes,
) -> int:
    if attach_type == "CSV":
        content_type = "text/csv"
    elif attach_type == "graph":
        content_type = "image/svg+xml"
        # content_type = "image/png"
    else:
        raise ValueError(f"Unknown type: {attach_type}")

    post_attach_meta_resp = session.post(
        f"{result_post_endpoint}/attachment",
        json={
            "test_result_id": result_id,
            "type": attach_type,
            "subtype": subtype,
            "description": description,
            "content_type": content_type,
        },
        params={},
        timeout=Timeout(connect=2.0, read=3.0),
    )
    post_attach_meta_resp.raise_for_status()
    attachment_id = post_attach_meta_resp.json()["id"]
    post_attach_data_resp = session.post(
        f"{result_post_endpoint}/attachment/{attachment_id}",
        data=content,
        params={},
        headers={"Content-type": attach_type},
        timeout=Timeout(connect=2.0, read=3.0),
    )
    post_attach_data_resp.raise_for_status()
    print(
        f"Uploaded: {subtype} {attach_type} to {result_post_endpoint}/attachment/{attachment_id}"
    )
    return attachment_id
