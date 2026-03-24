from pyvpw import Elm327

PORTNAME = 'COM10'

tool = Elm327(PORTNAME)
tool.send_command('AT S1') # enable spaces
print(tool.send_command('AT RV')[0])

while True:
    command = input('>> ')
    try:
        response = tool.send_command(command)
    except Exception as e:
        print(f'ERROR: {e}')
        continue

    for line in response:
        print(line)