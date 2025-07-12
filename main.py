from fastapi import FastAPI, HTTPException, Path, Query, Body, Depends
from typing import Optional, List, Dict, Annotated
from sqlalchemy.orm import Session

from models import Base, User, Post
from database import engine, session_local
from db import UserCreate, User as DbUser, PostCreate, PostResponse

app = FastAPI()

Base.metadata.create_all(bind=engine)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=DbUser)
async def creaate_user(user: UserCreate, db: Session = Depends(get_db)) -> DbUser:
    db_user = User(name=user.name, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.post("/posts/", response_model=PostResponse)
async def creaate_post(post: PostCreate, db: Session = Depends(get_db)) -> PostResponse:
    db_user = db.query(User).filter(User.id == post.author_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found')
    
    db_post= Post(title=post.title, body=post.body, author_id=post.author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    return db_post



@app.get("/posts/", response_model=List[PostResponse])
async def posts(db: Session = Depends(get_db)):
    return db.query(Post).all()

@app.get("/users/", response_model=List[DbUser])
async def users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/users/{id}", response_model=str)
async def users_id(id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail='User not found')

    return db_user.name

@app.get("/user/{id_user}/post/", response_model=List[PostResponse])
async def seak_post_id_user(id_user: int, db: Session = Depends(get_db)):
    db_post = db.query(Post).filter(Post.author_id == id_user).all()
    if db_post == []:
        raise HTTPException(status_code=404, detail='Post not found')
    
    return db_post


