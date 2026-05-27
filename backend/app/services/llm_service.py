def analyze_contract(context: str) -> dict:
    _ = context
    return {
        "summary": "Mock analysis summary",
        "risks": [
            {
                "type": "Mock Risk",
                "severity": "medium",
                "description": "This is a placeholder risk.",
            }
        ],
    }
