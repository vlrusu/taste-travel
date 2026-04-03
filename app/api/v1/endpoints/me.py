from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.integrations.google_places import GooglePlacesClient
from app.models.user import User
from app.repositories.taste_profile import TasteProfileRepository
from app.repositories.taste_seed import TasteSeedRepository
from app.repositories.user import UserRepository
from app.schemas.taste_profile import TasteProfileGenerateResponse, TasteProfileResponse
from app.schemas.taste_seed import (
    SeedRestaurantCreateRequest,
    SeedRestaurantResponse,
    SeedRestaurantSearchResponse,
)
from app.services.seed_restaurant import (
    DuplicateSeedRestaurantError,
    InvalidVerifiedSeedError,
    SeedRestaurantService,
)
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


@router.get("/me/seeds/search", response_model=list[SeedRestaurantSearchResponse])
def search_seed_places(
    name: str,
    city: str,
    current_user: User = Depends(get_current_user),
) -> list[SeedRestaurantSearchResponse]:
    del current_user
    client = GooglePlacesClient()
    try:
        return client.search_seed_places(name=name, city=city)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to search places") from error


@router.post("/me/seeds", response_model=SeedRestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_seed(
    payload: SeedRestaurantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = TasteSeedRepository(db)
    service = SeedRestaurantService(repository)
    try:
        seed = service.create_seed(
            user_id=current_user.id,
            name=payload.name,
            city=payload.city,
            sentiment=payload.sentiment,
            notes=payload.notes,
            source=payload.source,
            source_place_id=payload.source_place_id,
            formatted_address=payload.formatted_address,
            lat=payload.lat,
            lon=payload.lon,
            price_level=payload.price_level,
            rating=payload.rating,
            user_ratings_total=payload.user_ratings_total,
            raw_types=payload.raw_types,
            review_summary_text=payload.review_summary_text,
            editorial_summary_text=payload.editorial_summary_text,
            menu_summary_text=payload.menu_summary_text,
            raw_seed_note_text=payload.raw_seed_note_text,
            raw_place_metadata_json=payload.raw_place_metadata_json,
            raw_review_text=payload.raw_review_text,
            derived_traits_json=payload.derived_traits_json,
            ai_summary_text=payload.ai_summary_text,
            place_traits_json=payload.place_traits_json,
            is_verified_place=payload.is_verified_place,
        )
        db.commit()
        db.refresh(seed)
        return seed
    except DuplicateSeedRestaurantError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidVerifiedSeedError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A seed restaurant with that name and city already exists",
        ) from error


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
