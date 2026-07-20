"""
知识库管理 API (管理员专用)
"""
import os
import uuid
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_admin_user
from app.models.user import User
from app.models.document import Document
from app.config import settings

router = APIRouter()


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库文档列表"""
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

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(uuid.uuid4()))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = await db.execute(
        select(Document).where(Document.file_hash == file_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该文档已存在（内容重复）",
        )

    # Create document record
    document = Document(
        filename=filename,
        file_path=file_path,
        file_type=ext,
        file_size=file_size,
        file_hash=file_hash,
        status="pending",
        uploaded_by=admin_user.id,
    )
    db.add(document)
    await db.flush()
    doc_id = document.id

    # Commit first so the thread can find the document
    await db.commit()

    # Process document in background thread (non-blocking)
    import threading
    from app.tasks.document_tasks import run_process_in_thread
    thread = threading.Thread(
        target=run_process_in_thread,
        args=(doc_id,),
        daemon=True,
    )
    thread.start()

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

    # Delete from Chroma vector store
    try:
        from app.rag.vector_store import delete_documents_from_store
        delete_documents_from_store(document.id)
    except Exception:
        pass

    # Delete physical file
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        # Remove parent directory if empty
        parent_dir = os.path.dirname(document.file_path)
        if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
            os.rmdir(parent_dir)
    except Exception:
        pass

    # Delete from DB
    await db.delete(document)
    await db.flush()

    return {"message": "文档已删除"}


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """重新处理文档"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    document.status = "pending"
    document.error_message = None
    await db.flush()

    try:
        from app.tasks.document_tasks import process_document
        process_document.delay(document.id)
    except Exception:
        pass

    return {"message": "文档已重新加入处理队列", "status": "pending"}


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
