import os

import openai
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,  # type: ignore
    wait_random_exponential,  # type: ignore
)

openai.api_key = os.getenv('OPENAI_API_KEY')

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def get_completion(
    prompt: str | list[str],
    max_tokens: int = 256,
    stop_strs: list[str] | None = None,
    is_batched: bool = False
) -> str | list[str]:
    if not (is_batched and isinstance(prompt, list)) and not (not is_batched and isinstance(prompt, str)):
        raise ValueError("Invalid input: prompt should be a string when not batched, or a list of strings when batched.")
    client = OpenAI(
    api_key=os.environ.get("UPSTAGE_API_KEY"),
    base_url="https://api.upstage.ai/v1/solar"
    )
    messages= []
    sys_msg = (
        "You run in a loop of trajectory, Next plan.. "
        "Check the item name, quantity, price, option requested by instruction and the name, quantity, price, "
        "and option of the purchased item to review past mistakes and avoid repeating them. If a mistake occurs, "
        "analyze why it happened and explicitly state how you will avoid it in the future."
    )
    messages.append({"role": "system", "content": sys_msg})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model='solar-pro',
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
        top_p=1,
        # frequency_penalty=0.0,
        # presence_penalty=0.0,
        # stop=stop_strs,
    )
    if is_batched:
        res: list[str] = [""] * len(prompt)
        for choice in response.choices:
            res[choice.index] = choice.text
        return res
    return response.choices[0].message.content
