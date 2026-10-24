from pydantic import BaseModel, Field

class ClusterRequest(BaseModel):
    keywords: list[str]

class ClusterItem(BaseModel):
    cluster_name: str = "خوشه موضوعی"
    pillar_keyword: str = ""
    suggested_h1: str | None = None
    target_audience: str | None = None
    h2_keywords: list[str] = Field(default_factory=list)
    search_intent: str = "Informational"
    cannibalization_warning: str | None = None

class ClusterResponse(BaseModel):
    clusters: list[ClusterItem]
