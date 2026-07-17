from sqlalchemy.orm import Session

from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import ProcessTemplateResponse
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS


class ProcessOverlayCatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessOverlayRepository(db)

    def seed_templates(self) -> list[ProcessTemplateResponse]:
        created: list[ProcessTemplateResponse] = []
        for item in PROCESS_TEMPLATE_DEFINITIONS:
            template = self.repo.upsert_template(**item)
            created.append(ProcessTemplateResponse.model_validate(template))
        self.db.flush()
        return created

    def get_template_by_code(self, code: str) -> ProcessTemplateResponse | None:
        template = self.repo.get_template_by_code(code)
        if template is None:
            return None
        return ProcessTemplateResponse.model_validate(template)
