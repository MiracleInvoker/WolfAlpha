import ctypes
import json
import os
import subprocess 
from time import sleep
import utils
import win32gui
import win32con


clr = utils.clr
settings = utils.simul


hwnd_console_raw = ctypes.windll.kernel32.GetConsoleWindow()
target_hwnd = ctypes.windll.user32.GetAncestor(hwnd_console_raw, 3)
wq_session = utils.wq_login()


while True:
    os.system('cls')

    print('Alpha Expression:')
    lines = []
    while True:
        try:
            line = input()
            lines.append(line)
        except KeyboardInterrupt:
            break
    alpha_expression = '\n'.join(lines)
    os.system('cls')

    print(f'Universe {settings.Universe}:')
    universe = settings.Universe[int(input()) - 1]

    print('Delay:')
    delay = int(input())

    print(f'Neutralization: {settings.Neutralization}:')
    neutralization = settings.Neutralization[int(input()) - 1]

    print(f'Decay:')
    decay = int(input())

    print(f'Truncation:')
    truncation = float(input())

    print(f'NaN Handling:')
    nanHandling = input()

    print(f'Pasteurization:')
    pasteurization = input()

    body = {
        'type': 'REGULAR',
        'settings': {
            'nanHandling': nanHandling.upper(),
            'instrumentType': 'EQUITY',
            'delay': delay,
            'universe': universe,
            'truncation': truncation,
            'unitHandling': 'VERIFY',
            'testPeriod': 'P0D',
            'pasteurization': pasteurization.upper(),
            'region': 'USA',
            'language': 'FASTEXPR',
            'decay': decay,
            'neutralization': neutralization,
            'visualization': False
        },
        'regular': alpha_expression
    }

    r = wq_session.post(
        utils.API.simul,
        headers = {
            "accept": "application/json;version=2.0",
            "content-type": "application/json"
        },
        data = json.dumps(body)
    )

    simul = r.headers['Location']

    while True:
        resp = wq_session.get(simul)
        resp_json = resp.json()
        
        try:
            alpha = resp_json['alpha']
            break
        except:
            print(f'{clr.yellow}Alpha Progress: {resp_json['progress'] * 100}%{clr.white}')
            sleep(float(resp.headers['Retry-After']))

    results = wq_session.get(utils.API.alpha + alpha)
    results = results.json()

    while True:
        perf_resp = wq_session.get(utils.API.performance(alpha))
        if (perf_resp.text): break

        print(f'{clr.yellow}Getting Performance...{clr.white}')

        sleep(float(perf_resp.headers['Retry-After']))
    
    perf_resp = perf_resp.json()
    perf = perf_resp['score']['after'] - perf_resp['score']['before']

    insample = results['is']
    checks = insample['checks']

    result = ''

    result += f'Sharpe: {insample['sharpe']}, Fitness: {insample['fitness']}, Turnover: {round(100 * insample['turnover'], 2)}%, Performance: {perf}\n'
    result += f'PnL: {insample['pnl']}, Returns: {round(100 * insample['returns'], 2)}%, Drawdown: {round(100 * insample['drawdown'], 2)}%, Sub Universe Sharpe: {checks[5]['value']}, Margin: {round(10000 * insample['margin'], 2)}‱\n'
    if (checks[4]['result'] == 'FAIL'):
        if (checks[4].get('value')):
            result += f'Weight concentration {round(checks[4]['value'] * 100, 2)}% is above cutoff of {round(checks[4]['limit'] * 100, 2)}% on {checks[4]['date']}.\n'
        else:  
            result += 'Weight is too strongly concentrated or too few instruments are assigned weight.\n'
    if (checks[5]['result'] == 'FAIL'):
        result += f'Sub Universe Sharpe {checks[5]['value']} is not above {checks[5]['limit']}.\n'
    if (checks[6]['result'] == 'UNITS'):
        result += checks[6]['message'].replace('; ', '\n')
        result += '\n'

    win32gui.FlashWindowEx(target_hwnd, win32con.FLASHW_TRAY | win32con.FLASHW_TIMERNOFG, 0, 0)

    while True:
        if win32gui.GetForegroundWindow() == target_hwnd:
            win32gui.FlashWindowEx(target_hwnd, win32con.FLASHW_STOP, 0, 0)
            break
        sleep(0.25)

    subprocess.run("clip", text=True, input = result.strip())