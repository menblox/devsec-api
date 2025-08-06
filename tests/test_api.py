import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db

from app.database import Base


test_database_url = "sqlite:///:memory:"

test_engine = create_engine(
    test_database_url, connect_args={"check_same_thread": False}
)


tesingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    try:
        db = tesingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(name="client")
async def client_fixture():
    Base.metadata.create_all(bind=test_engine)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    Base.metadata.drop_all(bind=test_engine)


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/register/", json={"name": "Jame", "age": 14, "password": "qwerty"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Jame"
    assert data["age"] == 14
    assert "password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient):
    responce = await client.get("/users/")

    assert responce.status_code == 200

    data = responce.json()
    assert data == []

    response_1 = await client.post(
        "/register/",
        json={"name": "Jame", "age": 12, "password": "qwerty"},
    )

    assert response_1.status_code == 200

    data_1 = response_1.json()

    assert data_1["name"] == "Jame"
    assert data_1["age"] == 12
    assert "id" in data_1
    assert "password" not in data_1

    response_2 = await client.post(
        "/register/",
        json={"name": "Anna", "age": 27, "password": "qweasd"},
    )

    assert response_2.status_code == 200

    data_2 = response_2.json()

    assert data_2["name"] == "Anna"
    assert data_2["age"] == 27
    assert "id" in data_2
    assert "password" not in data_2

    responce_get = await client.get("/users/")

    assert responce_get.status_code == 200

    data_get = responce_get.json()

    assert len(data_get) == 2

    names = {"Jame", "Anna"}
    act_names = {user["name"] for user in data_get}

    assert act_names == names


@pytest.mark.asyncio
async def test_get_users_id(client: AsyncClient):
    response = await client.post(
        "/register/", json={"name": "Dog", "age": 56, "password": "qweq"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Dog"
    assert data["age"] == 56
    assert "id" in data
    assert "password" not in data

    id_user = data["id"]

    response_get = await client.get(f"/users/{id_user}")

    assert response_get.status_code == 200

    data_get = response_get.json()

    assert data_get == "Dog"

    response_get_fail = await client.get("/users/9999999")

    assert response_get_fail.status_code == 404

    data_fail = response_get_fail.json()

    assert data_fail["detail"] == "User not found"


# POSTS


@pytest.mark.asyncio
async def test_post_posts(client: AsyncClient):
    responce_user = await client.post(
        "/register/", json={"name": "Dog", "age": 56, "password": "qweq"}
    )

    assert responce_user.status_code == 200

    data_user = responce_user.json()

    assert data_user["name"] == "Dog"
    assert data_user["age"] == 56
    assert "id" in data_user
    assert "password" not in data_user

    id_user = int(data_user["id"])

    responce_post = await client.post(
        "/posts/", json={"title": "test_1", "body": "text_2", "author_id": id_user}
    )

    assert responce_post.status_code == 200

    data_post = responce_post.json()

    assert data_post["title"] == "test_1"
    assert data_post["body"] == "text_2"
    assert data_post["author_id"] == id_user
    assert "id" in data_post
    assert data_post["author"]["name"] == "Dog"

    responce_post_fail = await client.post(
        "/posts/", json={"title": "test_1", "body": "text_2", "author_id": 9999999}
    )

    assert responce_post_fail.status_code == 404

    data_post_fail = responce_post_fail.json()

    assert data_post_fail["detail"] == "User not found"


@pytest.mark.asyncio
async def test_get_posts(client: AsyncClient):
    response_none = await client.get("/posts/")
    assert response_none.status_code == 200
    data_none = response_none.json()
    assert data_none == []

    responce_user = await client.post(
        "/register/", json={"name": "Dog", "age": 56, "password": "qweq"}
    )

    assert responce_user.status_code == 200

    data_user = responce_user.json()

    assert data_user["name"] == "Dog"
    assert data_user["age"] == 56
    assert "id" in data_user
    assert "password" not in data_user

    id_user = int(data_user["id"])

    responce_post = await client.post(
        "/posts/", json={"title": "test_1", "body": "text_2", "author_id": id_user}
    )

    assert responce_post.status_code == 200

    data_post = responce_post.json()

    assert data_post["title"] == "test_1"
    assert data_post["body"] == "text_2"
    assert data_post["author_id"] == id_user
    assert "id" in data_post
    assert data_post["author"]["name"] == "Dog"

    responce_post1 = await client.post(
        "/posts/", json={"title": "test_3", "body": "text_4", "author_id": id_user}
    )
    assert responce_post1.status_code == 200
    data_post1 = responce_post1.json()
    assert data_post1["title"] == "test_3"
    assert data_post1["body"] == "text_4"
    assert data_post1["author_id"] == id_user
    assert "id" in data_post1
    assert data_post1["author"]["name"] == "Dog"

    responce_get = await client.get("/posts/")
    assert responce_get.status_code == 200
    data_get = responce_get.json()
    assert len(data_get) == 2
    titles = {"test_1", "test_3"}
    act_titles = {user["title"] for user in data_get}

    assert titles == act_titles


@pytest.mark.asyncio
async def test_userid_posts(client: AsyncClient):
    response_1 = await client.post(
        "/register/",
        json={"name": "Jame", "age": 12, "password": "qweq"},
    )

    assert response_1.status_code == 200

    data_1 = response_1.json()

    assert data_1["name"] == "Jame"
    assert data_1["age"] == 12
    assert "id" in data_1
    assert "password" not in data_1

    response_2 = await client.post(
        "/register/",
        json={"name": "Anna", "age": 27, "password": "qweqweq"},
    )

    assert response_2.status_code == 200

    data_2 = response_2.json()

    assert data_2["name"] == "Anna"
    assert data_2["age"] == 27
    assert "id" in data_2
    assert "password" not in data_2

    id_user1 = data_1["id"]
    id_user2 = data_2["id"]

    responce_post1 = await client.post(
        "/posts/", json={"title": "test_3", "body": "text_4", "author_id": id_user2}
    )
    assert responce_post1.status_code == 200
    data_post1 = responce_post1.json()
    assert data_post1["title"] == "test_3"
    assert data_post1["body"] == "text_4"
    assert data_post1["author_id"] == id_user2
    assert "id" in data_post1
    assert data_post1["author"]["name"] == "Anna"

    responce_get_id_posts_true = await client.get(f"/user/{id_user2}/post/")
    assert responce_get_id_posts_true.status_code == 200
    data_get_post_true = responce_get_id_posts_true.json()
    assert len(data_get_post_true) == 1
    assert data_get_post_true[0]["title"] == "test_3"

    responce_get_false = await client.get(f"/user/{id_user1}/post/")
    assert responce_get_false.status_code == 404
    data_get_false = responce_get_false.json()
    assert data_get_false["detail"] == "Post not found"

    responce_get_false1 = await client.get("/user/999999999/post/")
    assert responce_get_false1.status_code == 404
    data_get_false1 = responce_get_false1.json()
    assert data_get_false1["detail"] == "Post not found"
