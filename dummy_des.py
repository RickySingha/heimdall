from fastapi import FastAPI, Response, Request
import random

app = FastAPI()

@app.post("/webhook")
async def receive(request: Request):
    body = await request.body()
    if random.random() < 0.5:   # fail half the time on purpose
        return Response(status_code=500)
    print("Destination received:", body)
    return Response(status_code=200)