from pydantic import BaseModel

from domain.models.lesson2_models.decide import ResponseDirective

class ResponseInput(BaseModel):
    response_directive: ResponseDirective


class FastResponseInput(BaseModel):
    response_directive: ResponseDirective