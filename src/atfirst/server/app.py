from fastapi import FastAPI

app = FastAPI()


def get_app() -> FastAPI:
    return app
