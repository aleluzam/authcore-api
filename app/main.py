from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def route():
    return "Hello"