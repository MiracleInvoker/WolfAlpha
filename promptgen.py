import json
import utils

def operators():
    with open('operators_detailed.json', 'r') as f:
        operators = json.load(f)

    operator_prompt = ''

    for operator in operators:
        operator_prompt += operator['definition']
        operator_prompt += ':\n'

        # summary = operator.get('summary')

        # if (summary):
        #     operator_prompt += summary
        # else:
        #     operator_prompt += operator['description']
        #     operator_prompt += '\n'
        # operator_prompt += '\n'
        operator_prompt += operator['description']
        operator_prompt += '\n\n'

    print(operator_prompt.strip())


def prompt_with_fields():
    data_fields = ''

    with open('prompt.txt', 'r') as f:
        prompt = f.read().strip()
    
    sum = 0
    for data_set_id in utils.data_set.evergreen:
        with open(f'fields/evergreen/{data_set_id}.json') as f:
            data_set = json.load(f)
        
        sum += len(data_set)

    for data_set_id in utils.data_set.evergreen:
        with open(f'fields/evergreen/{data_set_id}.json') as f:
            data_set = json.load(f)
        
        for i in range(int((len(data_set) * 100 + sum - 1) / sum)):
            field = data_set[i]
            field_type = field['type']
            field_id = field['id']
            
            if(field_type == 'VECTOR'):
                data_fields += f'{field_id} (VECTOR): {field['description']}'
            if (field_type == 'MATRIX'):
                data_fields += f'{field_id} (MATRIX): {field['description']}'
            if (field_type == 'GROUP'):
                data_fields += f'{field_id} (GROUP): {field['description']}'
            data_fields += '\n'

    prompt = prompt.replace('{data_fields_substitute}', data_fields.strip())

    print(prompt)

    return prompt

operators()
prompt_with_fields()