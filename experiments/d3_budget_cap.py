from src import config, loop


def expensive_backend(messages, parallel=True):
    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "budget-test-1",
                    "type": "function",
                    "function": {
                        "name": "get_claim",
                        "arguments": '{"claim_id": "CLM-8842"}',
                    },
                }
            ],
        },
        "usage": {
            "prompt_tokens": 2,
            "completion_tokens": 0,
        },
    }


# Replace the real/scripted backend with our controlled test backend.
loop._backend_next_turn = expensive_backend

# For this test only, pretend each input token costs US$1.
# Two prompt tokens therefore cost US$2, which exceeds the US$1 ceiling.
config.price_for = lambda model: (1.0, 0.0)

result = loop.run_case("CLM-8842")

print("Turns executed:", result["turns"])
print("Cost recorded:", result["cost_usd"])
print("Stopped because:", result["stopped_early"])
