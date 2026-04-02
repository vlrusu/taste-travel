from enum import Enum


class SeedRestaurantSentiment(str, Enum):
    LOVE = "love"
    DISLIKE = "dislike"


class FeedbackType(str, Enum):
    PERFECT = "perfect"
    SAVED = "saved"
    DISMISSED = "dismissed"
    TOO_EXPENSIVE = "too_expensive"
    TOO_TOURISTY = "too_touristy"
    TOO_FORMAL = "too_formal"
    TOO_CASUAL = "too_casual"
    TOO_LOUD = "too_loud"
    NOT_MY_VIBE = "not_my_vibe"
