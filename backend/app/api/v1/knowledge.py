"""
知识库管理 API (管理员专用)
"""
import asyncio
import uuid
import hashlib
import threading
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.document import Document, ensure_document_sqlite_schema
from app.config import settings
from app.schemas.knowledge import DocumentContentResponse, UpdateContentRequest
from loguru import logger


router = APIRouter()
_document_file_lock = threading.RLock()


def _upload_root() -> Path:
    """返回已解析的上传根目录，所有文档物理文件必须位于该目录下。"""
    root = Path(settings.UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ensure_managed_path(file_path: str) -> Path:
    """验证数据库中的路径没有逃逸上传根目录。"""
    root = _upload_root()
    path = Path(file_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("document path is outside the upload directory") from exc
    return path


def _remove_document_file(file_path: str) -> None:
    """安全删除受管理的文件及其空 UUID 目录。"""
    path = _ensure_managed_path(file_path)
    if path.exists():
        path.unlink()
    if path.parent != _upload_root() and path.parent.is_dir() and not any(path.parent.iterdir()):
        path.parent.rmdir()


def _remove_document_file_locked(file_path: str) -> None:
    with _document_file_lock:
        _remove_document_file(file_path)


def _start_processing(document_id: str, revision: int) -> None:
    """提交文档处理任务（默认本进程线程，避免 Celery/Redis 阻塞 API）。"""

    def _run_in_thread() -> None:
        from app.tasks.document_tasks import run_process_in_thread
        try:
            run_process_in_thread(document_id, revision)
        except Exception as exc:
            logger.exception(
                "Background document processing failed for {}: {}",
                document_id,
                exc,
            )

    if not settings.USE_CELERY:
        threading.Thread(
            target=_run_in_thread,
            name=f"doc-process-{document_id[:8]}",
            daemon=True,
        ).start()
        return

    from app.core.redis import redis_client

    if redis_client is None:
        logger.warning(
            "USE_CELERY enabled but Redis unavailable; thread fallback for {}",
            document_id,
        )
        threading.Thread(target=_run_in_thread, daemon=True).start()
        return

    def _enqueue_celery() -> None:
        try:
            from app.tasks.document_tasks import process_document
            process_document.delay(document_id, revision)
            logger.info("Queued Celery task for document {}", document_id)
        except Exception as exc:
            logger.warning("Celery enqueue failed, thread fallback: {}", exc)
            _run_in_thread()

    threading.Thread(target=_enqueue_celery, daemon=True).start()


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
    await ensure_document_sqlite_schema(db)

    conditions = []
    if status_filter:
        conditions.append(Document.status == status_filter)

    # Count
    count_query = select(func.count()).select_from(Document)
    if conditions:
        count_query = count_query.where(*conditions)
    total = (await db.execute(count_query)).scalar() or 0

    # List
    query = select(Document).order_by(Document.created_at.desc())
    if conditions:
        query = query.where(*conditions)
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": doc.chunk_count,
                "status": doc.status,
                "error_message": doc.error_message,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到知识库"""
    await ensure_document_sqlite_schema(db)
    # Validate file type
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_types = ["pdf", "txt", "csv", "md", "docx"]
    if ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型 .{ext}，支持: {', '.join(allowed_types)}",
        )

    # Validate file size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE_MB}MB)",
        )

    # Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate before persisting a final file.
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该文档已存在（内容重复）",
        )

    root = _upload_root()
    temp_path: Path | None = None
    final_path: Path | None = None
    try:
        # Never use the user-controlled filename in the filesystem.  The temporary
        # file is atomically moved only after duplicate validation has passed.
        with tempfile.NamedTemporaryFile(dir=root, prefix=".upload-", delete=False) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

        storage_dir = root / str(uuid.uuid4())
        storage_dir.mkdir(mode=0o700)
        final_path = storage_dir / f"{uuid.uuid4().hex}.{ext}"
        os.replace(temp_path, final_path)
        temp_path = None

        document = Document(
            filename=filename,
            file_path=str(final_path),
            file_type=ext,
            file_size=file_size,
            file_hash=file_hash,
            status="pending",
            uploaded_by=admin_user.id,
        )
        db.add(document)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if final_path is not None:
            _remove_document_file(str(final_path))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该文档已存在（内容重复）")
    except Exception:
        await db.rollback()
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
        if final_path is not None:
            _remove_document_file(str(final_path))
        raise

    doc_id = document.id
    _start_processing(doc_id, document.revision)

    return {
        "id": doc_id,
        "filename": filename,
        "file_type": ext,
        "file_size": file_size,
        "status": "pending",
        "message": "文档已上传，正在排队处理",
    }


@router.get("/documents/{document_id}")
async def get_document_detail(
    document_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "file_hash": document.file_hash,
        "chunk_count": document.chunk_count,
        "status": document.status,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（同时删除向量和文件）"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # The vector store and filesystem each serialize write/delete operations in
    # this process, preventing a task from restoring a just-deleted document.
    try:
        from app.rag.vector_store import delete_documents_from_store
        await asyncio.to_thread(delete_documents_from_store, document.id)
    except Exception as e:
        logger.warning(f"Failed to delete vectors for document {document_id}: {e}")

    try:
        await asyncio.to_thread(_remove_document_file_locked, document.file_path)
    except ValueError:
        logger.error(f"Refusing to delete unmanaged path for document {document_id}")
    except Exception as e:
        logger.warning(f"Failed to delete file for document {document_id}: {e}")

    # Delete from DB
    await db.delete(document)
    await db.commit()

    return {"message": "文档已删除"}


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """重新处理文档"""
    await ensure_document_sqlite_schema(db)
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    document.revision += 1
    document.status = "pending"
    document.error_message = None
    await db.commit()
    _start_processing(document.id, document.revision)

    return {"message": "文档已重新加入处理队列", "status": "pending"}


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档原始文本内容（仅支持 txt/md/csv）"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 仅文本文件支持在线查看
    if document.file_type not in ("txt", "md", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该文件类型（.{document.file_type}）不支持在线查看，仅支持 txt/md/csv 格式。请下载后使用本地编辑器查看。",
        )

    try:
        file_path = _ensure_managed_path(document.file_path)
    except ValueError:
        logger.error(f"Refusing to read unmanaged path for document {document_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件已被删除")

    # 检查文件是否存在
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件已被删除")

    # 读取文件内容（UTF-8 优先，GBK 回退）
    content = ""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with file_path.open("r", encoding="gbk") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read document {document_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件编码不受支持，无法读取内容",
            )
    except Exception as e:
        logger.error(f"Failed to read document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="读取文件内容失败",
        )

    return DocumentContentResponse(
        document_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        content=content,
        size=len(content),
    )


@router.put("/documents/{document_id}/content")
async def update_document_content(
    document_id: str,
    body: UpdateContentRequest,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新文档内容并重新处理"""
    await ensure_document_sqlite_schema(db)
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 仅文本文件支持编辑
    if document.file_type not in ("txt", "md", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持编辑 txt/md/csv 格式的文档",
        )

    content_bytes = body.content.encode("utf-8")
    new_hash = hashlib.sha256(content_bytes).hexdigest()
    duplicate = await db.execute(
        select(Document.id).where(
            Document.file_hash == new_hash, Document.id != document.id
        )
    )
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该文档已存在（内容重复）")

    try:
        file_path = _ensure_managed_path(document.file_path)
    except ValueError:
        logger.error(f"Refusing to write unmanaged path for document {document_id}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文档存储路径无效")

    # Update the database first, then atomically replace the managed file. This
    # avoids partially written content being consumed by the background worker.
    document.file_size = len(content_bytes)
    document.file_hash = new_hash
    document.revision += 1
    document.status = "pending"
    document.error_message = None
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该文档已存在（内容重复）")

    try:
        with _document_file_lock:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=file_path.parent, prefix=".update-", delete=False
            ) as tmp:
                tmp.write(content_bytes)
                temp_path = Path(tmp.name)
            os.replace(temp_path, file_path)

        # 删除旧向量；向量存储内部持有进程内写锁，放到线程避免卡住事件循环。
        from app.rag.vector_store import delete_documents_from_store, reset_vector_store
        await asyncio.to_thread(delete_documents_from_store, document.id)
        reset_vector_store()
    except Exception as e:
        logger.error(f"Failed to update document {document_id}: {e}")
        document.status = "failed"
        document.error_message = f"更新文件或清理旧向量失败: {e}"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新文档失败")

    _start_processing(document.id, document.revision)
    return {"message": "文档内容已更新，正在重新处理", "status": "pending"}


@router.get("/stats")
async def get_knowledge_stats(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库统计信息"""
    # Document counts
    total_result = await db.execute(select(func.count()).select_from(Document))
    total_docs = total_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "completed")
    )
    completed_docs = completed_result.scalar() or 0

    processing_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "processing")
    )
    processing_docs = processing_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.status == "failed")
    )
    failed_docs = failed_result.scalar() or 0

    # Total chunks
    chunks_result = await db.execute(
        select(func.sum(Document.chunk_count)).select_from(Document)
    )
    total_chunks = chunks_result.scalar() or 0

    # Total file size
    size_result = await db.execute(
        select(func.sum(Document.file_size)).select_from(Document)
    )
    total_size = size_result.scalar() or 0

    return {
        "total_documents": total_docs,
        "completed_documents": completed_docs,
        "processing_documents": processing_docs,
        "failed_documents": failed_docs,
        "total_chunks": total_chunks,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
    }
