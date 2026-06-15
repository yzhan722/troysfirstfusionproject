class ToolsController:
    def status(self, _payload, _palette):
        return (
            "unifiedResult",
            {
                "ok": True,
                "module": "tools",
                "status": "placeholder",
                "message": "Automation tools are reserved for phase 3.",
            },
        )
