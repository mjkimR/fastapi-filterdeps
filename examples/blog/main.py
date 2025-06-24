from fastapi import FastAPI
from fastapi.responses import RedirectResponse


from database import init_db
from api.posts import router as posts_router
from api.users import router as users_router
from api.comments import router as comments_router
from api.votes import router as votes_router


async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Blog API Example", lifespan=lifespan)
app.include_router(posts_router)
app.include_router(users_router)
app.include_router(comments_router)
app.include_router(votes_router)


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
