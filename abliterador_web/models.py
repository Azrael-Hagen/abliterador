from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=300)


class LoginResponse(BaseModel):
    token: str


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=300)


class SignupResponse(BaseModel):
    username: str
    role: str


class UserProfileResponse(BaseModel):
    username: str
    role: str
    active: bool = True
    permissions: list[str] = Field(default_factory=list)
    workspace: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=300)
    role: str = Field(default="viewer", pattern="^(admin|manager|operator|viewer)$")


class UserRoleUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    role: str = Field(pattern="^(admin|manager|operator|viewer)$")


class UserActiveUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    active: bool


class UserDeleteRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)


class ModelPullRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)


class ModelPullJobResponse(BaseModel):
    job_id: str
    model: str
    status: str
    output_tail: str = ""


class DiagnosticsRepairRequest(BaseModel):
    actions: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=20000)
    use_file_tools: bool = False
    use_web_search: bool = False
    web_query: str = Field(default="", max_length=300)
    web_results_limit: int = Field(default=3, ge=1, le=10)
    use_recent_web_knowledge: bool = True


class ChatResponse(BaseModel):
    reply: str
    tool_events: list[str] = Field(default_factory=list)


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchResponse(BaseModel):
    query: str
    results: list[dict[str, str]] = Field(default_factory=list)


class FileWriteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)
    content: str = Field(max_length=200000)


class FileReadRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)


class FileListRequest(BaseModel):
    path: str = Field(default=".", max_length=300)


class FileDeleteRequest(BaseModel):
    path: str = Field(min_length=1, max_length=300)
