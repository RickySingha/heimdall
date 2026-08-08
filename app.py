import os
from fastapi import FastAPI, Request, Response, status, HTTPException,Header,BackgroundTasks
import logging,httpx,asyncio
import uuid
import hashlib
import hmac
import time
import sqlite3
from contextlib import asynccontextmanager
from database import save_webhook,init_db,update_status

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("webhook_proxy")

SHARED_SECRET=os.environ.get("SHARED_SECRET","weekend_key").encode()
REPLAY_SECONDS = 300
DEST_URL=DEST_URL = os.environ.get("DEST_URL", "http://127.0.0.1:9000/webhook")
MAX_RETRIES = 5
BASE_BACKOFF_SEC = 2
# seen_signature: set[str] = set()
def verify_signature(payload: bytes, timestamp:str,incoming_signature: str) ->bool:
    if not incoming_signature or not timestamp:
        return False
    signed_payload = timestamp.encode() +b"."+payload
    expected_hash = hmac.new(SHARED_SECRET,signed_payload,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hash,incoming_signature)



# def is_replay(signature:str)->bool:
#     if signature in seen_signature:
#         return True
#     seen_signature.add(signature)
#     return False

@asynccontextmanager
async def lifespan(app:FastAPI):
    logger.info("Initialising database")
    init_db()
    logger.info("Database Initialised")
    yield




app = FastAPI(lifespan=lifespan)

async def forward_with_retry(request_id: str, client_id: str, payload: bytes, headers: dict):
    attempt = 0
    forward_headers = {
        "content-type" : headers.get("content-type", "application/json"),
        "x-request-id" : request_id,
        "x-client_id" : client_id
    }
    async with httpx.AsyncClient(timeout=5) as client:
        while attempt <= MAX_RETRIES:
            try:
                response = await client.post(DEST_URL,content=payload,headers=forward_headers
                                             ) 
                if 200 <=response.status_code <300:
                    update_status(request_id=request_id,status="delivered",retry_count=attempt)
                    logger.info(f"[{request_id}] Delivered on attempt: {attempt}")
                    return
                logger.warning(f"[{request_id}] Destination returned {response.status_code}")

            except httpx.RequestError as err:
                logger.warning(f"[{request_id}] Delivery attempt {attempt} failed: {err}")

            attempt+=1
            update_status(request_id,"retrying",attempt)
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(BASE_BACKOFF_SEC**attempt)

    update_status(request_id,"failed",attempt)
    logger.error(f"[{request_id}] Exhausted retries. Marking as failed (dead letter)")

@app.post("/v1/intake/{client_id}")
async def webhook_intake(client_id : str, request: Request, background_tasks: BackgroundTasks,
                         x_webhook_signature: str = Header(default=None),
                         x_webhook_timestamp: str = Header(default=None)):
    request_id = str(uuid.uuid4())
    raw_payload = await request.body()
    headers = dict(request.headers)

    if not verify_signature(raw_payload,x_webhook_timestamp,x_webhook_signature):
        logger.warning(f"[{request_id}] Security Rejection: Invalid signature for client {client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cryptographic signature"
        )
    try:
        ts = int(x_webhook_timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail = "Bad timing request")
    if abs(time.time()-ts)  > REPLAY_SECONDS:
        logger.warning(f"[{request_id}] Rejected timestamp outside of tolerance")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request expired")

    try:
        save_webhook(request_id,client_id,raw_payload,headers,x_webhook_signature,ts)
    except sqlite3.IntegrityError:
        logger.warning(f"[{request_id}] Rejected: replayed signature")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate Request")
    background_tasks.add_task(forward_with_retry,request_id,client_id,raw_payload,headers)

    return Response(content="Accepted",status_code=status.HTTP_202_ACCEPTED,media_type="text/plain")

    # logger.info(f"Received incoming request for client: {client_id}")
    # logger.info(f"Payload size: {len(raw_payload)} bytes")
    # logger.info(f"Headers: {headers}")

    # return Response(
    #     content="Accepted",
    #     status_code=status.HTTP_202_ACCEPTED,
    #     media_type="text/plain"
    # )