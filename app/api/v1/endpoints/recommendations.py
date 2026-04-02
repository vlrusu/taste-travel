from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.recommendation import FeedbackRepository, RecommendationRepository
from app.repositories.taste_profile import TasteProfileRepository
from app.schemas.recommendation import (
    FeedbackResponse,
    RecommendationFeedbackRequest,
    RecommendationGenerateRequest,
    RecommendationGenerateResponse,
    RecommendationResponse,
)
from app.services.recommendation import RecommendationService


router = APIRouter()


@router.post("/recommendations:generate", response_model=RecommendationGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_recommendation(
    payload: RecommendationGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationGenerateResponse:
    service = RecommendationService(
        recommendation_repository=RecommendationRepository(db),
        taste_profile_repository=TasteProfileRepository(db),
    )
    recommendation = service.generate_for_user(
        user=current_user,
        destination_city=payload.destination_city,
        destination_country=payload.destination_country,
    )
    db.commit()
    db.refresh(recommendation)
    return RecommendationGenerateResponse(recommendation=recommendation)


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    repository = RecommendationRepository(db)
    recommendation = repository.get_for_user(
        user_id=current_user.id,
        recommendation_id=recommendation_id,
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return recommendation


@router.post("/recommendations/{recommendation_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    recommendation_id: UUID,
    payload: RecommendationFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    repository = RecommendationRepository(db)
    recommendation = repository.get_for_user(
        user_id=current_user.id,
        recommendation_id=recommendation_id,
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    service = RecommendationService(
        recommendation_repository=repository,
        taste_profile_repository=TasteProfileRepository(db),
        feedback_repository=FeedbackRepository(db),
    )
    feedback = service.submit_feedback(
        recommendation,
        user=current_user,
        feedback_type=payload.feedback_type,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(feedback)
    return feedback
