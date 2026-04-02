from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.taste_profile import TasteProfileRepository
from app.repositories.taste_seed import TasteSeedRepository
from app.repositories.user import UserRepository
from app.schemas.taste_profile import TasteProfileGenerateResponse, TasteProfileResponse
from app.schemas.taste_seed import SeedRestaurantCreateRequest, SeedRestaurantResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.taste_profile import TasteProfileService
from app.services.user import UserService


router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    service = UserService(UserRepository(db))
    user = service.update_user(current_user, **payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/seeds", response_model=list[SeedRestaurantResponse])
def list_seeds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    repository = TasteSeedRepository(db)
    return repository.list_for_user(current_user.id)


@router.post("/me/seeds", response_model=SeedRestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_seed(
    payload: SeedRestaurantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = TasteSeedRepository(db)
    seed = repository.create(
        user_id=current_user.id,
        name=payload.name,
        city=payload.city,
        sentiment=payload.sentiment,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(seed)
    return seed


@router.delete("/me/seeds/{seed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_seed(
    seed_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    repository = TasteSeedRepository(db)
    seed = repository.get_for_user(user_id=current_user.id, seed_id=seed_id)
    if seed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seed not found")
    repository.delete(seed)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/taste-profile:generate", response_model=TasteProfileGenerateResponse)
def generate_taste_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TasteProfileGenerateResponse:
    service = TasteProfileService(
        taste_seed_repository=TasteSeedRepository(db),
        taste_profile_repository=TasteProfileRepository(db),
    )
    profile = service.generate_for_user(current_user)
    db.commit()
    db.refresh(profile)
    return TasteProfileGenerateResponse(taste_profile=profile)


@router.get("/me/taste-profile", response_model=TasteProfileResponse)
def get_taste_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TasteProfileResponse:
    repository = TasteProfileRepository(db)
    profile = repository.get_for_user(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taste profile has not been generated",
        )
    return profile
