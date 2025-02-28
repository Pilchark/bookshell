import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db

# 创建测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试用例
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_book():
    # 测试创建图书
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]
    assert data["isbn"] == book_data["isbn"]
    
    # 测试创建重复ISBN的图书
    response = client.post("/books/", json=book_data)
    assert response.status_code == 400

def test_get_books():
    # 创建测试数据
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    client.post("/books/", json=book_data)

    # 测试获取图书列表
    response = client.get("/books/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == book_data["title"]

def test_get_book():
    # 创建测试数据
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    book_id = response.json()["id"]

    # 测试获取单本图书
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == book_data["title"]

    # 测试获取不存在的图书
    response = client.get("/books/999")
    assert response.status_code == 404

def test_update_book():
    # 创建测试数据
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    book_id = response.json()["id"]

    # 测试更新图书
    updated_data = {
        "title": "Updated Book",
        "author": "Updated Author",
        "isbn": "0987654321",
        "published_year": 2024,
        "description": "Updated Description"
    }
    response = client.put(f"/books/{book_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == updated_data["title"]

    # 测试更新不存在的图书
    response = client.put("/books/999", json=updated_data)
    assert response.status_code == 404

def test_delete_book():
    # 创建测试数据
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    book_id = response.json()["id"]

    # 测试删除图书
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200

    # 验证图书已被删除
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404

def test_borrow_return_book():
    # 创建测试数据
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    book_id = response.json()["id"]

    # 测试借书
    response = client.put(f"/books/{book_id}/borrow")
    assert response.status_code == 200

    # 测试重复借书
    response = client.put(f"/books/{book_id}/borrow")
    assert response.status_code == 400

    # 测试还书
    response = client.put(f"/books/{book_id}/return")
    assert response.status_code == 200

    # 测试重复还书
    response = client.put(f"/books/{book_id}/return")
    assert response.status_code == 400

def test_search_books():
    # 创建测试数据
    book_data_1 = {
        "title": "Python Programming",
        "author": "John Doe",
        "isbn": "1234567890",
        "published_year": 2023,
        "description": "Test Description"
    }
    book_data_2 = {
        "title": "Java Programming",
        "author": "Jane Smith",
        "isbn": "0987654321",
        "published_year": 2023,
        "description": "Test Description"
    }
    client.post("/books/", json=book_data_1)
    client.post("/books/", json=book_data_2)

    # 测试按标题搜索
    response = client.get("/books/search/?query=Python")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Programming"

    # 测试按作者搜索
    response = client.get("/books/search/?query=Smith")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["author"] == "Jane Smith"

    # 测试按ISBN搜索
    response = client.get("/books/search/?query=1234567890")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["isbn"] == "1234567890"

def test_edge_cases():
    # 测试创建无效年份的图书
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "1234567890",
        "published_year": -2023,  # 负数年份
        "description": "Test Description"
    }
    response = client.post("/books/", json=book_data)
    assert response.status_code == 200  # 注意：可能需要添加年份验证

    # 测试创建空标题的图书
    book_data["title"] = ""
    response = client.post("/books/", json=book_data)
    assert response.status_code == 200  # 注意：可能需要添加标题验证

    # 测试搜索特殊字符
    response = client.get("/books/search/?query=!@#$%^&*()")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

if __name__ == "__main__":
    # pytest.main(["-v", "test_main.py"])

    # run test_create_book
    pytest.main(["-v", "test_main.py::test_create_book"])

    # run in command line
    # `pytest -v test_main.py::test_create_book`
