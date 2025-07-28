from fastapi import FastAPI, HTTPException, Depends
from typing import List, Iterator
from sqlalchemy.orm import Session
from datetime import timedelta
import fastapi.security

from app.models import User, Post
from app.database import engine, session_local, Base
from app.db import UserCreate, User as DbUser, PostCreate, PostResponse, Token
from app.auth import get_password_hash, verify_password, create_access_token
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES


app = FastAPI()


Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=DbUser)
async def create_user(user: UserCreate, db: Session = Depends(get_db)) -> User:
    db_user = User(name=user.name, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/posts/", response_model=PostResponse)
async def create_post(post: PostCreate, db: Session = Depends(get_db)) -> Post:
    db_user = db.query(User).filter(User.id == post.author_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_post = Post(title=post.title, body=post.body, author_id=post.author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    return db_post


@app.post("/register/", response_model=DbUser)
async def register_users(user: UserCreate, db: Session = Depends(get_db)) -> User:
    db_user = db.query(User).filter(User.name == user.name).first()
    if db_user is not None:
        raise HTTPException(status_code=409, detail="Name Taken!")
    user_password = user.password
    hash_user_password = get_password_hash(user_password)

    db_user_hash = User(name=user.name, age=user.age, hash_password=hash_user_password)

    db.add(db_user_hash)
    db.commit()
    db.refresh(db_user_hash)

    return db_user_hash


@app.post("/token/", response_model=Token)
async def login_token(
    OA: fastapi.security.OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    db_user = db.query(User).filter(User.name == OA.username).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if verify_password(
        plain_password=OA.password, hashed_password=db_user.hash_password
    ):
        user = {"sub": db_user.name}
        token = create_access_token(
            data=user, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return Token(access_token=token, token_type="bearer")

    else:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/posts/", response_model=List[PostResponse])
async def posts(db: Session = Depends(get_db)) -> List[Post]:
    return db.query(Post).all()


@app.get("/users/", response_model=List[DbUser])
async def users(db: Session = Depends(get_db)) -> List[User]:
    return db.query(User).all()


@app.get("/users/{id}", response_model=str)
async def users_id(id: int, db: Session = Depends(get_db)) -> str:
    db_user = db.query(User).filter(User.id == id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return db_user.name


@app.get("/user/{id_user}/post/", response_model=List[PostResponse])
async def seak_post_id_user(id_user: int, db: Session = Depends(get_db)) -> List[Post]:
    db_post = db.query(Post).filter(Post.author_id == id_user).all()
    if db_post == []:
        raise HTTPException(status_code=404, detail="Post not found")

    return db_post
