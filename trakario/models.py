from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel
from pydantic.types import conint, UUID4
from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class ApplicantDB(models.Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=64, unique=True)
    name = fields.CharField(max_length=128)
    attributes = fields.JSONField()

    class Meta:
        table = "applicants"


class Stage(str, Enum):
    unprocessed = 'unprocessed'
    invite_sent = 'invite-sent'
    scheduled = 'scheduled'
    pending_evaluation = 'pending-evaluation'
    considering_rejecting = 'considering-rejecting'
    rejected = 'rejected'
    considering_accepting = 'considering-accepting'
    accepted = 'accepted'


class RatingIn(BaseModel):
    rater: str
    notes: str = ''
    attributes: Dict[str, conint(ge=0, le=5)]


class Rating(RatingIn):
    id: UUID4


class Applicant(BaseModel):
    id: int
    email: str
    name: str
    stage: Stage = Stage.unprocessed

    resumeUrl: Optional[str]
    githubUrl: Optional[str]
    emailText: str
    ratings: List[Rating] = []


ApplicantDBPydantic = pydantic_model_creator(ApplicantDB, name="Applicant")
ApplicantDBInPydantic = pydantic_model_creator(
    ApplicantDB, name="ApplicantIn", exclude_readonly=True
)


def applicant_db_to_applicant(applicant_db: ApplicantDBPydantic) -> Applicant:
    attrs = applicant_db.attributes
    return Applicant(
        id=applicant_db.id,
        name=applicant_db.name,
        email=applicant_db.email,
        githubUrl=attrs['githubUrl'],
        resumeUrl='/applicants/{}/resume/Resume_{}.pdf'.format(
            applicant_db.id, applicant_db.name.replace(' ', '-')
        ),
        emailText=attrs['emailText'],
        ratings=attrs['ratings'],
        stage=attrs['stage']
    )


def applicant_to_applicant_db(applicant: Applicant) -> ApplicantDBPydantic:
    return ApplicantDBPydantic(
        id=applicant.id,
        name=applicant.name,
        email=applicant.email,
        attributes=dict(
            githubUrl=applicant.githubUrl,
            emailText=applicant.emailText,
            ratings=applicant.ratings,
            stage=applicant.stage
        )
    )
