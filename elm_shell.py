import argparse
from pyvpw.device import Elm327

parser = argparse.ArgumentParser()
parser.add_argument('portname')
args = parser.parse_args()

tool = Elm327(args.portname)

while True:
    command = input('>> ')
    try:
        response = tool.send_command(command)
        for line in response:
            print(f'>> {line}')

    except Exception as e:
        print(f'ERROR: {e}')