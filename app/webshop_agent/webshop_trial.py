import os
from typing import Any

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from dotenv import load_dotenv
from env_history import EnvironmentHistory
from openai import OpenAI

# Load environment variables at the start
load_dotenv()

client = OpenAI(
    api_key=os.getenv("UPSTAGE_API_KEY"),
    base_url="https://api.upstage.ai/v1/solar"
)

WEBSHOP_URL = "https://hen-fitting-trout.ngrok-free.app/"
ACTION_TO_TEMPLATE = {
    'Description': 'description_page.html',
    'Features': 'features_page.html',
    'Reviews': 'review_page.html',
    'Attributes': 'attributes_page.html',
}
with open("webshop_agent/base_prompt.txt") as f:
    BASE_PROMPT = f.read()

def llm(prompt, stop=["\n"]):
    try:
        cur_try = 0
        while cur_try < 6:
            messages= []
            system = "You run in a loop of Action, Observation..\n **IMPORTANT**: 1. Never include Observation in your answer! 2. Answer just one action! \n"
            messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            stream = client.chat.completions.create(
                model="solar-pro",
                messages=messages,
                temperature=cur_try * 0.2,
                max_tokens=100,
                top_p=1.0,
            )
            text = stream.choices[0].message.content
            if len(text.strip()) >= 5:
                return text.strip()
            cur_try += 1
        return ""

    except Exception as e:
        # print(f"Buy 0 Fail: {e}")
        # import sys
        # sys.exit(1)
        return ""

def clean_str(p):
  return p.encode().decode("unicode-escape").encode("latin1").decode("utf-8")

def tag_visible(element):
    ignore = {'style', 'script', 'head', 'title', 'meta', '[document]'}
    return (
        element.parent.name not in ignore and not isinstance(element, Comment)
    )

def webshop_text(session, page_type, query_string='', page_num=1, asin='', options={}, subpage='', **kwargs):
    if page_type == 'init':
      url = (
          f'{WEBSHOP_URL}/{session}'
      )
    if page_type == 'search':
      url = (
          f'{WEBSHOP_URL}/search_results/{session}/'
          f'{query_string}/{page_num}'
      )
    elif page_type == 'item':
      url = (
          f'{WEBSHOP_URL}/item_page/{session}/'
          f'{asin}/{query_string}/{page_num}/{options}'
      )
    elif page_type == 'item_sub':
      url = (
          f'{WEBSHOP_URL}/item_sub_page/{session}/'
          f'{asin}/{query_string}/{page_num}/{subpage}/{options}'
      )
    elif page_type == 'end':
      url = (
          f'{WEBSHOP_URL}/done/{session}/'
          f'{asin}/{options}'
      )
    html = requests.get(url).text # type: ignore
    html_obj = BeautifulSoup(html, 'html.parser')
    texts = html_obj.findAll(text=True)
    visible_texts = list(filter(tag_visible, texts))
    if False:
        # For `simple` mode, return just [SEP] separators
        return ' [SEP] '.join(t.strip() for t in visible_texts if t != '\n')
    else:
        # Otherwise, return an observation with tags mapped to specific, unique separators
        observation = ''
        option_type = ''
        options = {}
        asins = []
        cnt = 0
        prod_cnt = 0
        just_prod = 0
        for t in visible_texts:
            if t == '\n': continue
            if t.replace('\n', '').replace('\\n', '').replace(' ', '') == '': continue
            # if t.startswith('Instruction:') and page_type != 'init': continue
            # print(t.parent.name, t)
            if t.parent.name == 'button':  # button
                processed_t = f'\n[{t}] '
            elif t.parent.name == 'label':  # options
                if f"'{t}'" in url: # type: ignore
                    processed_t = f'[[{t}]]'
                    # observation = f'You have clicked {t}.\n' + observation
                else:
                    processed_t = f'[{t}]'
                options[str(t)] = option_type
                # options[option_type] = options.get(option_type, []) + [str(t)]
            elif t.parent.get('class') == ["product-link"]: # product asins
                processed_t = f'\n[{t}] '
                if prod_cnt >= 3:
                  processed_t = ''
                prod_cnt += 1
                asins.append(str(t))
                just_prod = 0
            else: # regular, unclickable text
                processed_t =  '\n' + str(t) + ' '
                if cnt < 2 and page_type != 'init': processed_t = ''
                if just_prod <= 2 and prod_cnt >= 4: processed_t = ''
                option_type = str(t)
                cnt += 1
            just_prod += 1
            observation += processed_t
        info = {}
        if options:
          info['option_types'] = options
        if asins:
          info['asins'] = asins
        if 'Your score (min 0.0, max 1.0)' in visible_texts:
          idx = visible_texts.index('Your score (min 0.0, max 1.0)')
          info['reward'] = float(visible_texts[idx + 1])
          observation = 'Your score (min 0.0, max 1.0): ' + (visible_texts[idx + 1])
        return clean_str(observation), info

class webshopEnv:
    def __init__(self):
        self.sessions = {}

    def step(self, session, action):
        done = False
        observation_ = None
        if action == 'reset':
          self.sessions[session] = {'session': session, 'page_type': 'init'}
        elif action.startswith('think['):
          observation = 'OK.'
        elif action.startswith('search['):
          assert self.sessions[session]['page_type'] == 'init'
          query = action[7:-1]
          self.sessions[session] = {'session': session, 'page_type': 'search',
                                'query_string': query, 'page_num': 1}
        elif action.startswith('click['):
            position = action.find(']')
            button = action[6:position]
            if button == 'Buy Now':
                assert self.sessions[session]['page_type'] == 'item'
                self.sessions[session]['page_type'] = 'end'
                print(f"Buy {self.sessions[session]['asin']} Successfully.")
                done = True
            elif button == 'Back to Search':
                assert self.sessions[session]['page_type'] in ['search', 'item_sub', 'item']
                self.sessions[session] = {'session': session, 'page_type': 'init'}
            elif button == 'Next >':
                assert False # ad hoc page limitation
                assert self.sessions[session]['page_type'] == 'search'
                self.sessions[session]['page_num'] += 1
            elif button == '< Prev':
                assert self.sessions[session]['page_type'] in ['search', 'item_sub', 'item']
                if self.sessions[session]['page_type'] == 'search':
                    assert False
                    self.sessions[session]['page_num'] -= 1
                elif self.sessions[session]['page_type'] == 'item_sub':
                  self.sessions[session]['page_type'] = 'item'
                elif self.sessions[session]['page_type'] == 'item':
                  self.sessions[session]['page_type'] = 'search'
                  self.sessions[session]['options'] = {}
            elif button in ACTION_TO_TEMPLATE:
                assert self.sessions[session]['page_type'] == 'item'
                self.sessions[session]['page_type'] = 'item_sub'
                self.sessions[session]['subpage'] = button
            else:
                if self.sessions[session]['page_type'] == 'search':
                    assert button in self.sessions[session].get('asins', [])  # must be asins
                    self.sessions[session]['page_type'] = 'item'
                    self.sessions[session]['asin'] = button
                elif self.sessions[session]['page_type'] == 'item':
                    assert 'option_types' in self.sessions[session]
                    assert button in self.sessions[session]['option_types'], (button, self.sessions[session]['option_types'])  # must be options
                    option_type = self.sessions[session]['option_types'][button]
                    if 'options' not in self.sessions[session]:
                        self.sessions[session]['options'] = {}
                    self.sessions[session]['options'][option_type] = button
                    observation_ = f'You have clicked {button}.'
        else:
            assert False
        observation, info = webshop_text(**self.sessions[session])
        if observation_:
            observation = observation_
        self.sessions[session].update(info)
        reward = info.get('reward', 0.0)
        return observation, reward, done

def webshop_run(idx, env, base_prompt, memory: List[str], to_print=True, run_http=False, item = "") -> Tuple[EnvironmentHistory, bool]:
    action = 'reset'
    system_prompt = "You run in a loop of Action, Observation..\n **IMPORTANT**: 1. Never include Observation in your answer! 2. Complete the action answer one by one! \n"
    init_prompt = system_prompt + base_prompt
    prompt = ''

    res = env.step(idx, action)
    observation = res[0]
    if action == 'reset' and run_http==True:
        observation = f"""
WebShop
Instruction:
i am looking for {item}.
[Search]
"""
    if len(memory) > 3:
        env_history = EnvironmentHistory(base_prompt, observation, memory[-3:], [])
    else:
        env_history = EnvironmentHistory(base_prompt, observation, memory, [])
    env_history.reset()
    for i in range(15):
        try:
            if i:
                if i == 1:
                    env_history.add("action", f"\nAction: {action}")
                else:
                    env_history.add("action", action)
                res = env.step(idx, action)
                observation = res[0]
            if action == 'reset' and run_http==True:
                observation = f"""
WebShop
Instruction:
i am looking for {item}.
[Search]
"""
        except AssertionError:
            observation = 'Invalid action!'

        if action.startswith('think'):
            observation = 'OK.'

        if i:
            prompt += f' {action}\nObservation: {observation}\n\nAction:'
        else:
            prompt += f'{observation}\n\nAction:'

        if i:
            env_history.add("observation", observation)

        # if done, check if reward is complete value
        if res[2]:
            return env_history, res[1] == 1.0, res[1]

        action = llm(f"{system_prompt}{env_history}", stop=['\n']).lstrip(' ')
        if i == 14 and res[2] == False:
            print(f"Buy {idx} Fail: Attempt count exceeded")

    return env_history, False, 0.0

def run_trial(
        trial_log_path: str,
        world_log_path: str,
        trial_idx: int,
        env_configs: List[Dict[str, Any]],
        use_memory: bool,
        run_http : bool = False,
        item_string : str = "",
    ) -> list[dict[str, Any]]:
    env = webshopEnv()

    num_successes: int = 0
    sum_reward: float = 0.0
    num_additional_successes: int = 0
    num_envs: int = len(env_configs)
    if run_http:
        item_list = item_string.split(',')

    for z, env_config in enumerate(env_configs):
        if env_config["is_success"]:
            num_successes += 1
            sum_reward += 1.0
            # log to world log
            with open(world_log_path, 'a') as wf:
                wf.write(f'Environment #{z} Trial #{trial_idx}: SUCCESS\n')
            with open(trial_log_path, 'a') as wf:
                wf.write(f'\n#####\n\nEnvironment #{z}: Success\n\n#####\n')
            continue

        try:
            if run_http:
                final_env_history, is_success, reward = webshop_run(f'{z}', env, BASE_PROMPT, env_config["memory"] if use_memory else [], to_print=False, run_http=run_http, item = item_list[z])
            else:
                final_env_history, is_success, reward = webshop_run(f'{z}', env, BASE_PROMPT, env_config["memory"] if use_memory else [], to_print=False)
            sum_reward += reward
            if is_success:
                status_str: str = f'Environment #{z} Trial #{trial_idx}: SUCCESS'
                env_configs[z]["is_success"] = True
                num_successes += 1
                num_additional_successes += 1
            else:
                status_str: str = f'Environment #{z} Trial #{trial_idx}: FAIL({reward})'

            # log env results to trial log
            with open(trial_log_path, 'a') as wf:
                wf.write(f'\n#####\n\nEnvironment #{z}:\n{final_env_history!s}\n\nSTATUS: {"OK" if is_success else "FAIL"}\n\n#####\n')

        except AssertionError:
            status_str: str = f'Environment #{z} Trial #{trial_idx}: FAIL({reward})'

            # log env results to trial log
            with open(trial_log_path, 'a') as wf:
                wf.write(f'\n#####\n\nEnvironment #{z}:\nAssertion Error\n\nSTATUS: FAIL({reward})\n\n#####\n')

        # log to world log
        with open(world_log_path, 'a') as f:
            f.write(status_str + '\n')

    # log trial results to trial and world logs
    log_str: str = f"""
-----
SUCCESS: {num_successes}
ADDITIONAL SUCCESS: {num_additional_successes}
FAIL: {num_envs - num_successes}
TOTAL: {num_envs}
ACCURACY: {round(num_successes / num_envs, 2)}
REWARD ACCURACY: {round(sum_reward / num_envs, 2)}
-----"""
    with open(trial_log_path, 'a') as wf:
        wf.write(log_str)
    with open(world_log_path, 'a') as wf:
        wf.write(log_str + '\n')

    return env_configs
