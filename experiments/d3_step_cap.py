from src import loop


_counter = 0


def endless_backend(messages, parallel=True):
    global _counter
    _counter += 1

    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": f"step-{_counter}",
                    "type": "function",
                    "function": {
                        "name": "get_claim",
                        "arguments": '{"claim_id": "CLM-8842"}',
                    },
                }
            ],
        },
        "usage": {},
    }


loop._backend_next_turn = endless_backend

result = loop.run_case("CLM-8842")

print("Turns executed:", result["turns"])
print("Stopped because:", result["stopped_early"])
