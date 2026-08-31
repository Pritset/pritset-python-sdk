import os

from pritset import PritsetClient


access_token = os.environ.get("PRITSET_ACCESS_TOKEN")
secret = os.environ.get("PRITSET_SECRET")
template_id = os.environ.get("PRITSET_TEMPLATE_ID")

if not access_token or not secret or not template_id:
    raise RuntimeError("Set PRITSET_ACCESS_TOKEN, PRITSET_SECRET, and PRITSET_TEMPLATE_ID.")

with PritsetClient(access_token=access_token, secret=secret) as pritset:
    pdf = pritset.documents.generate(
        template_id,
        {"title": "Hello Pritset", "description": "Generated with the official Python SDK."},
    )
    pdf.save_to_file("generated.pdf")
