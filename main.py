import json


with open(f'fields/evergreen/option8.json') as f:
    data_set = json.load(f)

for i in range(len(data_set)):
    field = data_set[i]
    field_type = field['type']
    field_id = field['id']
    
    # if(field_type == 'VECTOR'):
    #     print(f'{field_id} (VECTOR): {field['description']}')
    # if (field_type == 'MATRIX'):
    #     print(f'{field_id} (MATRIX): {field['description']}')
    # if (field_type == 'GROUP'):
    #     print(f'{field_id} (GROUP): {field['description']}')

    print(f'{field_id}: {field['description']}')