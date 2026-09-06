from src import loop


_call_count = 0


def duplicate_backend(messages, parallel=True):
    global _call_count
    _call_count += 1

    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": f"dup-{_call_count}-a",
                    "type": "function",
                    "function": {
                        "name": "get_claim",
                        "arguments": '{"claim_id": "CLM-8842"}',
                    },
                },
                {
                    "id": f"dup-{_call_count}-b",
                    "type": "function",
                    "function": {
                        "name": "get_claim",
                        "arguments": '{"claim_id": "CLM-8842"}',
                    },
                },
            ],
        },
        "usage": {},
    }


loop._backend_next_turn = duplicate_backend

result = loop.run_case("CLM-8842")

tool_messages = [
    m for m in result["messages"]
    if m.get("role") == "tool"
]

print("Turns executed:", result["turns"])
print("Tool messages:")
for message in tool_messages:
    print(message["content"])
