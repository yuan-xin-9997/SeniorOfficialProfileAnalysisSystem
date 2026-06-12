from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.models import AnalysisTask, User
from app.db.session import get_db
from app.modules.analysis.schemas import AnalysisTaskCreate, AnalysisTaskRead
from app.modules.auth.dependencies import get_current_user

router = APIRouter()


@router.get("/tasks", response_model=list[AnalysisTaskRead])
def list_analysis_tasks(
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnalysisTask]:
    query = db.query(AnalysisTask)
    if current_user.role != "ADMIN":
        query = query.filter(AnalysisTask.created_by == current_user.id)
    return query.order_by(AnalysisTask.created_at.desc()).limit(limit).all()


@router.post("/tasks", response_model=AnalysisTaskRead, status_code=status.HTTP_201_CREATED)
def create_analysis_task(
    payload: AnalysisTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisTask:
    task = AnalysisTask(
        name=payload.name,
        task_type=payload.task_type,
        parameters=payload.parameters,
        weight_profile_id=payload.weight_profile_id,
        created_by=current_user.id,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=AnalysisTaskRead)
def get_analysis_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisTask:
    task = db.get(AnalysisTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.role != "ADMIN" and task.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return task

