from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

MODEL = "gemma-4-e4b-it"  # use your loaded model name

messages: list[ChatCompletionMessageParam] = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hi!"},
]

client = OpenAI(
    base_url="https://localai.gosztolya.cloud/v1",
    default_headers={"User-Agent": "curl/8.5.0"},
)
# print(client.models.list())  # list available models to verify connection
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.7,
    max_tokens=200,
    stream=True,
)


def stream_response():
    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

        # also print reasoning if available
        try:
            reasoning = chunk.choices[0].delta.reasoning
            if reasoning:
                yield f"{reasoning}]\n"
        except AttributeError:
            pass


reply = ""
for content in stream_response():
    print(content, end="", flush=True)
    reply += content

print()
