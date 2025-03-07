from typing import Any

from utils import get_completion

with open("./webshop_agent/reflection_few_shot_examples.txt") as f:
    FEW_SHOT_EXAMPLES = f.read()

def _get_scenario(s: str) -> str:
    """Parses the relevant scenario from the experience log."""
    return s.split("Instruction:")[-1].strip()

def _generate_reflection_query(log_str: str, memory: list[str]) -> str:
    """Allows the Agent to reflect upon a past experience."""
    scenario: str = _get_scenario(log_str)
    query: str = (
        "You will be given the history of a past experience in which you were placed in an environment and given a task to complete. "
        "You were unsuccessful in completing the task. Do not summarize your environment, but rather think about the strategy and path "
        "you took to attempt to complete the task. Devise a concise, new plan of action that accounts for your mistake with reference "
        "to specific actions that you should have taken. There are two examples below.\n\n"
        f"{FEW_SHOT_EXAMPLES}\n\n"
        f"Instruction: {scenario}"
    )

    if len(memory) > 0:
        query += '\n\nPlans from past attempts:\n'
        for i, m in enumerate(memory):
            query += f'Trial #{i}: {m}\n'

    query += "\n\nNew plan:"
    return query

def update_memory(trial_log_path: str, env_configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Updates the given env_config with the appropriate reflections."""
    with open(trial_log_path) as f:
        full_log: str = f.read()

    env_logs: list[str] = full_log.split('#####\n\n#####')
    if len(env_logs) != len(env_configs):
        raise ValueError(f'bad: {len(env_logs)}, {len(env_configs)}')
    for i, env in enumerate(env_configs):
        # if unsolved, get reflection and update env config
        if not env['is_success']:
            if len(env['memory']) > 3:
                memory: list[str] = env['memory'][-3:]
            else:
                memory: list[str] = env['memory']
            reflection_query: str = _generate_reflection_query(env_logs[i], memory)
            reflection: str = get_completion(reflection_query) # type: ignore
            env_configs[i]['memory'] += [reflection]

    return env_configs
