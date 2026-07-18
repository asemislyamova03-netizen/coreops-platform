"""Platform catalog seed definitions for Process Overlay."""

PROCESS_TEMPLATE_DEFINITIONS = [
    {
        "code": "flexity_sales_intake",
        "name": "Flexity Sales Intake",
        "description": (
            "Sales intake on flexity_sales: new_lead through proposal/negotiation "
            "to accepted/rejected (full graph)."
        ),
        "default_pipeline_code": "flexity_sales",
        "required_module_codes_json": ["crm", "parties"],
        "default_policy_blueprint_json": {
            "schema_version": 1,
            "process_template_code": "flexity_sales_intake",
            "pipeline_code": "flexity_sales",
            "stage_codes": [
                "new_lead",
                "contacted",
                "diagnosis",
                "proposal_prepared",
                "proposal_sent",
                "negotiation",
                "accepted",
                "rejected",
            ],
            "transitions": [
                {
                    "from_stage_code": "new_lead",
                    "to_stage_code": "contacted",
                    "conditions": {
                        "required_fields": [],
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "new_lead",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "contacted",
                    "to_stage_code": "diagnosis",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "contacted",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "diagnosis",
                    "to_stage_code": "proposal_prepared",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "diagnosis",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "proposal_prepared",
                    "to_stage_code": "proposal_sent",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "proposal_prepared",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "proposal_sent",
                    "to_stage_code": "negotiation",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "proposal_sent",
                    "to_stage_code": "accepted",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "proposal_sent",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "negotiation",
                    "to_stage_code": "accepted",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
                {
                    "from_stage_code": "negotiation",
                    "to_stage_code": "rejected",
                    "conditions": {
                        "required_roles": ["sales"],
                        "requires_approval": False,
                    },
                },
            ],
            "module_requirements": ["crm"],
            "terminal_stage_codes": ["accepted", "rejected"],
        },
        "is_active": True,
    },
]
