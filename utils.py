from base64 import b64encode
from dotenv import load_dotenv, set_key
import os
import requests
import sys
from time import sleep
import traceback


erase_line = '\r\x1b[2K'


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
    
    def pnl(alpha_id):
        return f'{API.base}/alphas/{alpha_id}/recordsets/pnl'


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


    return wq_session


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
    def simulate(wq_session, simulation_data):
        while True:
            try:
                simulation_response = wq_session.post(
                    API.simul,
                    json = simulation_data
                )

                simulation_progress_url = simulation_response.headers['Location']
                break

            except Exception:
                print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                sleep(1)

        trial = 0

        while True:
            trial += 1

            simulation_progress = wq_session.get(simulation_progress_url)

            if (simulation_progress.headers.get('Retry-After', 0) == 0):
                try:
                    alpha_id = simulation_progress.json()['alpha']

                    print(f'{erase_line}{clr.yellow}Alpha ID: {alpha_id}{clr.white}', end = '')

                    break

                except Exception:
                    print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                    sleep(1)
                    continue

            progress_percent = 100 * simulation_progress.json()['progress']

            print(f'{erase_line}{clr.yellow}Attempt #{trial} | Simulation Progress: {progress_percent}%{clr.white}', end = '')

            sleep(2 * float(simulation_progress.headers['Retry-After']))

        while True:
            try:
                alpha = wq_session.get(API.alpha + alpha_id)
                alpha = alpha.json()
                break
            except Exception:
                print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                sleep(1)

        while True:
            performance_response = wq_session.get(API.performance(alpha_id))
            if (performance_response.text):
                try:
                    performance_comparison = performance_response.json()
                    break
                except Exception:
                    print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                    sleep(1)

            print(f'{erase_line}{clr.yellow}Alpha ID: {alpha_id} | Getting Performance...{clr.white}', end = '')

            sleep(float(performance_response.headers['Retry-After']))
        
        alpha['Performance Comparison'] = performance_comparison

        score_change = performance_comparison['score']['after'] - performance_comparison['score']['before']
        alpha['Score Change'] = score_change

        print(f'{erase_line}{clr.yellow}Alpha ID: {alpha_id} | Performance: {score_change}{clr.white}')

        return alpha

    def get_performance(wq_session, alpha_id):
        while True:
            perf_resp = wq_session.get(API.performance(alpha_id))
            if (perf_resp.text):
                try:
                    perf = perf_resp.json()
                    break
                except Exception:
                    print(f'{clr.red}{traceback.format_exc()}{clr.white}')
                    sleep(1)

            print(f'{clr.yellow}Getting Performance...{clr.white}')

            sleep(float(perf_resp.headers['Retry-After']))

        performance = perf['score']['after'] - perf['score']['before']

        return performance

    def is_submittable():
        pass

    def to_text(alpha):
        settings = alpha['settings']
        regular = alpha['regular']

        regular = regular.replace(' ', '').replace('\r\n', '').replace('\n', '')

        alpha_txt = f"""
Alpha Expression:
{regular}
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

    def reverse(alpha_expression):

        if (';' in alpha_expression):
            return ';reverse('.join(alpha_expression.rsplit(';', 1)) + ')'
        else:
            return 'reverse(' + alpha_expression + ')'