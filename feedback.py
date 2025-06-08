import config
from google import genai
from google.genai import types
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import os
import pickle
from time import sleep
import traceback
import utils


with open(config.system_prompt_file, 'r') as f:
    system_prompt = f.read()

with open(config.simulations_file, 'w+') as f:
    json.dump([], f, indent=2)

with open(config.context_file, 'wb') as f:
    pickle.dump([], f)


clr = utils.clr

wq_session = utils.wq_login()
genai_client = genai.Client(
    api_key=os.getenv('GEMINI_API_KEY')
)

context = []
performance_history = []


plt.ion()
plt.style.use('dark_background')
fig, ax = plt.subplots()
line, = ax.plot(performance_history, marker='o')

ax.set_title('Performance History')
ax.set_xlabel('Iteration')
ax.set_ylabel('Performance')
ax.xaxis.set_major_locator(MaxNLocator(integer=True))
fig.canvas.manager.set_window_title('WolfAlpha')


def update_peformance(peformance):
    performance_history.append(peformance)
    line.set_xdata(range(1, 1 + len(performance_history)))
    line.set_ydata(performance_history)
    ax.relim()
    ax.autoscale_view()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.1)

plt.show(block = False)


model_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=config.thinking_budget
    ),
    temperature=config.temperature,
    response_mime_type='application/json',
    response_schema=types.Schema(
        type=types.Type.OBJECT,
        description=config.schema_description,
        required=list(config.schema.keys()),
        properties={
            'Alpha Expression': types.Schema(
                type=types.Type.STRING,
                description=config.schema['Alpha Expression'],
            ),
            'Universe': types.Schema(
                type=types.Type.STRING,
                description=config.schema['Universe'],
                enum=utils.simul.Universe,
            ),
            'Delay': types.Schema(
                type=types.Type.INTEGER,
                description=config.schema['Delay'],
            ),
            'Neutralization': types.Schema(
                type=types.Type.STRING,
                description=config.schema['Neutralization'],
                enum=utils.simul.Neutralization,
            ),
            'Decay': types.Schema(
                type=types.Type.INTEGER,
                description=config.schema['Decay'],
            ),
            'Truncation': types.Schema(
                type=types.Type.NUMBER,
                description=config.schema['Truncation'],
            ),
            'NaN Handling': types.Schema(
                type=types.Type.STRING,
                description=config.schema['NaN Handling'],
                enum=utils.simul.NaN_Handling,
            ),
            'Reasoning': types.Schema(
                type=types.Type.STRING,
                description=config.reasoning_description.strip()
            )
        },
    ),
    system_instruction=[
        types.Part.from_text(text=system_prompt.strip()),
    ]
)


class Model:
    def count_tokens(client, context):
        resp = client.models.count_tokens(
            model=config.model,
            contents=context
        )

        return resp.total_tokens

    def get_output(client, model_config, context):
        while True:
            try:
                response = client.models.generate_content(
                    model=config.model,
                    contents=context,
                    config=model_config
                )

                resp = response.text
                return json.loads(resp)

            except Exception:
                print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                sleep(1)

    def process_output(alpha):

        payload = {
            'type': 'REGULAR',
            'settings': {
                'nanHandling': alpha['NaN Handling'],
                'instrumentType': 'EQUITY',
                'delay': alpha['Delay'],
                'universe': alpha['Universe'],
                'truncation': alpha['Truncation'],
                'unitHandling': 'VERIFY',
                'testPeriod': 'P0D',
                'pasteurization': 'ON',
                'region': 'USA',
                'language': 'FASTEXPR',
                'decay': alpha['Decay'],
                'neutralization': alpha['Neutralization'],
                'visualization': False
            },
            'regular': alpha['Alpha Expression']
        }

        return payload
    
    def get_context(i, model_output):

        model_context = f"""
Iteration #{i + 1}
Alpha Expression:
{model_output['Alpha Expression']}

Reasoning:
{model_output['Reasoning']}

Simulation Settings:
Universe: {model_output['Universe']}
Delay: {model_output['Delay']}
Neutralization: {model_output['Neutralization']}
Decay: {model_output['Decay']}
Truncation: {model_output['Truncation']}
NaN Handling: {model_output['NaN Handling']}
"""
        return model_context.strip()


class User:
    def get_context(simul_resp):
        insample = simul_resp['is']
        checks = insample['checks']

        user_context = f"""
Simulation Results:
Sharpe: {insample['sharpe']}, Fitness: {insample['fitness']}, Turnover: {round(100 * insample['turnover'], 2)}%, Performance: {simul_resp['performance']}
Returns: {round(100 * insample['returns'], 2)}%, Drawdown: {round(100 * insample['drawdown'], 2)}%, Sub Universe Sharpe: {checks[5]['value']}, Margin: {round(10000 * insample['margin'], 2)}‱
"""

        if (checks[4]['result'] == 'FAIL'):
            if (checks[4].get('value')):
                user_context += f'Weight concentration {round(checks[4]['value'] * 100, 2)}% is above cutoff of {round(checks[4]['limit'] * 100, 2)}% on {checks[4]['date']}.\n'
            else:
                user_context += 'Weight is too strongly concentrated or too few instruments are assigned weight.\n'

        if (checks[5]['result'] == 'FAIL'):
            user_context += f'Sub Universe Sharpe {checks[5]['value']} is not above {checks[5]['limit']}.\n'

        if (checks[6]['result'] == 'UNITS'):
            user_context += checks[6]['message'].replace('; ', '\n')
            user_context += '\n'

        return user_context.strip()


context.append(
    types.Content(
        role='user',
        parts=[
            types.Part.from_text(text=config.initial_prompt)
        ]
    )
)


print(f'{clr.purple}Model: {config.model}')
print(f'Temperature: {config.temperature}')
print(f'System Prompt File: {config.system_prompt_file}{clr.white}')


print(f'{clr.green}{config.initial_prompt}{clr.white}')


for i in range(config.max_iterations):

    model_output = Model.get_output(genai_client, model_config, context)

    model_context = Model.get_context(i, model_output)
    alpha = Model.process_output(model_output)

    context.append(
        types.Content(
            role='model',
            parts=[
                types.Part.from_text(text=model_context)
            ]
        )
    )
    print(f'{clr.cyan}{model_context}{clr.white}')

    alpha_id, simul_resp = utils.Alpha.simulate(wq_session, alpha)
    performance = utils.Alpha.get_performance(wq_session, alpha_id)

    update_peformance(performance)

    simul_resp['performance'] = performance

    with open(config.simulations_file, 'r+') as f:
        data = json.load(f)
        data.append(simul_resp)
        f.seek(0)
        json.dump(data, f, indent=2)

    user_context = User.get_context(simul_resp)

    context.append(
        types.Content(
            role='user',
            parts=[
                types.Part.from_text(text=user_context)
            ]
        )
    )

    print(f'{clr.green}{user_context}{clr.white}')

    with open(config.context_file, 'wb') as f:
        pickle.dump(context, f)

    token_count = Model.count_tokens(genai_client, context)
    print(f'{clr.purple}Token Count: {token_count}{clr.white}')

    print()
