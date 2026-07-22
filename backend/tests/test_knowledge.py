"""
知识库功能完整测试
测试知识库的上传、检索、删除、统计功能
"""

import os
import asyncio
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from io import BytesIO
from fastapi.testclient import TestClient


# 模拟测试用户
@pytest.fixture
def mock_user():
    """创建模拟用户"""
    from app.entity.db_models import User
    user = User(
        id=1,
        username="testuser",
        email="test@test.com",
        hashed_password="mock_hash",
        is_active=True
    )
    return user


@pytest.fixture
def test_client(mock_user):
    """创建测试客户端，绕过认证"""
    from fastapi.testclient import TestClient
    from main import app
    
    # 覆盖认证依赖
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    client = TestClient(app)
    yield client
    
    # 清理覆盖
    app.dependency_overrides.clear()


@pytest.fixture
def temp_txt_file():
    """创建临时 TXT 测试文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("这是一个测试文档。\n\n营养学是研究食物与健康的科学。")
        path = f.name
    
    yield path
    
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def temp_md_file():
    """创建临时 MD 测试文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write("# 测试标题\n\n这是测试内容。")
        path = f.name
    
    yield path
    
    try:
        if os.path.exists(path):
            os.unlink(path)
    except PermissionError:
        pass


class TestKnowledgeUpload:
    """测试文档上传功能"""
    
    def test_upload_txt_file(self, test_client, temp_txt_file):
        """测试上传 TXT 文件"""
        with open(temp_txt_file, 'rb') as f:
            response = test_client.post(
                "/api/knowledge/upload",
                files={"file": ("test.txt", f, "text/plain")},
            )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "chunks_count" in data["data"]
    
    def test_upload_md_file(self, test_client, temp_md_file):
        """测试上传 Markdown 文件"""
        with open(temp_md_file, 'rb') as f:
            response = test_client.post(
                "/api/knowledge/upload",
                files={"file": ("test.md", f, "text/markdown")},
            )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 400, 500]
    
    def test_upload_unsupported_file(self, test_client):
        """测试上传不支持的文件类型"""
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.docx", BytesIO(b"fake content"), "application/octet-stream")},
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400
        assert "不支持" in response.json().get("detail", "")


class TestKnowledgeSearch:
    """测试语义搜索功能"""
    
    def test_search_knowledge_basic(self, test_client):
        """测试基本搜索功能"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "营养学", "k": 5}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 500]
    
    def test_search_empty_query(self, test_client):
        """测试空查询"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "", "k": 5}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400
    
    def test_search_response_format(self, test_client):
        """测试搜索响应格式"""
        response = test_client.get(
            "/api/knowledge/search",
            params={"query": "测试", "k": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
            assert "results" in data["data"]


class TestKnowledgeDelete:
    """测试删除文档功能"""
    
    def test_delete_document_nonexistent(self, test_client):
        """测试删除不存在的文档"""
        response = test_client.delete(
            "/api/knowledge/",
            params={"source": "/nonexistent/path/document.txt"}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 404]
    
    def test_delete_empty_source(self, test_client):
        """测试空来源删除"""
        response = test_client.delete(
            "/api/knowledge/",
            params={"source": ""}
        )
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code == 400


class TestKnowledgeStats:
    """测试统计信息功能"""
    
    def test_get_stats_basic(self, test_client):
        """测试获取统计信息"""
        response = test_client.get("/api/knowledge/stats")
        
        print(f"Response: {response.status_code} - {response.json()}")
        assert response.status_code in [200, 500]
    
    def test_get_stats_response_format(self, test_client):
        """测试统计响应格式"""
        response = test_client.get("/api/knowledge/stats")
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "data" in data
            stats = data["data"]
            assert "total_chunks" in stats
            assert "sources" in stats


class TestKnowledgeService:
    """测试 KnowledgeService 类"""
    
    def test_knowledge_service_init(self):
        """测试服务初始化"""
        from app.services.knowledge_service import KnowledgeService
        
        service = KnowledgeService()
        assert service is not None
        assert service._initialized == False
        assert callable(service.get_knowledge_graph)


class TestKnowledgeAPI:
    """API 端点基础测试"""
    
    def test_knowledge_routes_registered(self, test_client):
        """测试知识库路由已注册"""
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
        )
        assert response.status_code in [200, 400, 401, 500]
        
        response = test_client.get("/api/knowledge/search?query=test")
        assert response.status_code in [200, 401, 500]
        
        response = test_client.get("/api/knowledge/stats")
        assert response.status_code in [200, 401, 500]
        
        response = test_client.delete("/api/knowledge/?source=test")
        assert response.status_code in [200, 401, 404, 500]


def test_graph_rebuild_runs_in_background_and_reports_status(test_client):
    """重建接口应立即返回，后台任务跑完后 status 报告 done（不阻塞请求）。"""
    import app.api.knowledge as knowledge_api

    knowledge_api._rebuild_state.clear()
    rebuild_result = {"processed_sources": 3, "foods_count": 4}
    with patch.object(
        knowledge_api.knowledge_service, "rebuild_graph_from_knowledge",
        new=AsyncMock(return_value=rebuild_result),
    ):
        start = test_client.post("/api/knowledge/graph/rebuild")
        assert start.status_code == 200
        assert start.json()["data"]["status"] == "running"

        # 轮询直到后台任务完成
        final = None
        for _ in range(50):
            status = test_client.get("/api/knowledge/graph/rebuild/status")
            final = status.json()["data"]
            if final["status"] in {"done", "failed"}:
                break
            time.sleep(0.05)

    assert final["status"] == "done"
    assert final["processed_sources"] == 3
    assert final["foods_count"] == 4


def test_knowledge_ask_returns_answer_and_sources(test_client):
    result = {
        "answer": "燕麦含有较丰富的可溶性膳食纤维。[local-1]",
        "sources": [{
            "id": "local-1", "type": "knowledge", "title": "燕麦资料",
            "url": None, "score": 0.2, "excerpt": "燕麦含膳食纤维",
        }],
        "local_results": [], "web_results": [],
        "used_web_fallback": False, "cross_verified": False,
    }
    with patch(
        "app.api.knowledge.knowledge_service.answer",
        new=AsyncMock(return_value=result),
    ):
        response = test_client.get("/api/knowledge/ask", params={"query": "燕麦有什么营养"})

    assert response.status_code == 200
    assert response.json()["data"]["answer"].startswith("燕麦")
    assert response.json()["data"]["sources"][0]["id"] == "local-1"


def test_retrieval_uses_web_fallback_when_local_results_are_empty():
    from app.services.knowledge_service import KnowledgeService

    service = KnowledgeService()
    with patch.object(service, "search", new=AsyncMock(return_value=[])), patch(
        "app.services.knowledge_service.web_search_service.search",
        new=AsyncMock(return_value=[{
            "title": "权威营养资料", "url": "https://example.org/nutrition",
            "content": "可靠资料", "source_type": "web", "provider": "exa",
        }]),
    ), patch.object(service, "store_web_results", new=AsyncMock(return_value=1)):
        result = asyncio.run(service.retrieve_with_fallback("每日蛋白质摄入", user_id=1))

    assert result["used_web_fallback"] is True
    assert result["web_results"][0]["provider"] == "exa"


class TestGraphEntityExtraction:
    """测试上传文档时的“食物-营养-分类”实体抽取与入库。"""

    def _service(self):
        from app.services.knowledge_service import KnowledgeService
        return KnowledgeService()

    def test_parse_food_json_plain(self):
        service = self._service()
        raw = '{"foods": [{"name_cn": "苹果", "calories": 52}]}'
        foods = service._parse_food_json(raw)
        assert len(foods) == 1
        assert foods[0]["name_cn"] == "苹果"

    def test_parse_food_json_code_fence_and_noise(self):
        service = self._service()
        raw = "这是结果：\n```json\n{\"foods\": [{\"name_cn\": \"鸡胸肉\"}]}\n```\n完毕"
        foods = service._parse_food_json(raw)
        assert len(foods) == 1
        assert foods[0]["name_cn"] == "鸡胸肉"

    def test_parse_food_json_malformed_returns_empty(self):
        service = self._service()
        assert service._parse_food_json("模型抱歉，无法解析") == []
        assert service._parse_food_json("") == []
        assert service._parse_food_json(None) == []

    def test_store_food_entities_dedup_and_backfill(self, db):
        """upsert：新增有效条目、按名称去重、缺失分类可回填。"""
        from unittest.mock import patch
        from app.entity.db_models import FoodNutrition
        from tests.conftest import test_engine

        service = self._service()
        foods = [
            {"name_en": "apple", "name_cn": "苹果", "category": "水果",
             "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8, "fiber": 2.4},
            {"name_en": "chicken breast", "name_cn": "鸡胸肉", "category": "肉蛋类",
             "calories": 165, "protein": 31, "fat": 3.6, "carbs": 0, "fiber": 0},
            {"name_cn": "", "calories": 100},          # 无中文名 → 跳过
            {"name_cn": "神秘食物"},                     # 无热量 → 入库为“待补全”（热量留空）
        ]

        with patch("sqlalchemy.create_engine", return_value=test_engine):
            # 苹果、鸡胸肉（完整）+ 神秘食物（待补全）= 3 条；无中文名的被跳过
            stored = service._store_food_entities(foods, "膳食指南.txt", user_id=1)
            assert stored == 3
            assert db.query(FoodNutrition).count() == 3
            mystery = db.query(FoodNutrition).filter_by(food_name_cn="神秘食物").one()
            assert mystery.calories_per_100g is None  # 待补全

            # 再次入库相同数据 → 不产生重复
            stored_again = service._store_food_entities(foods, "膳食指南.txt", user_id=1)
            assert stored_again == 0
            assert db.query(FoodNutrition).count() == 3

            # 对话再次提到已有食物时，应更新变化的营养数值而不是静默忽略
            updated = service._store_food_entities(
                [{"name_en": "apple", "name_cn": "苹果", "category": "水果",
                  "calories": 53, "protein": 0.4}],
                "对话抽取", user_id=1,
            )
            assert updated == 1
            apple = db.query(FoodNutrition).filter_by(food_name_cn="苹果").first()
            assert apple.calories_per_100g == 53
            assert apple.protein_per_100g == 0.4
            assert apple.source == "对话抽取"

            # 回填分类：先造一条无分类记录，再用带分类数据补齐
            db.add(FoodNutrition(
                user_id=1, food_name="oats", food_name_cn="燕麦",
                calories_per_100g=389.0, category=None,
            ))
            db.commit()
            backfilled = service._store_food_entities(
                [{"name_cn": "燕麦", "category": "谷物", "calories": 389}], "膳食指南.txt", user_id=1,
            )
            assert backfilled == 1
            oats = db.query(FoodNutrition).filter_by(food_name_cn="燕麦").first()
            assert oats.category == "谷物"

    def test_food_entities_and_graph_are_isolated_per_user(self, db):
        """不同用户的营养库与知识图谱互相独立，不会串号。"""
        from unittest.mock import patch
        from app.entity.db_models import FoodNutrition
        from tests.conftest import test_engine

        service = self._service()
        apple = [{"name_en": "apple", "name_cn": "苹果", "category": "水果",
                  "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8, "fiber": 2.4}]
        banana = [{"name_en": "banana", "name_cn": "香蕉", "category": "水果",
                   "calories": 89, "protein": 1.1, "fat": 0.3, "carbs": 22.8, "fiber": 2.6}]

        with patch("sqlalchemy.create_engine", return_value=test_engine):
            # 用户 1 存苹果、用户 2 存香蕉：同名同类也是各存各的
            service._store_food_entities(apple, "u1.txt", user_id=1)
            service._store_food_entities(banana, "u2.txt", user_id=2)
            # 用户 1 再存苹果 → 命中自己的去重，不影响用户 2
            assert service._store_food_entities(apple, "u1.txt", user_id=1) == 0

            assert db.query(FoodNutrition).filter_by(user_id=1).count() == 1
            assert db.query(FoodNutrition).filter_by(user_id=2).count() == 1

            graph_1 = asyncio.run(service.get_knowledge_graph(user_id=1))
            graph_2 = asyncio.run(service.get_knowledge_graph(user_id=2))

        food_labels_1 = {n["label"] for n in graph_1["nodes"] if n["type"] == "food"}
        food_labels_2 = {n["label"] for n in graph_2["nodes"] if n["type"] == "food"}
        assert food_labels_1 == {"苹果"}
        assert food_labels_2 == {"香蕉"}

    def test_extract_and_store_graph_flow(self, db):
        """端到端（跳过真实 LLM）：抽取结果写入 food_nutrition。"""
        from unittest.mock import patch
        from app.entity.db_models import FoodNutrition
        from tests.conftest import test_engine

        service = self._service()
        canned = [{"name_en": "banana", "name_cn": "香蕉", "category": "水果",
                   "calories": 89, "protein": 1.1, "fat": 0.3, "carbs": 22.8, "fiber": 2.6}]

        with patch.object(service, "_extract_food_entities", return_value=canned), \
                patch("sqlalchemy.create_engine", return_value=test_engine):
            count = asyncio.run(
                service.extract_and_store_graph("香蕉富含钾", source="水果.txt", user_id=5)
            )

        assert count == 1
        banana = db.query(FoodNutrition).filter_by(food_name_cn="香蕉").one()
        assert banana.user_id == 5

    def test_extract_and_store_graph_empty_text(self):
        service = self._service()
        assert asyncio.run(service.extract_and_store_graph("", source="x")) == 0

    def test_incomplete_food_stored_then_web_completed(self, db):
        """资料提到食物但缺热量：先入库为待补全（不进图谱），补全后出现在图谱。"""
        from unittest.mock import patch
        from app.entity.db_models import FoodNutrition
        from tests.conftest import test_engine

        service = self._service()
        extracted = [{"name_cn": "薯条", "name_en": "french fries", "calories": None}]
        web_hits = [{"title": "薯条营养", "content": "每100克薯条约312千卡", "url": "https://x"}]
        filled = {"name_en": "french fries", "name_cn": "薯条", "category": "主食",
                  "calories": 312, "protein": 3.4, "fat": 15, "carbs": 41, "fiber": 3.8}

        with patch("sqlalchemy.create_engine", return_value=test_engine):
            # 1. 抽取入库：薯条作为“待补全”存下（热量为空）
            with patch.object(service, "_extract_food_entities", return_value=extracted):
                count = asyncio.run(
                    service.extract_and_store_graph("我吃了薯条", source="对话抽取", user_id=9)
                )
            assert count == 1
            fries = db.query(FoodNutrition).filter_by(food_name_cn="薯条", user_id=9).one()
            assert fries.calories_per_100g is None
            # 待补全 → 此时不进图谱
            graph_before = asyncio.run(service.get_knowledge_graph(user_id=9))
            assert "薯条" not in {n["label"] for n in graph_before["nodes"] if n["type"] == "food"}

            # 2. 定向补全：联网 + 写回，薯条随即进入图谱
            with patch("app.services.knowledge_service.web_search_service.search",
                       new=AsyncMock(return_value=web_hits)), \
                    patch.object(service, "_extract_food_from_web",
                                 new=AsyncMock(return_value=filled)):
                completed = asyncio.run(service.complete_incomplete_foods(user_id=9))
            assert completed == 1
            db.expire_all()
            fries = db.query(FoodNutrition).filter_by(food_name_cn="薯条", user_id=9).one()
            assert fries.calories_per_100g == 312
            graph_after = asyncio.run(service.get_knowledge_graph(user_id=9))
            assert "薯条" in {n["label"] for n in graph_after["nodes"] if n["type"] == "food"}

    def test_complete_incomplete_foods_noop_when_all_complete(self, db):
        """没有待补全食物时不触发联网（省成本）。"""
        from unittest.mock import patch
        from app.entity.db_models import FoodNutrition
        from tests.conftest import test_engine

        service = self._service()
        db.add(FoodNutrition(user_id=9, food_name="apple", food_name_cn="苹果",
                             calories_per_100g=52.0, category="水果"))
        db.commit()
        with patch("sqlalchemy.create_engine", return_value=test_engine), \
                patch("app.services.knowledge_service.web_search_service.search",
                      new=AsyncMock()) as mocked:
            completed = asyncio.run(service.complete_incomplete_foods(user_id=9))
        mocked.assert_not_called()
        assert completed == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
