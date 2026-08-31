import os
import time

from pritset import PritsetClient, Upload


access_token = os.environ.get("PRITSET_ACCESS_TOKEN")
secret = os.environ.get("PRITSET_SECRET")

if not access_token or not secret:
    raise RuntimeError("Set PRITSET_ACCESS_TOKEN and PRITSET_SECRET.")

with PritsetClient(access_token=access_token, secret=secret) as pritset:
    created = pritset.templates.create(
        name="SDK example %d" % int(time.time()),
        tags="sdk,example",
        template=Upload("./invoice.docx"),
    )
    try:
        details = pritset.templates.get(created.id)
        print(details.template.name)
    finally:
        pritset.templates.delete(created.id)
