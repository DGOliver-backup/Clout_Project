from fastapi import FastAPI, Response

app = FastAPI(title="Fake Origin")


@app.get("/small.txt")
async def small():
    return Response(
        content=b"hello world",
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=30"},
    )


@app.get("/medium.txt")
async def medium():
    return Response(
        content=b"a" * 1024 * 100,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=15"},
    )


@app.get("/large.txt")
async def large():
    return Response(
        content=b"b" * 1024 * 1024 * 5,
        media_type="text/plain",
        headers={"Cache-Control": "no-store"},
    )