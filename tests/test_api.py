import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Важно: импортируем create_engine, sessionmaker из sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Также импортируем declarative_base для SQLAlchemy 2.0, если вы его используете
# (это было в предыдущих шагах для устранения предупреждения)
from sqlalchemy.orm import declarative_base

# Импортирую моё приложение FastAPI и функцию get_db из main.py
# Это нужно, чтобы httpx мог "общаться" с моим приложением
from app.main import app, get_db

# Импортируем Base из database.py
# Base содержит информацию о моих таблицах (User, Post),
# и мы будем использовать ее для создания и удаления таблиц в тестовой БД.
from app.database import Base


# 1. Определяем URL для тестовой базы данных.
# ':memory:' означает, что база данных будет создана только в оперативной памяти
# и исчезнет после завершения тестов. Это идеально для изоляции и скорости.
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

# 2. Создаем движок SQLAlchemy для нашей тестовой базы данных.
# 'connect_args={"check_same_thread": False}' нужен для SQLite,
# чтобы разрешить множественные подключения в одном потоке (что часто бывает в тестах).
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Создаем "фабрику" сессий для тестовой базы данных.
# Это аналог session_local из вашего database.py, но для тестовой БД.
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# 4. Определяем функцию, которая будет заменять вашу оригинальную get_db() в тестах.
# Эта функция будет выдавать сессию из нашей *тестовой* базы данных.
def override_get_db():
    try:
        db = TestingSessionLocal()  # Получаем сессию из тестовой БД
        yield db  # Отдаем сессию тесту
    finally:
        db.close()  # Закрываем сессию после теста


# 5. Говорим FastAPI, что для всех тестов, когда ему понадобится get_db,
# он должен использовать нашу override_get_db вместо оригинальной.
app.dependency_overrides[get_db] = override_get_db


# Декоратор @pytest.fixture сообщает Pytest, что это фикстура.
# name="client" означает, что мы сможем использовать эту фикстуру,
# просто указав 'client' как аргумент в наших тестовых функциях.
@pytest_asyncio.fixture(name="client")
async def client_fixture():  # Имя функции фикстуры может быть любым
    # 1. Подготовительная работа: Создаем все таблицы в тестовой базе данных.
    # Base.metadata.create_all(bind=test_engine) использует информацию из ваших моделей (User, Post)
    # и создает соответствующие таблицы в нашей in-memory тестовой БД.
    Base.metadata.create_all(bind=test_engine)

    # 2. Создаем асинхронный HTTP-клиент.
    # ASGITransport(app=app) позволяет клиенту напрямую взаимодействовать с вашим FastAPI приложением.
    # base_url="http://test" - это просто заглушка, так как мы не запускаем реальный сервер.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 3. 'yield ac' - это ключевой момент!
        # Pytest "отдает" этот 'ac' (наш клиент) всем тестовым функциям,
        # которые запрашивают фикстуру 'client'.
        # Код после 'yield' будет выполнен только после того, как тест завершится.
        yield ac

    # 4. Очистка: Удаляем все таблицы из тестовой базы данных после каждого теста.
    # Это гарантирует, что следующий тест начнется с абсолютно чистой БД.
    Base.metadata.drop_all(bind=test_engine)


@pytest.mark.asyncio
# Мы указываем 'client: AsyncClient' как аргумент.
# Pytest автоматически найдет нашу фикстуру с именем "client" и передаст ее сюда.
async def test_create_user(client: AsyncClient):
    # 1. Отправляем POST-запрос на эндпоинт "/users/".
    # json={"name": "Rog", "age": 19} - это данные, которые мы отправляем в теле запроса.
    response = await client.post("/users/", json={"name": "Rog", "age": 19})

    # 2. Проверяем статус-код ответа.
    # 200 OK означает, что запрос был успешно обработан.
    assert response.status_code == 200

    # 3. Получаем данные из ответа в формате JSON.
    data = response.json()

    # 4. Проверяем, что данные в ответе соответствуют тому, что мы отправляли.
    assert data["name"] == "Rog"
    assert data["age"] == 19
    # 5. Проверяем, что в ответе есть поле "id" (FastAPI/SQLAlchemy должны его добавить).
    assert "id" in data


@pytest.mark.asyncio
async def test_get_users(client: AsyncClient):
    response = await client.get("/users/")

    assert response.status_code == 200

    data = response.json()

    assert data == []

    response_1 = await client.post(
        "/users/",
        json={"name": "Vov", "age": 12},
    )

    assert response_1.status_code == 200

    data_1 = response_1.json()

    assert data_1["name"] == "Vov"
    assert data_1["age"] == 12
    assert "id" in data_1

    response_2 = await client.post(
        "/users/",
        json={"name": "Anna", "age": 27},
    )

    assert response_2.status_code == 200

    data_2 = response_2.json()

    assert data_2["name"] == "Anna"
    assert data_2["age"] == 27
    assert "id" in data_2

    response_end = await client.get("/users/")

    assert response_end.status_code == 200

    data_end = response_end.json()

    assert len(data_end) == 2

    names = {"Vov", "Anna"}  # множество с именами
    act_names = {user["name"] for user in data_end}  # создаст множество с именами из бд

    assert act_names == names


@pytest.mark.asyncio
async def test_get_users_id(client: AsyncClient):
    response = await client.post("/users/", json={"name": "Dog", "age": 56})
    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Dog"
    assert data["age"] == 56
    assert "id" in data

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
    responce_user = await client.post("/users/", json={"name": "Dog", "age": 56})

    assert responce_user.status_code == 200

    data_user = responce_user.json()

    assert data_user["name"] == "Dog"
    assert data_user["age"] == 56
    assert "id" in data_user

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

    responce_user = await client.post("/users/", json={"name": "Dog", "age": 56})

    assert responce_user.status_code == 200

    data_user = responce_user.json()

    assert data_user["name"] == "Dog"
    assert data_user["age"] == 56
    assert "id" in data_user

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
        "/users/",
        json={"name": "Vov", "age": 12},
    )

    assert response_1.status_code == 200

    data_1 = response_1.json()

    assert data_1["name"] == "Vov"
    assert data_1["age"] == 12
    assert "id" in data_1

    response_2 = await client.post(
        "/users/",
        json={"name": "Anna", "age": 27},
    )

    assert response_2.status_code == 200

    data_2 = response_2.json()

    assert data_2["name"] == "Anna"
    assert data_2["age"] == 27
    assert "id" in data_2

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
