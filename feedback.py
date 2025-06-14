import config
from google import genai
from google.genai import types
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter
import os
import pickle
import time
import traceback
import utils
import requests
from PIL import Image

with open(config.system_prompt_file, 'r') as f:
    system_prompt = f.read()

with open(config.simulations_file, 'w+') as f:
    json.dump([], f, indent=2)

with open(config.context_file, 'wb') as f:
    pickle.dump([], f)

clr = utils.clr
wq_session = utils.wq_login()
genai_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

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

plt.show(block=False)

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
            'Alpha Expression': types.Schema(type=types.Type.STRING, description=config.schema['Alpha Expression']),
            'Universe': types.Schema(type=types.Type.STRING, description=config.schema['Universe'], enum=utils.simul.Universe),
            'Delay': types.Schema(type=types.Type.INTEGER, description=config.schema['Delay']),
            'Neutralization': types.Schema(type=types.Type.STRING, description=config.schema['Neutralization'], enum=utils.simul.Neutralization),
            'Decay': types.Schema(type=types.Type.INTEGER, description=config.schema['Decay']),
            'Truncation': types.Schema(type=types.Type.NUMBER, description=config.schema['Truncation']),
            'NaN Handling': types.Schema(type=types.Type.STRING, description=config.schema['NaN Handling'], enum=utils.simul.NaN_Handling),
            'Reasoning': types.Schema(type=types.Type.STRING, description=config.reasoning_description.strip())
        },
    ),
    system_instruction=[
        types.Part.from_text(text=system_prompt.strip()),
    ]
)

def analyze_pnl_graph(alpha_id: str, wq_token: str) -> str:
    MAX_WAIT_SECONDS = 120 
    POLL_INTERVAL_SECONDS = 10 

    IMAGE_FILENAME = "temp_pnl_graph.png"
    VISION_MODEL = 'gemini-1.5-flash-latest'

    start_time = time.time()
    pnl = None

    print(f"{clr.yellow}--- Starting PnL Analysis for alpha: {alpha_id} ---{clr.white}")
    
    while time.time() - start_time < MAX_WAIT_SECONDS:
        try:
            url = f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl"
            headers = {"Authorization": f"Bearer {wq_token}"}
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                error_msg = f"API returned non-200 status. Status: {response.status_code}, Body: {response.text}"
                print(f"{clr.red}{error_msg}{clr.white}")
                return f"Note: PnL Graph analysis failed. Reason: {error_msg}"
            
            data = response.json()

            if data.get('records'):
                pnl = data['records']
                print(f"{clr.green}Successfully fetched PnL data after {int(time.time() - start_time)} seconds.{clr.white}")
                break
            else:
                print(f"{clr.yellow}PnL data not yet populated. Retrying in {POLL_INTERVAL_SECONDS}s...{clr.white}")

        except json.JSONDecodeError:

            print(f"{clr.yellow}PnL data not yet available (received empty response). Retrying in {POLL_INTERVAL_SECONDS}s...{clr.white}")
        
        except Exception as e:
  
            error_summary = f"An unexpected error occurred while polling for PnL data: {e}"
            print(f"{clr.red}{error_summary}\n{traceback.format_exc()}{clr.white}")
            return f"Note: PnL analysis failed. Reason: {error_summary}"
        
        time.sleep(POLL_INTERVAL_SECONDS)

    if not pnl:
        timeout_msg = f"Timed out after {MAX_WAIT_SECONDS} seconds waiting for PnL data."
        print(f"{clr.red}{timeout_msg}{clr.white}")
        return f"Note: PnL analysis failed. Reason: {timeout_msg}"

    try:
        pnl_x = list(range(len(pnl)))
        pnl_y = [point[1] for point in pnl]

        pnl_fig, pnl_ax = plt.subplots(figsize=(10, 6))
        pnl_ax.plot(pnl_x, pnl_y, label=f'PnL for {alpha_id}', color='cyan')
        pnl_ax.set_title("PnL (Profit and Loss) Curve")
        pnl_ax.set_xlabel("Time")
        pnl_ax.set_ylabel("Cumulative PnL")
        pnl_ax.legend()
        pnl_ax.grid(True)
        pnl_ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.2f}'))
        
        pnl_fig.savefig(IMAGE_FILENAME, format='png', dpi=150, bbox_inches='tight')
        plt.close(pnl_fig)
        print(f"{clr.yellow}PnL graph saved as '{IMAGE_FILENAME}'.{clr.white}")

       
        print(f"{clr.yellow}Sending PnL graph to Gemini for analysis...{clr.white}")
        pnl_image = Image.open(IMAGE_FILENAME)
        pnl_analysis_prompt = """
        Analyze this financial PnL (Profit and Loss) curve. Provide a concise summary focusing on the alpha's performance characteristics. Describe:
        1. Overall Trend and Profitability: Is it generally profitable?
        2. Volatility: Is the curve smooth or erratic?
        3. Major Drawdowns: Identify any significant periods of loss.
        4. Late-stage Performance: How did the alpha perform towards the end of the period shown?
        """
        
        analysis_response = genai_client.models.generate_content(
            model=VISION_MODEL,
            contents=[pnl_analysis_prompt, pnl_image]
        )
        print(f"{clr.green}--- PnL Analysis Complete ---{clr.white}")
        return analysis_response.text

    except Exception as e:
        error_summary = f"An error occurred during graph creation or Gemini analysis: {e}"
        print(f"{clr.red}{error_summary}\n{traceback.format_exc()}{clr.white}")
        return f"Note: PnL Graph analysis failed after data fetch. Reason: {error_summary}"

class Model:
    def count_tokens(context):
        resp = genai_client.models.count_tokens(model=config.model, contents=context)
        return resp.total_tokens
    def get_output(context):
        while True:
            try:
                response = genai_client.models.generate_content(model=config.model, contents=context, config=model_config)
                return json.loads(response.text)
            except Exception:
                print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                time.sleep(1)
    def process_output(alpha):
        payload = {'type': 'REGULAR', 'settings': {'nanHandling': alpha['NaN Handling'], 'instrumentType': 'EQUITY', 'delay': alpha['Delay'], 'universe': alpha['Universe'], 'truncation': alpha['Truncation'], 'unitHandling': 'VERIFY', 'testPeriod': 'P0D', 'pasteurization': 'ON', 'region': 'USA', 'language': 'FASTEXPR', 'decay': alpha['Decay'], 'neutralization': alpha['Neutralization'], 'visualization': False}, 'regular': alpha['Alpha Expression']}
        return payload
    def get_context(i, model_output):
        model_context = f"Iteration #{i + 1}\nAlpha Expression:\n{model_output['Alpha Expression']}\n\nReasoning:\n{model_output['Reasoning']}\n\nSimulation Settings:\nUniverse: {model_output['Universe']}\nDelay: {model_output['Delay']}\nNeutralization: {model_output['Neutralization']}\nDecay: {model_output['Decay']}\nTruncation: {model_output['Truncation']}\nNaN Handling: {model_output['NaN Handling']}"
        return model_context.strip()


class User:
 
    def get_context(simul_resp):
        insample = simul_resp['is']
        checks = insample['checks']
        user_context = f"Simulation Results:\nSharpe: {insample['sharpe']}\nFitness: {insample['fitness']}\nPerformance: {simul_resp['Score Change']}\nTurnover: {round(100 * insample['turnover'], 2)}%"
        if (checks[4]['result'] == 'FAIL'):
            if (checks[4].get('value')): user_context += f'\nWeight concentration {round(checks[4]['value'] * 100, 2)}% is above cutoff of {round(checks[4]['limit'] * 100, 2)}% on {checks[4]['date']}.'
            else: user_context += '\nWeight is too strongly concentrated or too few instruments are assigned weight.'
        if (checks[5]['result'] == 'FAIL'): user_context += f'\nSub Universe Sharpe {checks[5]['value']} is not above {checks[5]['limit']}.'
        if (checks[6]['result'] == 'UNITS'): user_context += '\n' + checks[6]['message'].replace('; ', '\n')
        return user_context.strip()
    def save_iteration(context, alpha):
        with open(config.simulations_file, 'r+') as f:
            data = json.load(f)
            data.append(alpha)
            f.seek(0)
            json.dump(data, f, indent=2)
        with open(config.context_file, 'wb') as f: pickle.dump(context, f)

context.append(types.Content(role='user', parts=[types.Part.from_text(text=config.initial_prompt)]))
print(f'{clr.purple}Model: {config.model}')
print(f'Temperature: {config.temperature}')
print(f'System Prompt File: {config.system_prompt_file}{clr.white}')
print(f'{clr.green}{config.initial_prompt}{clr.white}')


for i in range(config.max_iterations):
    model_output = Model.get_output(context)
    model_context = Model.get_context(i, model_output)
    alpha_payload = Model.process_output(model_output)

    context.append(types.Content(role='model', parts=[types.Part.from_text(text=model_context)]))
    print(f'{clr.cyan}{model_context}{clr.white}')


    alpha = utils.Alpha.simulate(wq_session, alpha_payload)
    

    if not isinstance(alpha, dict):
        print(f"{clr.red}Simulation failed or returned an unexpected format. Skipping feedback.{clr.white}")

        context.append(types.Content(role='user', parts=[types.Part.from_text(text="The simulation failed to produce valid results. Please try a different approach.")]))
        continue

    update_peformance(alpha['Score Change'])

    user_context = User.get_context(alpha)


    if 'id' in alpha:
        alpha_id = alpha['id']
        wq_token = os.getenv("t")
        
        if wq_token:
            pnl_summary = analyze_pnl_graph(alpha_id, wq_token)

            user_context += f"\n\nPnL Curve Analysis:\n{pnl_summary}"
        else:
            print(f"{clr.red}WorldQuant token 't' not found in environment. Skipping PnL analysis.{clr.white}")
            user_context += "\n\nPnL analysis was skipped because the WorldQuant token was not found."
    else:
        print(f"{clr.yellow}Could not find 'id' key in simulation response. Skipping PnL analysis.{clr.white}")
        user_context += "\n\nPnL analysis was skipped because no alpha ID was found in the simulation results."
        
    context.append(types.Content(role='user', parts=[types.Part.from_text(text=user_context)]))
    print(f'{clr.green}{user_context}{clr.white}')

    User.save_iteration(context, alpha)
    token_count = Model.count_tokens(context)
    print(f'{clr.purple}Token Count: {token_count}{clr.white}')
    print()