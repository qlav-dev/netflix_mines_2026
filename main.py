from fastapi import FastAPI, Request
from pydantic import BaseModel

from db import get_connection

app = FastAPI()


@app.get("/ping")
def ping():
    return {"message": "pong"}

class Film(BaseModel):
    id: int | None = None
    nom: str
    note: float | None = None
    dateSortie: int
    image: str | None = None
    video: str | None = None
    genreId: int | None = None

@app.get("/films/{film_id}")
async def getfilm(request: Request):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM film WHERE id = {request.path_params["film_id"]}
            """)
        res = cursor.fetchone() # C 1 clai primair
        return res

@app.get("/genres")
async def getGenres():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * from genre
            """)
        res = cursor.fetchall()
        return res

@app.post("/film")
async def createFilm(film : Film):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO Film (Nom,Note,DateSortie,Image,Video)  
            VALUES('{film.nom}',{film.note},{film.dateSortie},'{film.image}','{film.video}') RETURNING *
            """)
        res = cursor.fetchone()
        print(res)
        return res


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
