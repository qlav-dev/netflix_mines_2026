from fastapi import FastAPI, Request
from pydantic import BaseModel

from db import get_connection


# Gestion des token user
import jwt

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import bcrypt
from datetime import timedelta
import datetime as dt

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

# connection

class User(BaseModel):
    email: str = None
    pseudo: str = None
    password: str = None

@app.post("/auth/register")
async def registerUser(user: User):
    # On met le sel "+ pseudo"
    salt = bcrypt.gensalt()

    # Hashing the password
    hash_password = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO Utilisateur (AdresseMail, Pseudo, MotDePasse) VALUES('{user.email}', '{user.pseudo}', '{hash_password}') RETURNING *
            """)
        res = dict(cursor.fetchone()) # On recup ce qu'on a mis dedans
        
        token = create_access_token(res, timedelta(days=1))
        output_dict = {
        "access_token": token,
        "token_type": "bearer"
        }

        return output_dict

@app.post("/auth/login")
async def loginUser(user: User ):
    ...

SECRET_KEY = "4a337e2670188a0b893fb6280f6890efbda50275c6f07cd68880afaf143c8996"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = dt.datetime.utcnow() + expires_delta
    else:
        expire = dt.datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
