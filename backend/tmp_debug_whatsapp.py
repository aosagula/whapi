import asyncio
import json

import asyncpg
import httpx


TARGET_ID = "11557034-e6fc-4e5c-9699-266ebae71637"


async def main() -> None:
    conn = await asyncpg.connect(
        host="host.docker.internal",
        port=5433,
        user="whapi_user",
        password="Us3eWhapi123",
        database="whapi_db",
    )
    row = await conn.fetchrow(
        """
        select id, session_name, wpp_token, status, phone_number
        from whatsapp_numbers
        where id = $1
        """,
        TARGET_ID,
    )
    await conn.close()

    if not row:
        print("NOT_FOUND")
        return

    data = dict(row)
    print("DB:", json.dumps(data, default=str))

    headers = {"Authorization": f"Bearer {data['wpp_token']}"}
    base = f"https://wppconnect.agentic4biz.com/api/{data['session_name']}"

    async with httpx.AsyncClient(timeout=20) as client:
        status_resp = await client.get(f"{base}/status-session", headers=headers)
        print("STATUS CODE:", status_resp.status_code)
        print("STATUS BODY:", status_resp.text[:4000])

        qr_resp = await client.get(f"{base}/qrcode-session", headers=headers)
        print("QR CODE:", qr_resp.status_code)
        print("QR CONTENT-TYPE:", qr_resp.headers.get("content-type"))
        if "image" in (qr_resp.headers.get("content-type") or ""):
            print("QR BYTES:", len(qr_resp.content))
        else:
            print("QR BODY:", qr_resp.text[:4000])


asyncio.run(main())
