from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=300)


class LoginResponse(BaseModel):
    token: str


class UserProfileResponse(BaseModel):
    username: str
    role: str
    workspace: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=300)
    role: str = Field(default="user", pattern="^(user|admin)$")


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=20000)
    use_file_tools: bool = False


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[str] = Field(default_factory=list)


class FileWriteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)
    content: str = Field(max_length=200000)


class FileReadRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)


class FileListRequest(BaseModel):
    path: str = Field(default=".", max_length=300)


class FileDeleteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)
