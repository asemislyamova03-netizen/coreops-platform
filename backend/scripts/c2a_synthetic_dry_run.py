import json
import uuid

from app.modules.imports_dry_run.pipeline import (
    DryRunNoOpTargetAdapter,
    SyntheticDryRunPipeline,
    SyntheticSourceAdapter,
)
from app.modules.imports_dry_run.schemas import SyntheticDryRunContext
from app.modules.imports_dry_run.synthetic_fixtures import build_consulting_synthetic_fixture


def main() -> None:
    fixture = build_consulting_synthetic_fixture()
    pipeline = SyntheticDryRunPipeline(
        source=SyntheticSourceAdapter(fixture),
        target=DryRunNoOpTargetAdapter(),
    )
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
            default_branch_id=uuid.UUID("00000000-0000-0000-0000-000000000333"),
            created_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000222"),
            scenario_name="c2a_default",
        )
    )
    print(
        json.dumps(
            {
                "summary": result.summary.model_dump(mode="json"),
                "report": result.report.model_dump(mode="json"),
                "target_endpoint_checks": [
                    {
                        "endpoint": item.endpoint,
                        "schema_name": item.schema_name,
                        "status": item.status,
                        "note": item.note,
                    }
                    for item in pipeline.target.endpoint_checks
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
