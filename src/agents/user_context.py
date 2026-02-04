from pydantic import BaseModel

class UserContext(BaseModel):
    chat_id: int
    first_name: str
    is_bot: bool
    