import sys
sys.path.insert(0, '/opt/hermes')
from agent.model_metadata import parse_available_output_tokens_from_error

err = (
    "This model's maximum context length is 32768 tokens. "
    "However, you requested 8192 output tokens and your prompt "
    "contains at least 24577 input tokens, for a total of at least "
    "32769 tokens. Please reduce the length of either one."
)
print('parsed:', parse_available_output_tokens_from_error(err))

# Mimic raw_msg embedding form in actual hermes call site
wrapped = f"HTTP 400: Provider returned error: {err}"
print('parsed wrapped:', parse_available_output_tokens_from_error(wrapped))

# Mimic OpenAI BadRequestError __str__ form — embeds metadata dict
# with json-escaped backslash-apostrophes
realistic = (
    "HTTP 400: Provider returned error: {'message': 'Provider returned error', "
    "'code': 400, 'metadata': {'raw': '{\"error\":{\"message\":\"This model\\'s "
    "maximum context length is 32768 tokens. However, you requested 8192 output "
    "tokens and your prompt contains at least 24577 input tokens, for a total of "
    "at least 32769 tokens. Please reduce the length of either one.\",\"code\":400,"
    "\"metadata\":{\"provider_name\":\"MiniMax\"}}}'}}"
)
print('parsed realistic:', parse_available_output_tokens_from_error(realistic))

# Also test parse_context_limit_from_error to confirm it works (matches hermes log)
from agent.model_metadata import parse_context_limit_from_error
print('parse_context_limit:', parse_context_limit_from_error(realistic))

# Approximate what openai library produces — BadRequestError.__str__
# typically returns "Error code: 400 - {body_dict}".
import openai
# Construct a fake error like the openai SDK does for "Provider returned error"
class FakeResponse:
    request = None
    headers = {}
    status_code = 400
err_body = {
    "error": {
        "message": "Provider returned error",
        "code": 400,
        "metadata": {
            "raw": '{"error":{"message":"This model\'s maximum context length is 32768 tokens. However, you requested 8192 output tokens and your prompt contains at least 24577 input tokens, for a total of at least 32769 tokens. Please reduce the length of either one.","code":400}}',
            "provider_name": "MiniMax"
        }
    }
}
print('--- str(BadRequestError) ---')
# What if the message passed in is the RAW body from openrouter?
real_msg = "Error code: 400 - " + str(err_body)
try:
    e = openai.BadRequestError(message=real_msg, response=FakeResponse(), body=err_body)
    msg = str(e).lower()
    print('len:', len(msg))
    print('first 500:', msg[:500])
    print('has "maximum context":', "maximum context" in msg)
    print('has "output tokens":', "output tokens" in msg)
    print('has "input tokens":', "input tokens" in msg)
    print('parsed_avail:', parse_available_output_tokens_from_error(msg))
    print('parsed_limit:', parse_context_limit_from_error(msg))
except Exception as ee:
    print('construct err:', ee)


