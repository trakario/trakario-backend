import json
from base64 import b64decode
from typing import List, Any
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Body
from fastapi.requests import Request
from fastapi.responses import Response
from loguru import logger
from tortoise.contrib.fastapi import register_tortoise

from trakario.config import config
from trakario.models import Applicant, ApplicantDB, ApplicantDBPydantic, \
    applicant_db_to_applicant, Rating, RatingIn, Stage

app = FastAPI(
    title='Automatic job applicant tracking system'
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_auth_cookie(request: Request) -> str:
    token = request.cookies.get('authToken')
    if not token:
        raise HTTPException(status_code=401, detail='Not authorized')
    return token


def authorized(token: str = Depends(get_auth_cookie)):
    if token != config.auth_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


auth_app = APIRouter(dependencies=[Depends(authorized)])


@auth_app.get("/test-auth", response_model=dict)
async def test_auth():
    return {'status': 'success'}


@app.get("/authorize", response_model=dict)
def authorize_route(code: str):
    if code != config.auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    r = Response(content=json.dumps({"status": "success"}))
    r.set_cookie("authToken", code, max_age=60 * 60 * 24 * 30 * 12, httponly=True)
    return r


@auth_app.get("/applicants", response_model=List[Applicant])
async def get_applicants():
    applicants_dbs = await ApplicantDBPydantic.from_queryset(ApplicantDB.all())
    return [applicant_db_to_applicant(i) for i in applicants_dbs]


@auth_app.get("/applicants/{applicant_id}", response_model=Applicant)
async def get_applicant(applicant_id: int):
    applicant_db = await ApplicantDBPydantic.from_queryset_single(
        ApplicantDB.get(id=applicant_id)
    )
    return applicant_db_to_applicant(applicant_db)


@auth_app.post("/applicants/{applicant_id}/ratings", response_model=Rating)
async def post_applicant_rating(applicant_id: int, rating: RatingIn):
    attrs = (await ApplicantDBPydantic.from_queryset_single(
        ApplicantDB.get(id=applicant_id)
    )).attributes
    rating = Rating(**rating.dict(), id=str(uuid4()))
    attrs['ratings'].append(json.loads(rating.json()))
    await ApplicantDB.filter(id=applicant_id).update(attributes=attrs)
    return rating


async def update_attr(applicant_id: int, key: str, value: Any) -> Any:
    attrs = (await ApplicantDBPydantic.from_queryset_single(
        ApplicantDB.get(id=applicant_id)
    )).attributes
    attrs[key] = value
    await ApplicantDB.filter(id=applicant_id).update(attributes=attrs)
    return value


@auth_app.put("/applicants/{applicant_id}/stage", response_model=Stage)
async def put_applicant_stage(applicant_id: int, stage: Stage = Body(...)):
    return await update_attr(applicant_id, 'stage', stage)


@auth_app.put("/applicants/{applicant_id}/name", response_model=str)
async def put_applicant_stage(applicant_id: int, name: str = Body(...)):
    count = await ApplicantDB.filter(id=applicant_id).update(name=name)
    if count != 1:
        raise HTTPException(status_code=404, detail="No such applicant")
    return name


@auth_app.delete("/applicants/{applicant_id}/ratings/{rating_id}")
async def del_applicant_rating(applicant_id: int, rating_id: str):
    applicant_db = await ApplicantDBPydantic.from_queryset_single(
        ApplicantDB.get(id=applicant_id)
    )
    attributes = applicant_db.attributes
    attributes['ratings'] = [i for i in attributes['ratings'] if i['id'] != rating_id]
    await ApplicantDB.filter(id=applicant_id).update(attributes=attributes)


@auth_app.get("/applicants/{applicant_id}/resume/{resume_filename}")
async def get_applicant_rating(applicant_id: int):
    applicant_db = await ApplicantDBPydantic.from_queryset_single(
        ApplicantDB.get(id=applicant_id)
    )
    if not applicant_db.attributes['resume']:
        raise HTTPException(status_code=404, detail='No resume found')
    return Response(
        b64decode(applicant_db.attributes['resume']),
        media_type='application/pdf',
        headers={'Content-disposition': 'inline'}
    )


app.mount('/', auth_app)


@app.on_event('startup')
def on_startup():
    logger.info('Login via: {}/#/?authToken={}', config.frontend_url, config.auth_token)


register_tortoise(
    app,
    db_url=config.db_url,
    modules={"models": ["trakario.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
