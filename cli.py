import sys
import os
import argparse
import github_api_client as ga
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('TOKEN')

try:
    parser = argparse.ArgumentParser()
    parser.add_argument('repository_path', nargs='?')
    namespace = parser.parse_args()
except:
    print('--------------------------------------------------------------')
    print('Возникла ошибка, передано слишком много аргументов')
    print('Передайте аргументом ссылку или владельца/имя репозитория')
    print('"https://github.com/Vi-812/git" либо "Vi-812/git"')
    sys.exit()

if not namespace.repository_path:
    print('Передайте аргументом ссылку или владельца/имя репозитория')
    print('"https://github.com/Vi-812/git" либо "Vi-812/git"')
    sys.exit()

instance_api_client = ga.GithubApiClient(token)
return_json = instance_api_client.get_report(namespace.repository_path)

print('---')
print(f'Имя репозитория: {instance_api_client.repo_owner_login}')
print(f'Версия проекта: {instance_api_client.repo_version}')
print(return_json)
print('---')
