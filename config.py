import time


simulations_file = ''
max_iterations = 100


system_prompt_file = 'T3'
model = 'gemini-2.5-flash-preview-05-20'
temperature = 0
thinking_budget = 24576
initial_prompt = """

"""
reasoning_description = 'A detailed explanation of the thought process behind constructing this Alpha. This should include the financial or statistical hypothesis, why specific operators and data fields were chosen, and how they are intended to interact to predict price movements. If this is an iteration, explain how it addresses previous results or explores new ideas.'


schema_description = 'Schema for Structured Output of Alpha Expression and its Simulation Settings.'
schema = {
    'Alpha Expression': 'Alphas are Mathematical models that seek to predict the future price movement of various financial instruments.',
    'Universe': 'Subset of region based on liquidity; smaller universes are more liquid.',
    'Delay': 'Delay=1 alphas trade in the morning using data from yesterday. Delay=0 alphas trade in the evening using data from today.',
    'Neutralization': 'Adjust alpha weights such that they sum to zero within each group of the selected type.',
    'Decay': 'Sets input data equal to a linearly decreasing weighted average of that data over the past selected number of days.',
    'Truncation': 'Maximum daily weight of each instrument. Should be a non-negative decimal.',
    'NaN Handling': 'Allows aggregation operators to output numeric values when input values are NaN for a given instrument and date.',
    'Reasoning': reasoning_description
}


if (simulations_file == ''):
    simulations_file = time.strftime('%d%m%Y-%H%M%S')

context_file = simulations_file

simulations_file = f'simulations/{simulations_file}.json'
system_prompt_file = f'prompts/{system_prompt_file}.txt'
context_file = f'contexts/{context_file}.pkl'


initial_prompt = initial_prompt.strip()