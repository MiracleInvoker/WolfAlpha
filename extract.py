import html2text
import json
import os
from time import sleep
import utils


settings = utils.simul
clr = utils.clr


def data_sets():
    wq_session = utils.wq_login()
    os.makedirs('data-sets', exist_ok = True)
    print(f'{clr.green}data-sets directory formed...{clr.white}')

    for region in settings.Region:
        for delay in settings.Delay:
            for universe in settings.Universe:
                resp = wq_session.get(utils.API.data_sets, params ={
                    'delay': delay,
                    'instrumentType': 'EQUITY',
                    'limit': 50,
                    'offset': 0,
                    'region': region,
                    'universe': universe
                })
                resp = resp.json()

                with open(f'data-sets/{region}D{delay}{universe}.json', 'w') as f:
                    json.dump(resp, f, indent = 2)

                print(f'{clr.green}Extracted {region} D{delay} {universe} Data Set...{clr.white}')


def data_fields():
    wq_session = utils.wq_login()

    os.makedirs('data-fields', exist_ok = True)
    print(f'{clr.green}data-fields directory formed...{clr.white}')

    for region in settings.Region:
        for delay in settings.Delay:
            for universe in settings.Universe:

                with open(f'data-sets/{region}D{delay}{universe}.json', 'r') as f:
                    data_sets = json.load(f)

                data_sets = data_sets['results']
                for data_set in data_sets:
                    category = data_set['id']

                    payload = {
                            'dataset.id': category,
                            'delay': delay,
                            'instrumentType': 'EQUITY',
                            'limit': 50,
                            'offset': 0,
                            'region': region,
                            'universe': universe,
                            'order': '-alphaCount'
                        }

                    fields = []

                    while True:
                        resp = wq_session.get(utils.API.data_fields, params = payload)

                        resp = resp.json()
                        result = resp['results']

                        if (result == []): break

                        fields += result
                        payload['offset'] += 50 


                    dir = f'data-fields/{region}/D{delay}/{universe}'
                    os.makedirs(dir, exist_ok = True)
                    with open(f'{dir}/{category}.json', 'w') as f:
                        json.dump(fields, f, indent = 2)

                    print(f'{clr.green}Extracted {len(fields)} ({region}/D{delay}/{universe}/{category}) Data Fields...{clr.white}')



def operators():
    wq_session = utils.wq_login()
    resp = wq_session.get(utils.API.operators)
    resp = resp.json()

    with open(f'operators.json', 'w') as f:
        json.dump(resp, f, indent = 2)

    print(f'{clr.green}Extracted {len(resp)} Operators...{clr.white}')


def operator_details():
    h = html2text.HTML2Text()
    h.ignore_links = True

    with open('operators.json', 'r') as f:
        operators = json.load(f)

    wq_session = utils.wq_login()

    for i in range(len(operators)):
        operator = operators[i]
        doc = operator['documentation']

        if (doc is None): continue

        resp = wq_session.get(utils.API.base + doc)
        resp = resp.json()

        contents = resp['content']

        desc = ''

        for content in contents:
            content_type = content['type']

            if (content_type == 'TEXT'):
                desc += h.handle(content['value']).replace('\n', ' ').replace('\n\n', '\n')
                desc += '\n'
            elif (content_type == 'SIMULATION_EXAMPLE'):
                alpha = content['value']
                desc += utils.alpha_json2txt(alpha)
                desc += '\n'
            else:
                continue

        operators[i]['summary'] = desc
        print(f'{clr.yellow}Adding detail to {i + 1}th Operator...{clr.white}')

    print(f'{clr.green}Added details to Operators...{clr.white}')
    with open('operators_detailed.json', 'w') as f:
        json.dump(operators, f, indent = 2)


def alphas_from_page(resp):
    alphas = []

    contents = resp['content']
    for content in contents:
        content_type = content['type']
        if (content_type == 'SIMULATION_EXAMPLE'):
            alpha = content['value']
            alpha['regular'] = alpha['regular'].replace(' ', '').replace('\r\n', '').replace('\n', '')
            alphas.append(alpha)

    return alphas

def alphas_from_operators():
    wq_session = utils.wq_login()

    with open('operators.json', 'r') as f:
        operators = json.load(f)

    alphas = []

    for i in range(len(operators)):
        operator = operators[i]
        doc = operator['documentation']

        if (doc is None): continue

        resp = wq_session.get(utils.API.base + doc)
        resp = resp.json()

        alphas += alphas_from_page(resp)
    
    print(f'{clr.green}Extracted {len(alphas)} Alphas from Operator Documentations...{clr.white}')

    with open('operator_alphas.json', 'w') as f:
        json.dump(alphas, f, indent = 2)


def alphas_from_tutorials():
    wq_session = utils.wq_login()

    alphas = []
    
    resp = wq_session.get(utils.API.tutorials)
    resp = resp.json()

    links = []

    results = resp['results']

    for result in results:
        pages = result['pages']
        for page in pages:
            links.append(page['id'])
    
    for link in links:
        resp = wq_session.get(utils.API.tutorial + link)
        resp = resp.json()

        alphas += alphas_from_page(resp)
    
    print(f'{clr.green}Extracted {len(alphas)} Alphas from Tutorial Documentations...{clr.white}')

    with open('tutorial_alphas.json', 'w') as f:
        json.dump(alphas, f, indent = 2)


def wq_alphas():
    alphas = []
    wq_session = utils.wq_login()

    payload = {
        'limit': 100,
        'offset': 0,
        'status': 'UNSUBMITTED',
        'order': '-is.sharpe',
        'hidden': 'false'
    }

    while (True):
        r = wq_session.get(utils.API.alphas, params = payload)
        r = r.json()

        alphas += r['results']
        print(f'{clr.yellow}{len(alphas)} Alphas Extracted...{clr.white}')

        if (r['next'] == None):
            break
        else:
            payload['offset'] += 100

    print(f'{clr.green}Total Alphas Extracted: {len(alphas)}{clr.white}')
    with open('wq_alphas.json', 'w') as f:
        json.dump(alphas, f, indent = 2)


def add_performance(alphas):
    wq_session = utils.wq_login()

    for i in range(len(alphas)):

        while True:
            resp = wq_session.get(utils.API.performance(alphas[i]['id']))

            if (resp.text): break

            sleep(2)
        
        resp = resp.json()
        perf = resp['score']['after'] - resp['score']['before']

        print(f'{clr.yellow}Performance added to {i + 1} Alphas{clr.white}')

        alphas[i]['performance'] = perf

    return alphas


def check_submission(alphas):
    wq_session = utils.wq_login()

    for i in range(len(alphas)):
            while True:
                resp = wq_session.get(utils.API.check_submission(alphas[i]['id']))

                if (resp.text): break

                print(f'{clr.cyan}Retrying...{clr.white}')
                sleep(3)
                
            
            resp = resp.json()

            alphas[i]['submittable'] = resp['is']['checks'][6]['result']
            print(f'{clr.yellow}Alpha #{i + 1}: {alphas[i]['id']} : {alphas[i]['submittable']}{clr.white}')

    return alphas

def missed_submissions():
    wq_alphas()

    with open('wq_alphas.json', 'r') as f:
        alphas = json.load(f)
    
    submittable_alphas = utils.submittable_alphas(alphas)
    submittable_alphas_perf = add_performance(submittable_alphas)

    submittable_alphas_perf_pos = []

    for alpha in submittable_alphas_perf:
        if (alpha['performance'] >= 0):
            submittable_alphas_perf_pos.append(alpha)

    print(f'{clr.green}Found {len(submittable_alphas_perf_pos)} Alphas with Positive Performance...{clr.white}')

    submittable_alphas_perf_sorted = sorted(submittable_alphas_perf_pos, key = lambda x: x['performance'], reverse = True)

    submittable_alphas_perf_sorted_checked = check_submission(submittable_alphas_perf_sorted)

    for alpha in submittable_alphas_perf_sorted_checked:
        if (alpha['submittable'] == 'PASS'):
            print(f'{clr.green}Alpha ID: {alpha['id']}, Performance: {alpha['performance']}{clr.white}')