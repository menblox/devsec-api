from pydantic import BaseModel


class UserBase(BaseModel):
    name: str
    age: int


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int

    class Config:
        from_attributes = True


class PostBase(BaseModel):
    title: str
    body: str
    author_id: int


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    id: int
    author: User

    class Config:
        from_attributes = True


class User_log_in(BaseModel):
    name: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class Name_JWT(BaseModel):
    name: str

    class Config:
        from_attributes = True
