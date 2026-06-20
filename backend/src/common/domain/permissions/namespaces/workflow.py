class WorkflowPermission:
    namespace: str = "workflows"

    view: str = "workflows.view"
    create: str = "workflows.create"
    update: str = "workflows.update"
    delete: str = "workflows.delete"
    view_usage: str = "workflows.view_usage"
    add_integration: str = "workflows.add_integration"
