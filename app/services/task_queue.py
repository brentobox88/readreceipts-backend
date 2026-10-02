# app/services/task_queue.py
import os
import json
import logging
from typing import Dict, Any, Optional
from redis import Redis
from rq import Queue
from datetime import datetime
from app.models.batch import Batch, BatchStatus
from app.models.receipt import Receipt
from app.database import SessionLocal
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(REDIS_URL)
task_queue = Queue(connection=redis_conn, default_timeout=3600)

class TaskQueueService:
    """Manages background job queuing for receipt processing"""
    
    @staticmethod
    def enqueue_receipt_processing(
        receipt_id: str,
        batch_id: str,
        file_bytes: bytes,
        filename: str
    ) -> str:
        """
        Enqueue a single receipt for async processing
        Returns: Job ID
        """
        job = task_queue.enqueue(
            "app.tasks.process_receipt_task",
            receipt_id=receipt_id,
            batch_id=batch_id,
            file_bytes=file_bytes,
            filename=filename,
            job_id=f"receipt-{receipt_id}",
            result_ttl=3600,
            failure_ttl=86400
        )
        logger.info(f"Enqueued receipt {receipt_id} as job {job.id}")
        return job.id
    
    @staticmethod
    def get_job_status(job_id: str) -> Dict[str, Any]:
        """Get status of a queued job"""
        from rq.job import Job
        job = Job.fetch(job_id, connection=redis_conn)
        
        return {
            "job_id": job.id,
            "status": job.get_status(),
            "result": job.result if job.is_finished else None,
            "exc_info": job.exc_info if job.is_failed else None,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "ended_at": job.ended_at
        }
    
    @staticmethod
    def get_batch_progress(batch_id: str, db: Session) -> Dict[str, Any]:
        """Calculate batch progress from job states"""
        from rq.job import Job
        
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return {"error": "Batch not found"}
        
        receipts = db.query(Receipt).filter(Receipt.batch_id == batch_id).all()
        
        completed = 0
        failed = 0
        processing = 0
        
        for receipt in receipts:
            job_id = f"receipt-{receipt.id}"
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                if job.is_finished:
                    completed += 1
                elif job.is_failed:
                    failed += 1
                else:
                    processing += 1
            except:
                pass
        
        progress = (completed / batch.total_files * 100) if batch.total_files else 0
        
        return {
            "batch_id": batch_id,
            "status": batch.status,
            "total": batch.total_files,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "progress_percent": round(progress, 2),
            "created_at": batch.created_at,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at
        }
    
    @staticmethod
    def clear_batch_jobs(batch_id: str, db: Session):
        """Clear all jobs for a batch (for cleanup/cancellation)"""
        from rq.job import Job
        
        receipts = db.query(Receipt).filter(Receipt.batch_id == batch_id).all()
        for receipt in receipts:
            job_id = f"receipt-{receipt.id}"
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                job.cancel()
            except:
                pass
