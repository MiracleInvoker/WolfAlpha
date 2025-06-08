import config
from google import genai
from google.genai import types
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import os
import pickle
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


def count_tokens(client, context):
    resp = client.models.count_tokens(
        model=config.model,
        contents=context
    )

    return resp.total_tokens


def generate_alpha(client, model_config, context):

    while True:
        try:
            response = client.models.generate_content(
                model=config.model,
                contents=context,
                config=model_config
            )

            return response.text

        except Exception as e:
            print(f'{clr.red}Exception in generate_alpha: {e}{clr.white}')


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

    model_output = generate_alpha(genai_client, model_config, context)

    alpha = json.loads(model_output)

    model_response = f"""
Iteration #{i + 1}
Alpha Expression:
{alpha['Alpha Expression']}

Reasoning:
{alpha['Reasoning']}

Simulation Settings:
Universe: {alpha['Universe']}
Delay: {alpha['Delay']}
Neutralization: {alpha['Neutralization']}
Decay: {alpha['Decay']}
Truncation: {alpha['Truncation']}
NaN Handling: {alpha['NaN Handling']}
"""
    model_response = model_response.strip()

    context.append(
        types.Content(
            role='model',
            parts=[
                types.Part.from_text(text=model_response)
            ]
        )
    )
    print(f'{clr.cyan}{model_response}{clr.white}')

    alpha_id, simul_resp = utils.Alpha.simulate(wq_session, alpha)
    performance = utils.Alpha.get_performance(wq_session, alpha_id)

    update_peformance(performance)

    simul_resp['performance'] = performance

    with open(config.simulations_file, 'r+') as f:
        data = json.load(f)
        data.append(simul_resp)
        f.seek(0)
        json.dump(data, f, indent=2)

    insample = simul_resp['is']
    checks = insample['checks']

    user_response = f"""
Simulation Results:
Sharpe: {insample['sharpe']}, Fitness: {insample['fitness']}, Turnover: {round(100 * insample['turnover'], 2)}%, Performance: {performance}
Returns: {round(100 * insample['returns'], 2)}%, Drawdown: {round(100 * insample['drawdown'], 2)}%, Sub Universe Sharpe: {checks[5]['value']}, Margin: {round(10000 * insample['margin'], 2)}‱
"""

    if (checks[4]['result'] == 'FAIL'):
        if (checks[4].get('value')):
            user_response += f'Weight concentration {round(checks[4]['value'] * 100, 2)}% is above cutoff of {round(checks[4]['limit'] * 100, 2)}% on {checks[4]['date']}.\n'
        else:
            user_response += 'Weight is too strongly concentrated or too few instruments are assigned weight.\n'

    if (checks[5]['result'] == 'FAIL'):
        user_response += f'Sub Universe Sharpe {checks[5]['value']} is not above {checks[5]['limit']}.\n'

    if (checks[6]['result'] == 'UNITS'):
        user_response += checks[6]['message'].replace('; ', '\n')
        user_response += '\n'

    user_response = user_response.strip()

    print(f'{clr.green}{user_response}{clr.white}')

    context.append(
        types.Content(
            role='user',
            parts=[
                types.Part.from_text(text=user_response)
            ]
        )
    )

    with open(config.context_file, 'wb') as f:
        pickle.dump(context, f)

    token_count = count_tokens(genai_client, context)
    print(f'{clr.purple}Token Count: {token_count}{clr.white}')

    print()
