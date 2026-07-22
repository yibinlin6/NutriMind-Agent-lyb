import os
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.entity.schemas import ApiResponse
from app.services.knowledge_service import knowledge_service

from app.core.security import get_current_user
from app.entity.db_models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

# 持有后台补全任务引用，避免被 GC 提前回收
_completion_tasks: set = set()


def _schedule_food_completion(user_id: int) -> None:
    """后台定向补全该用户「待补全」（缺热量）食物，不阻塞上传响应。"""
    import asyncio

    async def _run():
        try:
            await knowledge_service.complete_incomplete_foods(user_id)
        except Exception as exc:  # 后台任务不得影响上传主流程
            logger.warning("后台补全待补全食物失败: %s", exc)

    task = asyncio.create_task(_run())
    _completion_tasks.add(task)
    task.add_done_callback(_completion_tasks.discard)

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".text", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

@router.post("/upload", response_model=ApiResponse)
async def upload_document(
    file: UploadFile = File(..., description="文档文件 (PDF/MD/TXT) 或图片 (PNG/JPG)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上传文档"""
    # 1. 检查文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{file_ext}，支持：{', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 3. 上传到知识库（向量入库 + 抽取食物实体入图谱）
        result = await knowledge_service.embed_and_store(tmp_path, current_user.id)
        chunks_count = result.get("chunks_count", 0)
        foods_count = result.get("foods_count", 0)
        if chunks_count == 0:
            raise HTTPException(status_code=400, detail="文档处理失败，未生成有效内容")

        # 4. 后台补全本次入库的“待补全”（缺热量）食物：上传接口不等待，保持响应快。
        _schedule_food_completion(current_user.id)

        # 5. 返回结果
        return ApiResponse(
            code=200,
            message="文档上传成功",
            data={
                "filename": file.filename,
                "chunks_count": chunks_count,
                "foods_count": foods_count
            }
        )
    finally:
        # 5. 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

@router.get("/search", response_model=ApiResponse)
async def search_knowledge(
    query: str = ...,
    k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检索知识库"""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    try:
        results = await knowledge_service.search(query, k=k, user_id=current_user.id)
        return ApiResponse(
            code=200,
            data={
                "query": query,
                "results": results,
                "total": len(results)
            }
        )
    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/ask", response_model=ApiResponse)
async def ask_knowledge(
    query: str = ...,
    k: int = 5,
    verify_web: bool = False,
    store_web: bool = True,
    current_user: User = Depends(get_current_user),
):
    """营养知识问答：返回自然语言回答、关联知识库片段和网页来源。"""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    if k < 1 or k > 10:
        raise HTTPException(status_code=400, detail="k 必须在 1 到 10 之间")
    try:
        result = await knowledge_service.answer(
            query=query.strip(), k=k, user_id=current_user.id,
            verify_web=verify_web, store_web=store_web,
        )
        return ApiResponse(code=200, data={"query": query.strip(), **result})
    except Exception as e:
        logger.exception("知识库问答失败")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}") from e

@router.delete("/", response_model=ApiResponse)
async def delete_document(
    source: str = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定来源的文档"""
    if not source or not source.strip():
        raise HTTPException(status_code=400, detail="文档来源不能为空")

    try:
        success = await knowledge_service.delete_by_source(source, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="未找到指定文档")
        return ApiResponse(code=200, message="文档删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/stats", response_model=ApiResponse)
async def get_knowledge_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取知识库统计信息"""
    try:
        stats = await knowledge_service.get_collection_stats(current_user.id)
        return ApiResponse(code=200, data=stats)
    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")
@router.get("/graph", response_model=ApiResponse)
async def get_knowledge_graph(
    current_user: User = Depends(get_current_user),
):
    """获取营养知识图谱（nodes + edges）。
    基于 food_nutrition 表构建食物-分类-营养关系图，供前端可视化渲染。
    """
    try:
        graph = await knowledge_service.get_knowledge_graph(current_user.id)
        return ApiResponse(code=200, data=graph)
    except Exception as e:
        logger.error(f"获取知识图谱失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图谱失败: {str(e)}")


# 每个用户的重建进度（内存态）。重建耗时可能达分钟级，改为后台任务 + 轮询，
# 避免同步请求被前端/网关超时中断。
_rebuild_state: dict[int, dict] = {}
_rebuild_tasks: set = set()


async def _run_rebuild(user_id: int) -> None:
    try:
        result = await knowledge_service.rebuild_graph_from_knowledge(user_id)
        _rebuild_state[user_id] = {
            "status": "done",
            "processed_sources": result.get("processed_sources", 0),
            "foods_count": result.get("foods_count", 0),
            "error": None,
        }
    except Exception as exc:
        logger.exception("重建知识图谱失败")
        _rebuild_state[user_id] = {
            "status": "failed", "processed_sources": 0, "foods_count": 0,
            "error": str(exc),
        }


@router.post("/graph/rebuild", response_model=ApiResponse)
async def rebuild_knowledge_graph(
    current_user: User = Depends(get_current_user),
):
    """启动后台重建：立即返回，用 /graph/rebuild/status 轮询结果。

    重建会对用户已上传的每份资料重跑抽取，耗时可能达分钟级，不能在单个
    HTTP 请求里同步完成，否则会被前端超时误报“重建失败”。
    """
    import asyncio

    current = _rebuild_state.get(current_user.id)
    if current and current.get("status") == "running":
        return ApiResponse(code=200, message="重建已在进行中", data=current)

    _rebuild_state[current_user.id] = {
        "status": "running", "processed_sources": 0, "foods_count": 0, "error": None,
    }
    task = asyncio.create_task(_run_rebuild(current_user.id))
    _rebuild_tasks.add(task)
    task.add_done_callback(_rebuild_tasks.discard)
    return ApiResponse(code=200, message="重建已开始", data=_rebuild_state[current_user.id])


@router.get("/graph/rebuild/status", response_model=ApiResponse)
async def rebuild_knowledge_graph_status(
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的图谱重建进度。"""
    state = _rebuild_state.get(current_user.id) or {
        "status": "idle", "processed_sources": 0, "foods_count": 0, "error": None,
    }
    return ApiResponse(code=200, data=state)
