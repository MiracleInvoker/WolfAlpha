from base64 import b64encode
from dotenv import load_dotenv, set_key
import json
import os
import requests
from time import sleep


class API:
    base = 'https://api.worldquantbrain.com'
    auth = base + '/authentication'
    data_sets = base + '/data-sets'
    data_fields = base + '/data-fields'
    operators = base + '/operators'
    alphas = base + '/users/self/alphas'
    tutorials = base + '/tutorials'
    tutorial = base + '/tutorial-pages/'
    simul = base + '/simulations'
    alpha = base + '/alphas/'

    def performance(alpha_id):
        return f'{API.base}/competitions/{simul.Competition}/alphas/{alpha_id}/before-and-after-performance'

    def check_submission(alpha_id):
        return f'{API.base}/alphas/{alpha_id}/check'


class data_set:
    D1 = ['model16', 'model51', 'model53', 'model77', 'option9', 'sentiment1']
    evergreen = ['analyst4', 'fundamental2', 'fundamental6', 'news12',
                 'news18', 'option8', 'pv1', 'pv13', 'socialmedia8', 'socialmedia12']

    analyst4 = "Analyst Estimate Data for Equity"
    fundamental2 = "Report Footnotes"
    fundamental6 = "Company Fundamental Data for Equity"
    news12 = "US News Data"
    news18 = "Ravenpack News Data"
    option8 = "Volatility Data"
    pv1 = "Price Volume Data for Equity"
    pv13 = "Relationship Data for Equity"
    socialmedia8 = "Social Media Data for Equity"
    socialmedia12 = "Sentiment Data for Equity"

    model16 = "Fundamental Scores"
    model51 = "Systematic Risk Metrics"
    model53 = "Creditworthiness Risk Measure Model"
    model77 = "Analysts' Factor Model"
    option9 = "Options Analytics"
    sentiment1 = "Research Sentiment Data"


class simul:
    Competition = 'IQC2025S2'

    Region = ['USA']
    Delay = [0, 1]
    Universe = ['TOP3000', 'TOP1000', 'TOP500', 'TOP200', 'TOPSP500']
    Neutralization = ['NONE', 'MARKET', 'SECTOR', 'INDUSTRY', 'SUBINDUSTRY']
    NaN_Handling = ['ON', 'OFF']


class clr:
    black = '\x1b[0;30m'
    red = '\x1b[0;31m'
    green = '\x1b[0;32m'
    yellow = '\x1b[0;33m'
    blue = '\x1b[0;34m'
    purple = '\x1b[0;35m'
    cyan = '\x1b[0;36m'
    white = '\x1b[0;37m'


load_dotenv()


def wq_login():
    t = os.getenv('t')

    wq_session = requests.Session()

    wq_session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Edge/79.0.1451.30 Safari/537.36'
    })
    wq_session.cookies.update({
        't': t
    })

    resp = wq_session.get(API.auth)

    if (resp.status_code == 204 or resp.json()['token']['expiry'] < 1800):

        print(f'{clr.yellow}logging in...{clr.white}')
        authorization = os.getenv('email') + ':' + os.getenv('pass')
        authorization = b64encode(authorization.encode())

        resp = wq_session.post(
            API.auth, headers={'authorization': 'Basic ' + authorization.decode()})

        t = resp.headers['Set-Cookie'].split(';')[0][2:]
        wq_session.cookies.update({
            't': t
        })

        set_key('.env', 't', t)

    return wq_session


def alpha_json2txt(alpha):
    settings = alpha['settings']
    regular = alpha['regular']

    alpha_txt = f"""
Alpha Expression:
{regular.replace(' ', '').replace('\r\n', '').replace('\n', '')}
Simulation Settings:
Region: {settings['region']}
Universe: {settings['universe']}
Delay: {settings['delay']}
Decay: {settings['decay']}
Neutralization: {settings['neutralization']}
Truncation: {settings['truncation']}
Pasteurization: {settings['pasteurization']}
NaN Handling: {settings['nanHandling']}
"""

    return alpha_txt.strip()


def submittable_alphas(alphas):
    submittable_alphas = []

    for i in range(len(alphas)):
        is_submittable = True
        checks = alphas[i]['is']['checks']

        for j in range(6):
            if (checks[j]['result'] != 'PASS'):
                is_submittable = False
                break

        if (is_submittable):
            submittable_alphas.append(alphas[i])

    print(f'{clr.green}{len(submittable_alphas)} Submittable Alphas Found...{clr.white}')

    return submittable_alphas


class Alpha:
    def simulate(wq_session, alpha):
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

        while True:
            try:
                simul_post = wq_session.post(
                    API.simul,
                    headers={
                        "accept": "application/json;version=2.0",
                        "content-type": "application/json"
                    },
                    data=json.dumps(payload)
                )

                simul_loc = simul_post.headers['Location']
                break

            except Exception as e:
                print(f'{clr.red}Exception in simulate: {e}{clr.white}')


        trial = 0

        while True:
            try:
                simulation = wq_session.get(simul_loc)
                body = simulation.json()

            except Exception as e:
                print(f'{clr.red}Exception in simulate: {e}{clr.white}')
                continue

            trial += 1

            alpha_id = body.get('alpha')

            if (alpha_id is None):
                progress = body.get('progress')

                if (progress is None):
                    print(f'{clr.red}{body}{clr.white}')
                    break

                else:
                    status = f'{clr.yellow}Attempt #{trial} | Alpha Progress: {int(progress * 100):3d}%{clr.white}'
                    status = status.ljust(50)

                    print(status, end='\r', flush=True)

                    sleep(2 * float(simulation.headers['Retry-After']))

            else:
                print('\r' + ' ' * 80 + '\r', end='')
                print(f'{clr.yellow}Simulation Complete! | Alpha ID = {alpha_id}{clr.white}')
                break

        while True:
            try:
                simul_resp = wq_session.get(API.alpha + alpha_id)
                simul_resp = simul_resp.json()
                break
            except Exception as e:
                print(f'{clr.red}Exception in simulate: {e}{clr.white}')

        return alpha_id, simul_resp

    def get_performance(wq_session, alpha_id):
        while True:
            perf_resp = wq_session.get(API.performance(alpha_id))
            if (perf_resp.text):
                try:
                    perf = perf_resp.json()
                    break
                except Exception as e:
                    print(f'{clr.red}Exception in get_performance: {e}{clr.white}')

            print(f'{clr.yellow}Getting Performance...{clr.white}')

            sleep(float(perf_resp.headers['Retry-After']))

        performance = perf['score']['after'] - perf['score']['before']

        return performance

    def is_submittable():
        pass