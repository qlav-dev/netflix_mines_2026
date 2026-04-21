from fastapi import Depends, FastAPI, Request, Header
from pydantic import BaseModel
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db import get_connection
from typing import Annotated



# Gestion des token user
import jwt

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import bcrypt
from datetime import timedelta
import datetime as dt
import sqlite3

app = FastAPI()

security = HTTPBearer(auto_error=False)


@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/films")
async def getfilms_paginated(page: int = 1, per_page: int = 20, genre_id: int | None = None):
    with get_connection() as conn:
        cursor = conn.cursor()

        if genre_id is None:
            cursor.execute(f"""
                SELECT * FROM film ORDER BY DateSortie DESC LIMIT {per_page} OFFSET {(page - 1) * per_page}
                """)
        else:
            cursor.execute(f"""
                SELECT * FROM film  WHERE Genre_ID = {genre_id} ORDER BY DateSortie DESC LIMIT {per_page} OFFSET {(page - 1) * per_page}
                """)

        films = cursor.fetchall() # C 1 clai primair


        if genre_id is None:
            cursor.execute(f"""
                SELECT COUNT(*) FROM film 
            """)
        else:
            cursor.execute(f"""
                SELECT COUNT(*) FROM film WHERE Genre_ID = {genre_id}
                """)

        nb_films = cursor.fetchone()["COUNT(*)"]

        output = {
            "data": films,
            "page": page,
            "per_page": per_page,
            "total": nb_films
            }
        return output

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

salt = b'$2b$12$HS34zys/Tw6HsKps1esSLe' # goofy aah


def check_user_valid(user: User):
    if user.email is None or user.password is None or user.password is None:
        raise HTTPException(status_code=422, detail=f"Error: Il faut remplir tous les champs")

@app.post("/auth/register")
async def registerUser(user: User):

    check_user_valid(user)

    # On met le sel "+ pseudo"
    # salt = bcrypt.gensalt()
    # Hashing the password
    hash_password = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')

    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                INSERT INTO Utilisateur (AdresseMail, Pseudo, MotDePasse) VALUES('{user.email}', '{user.pseudo}', '{hash_password}') RETURNING *
                """)
            res = dict(cursor.fetchone()) # On recup ce qu'on a mis dedans
        except sqlite3.IntegrityError:
            # Deux emails
            raise HTTPException(status_code=409, detail=f"Erreur interne : Email already exists")


        token = create_access_token(res, timedelta(days=1))
        output_dict = {
        "access_token": token,
        "token_type": "bearer"
        }

        return output_dict


@app.post("/auth/login")
async def loginUser(user: User):
    # On met le sel "+ pseudo"
    # salt = bcrypt.gensalt()

    check_user_valid(user)

    # Hashing the password
    hash_password = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM Utilisateur WHERE AdresseMail = '{user.email}' AND MotDePasse = '{hash_password}'
            """)

        res = cursor.fetchone() # On recup ce qu'on a mis dedans
        if res is None:
            raise HTTPException(status_code=401, detail=f"Erreur interne: Email ou Password faux")
        res = dict(res)
        
        token = create_access_token(res, timedelta(days=1))
        output_dict = {
            "access_token": token,
            "token_type": "bearer"
        }

        #print(output_dict)

        return output_dict

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

class prefEntry(BaseModel):
    genre_id: int = 0

@app.post("/preferences", status_code=201)
async def add_pref(pref_entry: prefEntry, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
        Prend l'access token en argument, et l'entry preferée.
    """

    # First we check if the genre exists
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * from genre
            """)
        res = cursor.fetchall()

        if pref_entry.genre_id not in [x["ID"] for x in res]:
            raise HTTPException(status_code=409, detail="Erreur interne: Le genre n'existe pas !")

    print("token is: ", credentials)
    if credentials is None:
        raise HTTPException(status_code=422, detail="Erreur interne: Spap token")

    try:
        user_data = jwt.decode(credentials.credentials, SECRET_KEY, ALGORITHM)
    except: # moche
        raise HTTPException(status_code=401, detail="Erreur interne: Mauvais token")

    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                INSERT INTO Genre_Utilisateur (ID_Genre, ID_User) VALUES('{pref_entry.genre_id}', '{user_data["ID"]}') RETURNING *
                """)
            res = dict(cursor.fetchone()) # On recup ce qu'on a mis dedans
        except sqlite3.IntegrityError:
            # Déjà favoris pour cet user
            raise HTTPException(status_code=409, detail=f"Erreur interne : Conflit ! Le genre est déjà ajouté !")

    return {"message": "Everything ok"}

@app.delete("/preferences/{genre}")
async def preferences_del(genre: int, credentials: HTTPAuthorizationCredentials = Depends(security)):

    if credentials is None:
        raise HTTPException(status_code=422, detail="Erreur interne: Spap token")

    try:
        user_data = jwt.decode(credentials.credentials, SECRET_KEY, ALGORITHM)
    except: # moche
        raise HTTPException(status_code=401, detail="Erreur interne: Mauvais token")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT COUNT(*) FROM Genre_Utilisateur  WHERE ID_Genre = {genre} AND ID_User = {user_data["ID"]}
        """)

        res = cursor.fetchone()["COUNT(*)"]
        print("count: ", res)

        if res == 0:
            raise HTTPException(status_code=404, detail="Erreur interne: Genre non favori !")

        cursor.execute(f"""
            DELETE FROM Genre_Utilisateur WHERE ID_Genre = {genre} AND ID_User = {user_data["ID"]}
            """)
        

    return {"message": f"Deleted {genre} successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
{
  "email": "barna.baruchel@xibolu.bzh",
  "pseudo": "barnab",
  "password": "j4imel1fo"
}

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6NywiQWRyZXNzZU1haWwiOiJiYXJuYS5iYXJ1Y2hlbEB4aWJvbHUuYnpoIiwiUHNldWRvIjoiYmFybmFiIiwiTW90RGVQYXNzZSI6IiQyYiQxMiRIUzM0enlzL1R3NkhzS3BzMWVzU0xlc0FMSXU1eTVUL0pvRWRhZHBXbFBzdUt1MDVsTnpuQyIsImV4cCI6MTc3Njg1OTYzNn0.0RIDdWE0NJSLV5It-1rCALaXhIFHwt657dGHRDsumSw
"""